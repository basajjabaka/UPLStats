#!/usr/bin/env python3
"""
Match-report data extractor.

Walks every ``MATCH_REPORT-*.pdf`` under ``reports/<league>/<season>/md<N>/`` and
writes three tidy CSV files into ``csvs/new``:

    goalsNew.csv     league,season,game,player,team,min,added_time,md
    cautionsNew.csv  league,season,game,player,team,caution,min,added_time,double-caution,md
    subsNew.csv      league,season,game,in,out,min,added_time,team,md

A season folder is named with a dot where the slash goes, so ``upl/2025.26``
becomes league ``UPL``, season ``2025/26``.  Any folder that holds no ``md<N>``
subdirectory with PDFs in it is simply skipped, which keeps half-built
directories out of the output without any special casing.

The reports render the MATCH EVENTS table as

    | home team text | icon | minute | icon | away team text |

and the *only* thing that separates a goal from a booking is the little vector
icon in the icon column - the text layer carries the player name and nothing
else.  So the extractor:

1. reads the LEGEND block on page 1 and turns every legend icon into a colour
   signature -> caption lookup (the legend is drawn from exactly the same
   primitives as the icons used in the events table);
2. walks the MATCH EVENTS table row band by row band, using the table's own
   cell rectangles to define the bands - that is what makes wrapped two-line
   rows and page-spanning tables come out right;
3. classifies each row by matching its icon's colour signature against the
   legend, then routes it to goals / cautions / substitutions.

Every match is then checked against the score line the report prints for
itself: the goals found must add up to it, per team.  That check is independent
of the events table, so a matchday that passes it has not silently lost a goal.

Usage
-----
    python scripts/extract_match_data.py
    python scripts/extract_match_data.py --league UPL --season 2025/26
    python scripts/extract_match_data.py --last-matchday 12
    python scripts/extract_match_data.py --reports reports --out csvs/new

Exits non-zero if any report fails the score-line check.
"""

from __future__ import annotations

import argparse
import csv
import re
import sys
from collections import Counter
from pathlib import Path

try:
    import pdfplumber
except ImportError:  # pragma: no cover - dependency guard
    sys.exit("pdfplumber is required:  pip install pdfplumber")


# --------------------------------------------------------------------------
# configuration
# --------------------------------------------------------------------------

#: repo root, so the script works from any working directory
PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_REPORTS_DIR = PROJECT_ROOT / "reports"
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "csvs" / "new"

#: full club name (upper-cased, punctuation stripped) -> short code used in the CSVs.
TEAM_ABBREVIATIONS = {
    "BUL FC": "BUL",
    "URA FC": "URA",
    "ENTEBBE UPPC FC": "ENTEBBE",
    "BUHIMBA UNITED SAINTS FC": "BUHIMBA",
    "KITARA FC": "KITARA",
    "KCCA FC": "KCCA",
    "LUGAZI FC": "LUGAZI",
    "CALVARY FC": "CALVARY",
    "POLICE FOOTBALL CLUB": "POLICE",
    "MBARARA CITY FC": "MBARARA",
    "EXPRESS FC": "EXPRESS",
    "UPDF FC": "UPDF",
    "MAROONS FC": "MAROONS",
    "MAROON FC": "MAROONS",
    "NEC FC": "NEC",
    "SC VILLA": "Villa",
    "VIPERS SC": "VIPERS",
    "SC VIPERS": "VIPERS",
}

#: fill colours pdfplumber reports for MATCH EVENTS table cell backgrounds.
CELL_BACKGROUND_COLOURS = {
    (1.0, 1.0, 1.0),                                      # plain row
    (0.9216, 0.9216, 0.9216),                             # zebra row
    (0.9098, 0.9373, 0.9725),                             # period header row
}

#: legend caption -> what the event means for us.  The captions come straight
#: out of the PDF legend, so this is the only place the wording is spelled out.
LEGEND_GOAL_LABELS = {"Goal", "Own goal", "Penalty scored"}
LEGEND_CAUTION_LABELS = {
    "Yellow card": ("yellow", "No"),
    "Second yellow (Red card)": ("second yellow", "yes"),
    "Red card": ("red", "No"),
}
LEGEND_SUBSTITUTION_LABELS = {"Substitution"}

#: An own goal is printed on the side of the player who put it in his own net,
#: so the team that actually scored is the opponent.  Crediting it that way is
#: what keeps each team's goal count equal to the score line -- which is how
#: app.py reads the `team` column.  Flip this to False to credit the scorer's
#: own club instead.  No own goal appears in md1-md5; every one that turns up is
#: reported on stderr so it can be checked by hand.
OWN_GOAL_CREDITED_TO_OPPONENT = True

#: used only when the LEGEND block itself cannot be read.
FALLBACK_LEGEND = {
    ((0.2157, 0.2157, 0.2157),) * 3
    + ((0.8902, 0.898, 0.898), (0.9686, 0.9725, 0.9725), (1.0, 1.0, 1.0)): "Goal",
    ((0.0, 0.0, 0.0), (0.8902, 0.898, 0.898), (0.949, 0.6902, 0.0353),
     (0.9686, 0.9725, 0.9725), (0.9686, 0.9725, 0.9725)): "Yellow card",
    ((0.0, 0.0, 0.0), (0.0, 0.0, 0.0), (0.8902, 0.898, 0.898), (0.949, 0.6902, 0.0353),
     (0.9686, 0.9725, 0.9725), (0.9686, 0.9725, 0.9725),
     (0.9882, 0.3843, 0.2863)): "Second yellow (Red card)",
    ((0.0, 0.0, 0.0), (0.0, 0.0, 0.0), (0.8902, 0.898, 0.898),
     (0.9686, 0.9725, 0.9725), (0.9686, 0.9725, 0.9725), (0.9882, 0.3843, 0.2863)): "Red card",
    ((0.3647, 0.6863, 0.0118), (0.8706, 0.3176, 0.2353), (0.8902, 0.898, 0.898),
     (0.9686, 0.9725, 0.9725)): "Substitution",
}

