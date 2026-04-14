import json
import re
from collections import Counter, defaultdict
from pathlib import Path


def token_counter(text: str):
    return {
        "curly": Counter(re.findall(r"\{[^{}]+\}", text)),
        "html": Counter(re.findall(r"<[^>]+>", text)),
        "square": Counter(re.findall(r"\[[^\]]+\]", text)),
        "printf": Counter(re.findall(r"%(?:\d+\$)?[sdifxX]", text)),
        "newline": Counter(re.findall(r"\\n|\\r\\n", text)),
    }


def eq_tokens(a: str, b: str):
    ta = token_counter(a)
    tb = token_counter(b)
    return ta == tb, ta, tb


def norm_vi(text: str):
    x = text.strip().lower()
    x = re.sub(r"\s+", " ", x)
    return x


base = Path("d:/fds/work/Crimson Desert Localization Tool-103-1-2-1774602780")
src_path = base / "PALOC_Export/localizationstring_eng.paloc.json"
vi_path = base / "vertex_batch/merged/localizationstring_vi.paloc.json"
out_dir = base / "vertex_batch/review"
out_dir.mkdir(parents=True, exist_ok=True)

src = json.loads(src_path.read_text(encoding="utf-8"))
vi = json.loads(vi_path.read_text(encoding="utf-8"))
src_entries = src.get("entries", [])
vi_entries = vi.get("entries", [])
src_map = {str(e.get("key", "")): e for e in src_entries}
vi_map = {str(e.get("key", "")): e for e in vi_entries}

all_keys = sorted(src_map.keys())
mismatch_rows = []
same_as_original = 0
empty_translation = 0

for k in all_keys:
    s = src_map[k]
    t = vi_map.get(k, {})
    original = str(s.get("original", ""))
    translation = str(t.get("translation", ""))
    if translation == "":
        empty_translation += 1
    if translation == original:
        same_as_original += 1
    ok, ta, tb = eq_tokens(original, translation)
    if not ok:
        mismatch_rows.append(
            {
                "key": k,
                "original": original,
                "translation": translation,
                "src_tokens": ta,
                "vi_tokens": tb,
            }
        )

variant_map = defaultdict(Counter)
source_count = Counter()
for k in all_keys:
    s = src_map[k]
    t = vi_map[k]
    original = str(s.get("original", ""))
    translation = str(t.get("translation", ""))
    if original == "" or translation == "":
        continue
    if re.search(r"\{[^{}]+\}|<[^>]+>|\[[^\]]+\]|%(?:\d+\$)?[sdifxX]", original):
        continue
    if len(original) > 48:
        continue
    if not re.fullmatch(r"[A-Za-z0-9 :,'\"!?\-./()&+%]+", original):
        continue
    source_count[original] += 1
    variant_map[original][norm_vi(translation)] += 1

variant_rows = []
for source, counter in variant_map.items():
    if source_count[source] < 5:
        continue
    if len(counter) <= 1:
        continue
    variant_rows.append(
        {
            "source": source,
            "occurrences": source_count[source],
            "variant_count": len(counter),
            "variants": counter.most_common(10),
        }
    )
variant_rows.sort(key=lambda x: (x["variant_count"], x["occurrences"]), reverse=True)

term_patterns = {
    "Skill": [r"\bkỹ năng\b", r"\bchiêu thức\b"],
    "Required Skill": [r"kỹ năng yêu cầu", r"yêu cầu kỹ năng", r"kỹ năng cần thiết", r"required skill"],
    "Stamina": [r"\bthể lực\b", r"\btinh lực\b", r"\bstamina\b"],
    "Attack": [r"\btấn công\b", r"\bcông\b", r"\battack\b"],
    "Defense": [r"\bphòng thủ\b", r"\bphòng ngự\b", r"\bdefense\b"],
    "Critical": [r"\bchí mạng\b", r"\bbạo kích\b", r"\bcritical\b"],
}

term_variant_stats = {}
for term, patterns in term_patterns.items():
    c = Counter()
    for k in all_keys:
        s = src_map[k]
        t = vi_map[k]
        original = str(s.get("original", ""))
        translation = str(t.get("translation", "")).lower()
        if term.lower() not in original.lower():
            continue
        matched = False
        for p in patterns:
            if re.search(p, translation):
                c[p] += 1
                matched = True
        if not matched:
            c["unmatched"] += 1
    term_variant_stats[term] = dict(c)

report = {
    "entries_total": len(all_keys),
    "placeholder_mismatch_count": len(mismatch_rows),
    "same_as_original_count": same_as_original,
    "empty_translation_count": empty_translation,
    "same_as_original_ratio": round(same_as_original / len(all_keys), 6) if all_keys else 0.0,
    "empty_translation_ratio": round(empty_translation / len(all_keys), 6) if all_keys else 0.0,
    "multi_variant_sources_count": len(variant_rows),
    "term_variant_stats": term_variant_stats,
}

(out_dir / "final_quality_report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
(out_dir / "placeholder_mismatch_samples.json").write_text(json.dumps(mismatch_rows[:200], ensure_ascii=False, indent=2), encoding="utf-8")
(out_dir / "source_multi_variants_top200.json").write_text(json.dumps(variant_rows[:200], ensure_ascii=False, indent=2), encoding="utf-8")

print(json.dumps(report, ensure_ascii=True, indent=2))
