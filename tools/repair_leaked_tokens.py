import json
import re
from pathlib import Path


def build_old_mapping(source: str):
    mapping = {}
    idx = 0

    def repl_curly(match):
        nonlocal idx
        key = f"__TK_{idx}__"
        mapping[key] = match.group(0)
        idx += 1
        return key

    def repl_html(match):
        nonlocal idx
        key = f"__TK_{idx}__"
        mapping[key] = match.group(0)
        idx += 1
        return key

    def repl_square(match):
        nonlocal idx
        key = f"__TK_{idx}__"
        mapping[key] = match.group(0)
        idx += 1
        return key

    s = re.sub(r"\{[^{}]+\}", repl_curly, source)
    s = re.sub(r"<[^>]+>", repl_html, s)
    s = re.sub(r"\[[^\]]+\]", repl_square, s)
    return mapping


base = Path("d:/fds/work/Crimson Desert Localization Tool-103-1-2-1774602780")
sid_to_source_path = base / "vertex_batch/input/sid_to_source.json"
sid_to_vi_path = base / "vertex_batch/merged/sid_to_vi.json"
report_path = base / "vertex_batch/review/repair_leaked_tokens_report.json"

sid_to_source = json.loads(sid_to_source_path.read_text(encoding="utf-8"))
sid_to_vi = json.loads(sid_to_vi_path.read_text(encoding="utf-8"))

updated = 0
unresolved = []

for sid, source in sid_to_source.items():
    if sid not in sid_to_vi:
        continue
    t = str(sid_to_vi[sid])
    if "__TK_" not in t:
        continue
    mapping = build_old_mapping(str(source))
    new_t = t
    for k, v in mapping.items():
        new_t = new_t.replace(k, v)
    if "__TK_" in new_t:
        unresolved.append({"sid": sid, "translation": new_t})
    if new_t != t:
        sid_to_vi[sid] = new_t
        updated += 1

sid_to_vi_path.write_text(json.dumps(sid_to_vi, ensure_ascii=False, indent=2), encoding="utf-8")
report = {
    "updated_sid_count": updated,
    "unresolved_count": len(unresolved),
    "unresolved_sample": unresolved[:50],
}
report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps(report, ensure_ascii=True, indent=2))