#: distinctive colours, used to salvage an icon whose signature is not an exact
#: legend match (e.g. the renderer emitted one extra hair-line).
MARKER_COLOURS = {
    (0.949, 0.6902, 0.0353): "yellow",
    (0.9882, 0.3843, 0.2863): "red",
    (0.3647, 0.6863, 0.0118): "green",
    (0.8706, 0.3176, 0.2353): "rust",
    (0.2157, 0.2157, 0.2157): "ball",
}

ICON_SIZE_RANGE = (9.0, 10.2)      # the round icon badge is 9.6 x 9.6 pt
MINUTE_COLUMN_WIDTH = (22.0, 80.0)  # the icon strips beside it are only ~18pt
MINUTE_RE = re.compile(r"(\d+)\s*'?\s*(?:\(\s*\+\s*(\d+)\s*'?\s*\))?")
MINUTE_WORD_RE = re.compile(r"^\d+\s*'?\s*(?:\(\s*\+\s*\d+\s*'?\s*\))?$")
PERIOD_RE = re.compile(r"^(?:1P|2P|XT1|XT2|XT|P|PSO)$")
PERIOD_SCORE_RE = re.compile(
    r"(?:^|\s)(\d+)\s+(1st Period|2nd Period|Extra time)\s+(\d+)(?:\s|$)")
SUBSTITUTION_RE = re.compile(r"^in\s+(.+?)\s*,\s*out\s+(.+)$", re.IGNORECASE)
FILENAME_RE = re.compile(r"^MATCH_REPORT-(\d+)-(.+)-vs-(.+)$", re.IGNORECASE)
MATCHDAY_RE = re.compile(r"^md(\d+)$", re.IGNORECASE)

EVENTS_HEADING = "MATCH EVENTS"
EVENTS_TERMINATORS = ("PENALTY", "SIGNATURES")

#: every player and official carries a registration id like (002606M95).  It is
#: the only identifier in the report that is stable across spellings, so it is
#: what player-level joins should key on rather than the printed name.
#:
#: The letter is a gender marker, not a constant: female players and officials
#: are registered with an F, e.g. (026430F95).  Matching only M silently drops
#: them -- and would drop every player in the women's league.
REGISTRATION_ID = r"\d{6}[A-Z]\d{2}"
REGISTRATION_RE = re.compile(rf"\(({REGISTRATION_ID})\)")

#: minutes a full match is normalised to for per-90 work, stoppage aside
FULL_MATCH_MINUTES = 90

#: printed label (lower-cased, no colon) -> column name
OFFICIAL_ROLES = {
    "referee": "referee",
    "1st assistant referee": "assistant_1",
    "2nd assistant referee": "assistant_2",
    "fourth official": "fourth_official",
    "match commissioner": "commissioner",
    "referee assessor": "assessor",
}
OFFICIAL_FIELDS = list(OFFICIAL_ROLES.values())


# --------------------------------------------------------------------------
# small geometry helpers
# --------------------------------------------------------------------------

def _colour(value):
    """Normalise a pdfplumber colour so signatures compare reliably."""
    if value is None:
        return ()
    if isinstance(value, (int, float)):
        value = (value,)
    return tuple(round(float(v), 4) for v in value)


def _signature(curves):
    return tuple(sorted(_colour(c.get("non_stroking_color")) for c in curves))


def _mid_y(obj):
    return (obj["top"] + obj["bottom"]) / 2.0


def page_primitives(page):
    """Reduce a pdfplumber page to the plain dicts the parser needs."""
    return {
        "text": page.extract_text() or "",
        "words": page.extract_words(extra_attrs=["fontname", "size"]),
        "curves": [
            {
                "x0": c["x0"], "x1": c["x1"], "top": c["top"], "bottom": c["bottom"],
                "width": c["width"], "height": c["height"],
                "non_stroking_color": c.get("non_stroking_color"),
            }
            for c in page.curves
        ],
        "rects": [
            {
                "x0": r["x0"], "x1": r["x1"], "top": r["top"], "bottom": r["bottom"],
                "width": r["width"], "height": r["height"],
                "non_stroking_color": r.get("non_stroking_color"),
            }
            for r in page.rects
        ],
        "width": page.width,
        "height": page.height,
    }


# --------------------------------------------------------------------------
# legend
# --------------------------------------------------------------------------

def read_legend(pages):
    """Map every legend icon's colour signature to its printed caption."""
    for page in pages:
        if "LEGEND" not in page["text"]:
            continue
        heading = next((w for w in page["words"] if w["text"] == "LEGEND"), None)
        if heading is None:
            continue

        left = heading["x0"] - 10
        badges = [
            c for c in page["curves"]
            if c["x0"] >= left
            and c["top"] > heading["top"]
            and ICON_SIZE_RANGE[0] < c["width"] < ICON_SIZE_RANGE[1]
            and ICON_SIZE_RANGE[0] < c["height"] < ICON_SIZE_RANGE[1]
        ]

        legend = {}
        for badge in sorted(badges, key=lambda c: c["top"]):
            parts = [
                c for c in page["curves"]
                if c["x0"] >= badge["x0"] - 0.6 and c["x1"] <= badge["x1"] + 0.6
                and c["top"] >= badge["top"] - 0.6 and c["bottom"] <= badge["bottom"] + 0.6
            ]
            caption_words = sorted(
                (w for w in page["words"]
                 if w["x0"] > badge["x1"] and abs(_mid_y(w) - _mid_y(badge)) < 5.5),
                key=lambda w: w["x0"],
            )
            caption = " ".join(w["text"] for w in caption_words).strip()
            if caption:
                legend.setdefault(_signature(parts), caption)
        if legend:
            return legend
    return dict(FALLBACK_LEGEND)


