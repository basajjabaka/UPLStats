#!/usr/bin/env python3
"""
U21 stats extractor.

Reads the U21 player export dropped into ``reports/<league>/<season>/md<N>/``
(any ``*U21*.xlsx``) and writes one tidy CSV, ``csvs/new/u21New.csv``, with one
row per player per matchday file.

Each file is expected to hold that matchday's games only, so season figures are
the sum of the files.  Only raw counts are kept: the export's ratio columns
(minutes per goal, per-game rates, ...) are dropped and rebuilt downstream from
summed counts, because a ratio cannot be added across matchdays -- and the
export writes 0 wherever a rate is undefined, which would rank a player who has
never scored as the league's most efficient finisher.

    python scripts/extract_u21.py
    python scripts/extract_u21.py --reports reports --out csvs/new

Problems in a file are reported as warnings and never stop the run.
"""

from __future__ import annotations

import argparse
import sys
from datetime import date
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from extract_match_data import (DEFAULT_OUTPUT_DIR, DEFAULT_REPORTS_DIR,  # noqa: E402
                                FULL_MATCH_MINUTES, MATCHDAY_RE, abbreviate,
                                season_label, write_csv)

OUTPUT_NAME = "u21New.csv"

#: A player is U21 for a season when born on or after 1 January of the year
#: U21_AGE years before the season starts: 2026/27 -> born 1 January 2005 or
#: later, 2027/28 -> 1 January 2006 or later.  The cutoff is worked out from
#: the season label, so it moves forward a year with every new season without
#: anything here changing.
U21_AGE = 21


def u21_born_from(season):
    """Earliest date of birth still U21 that season: '2026/27' -> 2005-01-01."""
    return date(int(str(season)[:4]) - U21_AGE, 1, 1)

#: export header -> column name.  Every header here must be present.  The
#: export's other columns are left out on purpose: "Position" is only a row
#: counter, the added-time minutes column duplicates the plain one, and the
#: rest are ratios derived from the counts below.
COLUMN_MAP = {
    "Competition Name": "competition",
    "Jersey No.": "jersey",
    "In-game Position": "position",
    "Name": "player",
    "Team": "club",
    "Nationality": "nationality",
    "Games Played": "apps",
    "Minutes Played (not including added time)": "minutes",
    "Starter": "starts",
    "Substitutions in": "sub_in",
    "Substitutions out": "sub_out",
    "Goals": "goals",
    "Own Goals": "own_goals",
    "Assists": "assists",
    "Penalties": "penalties",
    "Yellow Cards": "yellows",
    "Red Cards (direct)": "reds_direct",
    "Red Card (2nd yellow)": "reds_second_yellow",
}

COUNT_COLUMNS = ["apps", "minutes", "starts", "sub_in", "sub_out", "goals",
                 "own_goals", "assists", "penalties", "yellows", "reds_direct",
                 "reds_second_yellow"]

U21_COLUMNS = (["league", "season", "md", "source_file", "player", "name_key",
                "team", "club", "position", "jersey", "nationality", "player_id",
                "date_of_birth"] + COUNT_COLUMNS)


def name_key(name):
    """Order- and case-insensitive key: 'YIGA STEVEN' == 'Steven Yiga'."""
    return " ".join(sorted(str(name).upper().split()))


def tidy_name(name):
    """'joel KIGENYI' -> 'Joel Kigenyi'; the export mixes every casing."""
    return " ".join(word.capitalize() for word in str(name).split())


def _optional_header(header):
    """Map a registration-id or date-of-birth header, should the export gain one."""
    text = header.lower()
    if "birth" in text or text in ("dob", "d.o.b."):
        return "date_of_birth"
    if "registration" in text or text in ("id", "player id", "fifa id", "fufa id"):
        return "player_id"
    return None


def find_u21_files(reports_dir=DEFAULT_REPORTS_DIR):
    """Every ``md<N>/*U21*.xlsx`` as (league, season, md, path), in matchday order.

    Excel's ``~$`` lock files, left beside a workbook while it is open, are
    skipped.
    """
    reports_dir = Path(reports_dir)
    found = []
    if not reports_dir.is_dir():
        return found
    for league_dir in sorted(p for p in reports_dir.iterdir() if p.is_dir()):
        for season_dir in sorted(p for p in league_dir.iterdir() if p.is_dir()):
            for md_dir in season_dir.iterdir():
                match = MATCHDAY_RE.match(md_dir.name)
                if not (md_dir.is_dir() and match):
                    continue
                for path in sorted(md_dir.glob("*.xlsx")):
                    if "U21" in path.name.upper() and not path.name.startswith("~$"):
                        found.append((league_dir.name.upper(),
                                      season_label(season_dir.name),
                                      int(match.group(1)), path))
    return sorted(found, key=lambda item: (item[0], item[1], item[2], item[3].name))


