import json
import re
from collections import Counter
from pathlib import Path


def protect_tokens(text: str):
    mapping = {}
    idx = 0

    def repl(match):
        nonlocal idx
        key = f"__TK_{idx}__"
        mapping[key] = match.group(0)
        idx += 1
        return key

    out = text
    for pattern in (r"\[[^\]]+\]", r"\{[^{}]+\}", r"<[^>]+>"):
        out = re.sub(pattern, repl, out)
    return out, mapping


def restore_tokens(text: str, mapping):
    out = text
    for k, v in mapping.items():
        out = out.replace(k, v)
    return out


def apply_rule(text: str, pattern: str, repl: str):
    new_text, n = re.subn(pattern, repl, text, flags=re.IGNORECASE)
    return new_text, n


base = Path("d:/fds/work/Crimson Desert Localization Tool-103-1-2-1774602780")
sid_to_source_path = base / "vertex_batch/input/sid_to_source.json"
sid_to_vi_path = base / "vertex_batch/merged/sid_to_vi.json"
out_report_path = base / "vertex_batch/review/glossary_normalize_report.json"

sid_to_source = json.loads(sid_to_source_path.read_text(encoding="utf-8"))
sid_to_vi = json.loads(sid_to_vi_path.read_text(encoding="utf-8"))

rule_counter = Counter()
updated_sid_count = 0

for sid, source in sid_to_source.items():
    if sid not in sid_to_vi:
        continue
    translation = str(sid_to_vi[sid])
    if not translation:
        continue

    protected, token_map = protect_tokens(translation)
    before = protected
    src_lower = str(source).lower()

    protected, n = apply_rule(protected, r"\bchiêu thức\b", "Kỹ năng")
    rule_counter["chiêu_thuc_to_ky_nang"] += n

    protected, n = apply_rule(protected, r"\brequired skill\b", "Kỹ năng yêu cầu")
    rule_counter["required_skill_en_to_vi"] += n
    protected, n = apply_rule(protected, r"\byêu cầu kỹ năng\b", "Kỹ năng yêu cầu")
    rule_counter["yeu_cau_ky_nang_to_ky_nang_yeu_cau"] += n
    protected, n = apply_rule(protected, r"\bkỹ năng cần thiết\b", "Kỹ năng yêu cầu")
    rule_counter["ky_nang_can_thiet_to_ky_nang_yeu_cau"] += n

    if "skill" in src_lower:
        protected, n = apply_rule(protected, r"\bskill\b", "Kỹ năng")
        rule_counter["skill_en_to_ky_nang"] += n

    if "stamina" in src_lower:
        protected, n = apply_rule(protected, r"\bstamina\b", "Thể lực")
        rule_counter["stamina_en_to_the_luc"] += n
        protected, n = apply_rule(protected, r"\btinh lực\b", "Thể lực")
        rule_counter["tinh_luc_to_the_luc"] += n

    if "attack" in src_lower:
        protected, n = apply_rule(protected, r"\battack\b", "tấn công")
        rule_counter["attack_en_to_tan_cong"] += n
        protected, n = apply_rule(protected, r"(?<!thành )(?<!tấn )\bcông\b", "tấn công")
        rule_counter["cong_to_tan_cong_contextual"] += n

    if "defense" in src_lower:
        protected, n = apply_rule(protected, r"\bphòng ngự\b", "phòng thủ")
        rule_counter["phong_ngu_to_phong_thu"] += n
        protected, n = apply_rule(protected, r"\bdefense\b", "phòng thủ")
        rule_counter["defense_en_to_phong_thu"] += n

    if "critical" in src_lower:
        protected, n = apply_rule(protected, r"\bbạo kích\b", "chí mạng")
        rule_counter["bao_kich_to_chi_mang"] += n
        protected, n = apply_rule(protected, r"\bcritical\b", "chí mạng")
        rule_counter["critical_en_to_chi_mang"] += n

    restored = restore_tokens(protected, token_map)
    if restored != translation:
        sid_to_vi[sid] = restored
        updated_sid_count += 1

sid_to_vi_path.write_text(json.dumps(sid_to_vi, ensure_ascii=False, indent=2), encoding="utf-8")

report = {
    "updated_sid_count": updated_sid_count,
    "rules_applied": dict(rule_counter),
}
out_report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps(report, ensure_ascii=True, indent=2))