def classify_icon(curves, legend):
    """Return the legend caption for an icon, or None when there is no icon."""
    if not curves:
        return None
    caption = legend.get(_signature(curves))
    if caption:
        return caption

    # No verbatim match - fall back to the marker colours that make each icon
    # unique, so an unexpected extra primitive cannot silently drop an event.
    markers = {
        MARKER_COLOURS[colour]
        for colour in (_colour(c.get("non_stroking_color")) for c in curves)
        if colour in MARKER_COLOURS
    }
    if "green" in markers:
        return "Substitution"
    if "yellow" in markers and "red" in markers:
        return "Second yellow (Red card)"
    if "yellow" in markers:
        return "Yellow card"
    if "red" in markers:
        return "Red card"
    if "ball" in markers:
        return "Goal"
    if "rust" in markers:
        return "Own goal"
    return None


# --------------------------------------------------------------------------
# MATCH EVENTS table
# --------------------------------------------------------------------------

def events_region(pages):
    """Yield (page, y_top, y_bottom) slices covering the MATCH EVENTS table.

    The table starts under the MATCH EVENTS heading and runs until the PENALTY
    SHOOT-OUT / SIGNATURES block, which may be several pages later.
    """
    start = None
    for index, page in enumerate(pages):
        if EVENTS_HEADING in page["text"]:
            start = index
            break
    if start is None:
        return []

    slices = []
    for index in range(start, len(pages)):
        page = pages[index]
        top = 0.0
        if index == start:
            heading = _heading_word(page, "MATCH", "EVENTS")
            if heading is None:
                return slices
            top = heading["top"]

        bottom = page["height"]
        for terminator in EVENTS_TERMINATORS:
            stop = next((w["top"] for w in page["words"]
                         if w["text"] == terminator and w["top"] > top), None)
            if stop is not None:
                bottom = min(bottom, stop)
        slices.append((page, top, bottom))
        if bottom < page["height"]:
            break
    return slices


def _heading_word(page, first, second):
    """Locate the first word of a two-word heading such as 'MATCH EVENTS'."""
    for word in page["words"]:
        if word["text"] != first:
            continue
        for other in page["words"]:
            if (other["text"] == second and abs(other["top"] - word["top"]) < 2
                    and 0 < other["x0"] - word["x1"] < 12):
                return word
    return None


def _row_bands(page, top, bottom, x_min=40.0, x_max=None):
    """Group a table's cell rectangles into (top, bottom) -> [cells] bands.

    ``x_min``/``x_max`` narrow the search to one block. The team sheets print the
    home and away squads side by side, so each has to be read on its own or a
    wrapped name from one side lands in the other's rows.
    """
    bands = {}
    for rect in page["rects"]:
        if _colour(rect.get("non_stroking_color")) not in CELL_BACKGROUND_COLOURS:
            continue
        if rect["height"] < 5 or not (5 <= rect["width"] <= 400):
            continue
        if rect["top"] < top - 0.5 or rect["bottom"] > bottom + 0.5:
            continue
        if rect["x0"] < x_min - 0.5:
            continue
        if x_max is not None and rect["x1"] > x_max + 0.5:
            continue
        bands.setdefault((round(rect["top"], 1), round(rect["bottom"], 1)), []).append(rect)
    return sorted(bands.items())


def _minute_column(bands, words):
    """Find the x-range of the minute column, given the rows and their words.

    ``words`` must be limited to the table itself: minute-shaped tokens also
    appear in the line-ups higher up the page, and letting those vote can hand
    the column to one of the 18pt icon strips instead.
    """
    columns = Counter()
    for _band, cells in bands:
        for cell in cells:
            column = (round(cell["x0"], 1), round(cell["x1"], 1))
            if MINUTE_COLUMN_WIDTH[0] < (column[1] - column[0]) < MINUTE_COLUMN_WIDTH[1]:
                columns[column] += 1
    if not columns:
        return None

    votes = Counter()
    for word in words:
        if not (PERIOD_RE.match(word["text"]) or MINUTE_WORD_RE.match(word["text"])):
            continue
        centre = (word["x0"] + word["x1"]) / 2.0
        for column, seen in columns.items():
            if column[0] < centre < column[1]:
                votes[column] += seen
    if votes:
        return max(votes.items(), key=lambda kv: kv[1])[0]
    return max(columns.items(), key=lambda kv: kv[1])[0]


def _cell_text(words, x_lo, x_hi):
    """Join the words inside one cell, reading top-to-bottom then left-to-right."""
    picked = [w for w in words if w["x0"] >= x_lo - 0.5 and w["x1"] <= x_hi + 0.5]
    if not picked:
        return ""
    picked.sort(key=lambda w: (round(w["top"] / 3.0), w["x0"]))
    return " ".join(w["text"] for w in picked).strip()


