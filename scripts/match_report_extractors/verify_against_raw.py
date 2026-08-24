#!/usr/bin/env python3
"""
Diff the extractor's output (csvs/new) against the hand-entered csvs/raw.

Only the games that actually have a PDF under ``reports/`` are compared, since
csvs/raw also covers matchdays whose reports are not in the repo.

Comparison is by multiset of rows, not row order: csvs/raw was typed up by hand
and its row order is not systematic.  Player names, team codes and the game key
are compared case-insensitively with whitespace collapsed, so that 'Villa' vs
'VILLA' is not reported as a difference while a genuinely different name is.

    python scripts/match_report_extractors/verify_against_raw.py
    python scripts/match_report_extractors/verify_against_raw.py --md 1 2 3 4 5
"""

from __future__ import annotations

import argparse
import csv
import re
from collections import Counter
from pathlib import Path

FILES = {
    "goals": ("goalsNew.csv", "goals.csv",
              ["game", "player", "team", "min", "added_time", "md"], {"player"}),
    "cautions": ("cautionsNew.csv", "cautions.csv",
                 ["game", "player", "team", "caution", "min", "added_time",
                  "double-caution", "md"], {"player"}),
    "subs": ("subsNew.csv", "subs.csv",
             ["game", "in", "out", "min", "added_time", "team", "md"], {"in", "out"}),
}


def read_csv(path):
    with Path(path).open(newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def normalise(row, columns, name_columns):
    key = []
    for column in columns:
        value = (row.get(column) or "").strip()
        if column == "game" or column in name_columns or column == "team":
            value = re.sub(r"\s+", " ", value).upper()
        elif column == "double-caution":
            value = value.lower()
        elif column == "min":
            value = value.replace(" ", "")
        key.append(value)
    return tuple(key)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--new", type=Path, default=Path("csvs/new"))
    parser.add_argument("--raw", type=Path, default=Path("csvs/raw"))
    parser.add_argument("--md", type=int, nargs="*", default=None,
                        help="matchdays to compare (default: every matchday in csvs/new)")
    args = parser.parse_args(argv)

    extracted = {name: read_csv(args.new / files[0]) for name, files in FILES.items()}
    matchdays = ({str(m) for m in args.md} if args.md
                 else {r["md"] for rows in extracted.values() for r in rows})
    games = {re.sub(r"\s+", " ", r["game"]).upper()
             for rows in extracted.values() for r in rows}

    total = 0
    for name, (_new_file, raw_file, columns, name_columns) in FILES.items():
        mine = Counter(normalise(r, columns, name_columns) for r in extracted[name]
                       if r["md"] in matchdays)
        raw = Counter(
            normalise(r, columns, name_columns) for r in read_csv(args.raw / raw_file)
            if r["md"] in matchdays
            and re.sub(r"\s+", " ", r["game"]).upper() in games
        )
        only_new, only_raw = mine - raw, raw - mine
        total += sum(only_new.values()) + sum(only_raw.values())

        print(f"\n=== {name}: {sum(mine.values())} extracted vs {sum(raw.values())} raw "
              f"| +{sum(only_new.values())} / -{sum(only_raw.values())}")
        for key in sorted(set(only_new) | set(only_raw)):
            if key in only_new:
                print(f"   + {key}  x{only_new[key]}")
            if key in only_raw:
                print(f"   - {key}  x{only_raw[key]}")

    print(f"\nmatchdays compared: {sorted(matchdays, key=int)}   games compared: {len(games)}")
    print(f"total differences: {total}   (+ = only in csvs/new, - = only in csvs/raw)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
