import argparse
import json
import os
import re
import subprocess
import time
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter
from pathlib import Path


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def iter_jsonl(path: Path):
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            yield json.loads(line)


def write_jsonl(path: Path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def extract_tokens(text: str):
    return {
        "curly": Counter(re.findall(r"\{[^{}]+\}", text)),
        "html": Counter(re.findall(r"<[^>]+>", text)),
        "square": Counter(re.findall(r"\[[^\]]+\]", text)),
    }


def tokens_match(source: str, translated: str):
    return extract_tokens(source) == extract_tokens(translated)


def protect_tokens(text: str):
    mapping = {}
    idx = 0

    def repl(match):
        nonlocal idx
        key = f"__TK_{idx}__"
        mapping[key] = match.group(0)
        idx += 1
        return key

    patterns = [r"\{[^{}]+\}", r"<[^>]+>", r"\[[^\]]+\]"]
    protected = text
    for p in patterns:
        protected = re.sub(p, repl, protected)
    return protected, mapping


def restore_tokens(text: str, mapping):
    out = text
    for k, v in mapping.items():
        out = out.replace(k, v)
    return out


def parse_items_json(text: str):
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


def call_vertex_generate(api_key, access_token, project_id, location, model, prompt):
    host = "aiplatform.googleapis.com" if location == "global" else f"{location}-aiplatform.googleapis.com"
    path = f"/v1/projects/{project_id}/locations/{location}/publishers/google/models/{model}:generateContent"
    if api_key:
        qs = urllib.parse.urlencode({"key": api_key})
        url = f"https://{host}{path}?{qs}"
    else:
        url = f"https://{host}{path}"
    body = {
        "systemInstruction": {
            "parts": [
                {
                    "text": "Bạn là biên dịch viên game EN->VI. Bắt buộc giữ nguyên token dạng __TK_n__, không thêm token mới."
                }
            ]
        },
        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": 0,
            "topP": 0.95,
            "maxOutputTokens": 4096,
            "responseMimeType": "application/json",
        },
    }
    headers = {"Content-Type": "application/json; charset=utf-8"}
    if (not api_key) and access_token:
        headers["Authorization"] = f"Bearer {access_token}"
    req = urllib.request.Request(
        url=url,
        data=json.dumps(body, ensure_ascii=False).encode("utf-8"),
        headers=headers,
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            payload = resp.read().decode("utf-8")
            return json.loads(payload), None
    except urllib.error.HTTPError as e:
        raw = e.read().decode("utf-8", errors="ignore")
        return None, f"http_error:{e.code}:{raw}"
    except Exception as e:
        return None, f"exception:{e}"


def extract_text_from_response(resp):
    candidates = resp.get("candidates", [])
    if not candidates:
        return ""
    content = candidates[0].get("content", {})
    parts = content.get("parts", [])
    texts = []
    for p in parts:
        t = p.get("text")
        if isinstance(t, str):
            texts.append(t)
    return "".join(texts).strip()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-dir", required=True)
    parser.add_argument("--api-key-env", default="VERTEX_API_KEY")
    parser.add_argument("--access-token", default="")
    parser.add_argument("--batch-size", type=int, default=30)
    parser.add_argument("--sleep-ms", type=int, default=150)
    parser.add_argument("--max-sids", type=int, default=0)
    args = parser.parse_args()

    api_key = os.getenv(args.api_key_env, "").strip()
    access_token = ""
    auth_mode = "api_key"
    if not api_key:
        auth_mode = "access_token"
        access_token = str(args.access_token).strip()
        if not access_token:
            try:
                access_token = subprocess.check_output(["gcloud", "auth", "print-access-token"], text=True).strip()
            except Exception as e:
                raise RuntimeError(f"Thiếu API key ({args.api_key_env}) và không lấy được access token: {e}")
        if not access_token:
            raise RuntimeError(f"Thiếu API key ({args.api_key_env}) và access token rỗng")

    base = Path(args.base_dir)
    config = read_json(base / "vertex_batch/config.json")
    project_id = str(config.get("project_id", "")).strip()
    location = str(config.get("location", "us-central1")).strip() or "us-central1"
    model_cfg = str(config.get("model", "publishers/google/models/gemini-3.1-flash-lite-preview")).strip()
    model = model_cfg.split("publishers/google/models/")[-1] if "publishers/google/models/" in model_cfg else model_cfg

    fallback_entries_path = base / "vertex_batch/review/fallback_entries.jsonl"
    sid_to_source_path = base / "vertex_batch/input/sid_to_source.json"
    sid_to_vi_path = base / "vertex_batch/merged/sid_to_vi.json"
    retry_dir = base / "vertex_batch/retry_online"
    retry_dir.mkdir(parents=True, exist_ok=True)

    fallback_entries = list(iter_jsonl(fallback_entries_path))
    sid_to_source = read_json(sid_to_source_path)
    sid_to_vi = read_json(sid_to_vi_path)

    target_sid_set = set()
    for row in fallback_entries:
        sid = str(row.get("sid", ""))
        reason = str(row.get("reason", ""))
        if not sid:
            continue
        if reason == "empty_source":
            continue
        target_sid_set.add(sid)

    target_sids = [sid for sid in target_sid_set if sid not in sid_to_vi and sid in sid_to_source]
    target_sids.sort()
    if args.max_sids > 0:
        target_sids = target_sids[: args.max_sids]

    failures = []
    translated_now = 0
    batches_total = (len(target_sids) + args.batch_size - 1) // args.batch_size if target_sids else 0
    done_batches = 0

    model_candidates = [model, "gemini-2.5-flash-lite", "gemini-2.5-flash"]
    location_candidates = [location] + ([] if location == "global" else ["global"])

    for i in range(0, len(target_sids), args.batch_size):
        chunk = target_sids[i : i + args.batch_size]
        items = []
        token_maps = {}
        for sid in chunk:
            source = str(sid_to_source[sid])
            protected, mapping = protect_tokens(source)
            token_maps[sid] = mapping
            items.append({"sid": sid, "text": protected})

        payload = json.dumps(items, ensure_ascii=False, separators=(",", ":"))
        prompt = (
            "Trả về JSON hợp lệ theo schema "
            "{\"items\":[{\"sid\":\"string\",\"translation\":\"string\"}]}. "
            "Dịch EN->VI ngữ cảnh game fantasy. "
            "BẮT BUỘC giữ nguyên mọi token dạng __TK_n__. "
            "Không thêm giải thích. Dữ liệu:\n" + payload
        )

        got = False
        last_error = None
        for loc in location_candidates:
            for m in model_candidates:
                resp, err = call_vertex_generate(api_key, access_token, project_id, loc, m, prompt)
                if err:
                    last_error = {"location": loc, "model": m, "error": err}
                    continue
                text = extract_text_from_response(resp)
                parsed_items = parse_items_json(text)
                if parsed_items is None:
                    last_error = {"location": loc, "model": m, "error": "parse_model_json_failed", "raw": text}
                    continue
                for it in parsed_items:
                    sid = str(it.get("sid", ""))
                    tr = str(it.get("translation", ""))
                    if sid not in token_maps:
                        continue
                    restored = restore_tokens(tr, token_maps[sid])
                    source = str(sid_to_source[sid])
                    if not tokens_match(source, restored):
                        failures.append(
                            {
                                "sid": sid,
                                "reason": "token_mismatch_retry",
                                "source": source,
                                "translation": restored,
                            }
                        )
                        continue
                    sid_to_vi[sid] = restored
                    translated_now += 1
                got = True
                break
            if got:
                break

        if not got:
            failures.append({"batch_index": (i // args.batch_size) + 1, "reason": "request_failed", "detail": last_error})

        done_batches += 1
        if done_batches % 10 == 0 or done_batches == batches_total:
            print(json.dumps({"done_batches": done_batches, "batches_total": batches_total, "translated_now": translated_now}, ensure_ascii=False), flush=True)
        if args.sleep_ms > 0:
            time.sleep(args.sleep_ms / 1000.0)

    write_json(sid_to_vi_path, sid_to_vi)
    write_jsonl(retry_dir / "retry_failures.jsonl", failures)
    stats = {
        "target_sid_count": len(target_sids),
        "translated_now": translated_now,
        "failures_count": len(failures),
        "auth_mode": auth_mode,
        "api_key_env": args.api_key_env,
        "model_candidates": model_candidates,
        "location_candidates": location_candidates,
    }
    write_json(retry_dir / "retry_stats.json", stats)
    print(json.dumps(stats, ensure_ascii=False, indent=2), flush=True)


if __name__ == "__main__":
    main()