def read_events_table(pages):
    """Return the raw rows of the MATCH EVENTS table across every page it spans."""
    rows = []
    for page, top, bottom in events_region(pages):
        bands = _row_bands(page, top, bottom)
        if not bands:
            continue
        left = min(cell["x0"] for _band, cells in bands for cell in cells)
        right = max(cell["x1"] for _band, cells in bands for cell in cells)
        table_words = [w for w in page["words"]
                       if bands[0][0][0] < _mid_y(w) < bands[-1][0][1]
                       and w["x0"] >= left - 1 and w["x1"] <= right + 1]

        minute_col = _minute_column(bands, table_words)
        if minute_col is None:
            continue
        m_x0, m_x1 = minute_col

        for (band_top, band_bottom), _cells in bands:
            words = [w for w in table_words if band_top < _mid_y(w) < band_bottom]
            curves = [c for c in page["curves"] if band_top < _mid_y(c) < band_bottom]

            rows.append({
                "minute": _cell_text(words, m_x0, m_x1),
                "home_text": _cell_text(words, left - 1, m_x0),
                "away_text": _cell_text(words, m_x1, right + 1),
                "home_icon": [c for c in curves
                              if c["x1"] <= m_x0 + 0.5 and c["x0"] >= left - 1],
                "away_icon": [c for c in curves
                              if c["x0"] >= m_x1 - 0.5 and c["x1"] <= right + 1],
            })
    return rows


# --------------------------------------------------------------------------
# team sheets, officials, staff and the header block
# --------------------------------------------------------------------------

#: squad tables never reach the officials column on the right of the page
SQUAD_RIGHT_LIMIT = 0.72


def _squad_blocks(page, top, bottom):
    """The two side-by-side squad blocks on a page, home first.

    The divider is found by merging the x-ranges the cells actually cover: the
    home and away sheets form two separate runs with a gutter between them.
    Taking the widest gap between column edges would not work, because the
    widest such gap is the away name column, not the gutter.
    """
    limit = page["width"] * SQUAD_RIGHT_LIMIT
    bands = _row_bands(page, top, bottom, x_max=limit)
    if not bands:
        return []

    spans = sorted((cell["x0"], cell["x1"]) for _band, cells in bands for cell in cells)
    merged = []
    for low, high in spans:
        if merged and low <= merged[-1][1] + 0.5:
            merged[-1][1] = max(merged[-1][1], high)
        else:
            merged.append([low, high])

    if len(merged) < 2:
        return []
    return [("home", merged[0][0], merged[0][1]),
            ("away", merged[1][0], merged[1][1])]


def _squad_columns(bands):
    """Shirt / name / minute column ranges, chosen by how often each appears.

    A squad table has one merged full-width cell for its header row. Picking the
    widest column would select that merge and swallow the minute alongside the
    name, so only columns present in most rows are considered.
    """
    tally = Counter((round(c["x0"], 1), round(c["x1"], 1))
                    for _band, cells in bands for c in cells)
    if not tally:
        return None, None, None
    common = sorted(column for column, seen in tally.items() if seen >= len(bands) / 2)
    if not common:
        common = sorted(tally)

    name_col = max(common, key=lambda c: c[1] - c[0])
    shirt_col = next((c for c in common if c[1] <= name_col[0] + 0.5), None)
    right = [c for c in common if c[0] >= name_col[1] - 0.5]
    minute_col = right[-1] if right else None
    return shirt_col, name_col, minute_col


def _text_lines(words, tolerance=4.0):
    """Group words into visual lines, tolerating small baseline drift.

    Rounding tops into fixed buckets splits a line whenever it straddles a
    bucket edge, which silently loses rows; clustering on the gap does not.
    """
    lines = []
    for word in sorted(words, key=lambda w: (w["top"], w["x0"])):
        if lines and abs(word["top"] - lines[-1][0]) <= tolerance:
            lines[-1][1].append(word)
        else:
            lines.append((word["top"], [word]))
    return [sorted(group, key=lambda w: w["x0"]) for _top, group in lines]


def _badges(page, top, bottom, x_min, x_max, legend):
    """Legend captions for the badges drawn on one squad row.

    A badge is several overlapping curves, and the legend is keyed on the whole
    group, so the curves have to be gathered per outer circle before being
    classified -- passing them in one at a time never matches anything.
    """
    captions = set()
    for outer in page["curves"]:
        if not (ICON_SIZE_RANGE[0] < outer["width"] < ICON_SIZE_RANGE[1]
                and ICON_SIZE_RANGE[0] < outer["height"] < ICON_SIZE_RANGE[1]):
            continue
        if not (top < _mid_y(outer) < bottom):
            continue
        if outer["x0"] < x_min - 1 or outer["x1"] > x_max + 1:
            continue
        parts = [c for c in page["curves"]
                 if c["x0"] >= outer["x0"] - 0.6 and c["x1"] <= outer["x1"] + 0.6
                 and c["top"] >= outer["top"] - 0.6 and c["bottom"] <= outer["bottom"] + 0.6]
        caption = legend.get(_signature(parts))
        if caption:
            captions.add(caption)
    return captions


def _read_squad_block(page, top, bottom, x_min, x_max, legend):
    """Every player row in one team's block of a squad table."""
    bands = _row_bands(page, top, bottom, x_min=x_min, x_max=x_max)
    if not bands:
        return []

    shirt_col, name_col, minute_col = _squad_columns(bands)
    if name_col is None:
        return []

    players = []
    for (band_top, band_bottom), _cells in bands:
        words = [w for w in page["words"]
                 if band_top < _mid_y(w) < band_bottom
                 and w["x0"] >= x_min - 1 and w["x1"] <= x_max + 1]
        if not words:
            continue

        name_cell = _cell_text(words, *name_col)
        identity = REGISTRATION_RE.search(name_cell)
        if not identity:
            continue                      # header row, or a blank slot

        name = REGISTRATION_RE.sub("", name_cell).strip()
        name = " ".join(name.split())
        if not name:
            continue

        shirt = _cell_text(words, *shirt_col) if shirt_col else ""
        minute = parse_minute(_cell_text(words, *minute_col)) if minute_col else None

        badges = _badges(page, band_top, band_bottom, x_min, x_max, legend)

        players.append({
            "shirt": shirt.strip(),
            "player": name,
            "player_id": identity.group(1),
            "is_captain": "yes" if "Captain" in badges else "no",
            "is_goalkeeper": "yes" if "Goalkeeper" in badges else "no",
            "minute": minute[2] if minute else None,
        })
    return players