def _examples(frame, limit=3):
    names = frame["player"].tolist()
    more = f" (+{len(names) - limit} more)" if len(names) > limit else ""
    return ", ".join(names[:limit]) + more


def read_u21_file(path, league, season, md):
    """One export -> (rows, warnings)."""
    where = f"{league} {season} md{md} {path.name}"
    try:
        raw = pd.read_excel(path, sheet_name=0, dtype=object)
    except Exception as error:                              # noqa: BLE001
        return [], [f"{where}: could not read ({error})"]

    raw.columns = [str(c).strip() for c in raw.columns]
    missing = [h for h in COLUMN_MAP if h not in raw.columns]
    if missing:
        return [], [f"{where}: skipped, export is missing column(s) {missing}"]

    optional = {h: _optional_header(h) for h in raw.columns if h not in COLUMN_MAP}
    optional = {h: c for h, c in optional.items() if c}
    df = raw[list(COLUMN_MAP) + list(optional)].rename(columns={**COLUMN_MAP, **optional})
    df = df[df["player"].notna() & (df["player"].astype(str).str.strip() != "")].copy()

    for column in COUNT_COLUMNS:
        df[column] = pd.to_numeric(df[column], errors="coerce").fillna(0).round().astype(int)
    for column in ("player_id", "date_of_birth"):
        if column not in df.columns:
            df[column] = ""

    df["name_key"] = df["player"].map(name_key)
    df["player"] = df["player"].map(tidy_name)
    df["team"] = df["club"].map(lambda club: abbreviate(str(club)).upper())
    df["jersey"] = pd.to_numeric(df["jersey"], errors="coerce").map(
        lambda n: "" if pd.isna(n) else str(int(n)))
    df["position"] = df["position"].fillna("").astype(str).str.strip()
    df["league"], df["season"], df["md"], df["source_file"] = league, season, md, path.name

    warnings = []
    checks = (
        (df["apps"] > 1, "show more than one game in a one-matchday file"),
        (df["apps"] != df["starts"] + df["sub_in"], "have games != starts + subs in"),
        (df["minutes"] > FULL_MATCH_MINUTES * df["apps"], "have more minutes than 90 x games"),
        (df.duplicated(["team", "name_key"], keep=False), "appear more than once"),
    )
    for mask, problem in checks:
        if mask.any():
            warnings.append(f"{where}: {int(mask.sum())} player(s) {problem}: "
                            f"{_examples(df[mask])}")
    stated = set(df["competition"].dropna().astype(str))
    if stated and not any(season in text for text in stated):
        warnings.append(f"{where}: competition {sorted(stated)} does not mention "
                        f"{season} -- is the file in the right season folder?")

    return df[U21_COLUMNS].to_dict("records"), warnings


def extract_files(files):
    """Read every (league, season, md, path) -> (rows, warnings)."""
    rows, warnings = [], []
    per_folder = {}
    for league, season, md, path in files:
        per_folder.setdefault(path.parent, []).append(path.name)
        file_rows, file_warnings = read_u21_file(path, league, season, md)
        rows += file_rows
        warnings += file_warnings
    for folder, names in per_folder.items():
        if len(names) > 1:
            warnings.append(f"{folder}: {len(names)} U21 files in one matchday "
                            f"folder, all were read: {names}")
    return rows, warnings


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Extract the per-matchday U21 player exports.")
    parser.add_argument("--reports", type=Path, default=DEFAULT_REPORTS_DIR,
                        help="directory holding the <league>/<season> folders (default: reports)")
    parser.add_argument("--out", type=Path, default=DEFAULT_OUTPUT_DIR,
                        help="output directory (default: csvs/new)")
    parser.add_argument("--quiet", action="store_true")
    args = parser.parse_args(argv)

    files = find_u21_files(args.reports)
    rows, warnings = extract_files(files)
    write_csv(args.out / OUTPUT_NAME, U21_COLUMNS, rows)

    if not args.quiet:
        print(f"{len(files)} U21 file(s) -> {args.out / OUTPUT_NAME}  ({len(rows)} rows)")
        for league, season, md, path in files:
            print(f"  {league} {season} md{md}  {path.name}")
    for warning in warnings:
        print(f"WARNING {warning}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
