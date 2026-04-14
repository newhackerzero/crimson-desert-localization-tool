#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
merge_translations.py

Trích xuất cặp `key` + `translation` từ hai file JSON (VI / ENG)
và ghép phần `translation` từ file tiếng Việt vào file tiếng Anh khi `key` trùng.

Usage (defaults assume this script is in the project's `tools/` folder):
  python merge_translations.py

Options:
  -v, --vi PATH          Path to Vietnamese paloc JSON
  -e, --eng PATH         Path to English paloc JSON
  -o, --out PATH         Output path for merged ENG JSON (defaults to ENG dir)
  --out-vi-kv PATH       Output path for extracted VI key/translation JSON
  --out-eng-kv PATH      Output path for extracted ENG key/translation JSON
  --csv                  Also write CSV versions of extracted key/translation files
  --replace-empty        Replace ENG translation even if VI translation is empty
  --replace-untranslated Replace even when VI translation equals ENG original
  --dry-run              Do everything except write merged ENG JSON
  --backup               Make a backup copy of the ENG JSON before writing
"""

from __future__ import annotations
import argparse
import json
import os
import sys
import csv
import shutil
from typing import Dict, List, Any


def load_json(path: str) -> Dict[str, Any]:
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def write_json(path: str, data: Any) -> None:
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def extract_kv_list(data: Dict[str, Any]) -> List[Dict[str, str]]:
    return [
        {'key': str(e.get('key')), 'translation': e.get('translation') or ''}
        for e in data.get('entries', [])
    ]


def kv_map_from_list(kv_list: List[Dict[str, str]]) -> Dict[str, str]:
    return {item['key']: item['translation'] for item in kv_list}


def write_kv_csv(path: str, kv_list: List[Dict[str, str]]) -> None:
    with open(path, 'w', newline='', encoding='utf-8') as f:
        w = csv.writer(f)
        w.writerow(['key', 'translation'])
        for it in kv_list:
            w.writerow([it['key'], it['translation']])


def merge_translations(eng_data: Dict[str, Any], vi_map: Dict[str, str],
                       replace_empty: bool = False,
                       replace_untranslated: bool = False) -> Dict[str, int]:
    replaced = 0
    skipped_empty = 0
    skipped_untranslated = 0
    not_found = 0
    for e in eng_data.get('entries', []):
        k = str(e.get('key'))
        if k not in vi_map:
            not_found += 1
            continue
        vi_tr = vi_map.get(k) or ''
        eng_orig = e.get('original') or ''
        if not replace_empty and vi_tr.strip() == '':
            skipped_empty += 1
            continue
        if not replace_untranslated and vi_tr == eng_orig:
            skipped_untranslated += 1
            continue
        e['translation'] = vi_tr
        replaced += 1
    return {
        'replaced': replaced,
        'skipped_empty': skipped_empty,
        'skipped_untranslated': skipped_untranslated,
        'not_found': not_found
    }


def default_paths() -> Dict[str, str]:
    # script is expected in tools/ under the project dir
    here = os.path.abspath(os.path.dirname(__file__))
    project = os.path.abspath(os.path.join(here, '..'))
    vi_default = os.path.join(project, 'vertex_batch', 'merged', 'localizationstring_vi.paloc.json')
    eng_default = os.path.join(project, 'PALOC_Export', 'localizationstring_eng.paloc.json')
    out_vi_kv = os.path.join(project, 'vi_kv.json')
    out_eng_kv = os.path.join(project, 'eng_kv.json')
    return {
        'vi': vi_default,
        'eng': eng_default,
        'out_vi_kv': out_vi_kv,
        'out_eng_kv': out_eng_kv,
        'project': project
    }


def parse_args() -> argparse.Namespace:
    dp = default_paths()
    p = argparse.ArgumentParser(description='Extract and merge paloc JSON translations')
    p.add_argument('-v', '--vi', default=dp['vi'], help='Vietnamese paloc JSON')
    p.add_argument('-e', '--eng', default=dp['eng'], help='English paloc JSON')
    p.add_argument('-o', '--out', default=None, help='Merged ENG JSON output path')
    p.add_argument('--out-vi-kv', default=dp['out_vi_kv'], help='Extracted VI key/translation JSON')
    p.add_argument('--out-eng-kv', default=dp['out_eng_kv'], help='Extracted ENG key/translation JSON')
    p.add_argument('--csv', action='store_true', help='Also write CSV files for extracted KV')
    p.add_argument('--replace-empty', action='store_true', help='Replace ENG translation even if VI translation is empty')
    p.add_argument('--replace-untranslated', action='store_true', help='Replace even when VI translation equals ENG original')
    p.add_argument('--dry-run', action='store_true', help='Do not write merged ENG JSON')
    p.add_argument('--backup', action='store_true', help='Make a backup of ENG JSON before writing')
    p.add_argument('--verbose', '-V', action='store_true', help='Verbose output')
    return p.parse_args()


def main() -> None:
    args = parse_args()
    if not os.path.exists(args.vi):
        print('VI file not found:', args.vi, file=sys.stderr)
        sys.exit(2)
    if not os.path.exists(args.eng):
        print('ENG file not found:', args.eng, file=sys.stderr)
        sys.exit(2)

    vi_data = load_json(args.vi)
    eng_data = load_json(args.eng)

    vi_kv = extract_kv_list(vi_data)
    eng_kv = extract_kv_list(eng_data)

    # write extracted KV JSON
    write_json(args.out_vi_kv, vi_kv)
    write_json(args.out_eng_kv, eng_kv)
    if args.csv:
        write_kv_csv(os.path.splitext(args.out_vi_kv)[0] + '.csv', vi_kv)
        write_kv_csv(os.path.splitext(args.out_eng_kv)[0] + '.csv', eng_kv)

    vi_map = kv_map_from_list(vi_kv)

    # determine output path
    if args.out:
        out_path = args.out
    else:
        eng_basename = os.path.basename(args.eng)
        if eng_basename.endswith('.paloc.json'):
            out_basename = eng_basename.replace('.paloc.json', '_merged_vi.paloc.json')
        else:
            out_basename = eng_basename + '_merged_vi.json'
        out_path = os.path.join(os.path.dirname(args.eng), out_basename)

    if args.backup:
        bak = args.eng + '.backup'
        shutil.copy2(args.eng, bak)
        if args.verbose:
            print('Backup created:', bak)

    stats = merge_translations(eng_data, vi_map, replace_empty=args.replace_empty,
                               replace_untranslated=args.replace_untranslated)

    if args.dry_run:
        print('Dry-run: not writing merged file. Stats:', stats)
    else:
        write_json(out_path, eng_data)
        print('Merged ENG written to:', out_path)
        print('Stats:', stats)


if __name__ == '__main__':
    main()
