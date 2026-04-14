import json
import re
from collections import Counter
from pathlib import Path


def protect(text: str):
    mapping = {}
    idx = 0

    def repl(match):
        nonlocal idx
        k = f"__P_{idx}__"
        mapping[k] = match.group(0)
        idx += 1
        return k

    out = text
    for pattern in (r"\{[^{}]+\}", r"<[^>]+>", r"%(?:\d+\$)?[sdifxX]"):
        out = re.sub(pattern, repl, out)
    return out, mapping


def restore(text: str, mapping):
    out = text
    for k, v in mapping.items():
        out = out.replace(k, v)
    return out


base = Path("d:/fds/work/Crimson Desert Localization Tool-103-1-2-1774602780")
sid_to_vi_path = base / "vertex_batch/merged/sid_to_vi.json"
report_path = base / "vertex_batch/review/term_unify_report.json"

sid_to_vi = json.loads(sid_to_vi_path.read_text(encoding="utf-8"))
counts = Counter()
updated = 0

rules = [
    (r"\brequired skill\b", "Kỹ năng yêu cầu", "required_skill"),
    (r"\bchiêu thức\b", "Kỹ năng", "chieu_thuc"),
    (r"\byêu cầu kỹ năng\b", "Kỹ năng yêu cầu", "yeu_cau_ky_nang"),
    (r"\bkỹ năng cần thiết\b", "Kỹ năng yêu cầu", "ky_nang_can_thiet"),
    (r"\bphòng ngự\b", "phòng thủ", "phong_ngu"),
    (r"\bbạo kích\b", "chí mạng", "bao_kich"),
    (r"\bstamina\b", "Thể lực", "stamina"),
    (r"\btinh lực\b", "Thể lực", "tinh_luc"),
    (r"\battack\b", "tấn công", "attack_en"),
    (r"\bdefense\b", "phòng thủ", "defense_en"),
    (r"\bcritical\b", "chí mạng", "critical_en"),
    (r"(?<!thành )(?<!tấn )\bcông\b", "tấn công", "cong_to_tan_cong"),
]

for sid, text in sid_to_vi.items():
    t = str(text)
    if not t:
        continue
    protected, mapping = protect(t)
    before = protected
    for pattern, repl, name in rules:
        protected, n = re.subn(pattern, repl, protected, flags=re.IGNORECASE)
        counts[name] += n
    after = restore(protected, mapping)
    if after != t:
        sid_to_vi[sid] = after
        updated += 1

sid_to_vi_path.write_text(json.dumps(sid_to_vi, ensure_ascii=False, indent=2), encoding="utf-8")
report = {"updated_sid_count": updated, "rules_applied": dict(counts)}
report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps(report, ensure_ascii=True, indent=2))