def _block_bounds(page, heading):
    """Vertical extent of a titled block such as STARTING or SUBSTITUTES.

    SUBSTITUTES shares its page with MATCH EVENTS, whose table spans both squad
    columns; without stopping at that heading the two tables merge into one run
    and the block splitter finds no gutter.
    """
    tops = [w["top"] for w in page["words"] if w["text"] == heading]
    if not tops:
        return None
    top = min(tops)
    bottom = page["height"]
    events = _heading_word(page, "MATCH", "EVENTS")
    if events is not None and events["top"] > top:
        bottom = events["top"]
    return top, bottom


def read_squads(pages, meta):
    """Starting XI and substitutes for both teams, with minutes played."""
    legend = read_legend(pages)
    rows = []

    for page in pages:
        for heading, role in (("STARTING", "starting"), ("SUBSTITUTES", "substitute")):
            if heading not in page["text"]:
                continue
            bounds = _block_bounds(page, heading)
            if bounds is None:
                continue
            top, bottom = bounds

            for side, x_min, x_max in _squad_blocks(page, top, bottom):
                team = meta["home"] if side == "home" else meta["away"]
                declared = _declared_count(page, heading, side)
                players = _read_squad_block(page, top, bottom, x_min, x_max, legend)

                for player in players:
                    minute = player.pop("minute")
                    on_minute = minute if role == "substitute" else 0
                    off_minute = minute if role == "starting" else None
                    if role == "substitute" and minute is None:
                        played = 0                       # unused substitute
                    else:
                        start = on_minute or 0
                        played = max(0, (off_minute if off_minute is not None
                                         else FULL_MATCH_MINUTES) - start)
                    rows.append({
                        "league": meta["league"], "season": meta["season"],
                        "game": meta["game"], "md": meta["md"],
                        "team": team, "venue": side,
                        "role": role,
                        "on_minute": on_minute if role == "substitute" else 0,
                        "off_minute": off_minute,
                        "minutes_played": played,
                        "declared": declared,
                        **player,
                    })
    return rows


def _declared_count(page, heading, side):
    """The count the report prints for itself, e.g. STARTING (11).

    Squads are not always eleven -- at least one report reads STARTING (10) --
    so this is what the extracted rows get validated against.
    """
    split = page["width"] / 2.0
    for word in page["words"]:
        if word["text"] != heading:
            continue
        on_left = word["x0"] < split
        if (side == "home") != on_left:
            continue
        following = [w for w in page["words"]
                     if abs(w["top"] - word["top"]) < 2 and 0 < w["x0"] - word["x1"] < 20]
        for candidate in sorted(following, key=lambda w: w["x0"]):
            found = re.match(r"^\((\d+)\)$", candidate["text"])
            if found:
                return int(found.group(1))
    return None


#: a person's name is the run of capitalised words immediately before their id.
#: Anchoring on the id rather than the start of the line keeps stray text out --
#: the squad table's shirt numbers bleed into this column on some reports, so a
#: line can read "(11) Kaweesa Andrew (000190M78)".
#: Names are not reliably capitalised either -- reports carry both
#: "Oloya William" and "nassolo elizabeth" -- so case is not used as a signal.
PERSON_RE = re.compile(rf"([A-Za-z][A-Za-z'\-]*(?:\s+[A-Za-z][A-Za-z'\-]*){{0,3}})"
                       rf"\s*\(({REGISTRATION_ID})\)")


def _officials_column(page):
    """Left edge of the officials column, found from the role labels themselves.

    The column's x position moves between reports as the squad tables resize, so
    a fixed fraction of the page width silently drops the whole block on some of
    them.
    """
    labels = []
    for group in _text_lines(page["words"]):
        text = " ".join(w["text"] for w in group).strip().rstrip(":").strip()
        if text.lower() in OFFICIAL_ROLES:
            labels.append(min(w["x0"] for w in group))
    return min(labels) - 5 if labels else None


def read_officials(pages):
    """Match officials from the right-hand column of the first page.

    The block alternates a role label and a "Name (id)" line beneath it.
    """
    officials = {}
    for page in pages:
        origin = _officials_column(page)
        if origin is None:
            continue
        words = [w for w in page["words"] if w["x0"] >= origin]
        ordered = [" ".join(w["text"] for w in group) for group in _text_lines(words)]

        for index, line in enumerate(ordered):
            label = line.strip().rstrip(":").strip()
            field = OFFICIAL_ROLES.get(label.lower())
            if not field:
                continue
            for following in ordered[index + 1:index + 3]:
                found = PERSON_RE.search(following)
                if found:
                    officials[field] = " ".join(found.group(1).split())
                    officials[f"{field}_id"] = found.group(2)
                    break
        if officials:
            break
    return officials


def _staff_divider(page):
    """x that separates the home and away staff columns.

    Both teams' staff share one visual line, and the away column starts well
    left of the page midpoint, so the squad table's gutter is used instead.
    """
    bounds = _block_bounds(page, "SUBSTITUTES")
    if bounds:
        blocks = _squad_blocks(page, *bounds)
        if len(blocks) == 2:
            return (blocks[0][2] + blocks[1][1]) / 2.0
    return page["width"] / 2.0


