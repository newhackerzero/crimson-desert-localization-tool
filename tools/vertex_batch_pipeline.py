import argparse
import json
import re
from collections import Counter
from pathlib import Path


def read_json(path: Path):
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def write_json(path: Path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def read_jsonl(path: Path):
    with path.open("r", encoding="utf-8") as f:
        for line_number, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            yield line_number, json.loads(line)


def write_jsonl(path: Path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def build_sid(index: int, width: int = 6) -> str:
    return f"s{index:0{width}d}"


def extract_tokens(text: str):
    return {
        "curly": Counter(re.findall(r"\{[^{}]+\}", text)),
        "html": Counter(re.findall(r"<[^>]+>", text)),
        "square": Counter(re.findall(r"\[[^\]]+\]", text)),
    }


def tokens_match(source: str, translated: str):
    a = extract_tokens(source)
    b = extract_tokens(translated)
    return a == b


def cmd_extract(args):
    source_path = Path(args.source)
    out_dir = Path(args.out_dir)
    data = read_json(source_path)
    entries = data.get("entries", [])

    text_to_sid = {}
    key_to_sid = {}
    sid_to_source = {}

    for entry in entries:
        key = str(entry.get("key", ""))
        source_text = str(entry.get("original", ""))
        sid = text_to_sid.get(source_text)
        if sid is None:
            sid = build_sid(len(text_to_sid) + 1, args.sid_width)
            text_to_sid[source_text] = sid
            sid_to_source[sid] = source_text
        key_to_sid[key] = sid

    write_json(out_dir / "key_to_sid.json", key_to_sid)
    write_json(out_dir / "sid_to_source.json", sid_to_source)
    stats = {
        "entries_count": len(entries),
        "unique_source_count": len(sid_to_source),
        "dedupe_saved_count": len(entries) - len(sid_to_source),
        "dedupe_saved_ratio": round((len(entries) - len(sid_to_source)) / len(entries), 6) if entries else 0.0,
        "empty_source_count": sum(1 for text in sid_to_source.values() if text == ""),
    }
    write_json(out_dir / "extract_stats.json", stats)
    print(json.dumps(stats, ensure_ascii=False, indent=2))


def chunk_items(items, batch_size: int, max_chars: int):
    chunks = []
    current = []
    current_chars = 0
    for item in items:
        item_chars = len(item["text"])
        if current and (len(current) >= batch_size or current_chars + item_chars > max_chars):
            chunks.append(current)
            current = []
            current_chars = 0
        current.append(item)
        current_chars += item_chars
    if current:
        chunks.append(current)
    return chunks


def build_request_row(items, temperature, top_p, max_output_tokens):
    payload = json.dumps(items, ensure_ascii=False, separators=(",", ":"))
    user_text = (
        "Trả về JSON hợp lệ theo schema "
        "{\"items\":[{\"sid\":\"string\",\"translation\":\"string\"}]}. "
        "Dịch EN->VI theo ngữ cảnh game fantasy, giữ nguyên token đặc biệt, tag HTML và tag trong ngoặc vuông. "
        "Không thêm giải thích. Dữ liệu:\n"
        + payload
    )
    return {
        "request": {
            "systemInstruction": {
                "parts": [
                    {
                        "text": (
                            "Bạn là biên dịch viên game EN->VI. Giữ nguyên 100% các token dạng {..}, <..>, [..], "
                            "không thay đổi số, ký hiệu, và định dạng."
                        )
                    }
                ]
            },
            "contents": [
                {
                    "role": "user",
                    "parts": [{"text": user_text}],
                }
            ],
            "generationConfig": {
                "temperature": temperature,
                "topP": top_p,
                "maxOutputTokens": max_output_tokens,
                "responseMimeType": "application/json",
            },
        }
    }


def cmd_build_batch(args):
    sid_to_source = read_json(Path(args.sid_to_source))
    items = []
    for sid, text in sid_to_source.items():
        if args.skip_empty and text == "":
            continue
        items.append({"sid": sid, "text": text})

    chunks = chunk_items(items, args.batch_size, args.max_chars)
    rows = []
    manifest = []
    for i, chunk in enumerate(chunks, 1):
        rows.append(build_request_row(chunk, args.temperature, args.top_p, args.max_output_tokens))
        manifest.append(
            {
                "batch_index": i,
                "items_count": len(chunk),
                "sids": [x["sid"] for x in chunk],
            }
        )

    out_jsonl = Path(args.output_jsonl)
    write_jsonl(out_jsonl, rows)
    write_json(Path(args.manifest_json), {"batches": manifest})
    stats = {
        "input_items_count": len(items),
        "batches_count": len(rows),
        "batch_size": args.batch_size,
        "max_chars": args.max_chars,
        "skip_empty": args.skip_empty,
    }
    write_json(Path(args.stats_json), stats)
    print(json.dumps(stats, ensure_ascii=False, indent=2))


def extract_response_text(row):
    response = row.get("response", {})
    candidates = response.get("candidates", [])
    if not candidates:
        return ""
    content = candidates[0].get("content", {})
    parts = content.get("parts", [])
    texts = []
    for part in parts:
        text = part.get("text")
        if isinstance(text, str):
            texts.append(text)
    return "".join(texts).strip()


def try_parse_items(text: str):
    try:
        data = json.loads(text)
        if isinstance(data, dict) and isinstance(data.get("items"), list):
            return data["items"]
    except Exception:
        pass
    m = re.search(r"\{[\s\S]*\}", text)
    if not m:
        return None
    try:
        data = json.loads(m.group(0))
        if isinstance(data, dict) and isinstance(data.get("items"), list):
            return data["items"]
    except Exception:
        return None
    return None


def cmd_parse_output(args):
    sid_to_source = read_json(Path(args.sid_to_source))
    output_dir = Path(args.output_dir)
    jsonl_files = sorted(output_dir.rglob("*.jsonl"))
    sid_to_vi = {}
    invalid_rows = []
    status_fail_count = 0
    parse_fail_count = 0
    token_fail_count = 0
    duplicate_conflict_count = 0

    for file_path in jsonl_files:
        for line_number, row in read_jsonl(file_path):
            status = row.get("status", "")
            if status:
                status_fail_count += 1
                invalid_rows.append(
                    {
                        "file": str(file_path),
                        "line": line_number,
                        "reason": "status_error",
                        "status": status,
                    }
                )
                continue

            text = extract_response_text(row)
            items = try_parse_items(text)
            if items is None:
                parse_fail_count += 1
                invalid_rows.append(
                    {
                        "file": str(file_path),
                        "line": line_number,
                        "reason": "parse_error",
                        "response_text": text,
                    }
                )
                continue

            for item in items:
                sid = str(item.get("sid", ""))
                translation = str(item.get("translation", ""))
                source = sid_to_source.get(sid)
                if source is None:
                    invalid_rows.append(
                        {
                            "file": str(file_path),
                            "line": line_number,
                            "reason": "unknown_sid",
                            "sid": sid,
                        }
                    )
                    continue

                if not tokens_match(source, translation):
                    token_fail_count += 1
                    invalid_rows.append(
                        {
                            "file": str(file_path),
                            "line": line_number,
                            "reason": "token_mismatch",
                            "sid": sid,
                            "source": source,
                            "translation": translation,
                        }
                    )
                    continue

                prev = sid_to_vi.get(sid)
                if prev is not None and prev != translation:
                    duplicate_conflict_count += 1
                    invalid_rows.append(
                        {
                            "file": str(file_path),
                            "line": line_number,
                            "reason": "duplicate_conflict",
                            "sid": sid,
                            "previous": prev,
                            "current": translation,
                        }
                    )
                    continue
                sid_to_vi[sid] = translation

    write_json(Path(args.sid_to_vi), sid_to_vi)
    write_jsonl(Path(args.invalid_rows_jsonl), invalid_rows)
    stats = {
        "jsonl_files_count": len(jsonl_files),
        "translated_sid_count": len(sid_to_vi),
        "source_sid_count": len(sid_to_source),
        "coverage_ratio": round(len(sid_to_vi) / len(sid_to_source), 6) if sid_to_source else 0.0,
        "status_fail_count": status_fail_count,
        "parse_fail_count": parse_fail_count,
        "token_fail_count": token_fail_count,
        "duplicate_conflict_count": duplicate_conflict_count,
        "invalid_rows_count": len(invalid_rows),
    }
    write_json(Path(args.stats_json), stats)
    print(json.dumps(stats, ensure_ascii=False, indent=2))


def cmd_merge(args):
    paloc = read_json(Path(args.paloc_json))
    key_to_sid = read_json(Path(args.key_to_sid))
    sid_to_vi = read_json(Path(args.sid_to_vi))

    entries = paloc.get("entries", [])
    updated_count = 0
    fallback_count = 0
    missing_sid_count = 0

    for entry in entries:
        key = str(entry.get("key", ""))
        sid = key_to_sid.get(key)
        if sid is None:
            missing_sid_count += 1
            fallback_count += 1
            continue
        translated = sid_to_vi.get(sid)
        if translated is None:
            fallback_count += 1
            if args.fallback == "original":
                entry["translation"] = str(entry.get("original", ""))
            continue
        entry["translation"] = translated
        updated_count += 1

    write_json(Path(args.output_json), paloc)
    stats = {
        "entries_count": len(entries),
        "updated_count": updated_count,
        "fallback_count": fallback_count,
        "missing_sid_count": missing_sid_count,
        "updated_ratio": round(updated_count / len(entries), 6) if entries else 0.0,
    }
    write_json(Path(args.stats_json), stats)
    print(json.dumps(stats, ensure_ascii=False, indent=2))


def cmd_qa(args):
    sid_to_source = read_json(Path(args.sid_to_source))
    sid_to_vi = read_json(Path(args.sid_to_vi))
    key_to_sid = read_json(Path(args.key_to_sid))
    placeholder_mismatch_count = 0

    for sid, source in sid_to_source.items():
        translated = sid_to_vi.get(sid)
        if translated is None:
            continue
        if not tokens_match(source, translated):
            placeholder_mismatch_count += 1

    key_translated_count = 0
    for sid in key_to_sid.values():
        if sid in sid_to_vi:
            key_translated_count += 1

    stats = {
        "sid_source_count": len(sid_to_source),
        "sid_translated_count": len(sid_to_vi),
        "sid_coverage_ratio": round(len(sid_to_vi) / len(sid_to_source), 6) if sid_to_source else 0.0,
        "key_count": len(key_to_sid),
        "translated_key_count": key_translated_count,
        "translated_key_ratio": round(key_translated_count / len(key_to_sid), 6) if key_to_sid else 0.0,
        "placeholder_mismatch_count": placeholder_mismatch_count,
    }
    write_json(Path(args.stats_json), stats)
    print(json.dumps(stats, ensure_ascii=False, indent=2))


def cmd_write_job_request(args):
    body = {
        "displayName": args.display_name,
        "model": args.model,
        "inputConfig": {
            "instancesFormat": "jsonl",
            "gcsSource": {"uris": [args.input_uri]},
        },
        "outputConfig": {
            "predictionsFormat": "jsonl",
            "gcsDestination": {"outputUriPrefix": args.output_uri_prefix},
        },
    }
    write_json(Path(args.output_json), body)
    print(json.dumps(body, ensure_ascii=False, indent=2))


def make_parser():
    parser = argparse.ArgumentParser(prog="vertex_batch_pipeline")
    sub = parser.add_subparsers(dest="command", required=True)

    p_extract = sub.add_parser("extract")
    p_extract.add_argument("--source", required=True)
    p_extract.add_argument("--out-dir", required=True)
    p_extract.add_argument("--sid-width", type=int, default=6)
    p_extract.set_defaults(func=cmd_extract)

    p_build = sub.add_parser("build-batch")
    p_build.add_argument("--sid-to-source", required=True)
    p_build.add_argument("--output-jsonl", required=True)
    p_build.add_argument("--manifest-json", required=True)
    p_build.add_argument("--stats-json", required=True)
    p_build.add_argument("--batch-size", type=int, default=40)
    p_build.add_argument("--max-chars", type=int, default=8000)
    p_build.add_argument("--temperature", type=float, default=0.0)
    p_build.add_argument("--top-p", type=float, default=0.95)
    p_build.add_argument("--max-output-tokens", type=int, default=4096)
    p_build.add_argument("--skip-empty", action="store_true")
    p_build.set_defaults(func=cmd_build_batch)

    p_parse = sub.add_parser("parse-output")
    p_parse.add_argument("--sid-to-source", required=True)
    p_parse.add_argument("--output-dir", required=True)
    p_parse.add_argument("--sid-to-vi", required=True)
    p_parse.add_argument("--invalid-rows-jsonl", required=True)
    p_parse.add_argument("--stats-json", required=True)
    p_parse.set_defaults(func=cmd_parse_output)

    p_merge = sub.add_parser("merge")
    p_merge.add_argument("--paloc-json", required=True)
    p_merge.add_argument("--key-to-sid", required=True)
    p_merge.add_argument("--sid-to-vi", required=True)
    p_merge.add_argument("--output-json", required=True)
    p_merge.add_argument("--stats-json", required=True)
    p_merge.add_argument("--fallback", choices=["original", "keep"], default="original")
    p_merge.set_defaults(func=cmd_merge)

    p_qa = sub.add_parser("qa")
    p_qa.add_argument("--sid-to-source", required=True)
    p_qa.add_argument("--sid-to-vi", required=True)
    p_qa.add_argument("--key-to-sid", required=True)
    p_qa.add_argument("--stats-json", required=True)
    p_qa.set_defaults(func=cmd_qa)

    p_req = sub.add_parser("write-job-request")
    p_req.add_argument("--display-name", required=True)
    p_req.add_argument("--model", required=True)
    p_req.add_argument("--input-uri", required=True)
    p_req.add_argument("--output-uri-prefix", required=True)
    p_req.add_argument("--output-json", required=True)
    p_req.set_defaults(func=cmd_write_job_request)

    return parser


def main():
    parser = make_parser()
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
