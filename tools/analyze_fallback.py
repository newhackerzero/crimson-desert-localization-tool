import json
from collections import Counter, defaultdict
from pathlib import Path


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def iter_jsonl(path: Path):
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            yield json.loads(line)


def parse_request_sids(line_obj):
    request = line_obj.get("request", {})
    contents = request.get("contents", [])
    if not contents:
        return []
    parts = contents[0].get("parts", [])
    if not parts:
        return []
    text = parts[0].get("text", "")
    if "Dữ liệu:\n" not in text:
        return []
    payload = text.split("Dữ liệu:\n", 1)[1]
    arr = json.loads(payload)
    return [x.get("sid") for x in arr if isinstance(x, dict) and x.get("sid")]


def main():
    base = Path("d:/fds/work/Crimson Desert Localization Tool-103-1-2-1774602780")
    merged_path = base / "vertex_batch/merged/localizationstring_vi.paloc.json"
    key_to_sid_path = base / "vertex_batch/input/key_to_sid.json"
    sid_to_source_path = base / "vertex_batch/input/sid_to_source.json"
    sid_to_vi_path = base / "vertex_batch/merged/sid_to_vi.json"
    invalid_rows_path = base / "vertex_batch/logs/invalid_rows.jsonl"
    predictions_path = base / "vertex_batch/output/run_001/predictions.jsonl"
    out_dir = base / "vertex_batch/review"
    out_dir.mkdir(parents=True, exist_ok=True)

    merged = load_json(merged_path)
    entries = merged["entries"]
    key_to_sid = load_json(key_to_sid_path)
    sid_to_source = load_json(sid_to_source_path)
    sid_to_vi = load_json(sid_to_vi_path)

    line_to_sids = {}
    with predictions_path.open("r", encoding="utf-8") as f:
        for line_no, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                line_obj = json.loads(line)
                line_to_sids[line_no] = parse_request_sids(line_obj)
            except Exception:
                line_to_sids[line_no] = []

    sid_reason = defaultdict(list)
    for obj in iter_jsonl(invalid_rows_path):
        reason = obj.get("reason", "unknown")
        sid = obj.get("sid")
        if sid:
            sid_reason[str(sid)].append(reason)
            continue
        line_no = obj.get("line")
        if isinstance(line_no, int):
            for s in line_to_sids.get(line_no, []):
                sid_reason[str(s)].append(reason)

    priority = {
        "token_mismatch": 100,
        "duplicate_conflict": 90,
        "parse_error": 80,
        "status_error": 70,
        "unknown_sid": 60,
        "empty_source": 50,
        "no_output_for_sid": 10,
    }

    def pick_reason(sid):
        if sid in sid_to_vi:
            return "translated"
        reasons = sid_reason.get(sid, [])
        if reasons:
            reasons.sort(key=lambda x: priority.get(x, 1), reverse=True)
            return reasons[0]
        if sid_to_source.get(sid, "") == "":
            return "empty_source"
        return "no_output_for_sid"

    fallback_rows = []
    reason_counter_key = Counter()
    reason_counter_sid = Counter()
    seen_sid = set()
    for e in entries:
        key = str(e.get("key", ""))
        sid = str(key_to_sid.get(key, ""))
        if not sid or sid in sid_to_vi:
            continue
        reason = pick_reason(sid)
        row = {
            "key": key,
            "sid": sid,
            "marker": e.get("marker", ""),
            "reason": reason,
            "original": e.get("original", ""),
            "translation": e.get("translation", ""),
        }
        fallback_rows.append(row)
        reason_counter_key[reason] += 1
        if sid not in seen_sid:
            reason_counter_sid[reason] += 1
            seen_sid.add(sid)

    fallback_entries_path = out_dir / "fallback_entries.jsonl"
    with fallback_entries_path.open("w", encoding="utf-8") as f:
        for row in fallback_rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")

    fallback_sample_path = out_dir / "fallback_sample_200.json"
    fallback_sample_path.write_text(
        json.dumps(fallback_rows[:200], ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    summary = {
        "entries_total": len(entries),
        "fallback_keys_total": len(fallback_rows),
        "fallback_key_ratio": round(len(fallback_rows) / len(entries), 6) if entries else 0.0,
        "unique_sid_total": len(sid_to_source),
        "translated_sid_total": len(sid_to_vi),
        "fallback_sid_total": len(sid_to_source) - len(sid_to_vi),
        "fallback_reasons_by_key": dict(reason_counter_key),
        "fallback_reasons_by_sid": dict(reason_counter_sid),
        "output_files": {
            "fallback_entries_jsonl": str(fallback_entries_path),
            "fallback_sample_200_json": str(fallback_sample_path),
        },
    }
    summary_path = out_dir / "fallback_summary.json"
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