def read_staff(pages, meta):
    """Coaching and medical staff, one row each, split home/away by position."""
    rows = []
    for page in pages:
        if "Head Coach" not in page["text"]:
            continue
        split = _staff_divider(page)
        for group in _text_lines(page["words"]):
            for side, team in (("home", meta["home"]), ("away", meta["away"])):
                picked = [w for w in group
                          if (w["x0"] < split) == (side == "home")]
                if not picked:
                    continue
                text = " ".join(w["text"] for w in sorted(picked, key=lambda w: w["x0"]))
                found = re.match(rf"\s*([A-Za-z ]+?):\s*(.+?)\s*\(({REGISTRATION_ID})\)",
                                 text)
                if not found:
                    continue
                rows.append({
                    "league": meta["league"], "season": meta["season"],
                    "game": meta["game"], "md": meta["md"],
                    "team": team, "venue": side,
                    "role": " ".join(found.group(1).split()),
                    "name": " ".join(found.group(2).split()),
                    "staff_id": found.group(3),
                })
        if rows:
            break
    return rows


def read_match_info(pages, meta):
    """The header block: when, where, how many watched, and who officiated."""
    text = pages[0]["text"] if pages else ""
    info = {
        "league": meta["league"], "season": meta["season"],
        "game": meta["game"], "md": meta["md"],
        "match_no": meta["number"],
        "home": meta["home"], "away": meta["away"],
    }

    kickoff = re.search(r"(\d{2}/\d{2}/\d{4})\s+(\d{2}:\d{2})", text)
    info["date"] = kickoff.group(1) if kickoff else ""
    info["kickoff"] = kickoff.group(2) if kickoff else ""

    venue = re.search(r"Africa/Kampala\s*[^\w\n]*\s*(.+?)\s*Match No:", text, re.S)
    info["venue"] = " ".join(venue.group(1).split()) if venue else ""

    # Attendance is printed in only about half the reports, so it stays blank
    # rather than being defaulted to a number nobody counted.
    attendance = re.search(r"Attendance:\s*(\d+)", text)
    info["attendance"] = int(attendance.group(1)) if attendance else ""

    duration = re.search(r"Duration:\s*(.+?)\s*(?:\n|Report Date)", text)
    info["duration"] = " ".join(duration.group(1).split()) if duration else ""

    score = report_score(pages)
    info["home_goals"], info["away_goals"] = score if score else ("", "")

    for field in OFFICIAL_FIELDS:
        info[field] = ""
        info[f"{field}_id"] = ""
    info.update(read_officials(pages))
    return info


# --------------------------------------------------------------------------
# match metadata
# --------------------------------------------------------------------------

def abbreviate(team_name):
    """Full club name -> the short code the CSVs use."""
    key = re.sub(r"[^A-Z0-9 ]", "", (team_name or "").upper())
    key = re.sub(r"\s+", " ", key).strip()
    if key in TEAM_ABBREVIATIONS:
        return TEAM_ABBREVIATIONS[key]
    stripped = re.sub(r"\b(FC|SC|CITY|UNITED|SAINTS|FOOTBALL|CLUB)\b", " ", key)
    stripped = re.sub(r"\s+", " ", stripped).strip()
    return (stripped or key).split(" ")[0]


def match_metadata(pdf_path, pages, league="", season=""):
    """Competition, match number, matchday and the two team codes (home first)."""
    number = 0
    home = away = ""

    filename_match = FILENAME_RE.match(pdf_path.stem)
    if filename_match:
        number = int(filename_match.group(1))
        home, away = filename_match.group(2).strip(), filename_match.group(3).strip()

    # The MATCH EVENTS heading is followed by "<HOME>   <AWAY>"; prefer that,
    # because it is the club name the report itself prints.
    for page, top, _bottom in events_region(pages):
        header = [w for w in page["words"]
                  if top < w["top"] < top + 22 and w["text"] not in ("MATCH", "EVENTS")]
        if header:
            split = page["width"] / 2.0
            ordered = sorted(header, key=lambda w: w["x0"])
            left = " ".join(w["text"] for w in ordered if w["x1"] < split)
            right = " ".join(w["text"] for w in ordered if w["x0"] >= split)
            if left and right:
                home, away = left, right
        break

    matchday = None
    folder = MATCHDAY_RE.match(pdf_path.parent.name)
    if folder:
        matchday = int(folder.group(1))

    home_abbr, away_abbr = abbreviate(home), abbreviate(away)
    return {
        "number": number,
        "md": matchday,
        "league": league,
        "season": season,
        "home": home_abbr,
        "away": away_abbr,
        "game": f"{home_abbr.upper()}-vs-{away_abbr.upper()}",
    }


# --------------------------------------------------------------------------
# extraction
# --------------------------------------------------------------------------

def parse_minute(text):
    """"90'(+1')" -> ("90(+1)", "yes", 90, 1);  "65'" -> ("65", "no", 65, 0)."""
    match = MINUTE_RE.search(text or "")
    if not match:
        return None
    minute = int(match.group(1))
    extra = int(match.group(2)) if match.group(2) else 0
    if extra:
        return f"{minute}(+{extra})", "yes", minute, extra
    return f"{minute}", "no", minute, 0


