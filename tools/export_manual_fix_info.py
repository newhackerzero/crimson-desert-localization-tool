import json
from pathlib import Path


base = Path("d:/fds/work/Crimson Desert Localization Tool-103-1-2-1774602780")
key_to_sid = json.loads((base / "vertex_batch/input/key_to_sid.json").read_text(encoding="utf-8"))
sid_to_source = json.loads((base / "vertex_batch/input/sid_to_source.json").read_text(encoding="utf-8"))

manual_updates = {
    "s028363",
    "s031447",
    "s036281",
    "s039876",
    "s042861",
    "s046109",
    "s046549",
    "s050951",
    "s058918",
    "s062490",
    "s070785",
    "s073580",
    "s074703",
    "s076792",
    "s077585",
    "s084188",
    "s085540",
    "s087081",
    "s090543",
}

sid_to_keys = {sid: [] for sid in manual_updates}
for key, sid in key_to_sid.items():
    if sid in sid_to_keys:
        sid_to_keys[sid].append(key)
for sid in sid_to_keys:
    sid_to_keys[sid].sort(key=lambda x: (0, int(x)) if x.isdigit() else (1, x))

flat_keys = []
for sid in sorted(sid_to_keys):
    for key in sid_to_keys[sid]:
        flat_keys.append({"sid": sid, "key": key})

missing_sid = None
for sid, text in sid_to_source.items():
    if text == "":
        missing_sid = sid
        break

missing_sid_keys = [k for k, sid in key_to_sid.items() if sid == missing_sid]
missing_sid_keys.sort(key=lambda x: (0, int(x)) if x.isdigit() else (1, x))

out_dir = base / "vertex_batch/review"
out_dir.mkdir(parents=True, exist_ok=True)

manual_out = {
    "manual_fixed_sid_count": len(manual_updates),
    "manual_fixed_key_count": len(flat_keys),
    "sid_to_keys": sid_to_keys,
    "flat_keys": flat_keys,
}
(out_dir / "manual_fix_19_keys.json").write_text(json.dumps(manual_out, ensure_ascii=False, indent=2), encoding="utf-8")

missing_out = {
    "missing_sid": missing_sid,
    "missing_sid_source": sid_to_source.get(missing_sid),
    "missing_sid_key_count": len(missing_sid_keys),
    "missing_sid_keys": missing_sid_keys,
}
(out_dir / "missing_sid_details.json").write_text(json.dumps(missing_out, ensure_ascii=False, indent=2), encoding="utf-8")

print(json.dumps({
    "manual_fixed_sid_count": len(manual_updates),
    "manual_fixed_key_count": len(flat_keys),
    "missing_sid": missing_sid,
    "missing_sid_key_count": len(missing_sid_keys),
}, ensure_ascii=False, indent=2))
