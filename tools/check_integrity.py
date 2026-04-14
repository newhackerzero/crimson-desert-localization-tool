import json
from pathlib import Path


src_path = Path("d:/fds/work/Crimson Desert Localization Tool-103-1-2-1774602780/PALOC_Export/localizationstring_eng.paloc.json")
vi_path = Path("d:/fds/work/Crimson Desert Localization Tool-103-1-2-1774602780/vertex_batch/merged/localizationstring_vi.paloc.json")
out_path = Path("d:/fds/work/Crimson Desert Localization Tool-103-1-2-1774602780/vertex_batch/review/integrity_check.json")

src = json.loads(src_path.read_text(encoding="utf-8"))
vi = json.loads(vi_path.read_text(encoding="utf-8"))

src_entries = src.get("entries", [])
vi_entries = vi.get("entries", [])

src_keys = [str(e.get("key", "")) for e in src_entries]
vi_keys = [str(e.get("key", "")) for e in vi_entries]

src_key_set = set(src_keys)
vi_key_set = set(vi_keys)

missing_in_vi = sorted(src_key_set - vi_key_set)
extra_in_vi = sorted(vi_key_set - src_key_set)

src_map = {str(e.get("key", "")): e for e in src_entries}
vi_map = {str(e.get("key", "")): e for e in vi_entries}

marker_mismatch = 0
original_mismatch = 0
schema_mismatch = 0
for k in src_key_set & vi_key_set:
    s = src_map[k]
    t = vi_map[k]
    if set(t.keys()) != {"marker", "key", "original", "translation"}:
        schema_mismatch += 1
    if str(s.get("marker", "")) != str(t.get("marker", "")):
        marker_mismatch += 1
    if str(s.get("original", "")) != str(t.get("original", "")):
        original_mismatch += 1

report = {
    "src_entries_count": len(src_entries),
    "vi_entries_count": len(vi_entries),
    "entries_count_equal": len(src_entries) == len(vi_entries),
    "src_unique_keys": len(src_key_set),
    "vi_unique_keys": len(vi_key_set),
    "key_set_equal": src_key_set == vi_key_set,
    "missing_in_vi_count": len(missing_in_vi),
    "extra_in_vi_count": len(extra_in_vi),
    "marker_mismatch_count": marker_mismatch,
    "original_mismatch_count": original_mismatch,
    "schema_mismatch_count": schema_mismatch,
    "metadata_equal": src.get("metadata") == vi.get("metadata"),
    "missing_in_vi_sample": missing_in_vi[:20],
    "extra_in_vi_sample": extra_in_vi[:20],
}

out_path.parent.mkdir(parents=True, exist_ok=True)
out_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps(report, ensure_ascii=False, indent=2))