def extract_match(pages, meta):
    """Pull goals / cautions / substitutions out of one parsed match report."""
    legend = read_legend(pages)
    goals, cautions, subs = [], [], []
    order = 0

    for row in read_events_table(pages):
        if PERIOD_RE.match(row["minute"].strip()):
            continue
        minute = parse_minute(row["minute"])
        if minute is None:
            continue
        min_text, added_time, minute_no, extra = minute

        for side, team in (("home", meta["home"]), ("away", meta["away"])):
            caption = classify_icon(row[f"{side}_icon"], legend)
            if caption is None:
                continue
            text = " ".join(row[f"{side}_text"].split())
            if not text:
                continue
            order += 1
            sort_key = (minute_no, extra, order)

            if caption in LEGEND_SUBSTITUTION_LABELS:
                sub = SUBSTITUTION_RE.match(text)
                if not sub:
                    print(f"  ! unparsed substitution {text!r} "
                          f"({meta['game']} {min_text}')", file=sys.stderr)
                    continue
                subs.append({
                    "league": meta["league"],
                    "season": meta["season"],
                    "game": meta["game"],
                    "in": sub.group(1).strip(),
                    "out": sub.group(2).strip(),
                    "min": min_text,
                    "added_time": added_time,
                    "team": team,
                    "md": meta["md"],
                    "_sort": sort_key,
                })
            elif caption in LEGEND_CAUTION_LABELS:
                kind, double = LEGEND_CAUTION_LABELS[caption]
                cautions.append({
                    "league": meta["league"],
                    "season": meta["season"],
                    "game": meta["game"],
                    "player": text,
                    "team": team,
                    "caution": kind,
                    "min": min_text,
                    "added_time": added_time,
                    "double-caution": double,
                    "md": meta["md"],
                    "_sort": sort_key,
                })
            elif caption in LEGEND_GOAL_LABELS:
                scoring_team = team
                if caption == "Own goal":
                    if OWN_GOAL_CREDITED_TO_OPPONENT:
                        scoring_team = meta["away"] if side == "home" else meta["home"]
                    print(f"  i own goal by {text} ({meta['game']} {min_text}') "
                          f"credited to {scoring_team}", file=sys.stderr)
                goals.append({
                    "league": meta["league"],
                    "season": meta["season"],
                    "game": meta["game"],
                    "player": text,
                    "team": scoring_team,
                    "min": min_text,
                    "added_time": added_time,
                    "md": meta["md"],
                    "_sort": sort_key,
                })
            # "Penalty missed" and anything else is none of the three outputs.

    for bucket in (goals, cautions, subs):
        bucket.sort(key=lambda row: row["_sort"])
    return goals, cautions, subs


def report_score(pages):
    """The final score as the report itself states it, from its per-period lines.

    Page 1 prints '<home> 1st Period <away>', '<home> 2nd Period <away>' and
    '<home> Extra time <away>'; summing them is independent of the events table,
    which makes it a real check on the goals we pulled out of it.
    """
    home = away = 0
    found = False
    for line in pages[0]["text"].splitlines():
        match = PERIOD_SCORE_RE.search(line.strip())
        if match:
            home += int(match.group(1))
            away += int(match.group(3))
            found = True
    return (home, away) if found else None


def check_against_score(meta, goals, pages):
    """Return a warning string when the goals found disagree with the score line."""
    score = report_score(pages)
    if score is None:
        return "no score line found in report"
    home = sum(1 for g in goals if g["team"] == meta["home"])
    away = sum(1 for g in goals if g["team"] == meta["away"])
    if (home, away) != score:
        return f"extracted {home}:{away} but report says {score[0]}:{score[1]}"
    return None


def extract_squads(pages, meta):
    """Team sheets, staff and header for one report."""
    return read_squads(pages, meta), read_staff(pages, meta), read_match_info(pages, meta)


def check_squad_counts(meta, lineups):
    """Return a warning when a squad block does not match its printed count.

    Each block is headed STARTING (11) / SUBSTITUTES (9), so the report states
    how many rows it contains.  Comparing against that -- never against a hard
    eleven, since at least one report legitimately reads STARTING (10) -- is what
    catches a dropped or duplicated player.
    """
    seen, declared = {}, {}
    for row in lineups:
        key = (row["team"], row["role"])
        seen[key] = seen.get(key, 0) + 1
        if row.get("declared") is not None:
            declared[key] = row["declared"]

    problems = [f"{team} {role} {seen[(team, role)]} of {count}"
                for (team, role), count in declared.items()
                if seen.get((team, role), 0) != count]
    if not lineups:
        return "no team sheet found"
    return "squad size mismatch: " + ", ".join(problems) if problems else None


def parse_report(pdf_path, league="", season=""):
    """Parse one match report PDF -> (metadata, (goals, cautions, subs), pages)."""
    pdf_path = Path(pdf_path)
    with pdfplumber.open(str(pdf_path)) as pdf:
        pages = [page_primitives(page) for page in pdf.pages]
    meta = match_metadata(pdf_path, pages, league, season)
    return meta, extract_match(pages, meta), pages


# --------------------------------------------------------------------------
# driver
# --------------------------------------------------------------------------

GOAL_COLUMNS = ["league", "season", "game", "player", "team", "min", "added_time", "md"]
CAUTION_COLUMNS = ["league", "season", "game", "player", "team", "caution", "min",
                   "added_time", "double-caution", "md"]
SUB_COLUMNS = ["league", "season", "game", "in", "out", "min", "added_time", "team", "md"]

LINEUP_COLUMNS = ["league", "season", "game", "md", "team", "venue", "shirt",
                  "player", "player_id", "role", "is_captain", "is_goalkeeper",
                  "on_minute", "off_minute", "minutes_played"]
STAFF_COLUMNS = ["league", "season", "game", "md", "team", "venue", "role",
                 "name", "staff_id"]
MATCH_INFO_COLUMNS = (["league", "season", "game", "md", "match_no", "home", "away",
                       "date", "kickoff", "venue", "attendance", "duration",
                       "home_goals", "away_goals"]
                      + [c for field in OFFICIAL_FIELDS
                         for c in (field, f"{field}_id")])


def _report_sort_key(pdf):
    match = FILENAME_RE.match(pdf.stem)
    return (int(match.group(1)) if match else 10 ** 6, pdf.name)


