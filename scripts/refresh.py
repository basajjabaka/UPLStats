#!/usr/bin/env python3
"""
Unattended refresh: pick up new match reports, re-extract only what changed,
then re-run the wrangle step.

Designed to be run on a timer and to be cheap when there is nothing to do.
A full extract costs roughly six seconds per PDF, so re-parsing an entire
season on every tick would take ~25 minutes.  Instead each report's extracted
rows are cached against a fingerprint of the file (size + mtime); a run only
pays for the reports that are genuinely new or have changed on disk.

    python scripts/refresh.py                # the scheduled entry point
    python scripts/refresh.py --force        # ignore the cache, re-parse all
    python scripts/refresh.py --deploy       # also publish to shinyapps.io
    python scripts/refresh.py --status       # what would run, without running

Exit codes
----------
    0  finished cleanly (whether or not anything changed)
    1  finished, but at least one report failed its score-line check
    2  could not run (another refresh holds the lock, or a step failed)
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import extract_match_data as extractor

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = Path(__file__).resolve().parent

STATE_DIR = PROJECT_ROOT / "csvs" / ".refresh"
CACHE_DIR = STATE_DIR / "reports"
LOCK_FILE = STATE_DIR / "refresh.lock"
LOG_FILE = PROJECT_ROOT / "logs" / "refresh.log"

#: a report whose mtime is newer than this is assumed to still be copying, and
#: is left for the next run rather than parsed half-written
SETTLE_SECONDS = 45

#: a lock older than this is treated as abandoned (a crashed or killed run)
STALE_LOCK_HOURS = 6

#: Bump whenever the extractor starts producing something new. Cache entries
#: from an older version are re-parsed even though the PDF itself has not
#: changed -- without this, adding an output would leave every report "up to
#: date" and the new file permanently empty.
CACHE_VERSION = 2

OUTPUT_FILES = (
    ("goalsNew.csv", extractor.GOAL_COLUMNS, "goals"),
    ("cautionsNew.csv", extractor.CAUTION_COLUMNS, "cautions"),
    ("subsNew.csv", extractor.SUB_COLUMNS, "subs"),
    ("lineupsNew.csv", extractor.LINEUP_COLUMNS, "lineups"),
    ("staffNew.csv", extractor.STAFF_COLUMNS, "staff"),
    ("matchInfoNew.csv", extractor.MATCH_INFO_COLUMNS, "info"),
)


# --------------------------------------------------------------------------
# logging
# --------------------------------------------------------------------------

def log(message, quiet=False):
    """Timestamped line to stdout and to logs/refresh.log."""
    line = f"{datetime.now():%Y-%m-%d %H:%M:%S}  {message}"
    if not quiet:
        print(line, flush=True)
    try:
        LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
        with LOG_FILE.open("a", encoding="utf-8") as handle:
            handle.write(line + "\n")
    except OSError:
        pass  # never let logging break the run


# --------------------------------------------------------------------------
# lock
# --------------------------------------------------------------------------

def acquire_lock():
    """Refuse to start when another refresh is already in flight.

    The first run of a season can take far longer than the gap between two
    ticks, so overlapping runs are a real possibility rather than a theoretical
    one.  A lock left behind by a killed run is taken over once it goes stale.
    """
    LOCK_FILE.parent.mkdir(parents=True, exist_ok=True)
    if LOCK_FILE.exists():
        age_hours = (time.time() - LOCK_FILE.stat().st_mtime) / 3600
        if age_hours < STALE_LOCK_HOURS:
            log(f"another refresh is running ({LOCK_FILE.read_text().strip()}); "
                f"exiting")
            return False
        log(f"taking over a stale lock ({age_hours:.1f}h old)")
    LOCK_FILE.write_text(f"pid={os.getpid()} started={datetime.now():%Y-%m-%d %H:%M:%S}")
    return True


def release_lock():
    try:
        LOCK_FILE.unlink(missing_ok=True)
    except OSError:
        pass


# --------------------------------------------------------------------------
# per-report cache
# --------------------------------------------------------------------------

def fingerprint(pdf):
    """Cheap identity for a file: size plus whole-second mtime."""
    stat = pdf.stat()
    return f"{stat.st_size}:{int(stat.st_mtime)}"


def cache_file(relative_path):
    digest = hashlib.sha1(str(relative_path).encode("utf-8")).hexdigest()[:16]
    return CACHE_DIR / f"{digest}.json"


def read_cache(relative_path, expected):
    path = cache_file(relative_path)
    if not path.exists():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if payload.get("cache_version") != CACHE_VERSION:
        return None
    return payload if payload.get("fingerprint") == expected else None


def write_cache(relative_path, payload):
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cache_file(relative_path).write_text(
        json.dumps(payload, ensure_ascii=False), encoding="utf-8")


def prune_cache(live_paths):
    """Drop cache entries for reports that are no longer on disk."""
    if not CACHE_DIR.exists():
        return 0
    keep = {cache_file(p).name for p in live_paths}
    removed = 0
    for path in CACHE_DIR.glob("*.json"):
        if path.name not in keep:
            path.unlink(missing_ok=True)
            removed += 1
    return removed


# --------------------------------------------------------------------------
# extraction
# --------------------------------------------------------------------------

def settled(pdf):
    """False while a file still looks like it is being written."""
    return (time.time() - pdf.stat().st_mtime) >= SETTLE_SECONDS


def extract_all(force=False, quiet=False):
    """Rebuild the three csvs/new files, parsing only what changed.

    Returns (changed, parsed, skipped, deferred, warnings).
    """
    rows = {key: [] for _name, _columns, key in OUTPUT_FILES}
    parsed = cached = deferred = 0
    warnings = []
    live_paths = []
    changed = force

    for league, season, season_dir in extractor.discover_seasons(extractor.DEFAULT_REPORTS_DIR):
        reports = extractor.find_reports(season_dir)
        log(f"  {league} {season}: {len(reports)} report(s)", quiet)

        for pdf in reports:
            relative = pdf.relative_to(PROJECT_ROOT)
            live_paths.append(relative)
            mark = fingerprint(pdf)

            payload = None if force else read_cache(relative, mark)
            if payload is None:
                if not settled(pdf):
                    log(f"    deferring {pdf.name} (still being written)", quiet)
                    deferred += 1
                    continue
                try:
                    meta, (goals, cautions, subs), pages = extractor.parse_report(
                        pdf, league, season)
                except Exception as error:                  # noqa: BLE001
                    log(f"    !! could not parse {pdf.name}: {error}", quiet)
                    deferred += 1
                    continue

                lineups, staff, info = extractor.extract_squads(pages, meta)
                notes = [extractor.check_against_score(meta, goals, pages),
                         extractor.check_squad_counts(meta, lineups)]
                warning = "; ".join(n for n in notes if n) or None
                payload = {
                    "cache_version": CACHE_VERSION,
                    "fingerprint": mark,
                    "game": meta["game"],
                    "md": meta["md"],
                    "warning": warning,
                    # _sort is only meaningful inside one report, and it has
                    # already been applied, so it is not worth persisting
                    "goals": [{k: v for k, v in r.items() if k != "_sort"} for r in goals],
                    "cautions": [{k: v for k, v in r.items() if k != "_sort"} for r in cautions],
                    "subs": [{k: v for k, v in r.items() if k != "_sort"} for r in subs],
                    "lineups": lineups,
                    "staff": staff,
                    "info": [info],
                }
                write_cache(relative, payload)
                parsed += 1
                changed = True
                log(f"    parsed {meta['game']} (md{meta['md']}) "
                    f"goals={len(goals)} cautions={len(cautions)} subs={len(subs)} "
                    f"squad={len(lineups)}"
                    f"{'  !! ' + warning if warning else ''}", quiet)
            else:
                cached += 1

            for key in rows:
                rows[key].extend(payload[key])
            if payload.get("warning"):
                warnings.append(f"{relative}: {payload['warning']}")

    removed = prune_cache(live_paths)
    if removed:
        log(f"  dropped {removed} cache entr(y/ies) for reports no longer on disk")
        changed = True

    if changed:
        for filename, columns, key in OUTPUT_FILES:
            extractor.write_csv(extractor.DEFAULT_OUTPUT_DIR / filename, columns, rows[key])
        log("  wrote csvs/new: " + ", ".join(
            f"{key}={len(rows[key])}" for _name, _columns, key in OUTPUT_FILES), quiet)

    return changed, parsed, cached, deferred, warnings


# --------------------------------------------------------------------------
# downstream steps
# --------------------------------------------------------------------------

def run_step(name, command):
    """Run a child script, folding its output into the log."""
    log(f"running {name}...")
    result = subprocess.run(command, cwd=PROJECT_ROOT, capture_output=True,
                            text=True, encoding="utf-8", errors="replace")
    if result.returncode != 0:
        log(f"!! {name} failed (exit {result.returncode})")
        for line in (result.stderr or result.stdout or "").strip().splitlines()[-15:]:
            log(f"   {line}")
        return False
    log(f"{name} finished")
    return True


def deploy_command():
    """The rsconnect invocation, using the app id already saved in the repo."""
    config = PROJECT_ROOT / "rsconnect-python" / "UPLStats.json"
    app_id = None
    if config.exists():
        try:
            saved = json.loads(config.read_text(encoding="utf-8"))
            app_id = next(iter(saved.values()), {}).get("app_id")
        except (OSError, json.JSONDecodeError, StopIteration):
            app_id = None
    command = [sys.executable, "-m", "rsconnect", "deploy", "shiny", "."]
    if app_id:
        command += ["--app-id", str(app_id)]
    return command


# --------------------------------------------------------------------------
# driver
# --------------------------------------------------------------------------

def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Pick up new match reports and refresh the dashboard data.")
    parser.add_argument("--force", action="store_true",
                        help="ignore the cache and re-parse every report")
    parser.add_argument("--deploy", action="store_true",
                        help="publish to shinyapps.io when the data changed")
    parser.add_argument("--no-wrangle", action="store_true",
                        help="stop after writing csvs/new")
    parser.add_argument("--status", action="store_true",
                        help="report what would be parsed, then exit")
    parser.add_argument("--quiet", action="store_true",
                        help="log to the file only, not to stdout")
    args = parser.parse_args(argv)

    if args.status:
        pending = []
        for league, season, season_dir in extractor.discover_seasons(
                extractor.DEFAULT_REPORTS_DIR):
            for pdf in extractor.find_reports(season_dir):
                relative = pdf.relative_to(PROJECT_ROOT)
                if read_cache(relative, fingerprint(pdf)) is None:
                    pending.append(f"{league} {season}  {pdf.name}"
                                   f"{'' if settled(pdf) else '  (still writing)'}")
        print(f"{len(pending)} report(s) would be parsed")
        for item in pending:
            print("  " + item)
        return 0

    if not acquire_lock():
        return 2

    started = time.time()
    try:
        log("=" * 62, args.quiet)
        log("refresh started", args.quiet)

        changed, parsed, cached, deferred, warnings = extract_all(args.force, args.quiet)
        log(f"extract: {parsed} parsed, {cached} from cache, {deferred} deferred",
            args.quiet)

        if not changed:
            log(f"nothing new; finished in {time.time() - started:.1f}s", args.quiet)
            return 1 if warnings else 0

        if not args.no_wrangle:
            if not run_step("wrangle.py", [sys.executable, str(SCRIPTS_DIR / "wrangle.py")]):
                return 2

        if warnings:
            # The data is still written, but a score line that does not
            # reconcile is worth a human look before it goes public.
            log(f"!! {len(warnings)} report(s) failed the score-line check:", args.quiet)
            for warning in warnings:
                log(f"   {warning}", args.quiet)
            if args.deploy:
                log("skipping deploy because of the score-line warnings above",
                    args.quiet)
        elif args.deploy:
            if not run_step("rsconnect deploy", deploy_command()):
                return 2

        log(f"refresh finished in {time.time() - started:.1f}s", args.quiet)
        return 1 if warnings else 0
    finally:
        release_lock()


if __name__ == "__main__":
    raise SystemExit(main())