def find_reports(season_dir, last_matchday=None):
    """Every match report in md1..md<last_matchday>, in matchday then match order.

    Without ``last_matchday`` every ``md<N>`` folder present is included; pass it
    to stop before a matchday whose reports are still coming in.
    """
    matchdays = sorted(
        (int(MATCHDAY_RE.match(d.name).group(1)), d)
        for d in Path(season_dir).iterdir()
        if d.is_dir() and MATCHDAY_RE.match(d.name)
    )
    reports = []
    for number, folder in matchdays:
        if last_matchday is not None and number > last_matchday:
            continue
        reports += sorted(folder.glob("*.pdf"), key=_report_sort_key)
    return reports


def season_label(folder_name):
    """'2025.26' -> '2025/26'.  The dot stands in for a slash on disk."""
    return folder_name.replace(".", "/")


def discover_seasons(reports_dir):
    """Every ``<league>/<season>`` under reports_dir that actually holds reports.

    Yields ``(league, season, path)`` with the league upper-cased and the season
    in its display form.  A directory only counts as a season when at least one
    of its ``md<N>`` children contains a PDF, so partially created folders and
    strays sitting at the wrong depth are ignored rather than producing empty
    league entries.
    """
    reports_dir = Path(reports_dir)
    if not reports_dir.is_dir():
        return []

    seasons = []
    for league_dir in sorted(p for p in reports_dir.iterdir() if p.is_dir()):
        for season_dir in sorted(p for p in league_dir.iterdir() if p.is_dir()):
            if find_reports(season_dir):
                seasons.append((league_dir.name.upper(),
                                season_label(season_dir.name),
                                season_dir))
    return seasons


def write_csv(path, columns, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Extract goals, cautions and substitutions from UPL match reports.")
    parser.add_argument("--reports", type=Path, default=DEFAULT_REPORTS_DIR,
                        help="directory holding the <league>/<season> folders (default: reports)")
    parser.add_argument("--out", type=Path, default=DEFAULT_OUTPUT_DIR,
                        help="output directory (default: csvs/new)")
    parser.add_argument("--league", default=None,
                        help="only this league, e.g. UPL (default: every league found)")
    parser.add_argument("--season", default=None,
                        help="only this season, e.g. 2025/26 (default: every season found)")
    parser.add_argument("--last-matchday", type=int, default=None,
                        help="highest matchday to include (default: every md<N> folder found)")
    parser.add_argument("--no-verify", action="store_true",
                        help="skip the check that goals found match the report's score line")
    parser.add_argument("--quiet", action="store_true")
    args = parser.parse_args(argv)

    seasons = discover_seasons(args.reports)
    if args.league:
        seasons = [s for s in seasons if s[0] == args.league.upper()]
    if args.season:
        wanted = season_label(args.season)
        seasons = [s for s in seasons if s[1] == wanted]
    if not seasons:
        sys.exit(f"no match reports found under {args.reports}")

    all_goals, all_cautions, all_subs = [], [], []
    all_lineups, all_staff, all_info = [], [], []
    warnings = []
    total_reports = 0

    for league, season, season_dir in seasons:
        reports = find_reports(season_dir, args.last_matchday)
        total_reports += len(reports)
        if not args.quiet:
            print(f"\n=== {league} {season}  ({len(reports)} reports) ===")

        for pdf in reports:
            meta, (goals, cautions, subs), pages = parse_report(pdf, league, season)
            all_goals += goals
            all_cautions += cautions
            all_subs += subs

            lineups, staff, info = extract_squads(pages, meta)
            all_lineups += lineups
            all_staff += staff
            all_info.append(info)

            warning = None if args.no_verify else check_against_score(meta, goals, pages)
            squad_warning = None if args.no_verify else check_squad_counts(meta, lineups)
            for note in (warning, squad_warning):
                if note:
                    warnings.append(f"{pdf}: {note}")
            if not args.quiet:
                notes = "   !! " + "; ".join(n for n in (warning, squad_warning) if n) \
                    if (warning or squad_warning) else ""
                print(f"md{str(meta['md']):<3} {meta['game']:<24} "
                      f"goals={len(goals):<3} cautions={len(cautions):<3} "
                      f"subs={len(subs):<3} squad={len(lineups)}{notes}")

    write_csv(args.out / "goalsNew.csv", GOAL_COLUMNS, all_goals)
    write_csv(args.out / "cautionsNew.csv", CAUTION_COLUMNS, all_cautions)
    write_csv(args.out / "subsNew.csv", SUB_COLUMNS, all_subs)
    write_csv(args.out / "lineupsNew.csv", LINEUP_COLUMNS, all_lineups)
    write_csv(args.out / "staffNew.csv", STAFF_COLUMNS, all_staff)
    write_csv(args.out / "matchInfoNew.csv", MATCH_INFO_COLUMNS, all_info)

    if not args.quiet:
        print(f"\n{total_reports} reports across {len(seasons)} season(s) -> {args.out}")
        for league, season, _dir in seasons:
            print(f"  {league} {season}")
        print(f"  goalsNew.csv      {len(all_goals)} rows")
        print(f"  cautionsNew.csv   {len(all_cautions)} rows")
        print(f"  subsNew.csv       {len(all_subs)} rows")
        print(f"  lineupsNew.csv    {len(all_lineups)} rows")
        print(f"  staffNew.csv      {len(all_staff)} rows")
        print(f"  matchInfoNew.csv  {len(all_info)} rows")
        if not args.no_verify:
            print(f"  checks: {total_reports - len(warnings)}/{total_reports} "
                  f"reports agree on score line and squad size")

    for warning in warnings:
        print(f"WARNING {warning}", file=sys.stderr)
    return 1 if warnings else 0


if __name__ == "__main__":
    raise SystemExit(main())
