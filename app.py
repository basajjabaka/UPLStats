import functools
import html
import json
import re
import sys
from pathlib import Path
from urllib.parse import quote
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import plotly.io as pio
import folium as fl
from folium.plugins import HeatMap
from shiny import reactive
from shiny.express import app_opts, render, input, ui
from shinywidgets import render_plotly, render_altair, render_widget
import matplotlib.pyplot as plt


# css styling
ui.tags.style(
    """
    body {
        background: linear-gradient(135deg, #f5f7fa 0%, #e4e8ec 100%);
        font-family: 'Nexover', 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
        /* clear the floating bar hanging over the top of the page */
        padding-top: 108px !important;
    }

    /* ---------------------------------------------------------------------
       Floating navbar: hangs inset from every edge, then tucks up on scroll
       --------------------------------------------------------------------- */
    .navbar.fixed-top {
        background: #F5901F !important;
        border: none;
        border-radius: 9999px;
        margin: 20px 28px;
        width: auto;
        padding: 6px 14px;
        box-shadow: 0 10px 30px rgba(15, 23, 42, 0.18);
        transition: margin 0.25s ease, box-shadow 0.25s ease, border-radius 0.25s ease;
    }

    .navbar.fixed-top.navbar-scrolled {
        margin: 8px 16px;
        border-radius: 9999px;
        box-shadow: 0 14px 38px rgba(15, 23, 42, 0.30);
    }

    /* Belt and braces after the Tailwind `collapse` collision: from the
       navbar's expand breakpoint upward the item container must stay visible,
       whatever else claims the class name. Below it, Bootstrap's toggler
       controls the dropdown as usual. */
    @media (min-width: 768px) {
        .navbar.fixed-top .navbar-collapse {
            display: flex !important;
            visibility: visible !important;
            flex-basis: auto;
        }
    }

    .navbar.fixed-top .navbar-nav {
        display: flex;
        flex-direction: row;
        align-items: center;
        flex-wrap: wrap;
        visibility: visible !important;
    }

    .navbar.fixed-top .navbar-brand {
        color: #ffffff !important;
        font-weight: 800;
        letter-spacing: 0.14em;
        font-size: 18px;
        padding-left: 18px;
    }

    .navbar.fixed-top .nav-link {
        color: rgba(255, 255, 255, 0.94) !important;
        text-transform: uppercase;
        letter-spacing: 0.04em;
        font-size: 12.5px;
        font-weight: 600;
        padding: 9px 13px !important;
        border-radius: 9999px;
        white-space: nowrap;
        transition: background 0.2s ease, color 0.2s ease;
    }

    /* Six sections plus the competition switcher is a lot of bar. Tighten the
       spacing before the browser is forced to wrap it. */
    @media (max-width: 1400px) {
        .navbar.fixed-top { margin: 14px 16px; }
        .navbar.fixed-top .navbar-brand { font-size: 15px; padding-left: 10px; }
        .navbar.fixed-top .nav-link {
            font-size: 11.5px;
            padding: 8px 9px !important;
            letter-spacing: 0.02em;
        }
    }

    .navbar.fixed-top .nav-link:hover {
        background: rgba(255, 255, 255, 0.18);
    }

    .navbar.fixed-top .nav-link.active {
        background: #ffffff;
        color: #D97706 !important;
    }

    /* league + season pickers sitting where the reference bar has its CTA */
    .navbar-switcher {
        display: flex;
        align-items: center;
        gap: 8px;
        background: #ffffff;
        border-radius: 9999px;
        padding: 4px 8px;
        margin-left: 8px;
    }

    .navbar-switcher .shiny-input-container {
        margin-bottom: 0 !important;
        width: auto;
    }

    .navbar-switcher select,
    .navbar-switcher .selectize-input {
        border: none !important;
        background: transparent !important;
        box-shadow: none !important;
        color: #D97706 !important;
        font-weight: 700;
        font-size: 13px;
        text-transform: uppercase;
        letter-spacing: 0.04em;
        min-height: 30px !important;
        padding: 2px 8px !important;
    }

    @media (max-width: 900px) {
        body { padding-top: 150px !important; }
        .navbar.fixed-top { border-radius: 20px; }
        .navbar-switcher { margin: 8px 0 4px 0; }
    }

    /* ---------------------------------------------------------------------
       Landing gate
       --------------------------------------------------------------------- */
    .landing-overlay {
        position: fixed;
        inset: 0;
        z-index: 2000;
        display: flex;
        align-items: center;
        justify-content: center;
        padding: 24px;
        /* Nnalubaale at night, darkened just enough for the card to stand out */
        background: linear-gradient(135deg, rgba(15, 23, 42, 0.60) 0%, rgba(15, 23, 42, 0.25) 100%),
                    url('landing-bg.jpg') center / cover no-repeat, #0F172A;
    }

    .landing-card {
        width: 100%;
        max-width: 520px;
        background: #ffffff;
        border-radius: 24px;
        padding: 40px;
        box-shadow: 0 30px 60px rgba(0, 0, 0, 0.35);
        text-align: center;
    }

    .landing-eyebrow {
        color: #F5901F;
        text-transform: uppercase;
        letter-spacing: 0.18em;
        font-size: 12px;
        font-weight: 700;
        margin-bottom: 6px;
    }

    .landing-title {
        font-size: 30px;
        font-weight: 800;
        color: #0F172A;
        margin: 0 0 10px 0;
    }

    .landing-sub {
        color: #64748B;
        font-size: 15px;
        margin-bottom: 26px;
    }

    .landing-fields {
        display: flex;
        gap: 16px;
        text-align: left;
        margin-bottom: 24px;
    }

    .landing-fields > * { flex: 1; }

    .landing-button {
        width: 100%;
        background: #F5901F !important;
        border: none !important;
        color: #ffffff !important;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        border-radius: 9999px !important;
        padding: 13px 24px !important;
    }

    .landing-button:hover { background: #D97706 !important; }

    .modebar {
        display: none !important;
    }

    .sidebar .well {
        background: linear-gradient(135deg, #1a5f7a 0%, #2e8b57 100%);
        border: none;
        border-radius: 10px;
        padding: 15px;
    }

    .nav-tabs .nav-link {
        background: linear-gradient(135deg, #1a5f7a 0%, #2e8b57 100%);
        color: white !important;
        border: none;
        margin-right: 5px;
        border-radius: 10px 10px 0 0;
        font-weight: 600;
        padding: 12px 20px;
        transition: all 0.3s ease;
    }

    .nav-tabs .nav-link:hover {
        background: linear-gradient(135deg, #2e8b57 0%, #1a5f7a 100%);
        transform: translateY(-2px);
    }

    .nav-tabs .nav-link.active {
        background: linear-gradient(135deg, #ff6b6b 0%, #feca57 100%);
        color: white !important;
    }

    .card {
        border: none;
        border-radius: 15px;
        box-shadow: 0 4px 15px rgba(0,0,0,0.1);
        transition: all 0.3s ease;
        margin-bottom: 20px;
    }

    .card:hover {
        transform: translateY(-5px);
        box-shadow: 0 8px 25px rgba(0,0,0,0.15);
    }

    .card-header {
        background: linear-gradient(135deg, #1a5f7a 0%, #2e8b57 100%);
        color: white;
        border-radius: 15px 15px 0 0 !important;
        font-weight: bold;
        font-size: 16px;
        padding: 15px;
    }

    .stat-card {
        background: white;
        border-radius: 15px;
        padding: 20px;
        text-align: center;
        box-shadow: 0 4px 15px rgba(0,0,0,0.1);
        transition: all 0.3s ease;
    }

    .stat-card:hover {
        transform: translateY(-5px);
        box-shadow: 0 8px 25px rgba(0,0,0,0.15);
    }

    .stat-card h3 {
        font-size: 36px;
        font-weight: bold;
        color: #1a5f7a;
        margin-bottom: 5px;
    }

    .stat-card p {
        color: #666;
        font-size: 14px;
        text-transform: uppercase;
        letter-spacing: 1px;
    }

    .stat-card.goals {
        border-left: 5px solid #2ecc71;
    }

    .stat-card.cards {
        border-left: 5px solid #e74c3c;
    }

    .stat-card.subs {
        border-left: 5px solid #3498db;
    }

    .stat-card.matches {
        border-left: 5px solid #9b59b6;
    }

    .shiny-input-container {
        margin-bottom: 15px;
    }

    .selectize-input {
        border-radius: 10px !important;
        border: 2px solid #1a5f7a !important;
    }

    .nav-content {
        background: white;
        border-radius: 0 0 15px 15px;
        padding: 20px;
        box-shadow: 0 4px 15px rgba(0,0,0,0.1);
    }
    
    /* Table styling for proper alignment */
    table {
        width: 100%;
        border-collapse: collapse;
    }
    
    table th {
        text-align: left;
        padding: 10px;
        background-color: #f5f5f5;
        font-weight: bold;
        border-bottom: 2px solid #ddd;
    }
    
    table td {
        text-align: left;
        padding: 10px;
        border-bottom: 1px solid #eee;
    }
    
    /* Orange card headers for Overview and Matchday Analysis */
    .overview-card-header {
        background: #FF8C00 !important;
        color: white;
        border-radius: 15px 15px 0 0 !important;
        font-weight: bold;
        font-size: 16px;
        padding: 15px;
    }
    """
)


#import transformed csvs
inputDIR = Path(__file__).resolve().parent / "csvs/transformed"

# Which side of the "HOME-vs-AWAY" key each event belongs to
def add_venue(df):
    """Tag every event row as home or away, from the game key."""
    home = df['game'].astype(str).str.upper().str.split('-VS-').str[0].str.strip()
    df['venue'] = np.where(df['team'].astype(str).str.upper() == home, 'home', 'away')
    return df


def load_events(name):
    """Read one transformed event table, upper-casing teams and tagging venue."""
    df = pd.read_csv(inputDIR / f"transformed_{name}.csv")
    df['team'] = df['team'].astype(str).str.upper()
    return add_venue(df)


ALL_GOALS = load_events("goals")
ALL_CAUTIONS = load_events("cautions")
ALL_SUBS = load_events("subs")

# match-level tables rebuilt from the goal events by wrangle.py
ALL_MATCHES = pd.read_csv(inputDIR / "transformed_matches.csv")
ALL_TEAM_MATCHES = pd.read_csv(inputDIR / "transformed_team_matches.csv")
ALL_COMEBACKS = pd.read_csv(inputDIR / "transformed_comebacks.csv")

# team sheets, staff and match headers read straight off the reports
ALL_LINEUPS = pd.read_csv(inputDIR / "transformed_lineups.csv")
ALL_LINEUPS['team'] = ALL_LINEUPS['team'].astype(str).str.upper()
ALL_STAFF = pd.read_csv(inputDIR / "transformed_staff.csv")
ALL_STAFF['team'] = ALL_STAFF['team'].astype(str).str.upper()
ALL_MATCH_INFO = pd.read_csv(inputDIR / "transformed_match_info.csv")

# U21 players, one row per player per matchday: from the weekly U21 export, or
# from the team sheets (by the birth year in the registration id) for a
# matchday without one.  Built by wrangle.py.
U21_SUM_COLUMNS = ['apps', 'minutes', 'starts', 'sub_in', 'sub_out', 'goals',
                   'own_goals', 'assists', 'penalties', 'yellows', 'reds_direct',
                   'reds_second_yellow']
U21_EXPORT_ONLY = ['own_goals', 'assists', 'penalties']   # not in the reports
_U21_PATH = inputDIR / "transformed_u21_matchday.csv"
ALL_U21 = (pd.read_csv(_U21_PATH, dtype={'player_id': str, 'jersey': str})
           if _U21_PATH.exists() else
           pd.DataFrame(columns=['league', 'season', 'md', 'source', 'player_key',
                                 'player_id', 'player', 'team', 'position', 'jersey',
                                 'birth_year', 'u21_born_from'] + U21_SUM_COLUMNS
                                + ['report_minutes', 'team_points', 'team_matches']))
ALL_U21['team'] = ALL_U21['team'].astype(str).str.upper()
for _column in ('player_id', 'jersey', 'position'):
    ALL_U21[_column] = ALL_U21[_column].fillna('')

#: a player needs this many minutes before a per-90 rate says anything
MIN_MINUTES_FOR_RATE = 270

# Team color mapping
TEAM_COLORS = {
    "VIPERS": "#DC143C",      # Red
    "KCCA": "#FFD700",        # Yellow
    "VILLA": "#4169E1",       # Royal Blue
    "POLICE": "#00008B",      # Dark Blue
    "ENTEBBE": "#FFD700",     # Yellow
    "KITARA": "#DC143C",      # Red
    "NEC": "#FF8C00",         # Orange
    "BUL": "#FFD700",         # Yellow
    "MAROONS": "#800000",     # Maroon
    "URA": "#FFD700",         # Yellow
    "EXPRESS": "#DC143C",     # Red
    "UPDF": "#4B5320",        # Army Green
    "BUHIMBA": "#90EE90",     # Light Green
    "CALVARY": "#000000",     # Black
    "LUGAZI": "#90EE90",      # Light Green
    "MBARARA": "#1E90FF",     # Dodger Blue
    # clubs new in 2026/27
    "NTUGASAZE": "#DC143C",   # Red
    "BLACKS": "#F08080",      # Light Red
    "KIGEZI": "#4CAF50",      # Leafy Green
    "KATAKA": "#FFF176",      # Light Yellow
}

# -----------------------------------------------------------------------------
# Which competitions are on offer
# -----------------------------------------------------------------------------
# Only league/season pairs that actually carry rows are listed, so a season
# folder that has been created but not yet filled never reaches the picker.
# A season with nothing but U21 exports is listed as well, for the U21 page,
# but is never the one preselected: every other page would open empty.

def _competitions(frames):
    pairs = set()
    for df in frames:
        pairs.update(zip(df['league'].astype(str), df['season'].astype(str)))
    return pairs


MATCH_SEASONS = _competitions((ALL_GOALS, ALL_CAUTIONS, ALL_SUBS))

LEAGUE_SEASONS = {}
for _league, _season in sorted(MATCH_SEASONS | _competitions((ALL_U21,))):
    LEAGUE_SEASONS.setdefault(_league, []).append(_season)
for _league in LEAGUE_SEASONS:                      # newest season first
    LEAGUE_SEASONS[_league] = sorted(LEAGUE_SEASONS[_league], reverse=True)


def seasons_for(league):
    return LEAGUE_SEASONS.get(league, [])


def default_season(league):
    """The newest season with match reports, else the newest of any kind."""
    options = seasons_for(league)
    return next((s for s in options if (league, s) in MATCH_SEASONS),
                options[0] if options else None)


ALL_LEAGUES = sorted(LEAGUE_SEASONS)
DEFAULT_LEAGUE = ALL_LEAGUES[0] if ALL_LEAGUES else ""
DEFAULT_SEASON = (default_season(DEFAULT_LEAGUE) or "") if DEFAULT_LEAGUE else ""


# -----------------------------------------------------------------------------
# Static assets: club logos, the landing photo and the app font
# -----------------------------------------------------------------------------
# Logos sit with the reports, one folder per season
# (reports/<league>/<season>/club_logos), each file named after its club.  Only
# those folders -- never the reports beside them -- are served, at
# logos/<league>/<season>/.

APP_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(APP_DIR / "scripts"))
from clubs import abbreviate  # noqa: E402  (the same club codes as the CSVs)

STATIC_ASSETS = {}
LOGO_SUFFIXES = {'.png', '.svg', '.jpg', '.jpeg', '.webp'}
SEASON_LOGOS = {}          # (league, season) -> {team: url}, as filed

for _folder in sorted((APP_DIR / "reports").glob("*/*/club_logos")):
    _league, _season_dir = _folder.parent.parent.name.upper(), _folder.parent.name
    _mount = f"logos/{_league}/{_season_dir}"
    STATIC_ASSETS["/" + _mount] = _folder
    SEASON_LOGOS[(_league, _season_dir.replace('.', '/'))] = {
        abbreviate(re.sub(r"[-_]+", " ", _file.stem)).upper(): f"{_mount}/{quote(_file.name)}"
        for _file in sorted(_folder.iterdir()) if _file.suffix.lower() in LOGO_SUFFIXES
    }


def logos_for(league, season):
    """Team -> logo URL for one competition.

    The season's own folder wins.  A club without a logo that season borrows
    one from the nearest season that has it, so earlier seasons still show
    logos for clubs that are still around.
    """
    if not str(season)[:4].isdigit():
        return {}
    start = int(str(season)[:4])
    others = [s for (lg, s) in SEASON_LOGOS if lg == league and str(s)[:4].isdigit()]
    found = {}
    for other in sorted(others, key=lambda s: abs(int(s[:4]) - start), reverse=True):
        found.update(SEASON_LOGOS[(league, other)])       # nearest season applied last
    return found


#: every competition's logos, for the dropdown renderers in the browser
CLUB_LOGOS = {league: {season: logos_for(league, season) for season in seasons}
              for league, seasons in LEAGUE_SEASONS.items()}

LANDING_IMAGE = APP_DIR / "visuals" / "nnalubaale_night_effects.jpg"
if LANDING_IMAGE.exists():
    STATIC_ASSETS["/landing-bg.jpg"] = LANDING_IMAGE

# Nexover is a licensed font, so it is not bundled with the code: put the
# licensed files (.woff2 / .woff / .ttf / .otf) in visuals/fonts and every
# weight found there is loaded.  Until then the fallbacks below are used.
APP_FONT = "'Nexover', 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif"
FONT_DIR = APP_DIR / "visuals" / "fonts"
FONT_FORMATS = {'.woff2': 'woff2', '.woff': 'woff', '.ttf': 'truetype', '.otf': 'opentype'}
FONT_WEIGHTS = (('thin', 100), ('extralight', 200), ('light', 300), ('medium', 500),
                ('semibold', 600), ('extrabold', 800), ('bold', 700), ('black', 900))


def _font_face_key(name):
    """(weight, style) read off a font file name, e.g. 'Nexover-BoldItalic.otf'."""
    squashed = re.sub(r"[-_ ]", "", name.lower())
    weight = next((w for word, w in FONT_WEIGHTS if word in squashed), 400)
    return weight, ("italic" if "italic" in squashed else "normal")


_font_files = (sorted(p for p in FONT_DIR.iterdir() if p.suffix.lower() in FONT_FORMATS)
               if FONT_DIR.is_dir() else [])
if _font_files:
    STATIC_ASSETS["/fonts"] = FONT_DIR
_faces = []
for _weight, _style in sorted({_font_face_key(p.name) for p in _font_files}):
    _sources = sorted((p for p in _font_files if _font_face_key(p.name) == (_weight, _style)),
                      key=lambda p: list(FONT_FORMATS).index(p.suffix.lower()))
    _src = ", ".join(f"url('fonts/{quote(p.name)}') format('{FONT_FORMATS[p.suffix.lower()]}')"
                     for p in _sources)
    _faces.append(f"@font-face {{ font-family: 'Nexover'; font-weight: {_weight}; "
                  f"font-style: {_style}; font-display: swap; src: {_src}; }}")
FONT_FACES = "\n".join(_faces)

app_opts(static_assets=STATIC_ASSETS)

# charts pick the font up from the default template
pio.templates["uplstats"] = go.layout.Template(layout={"font": {"family": APP_FONT}})
pio.templates.default = "plotly+uplstats"

ui.tags.style(FONT_FACES + f"""
    :root {{ --bs-body-font-family: {APP_FONT}; --bs-font-sans-serif: {APP_FONT}; }}
    body, button, input, select, textarea, table,
    .selectize-input, .selectize-dropdown {{ font-family: {APP_FONT}; }}

    /* the bar carries no title; the page names speak for themselves */
    .navbar.fixed-top .navbar-brand {{ display: none; }}

    /* club logos in tables, dropdowns and on the team page */
    .club-cell {{ display: inline-flex; align-items: center; gap: 8px; white-space: nowrap; }}
    .club-logo {{ height: 22px; width: 22px; object-fit: contain; flex: none; }}
    .match-cell {{ display: inline-flex; align-items: center; gap: 8px; white-space: nowrap; }}
    .match-cell .vs {{ color: #94A3B8; font-size: 12px; }}
    .club-option {{ display: flex; align-items: center; gap: 8px; }}
    .club-option .club-logo {{ height: 20px; width: 20px; }}
    .team-crest {{ display: flex; justify-content: center; margin: 14px 0 6px 0; }}
    .team-crest img {{ height: 110px; max-width: 100%; object-fit: contain; }}
""")

ui.tags.head(ui.tags.script(
    "window.CLUB_LOGOS = " + json.dumps(CLUB_LOGOS) + ";\n" + """
    // a club's logo for the league and season picked in the bar
    window.clubLogo = function (team) {
        var league = $('#league').val(), season = $('#season').val();
        var logos = (window.CLUB_LOGOS[league] || {})[season] || {};
        var url = logos[String(team || '').toUpperCase()];
        return url ? '<img class="club-logo" src="' + url + '" alt="">' : '';
    };
    // 'option' / 'item' are the classes selectize's own templates carry, and
    // its styling and item handling expect them
    function clubRow(kind, team, label, escape) {
        return '<div class="' + kind + ' club-option">' + window.clubLogo(team)
            + escape(label) + '</div>';
    }
    // selectize renderers: a club dropdown's values are the clubs themselves ...
    window.clubRender = {
        option: function (d, escape) { return clubRow('option', d.value, d.label, escape); },
        item: function (d, escape) { return clubRow('item', d.value, d.label, escape); }
    };
    // ... while players are labelled 'Name (TEAM)', so the club comes from the label
    function playerClub(label) {
        var m = /\\(([^()]+)\\)\\s*$/.exec(label || '');
        return m ? m[1] : '';
    }
    window.playerRender = {
        option: function (d, escape) {
            return clubRow('option', playerClub(d.label), d.label, escape);
        },
        item: function (d, escape) {
            return clubRow('item', playerClub(d.label), d.label, escape);
        }
    };
    """))


# -----------------------------------------------------------------------------
# Reactive slices: everything below reads the selected competition, never the
# full tables, so switching league or season redraws the whole dashboard.
# -----------------------------------------------------------------------------

def _chosen(name, fallback):
    """Read a select that may not exist yet, without silencing the output.

    Reading an unset input raises SilentException, which would blank every
    dependent output on the very first flush.
    """
    value = getattr(input, name)
    return (value() or fallback) if value.is_set() else fallback


def _slice(df):
    league = _chosen("league", DEFAULT_LEAGUE)
    season = _chosen("season", DEFAULT_SEASON)
    return df[(df['league'] == league) & (df['season'] == season)]


@reactive.calc
def goals_df():
    return _slice(ALL_GOALS)


@reactive.calc
def cautions_df():
    return _slice(ALL_CAUTIONS)


@reactive.calc
def subs_df():
    return _slice(ALL_SUBS)


@reactive.calc
def matches_df():
    return _slice(ALL_MATCHES)


@reactive.calc
def team_matches_df():
    return _slice(ALL_TEAM_MATCHES)


@reactive.calc
def comebacks_df():
    return _slice(ALL_COMEBACKS)


@reactive.calc
def lineups_df():
    return _slice(ALL_LINEUPS)


@reactive.calc
def staff_df():
    return _slice(ALL_STAFF)


@reactive.calc
def match_info_df():
    return _slice(ALL_MATCH_INFO)


PROFILE_COLUMNS = ['player_id', 'player', 'team', 'matches', 'starts', 'sub_apps',
                   'minutes', 'goals', 'goals_per_90', 'yellows', 'reds', 'cards',
                   'cards_per_90']


def _norm_name(value):
    return " ".join(str(value).upper().split())


@reactive.calc
def player_profiles():
    """One row per player: minutes, appearances, goals and cards.

    Minutes come from the team sheets, which is the denominator that makes any
    per-90 rate possible.  Goals and cautions carry only a printed name, so each
    is matched back to that match's team sheet to pick up the player's
    registration id -- and the rows are keyed on the id, not the name, because
    the same player is spelled inconsistently between reports.
    """
    squad = lineups_df()
    if squad.empty:
        return pd.DataFrame(columns=PROFILE_COLUMNS)

    lookup = {(row.game, _norm_name(row.player)): row.player_id
              for row in squad.itertuples()}

    played = squad[squad['minutes_played'] > 0]
    profile = played.groupby('player_id').agg(
        player=('player', 'first'),
        team=('team', 'first'),
        matches=('game', 'nunique'),
        minutes=('minutes_played', 'sum'),
        starts=('role', lambda s: (s == 'starting').sum()),
        sub_apps=('role', lambda s: (s == 'substitute').sum()),
    ).reset_index()

    def tally(frame):
        """Count events per registration id."""
        if frame.empty:
            return {}
        found = [lookup.get((row.game, _norm_name(row.player)))
                 for row in frame.itertuples()]
        return pd.Series([i for i in found if i]).value_counts().to_dict()

    cautions = cautions_df()
    dismissals = cautions[cautions['caution'].isin(['red', 'second yellow'])] \
        if not cautions.empty else cautions
    bookings = cautions[cautions['caution'] == 'yellow'] \
        if not cautions.empty else cautions

    for column, counts in (('goals', tally(goals_df())),
                           ('yellows', tally(bookings)),
                           ('reds', tally(dismissals))):
        profile[column] = profile['player_id'].map(counts).fillna(0).astype(int)

    profile['cards'] = profile['yellows'] + profile['reds']
    profile['goals_per_90'] = (profile['goals'] / profile['minutes'] * 90).round(2)
    profile['cards_per_90'] = (profile['cards'] / profile['minutes'] * 90).round(2)
    return profile.sort_values('minutes', ascending=False)[PROFILE_COLUMNS]


def player_label(row):
    """'Name (TEAM)' -- team included because names repeat across squads."""
    return f"{row['player']} ({row['team']})"


@reactive.calc
def u21_df():
    return _slice(ALL_U21)


U21_TOTAL_COLUMNS = (['player_key', 'player', 'team', 'position', 'birth_year',
                      'debut_md'] + U21_SUM_COLUMNS
                     + ['ga', 'ga_per_90', 'cards', 'team_ppg'])


def u21_totals(rows):
    """Totals per U21 player over whatever matchday rows are passed in.

    Rates are rebuilt from the summed counts -- never averaged -- and per-90
    only once a player reaches MIN_MINUTES_FOR_RATE, which also keeps a 0-minute
    stoppage-time cameo out of any division.  Assists stay blank for a player
    whose matchdays all came from the match reports, which do not record them.
    """
    if rows.empty:
        return pd.DataFrame(columns=U21_TOTAL_COLUMNS)
    rows = rows.sort_values('md')
    grouped = rows.groupby('player_key')
    totals = grouped[U21_SUM_COLUMNS].sum(min_count=1)
    known = [c for c in U21_SUM_COLUMNS if c not in U21_EXPORT_ONLY]
    totals[known] = totals[known].fillna(0).astype(int)
    totals['player'] = grouped['player'].last()
    totals['team'] = grouped['team'].last()
    totals['position'] = (rows.assign(position=rows['position'].replace('', np.nan))
                              .groupby('player_key')['position'].last())
    totals['birth_year'] = grouped['birth_year'].max()

    played = rows[rows['apps'] > 0]
    totals['debut_md'] = played.groupby('player_key')['md'].min()
    points = played.groupby('player_key')[['team_points', 'team_matches']].sum(min_count=1)
    totals['team_ppg'] = (points['team_points'] / points['team_matches']).round(2)

    totals['ga'] = totals['goals'] + totals['assists'].fillna(0)
    totals['ga_per_90'] = np.where(totals['minutes'] >= MIN_MINUTES_FOR_RATE,
                                   (totals['ga'] / totals['minutes'] * 90).round(2),
                                   np.nan)
    totals['cards'] = (totals['yellows'] + totals['reds_direct']
                       + totals['reds_second_yellow'])
    totals = totals.reset_index()
    totals['position'] = totals['position'].fillna('')
    return totals.sort_values(['minutes', 'ga'], ascending=False)[U21_TOTAL_COLUMNS]


@reactive.calc
def u21_season():
    return u21_totals(u21_df())


@reactive.calc
def referee_record():
    """Matches and cards per referee, from the match headers."""
    info = match_info_df()
    if info.empty or 'referee' not in info.columns:
        return pd.DataFrame(columns=['referee', 'matches', 'cards', 'cards_per_match'])

    named = info[info['referee'].notna() & (info['referee'].astype(str) != '')]
    if named.empty:
        return pd.DataFrame(columns=['referee', 'matches', 'cards', 'cards_per_match'])

    cards_by_game = cautions_df().groupby('game').size()
    named = named.assign(cards=named['game'].map(cards_by_game).fillna(0).astype(int))
    table = named.groupby('referee').agg(
        matches=('game', 'nunique'), cards=('cards', 'sum')).reset_index()
    table['cards_per_match'] = (table['cards'] / table['matches']).round(2)
    return table.sort_values(['cards_per_match', 'matches'], ascending=False)


@reactive.calc
def teams():
    found = set()
    for df in (goals_df(), cautions_df(), subs_df()):
        found.update(df['team'].dropna().astype(str).unique())
    return sorted(t for t in found if t.lower() != 'nan' and t.strip() != '')


@reactive.calc
def matchdays():
    found = set()
    for df in (goals_df(), cautions_df(), subs_df()):
        found.update(int(md) for md in df['md'].unique() if pd.notna(md))
    return sorted(found)


def selected_md():
    """The chosen matchday as an int, or None before the select is populated."""
    raw = _chosen("selected_matchday", None)
    available = matchdays()
    if raw and int(raw) in available:
        return int(raw)
    # the select still holds the previous competition's matchday for one tick
    return available[0] if available else None


def selected_team():
    """The chosen team, or None before the select is populated."""
    raw = _chosen("selected_team", None)
    available = teams()
    if raw in available:
        return raw
    return available[0] if available else None

@reactive.calc
def club_logos():
    """Team -> logo URL for the league and season picked in the bar."""
    return logos_for(_chosen("league", DEFAULT_LEAGUE), _chosen("season", DEFAULT_SEASON))


def club_html(team):
    """A club name led by its logo, as escaped table-cell HTML."""
    name = html.escape(str(team))
    url = club_logos().get(str(team).upper())
    if not url:
        return name
    return (f'<span class="club-cell"><img class="club-logo" src="{url}" alt="" '
            f'loading="lazy">{name}</span>')


def match_html(game):
    """A 'HOME-vs-AWAY' game key with both clubs' logos."""
    sides = re.split(r"-vs-", str(game), flags=re.IGNORECASE)
    if len(sides) != 2:
        return html.escape(str(game))
    home, away = (side.strip() for side in sides)
    return (f'<span class="match-cell">{club_html(home)}<span class="vs">vs</span>'
            f'{club_html(away)}</span>')


def logo_table(data, clubs=(), matches=()):
    """A table ready for @render.table(escape=False).

    Club and match columns get their logos; every other text cell is escaped
    here instead, since the renderer no longer does it.
    """
    data = data.copy()
    for column in data.columns:
        if column in clubs:
            data[column] = data[column].map(club_html)
        elif column in matches:
            data[column] = data[column].map(match_html)
        else:
            data[column] = data[column].map(
                lambda value: html.escape(value) if isinstance(value, str) else value)
    return data


# Helper function for team-colored headers
def get_team_header_style(team):
    """Generate header style based on team color, with the club's logo at the right"""
    color = TEAM_COLORS.get(team, "#1a5f7a")
    logo = club_logos().get(str(team).upper())
    layers = f"url('{logo}') no-repeat right 14px center / auto 70%, " if logo else ""
    return f"background: {layers}{color} !important; color: white; border-radius: 15px 15px 0 0 !important; font-weight: bold; font-size: 16px; padding: 15px;"

# Process caution colors (yellow, red, second yellow)
def get_caution_color(row):
    """Normalise a caution row to one of the three keys in CAUTION_COLORS.

    A second yellow is stored as caution='second yellow' with double-caution
    ='yes'; the double-caution flag alone is also honoured so a row entered
    either way lands in the same bucket.  Rows with no card type recorded are
    labelled rather than left as NaN, which used to show up as a 'nan' slice.
    """
    caution = str(row['caution']).strip().lower()
    double = str(row['double-caution']).strip().lower() in ('yes', 'y', 'true')
    if caution in ('second yellow', 'second_yellow') or (caution == 'yellow' and double):
        return 'second yellow'
    if caution in ('', 'nan', 'none'):
        return 'not recorded'
    return caution

ALL_CAUTIONS['caution_display'] = ALL_CAUTIONS.apply(get_caution_color, axis=1)

# Caution color mapping
CAUTION_COLORS = {
    'yellow': '#E8B400',        # darkened for contrast against white cards
    'red': '#FF0000',
    'second yellow': '#FF8C00',  # Orange for second yellow
    'not recorded': '#BDC3C7'    # Grey for rows with no card type in the source
}

# Standard football time buckets, with stoppage time kept out of the next bucket
MINUTE_BUCKETS = ['0-15', '16-30', '31-45', '45+', '46-60', '61-75', '76-90', '90+']

def minute_bucket(base_minute, stoppage):
    """Place an event in a standard 15-minute bucket.

    Uses the un-inflated minute, so a 45(+2) goal lands in '45+' rather than
    being counted as a 47th-minute event in the second half.
    """
    if stoppage > 0:
        return '45+' if base_minute <= 45 else '90+'
    if base_minute <= 15:
        return '0-15'
    if base_minute <= 30:
        return '16-30'
    if base_minute <= 45:
        return '31-45'
    if base_minute <= 60:
        return '46-60'
    if base_minute <= 75:
        return '61-75'
    if base_minute <= 90:
        return '76-90'
    return '90+'

def empty_figure(message="No data recorded for this season yet"):
    """A blank plot carrying an explanation.

    A season folder can exist before any match reports land in it, so every
    chart needs something sensible to show for an empty selection.
    """
    fig = go.Figure()
    fig.add_annotation(text=message, showarrow=False,
                       xref="paper", yref="paper", x=0.5, y=0.5,
                       font=dict(size=14, color="#888"))
    fig.update_layout(
        xaxis=dict(visible=False), yaxis=dict(visible=False),
        plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)'
    )
    return fig


def _axis_top(trace, axis):
    """The largest value one trace puts on an axis.

    A histogram carries raw values, not counts, so the tallest bar on its count
    axis is estimated by binning those values the same number of ways.
    """
    values = getattr(trace, axis)
    if trace.type == 'histogram' and values is None:
        other = 'x' if axis == 'y' else 'y'
        raw = getattr(trace, other)          # an array: never test it for truth
        raw = pd.to_numeric(pd.Series(list(raw) if raw is not None else []),
                            errors='coerce').dropna()
        if raw.empty:
            return 0
        bins = getattr(trace, f'nbins{other}') or 10
        return int(np.histogram(raw, bins=bins)[0].max())
    numbers = pd.to_numeric(pd.Series(list(values if values is not None else [])),
                            errors='coerce').dropna()
    return numbers.max() if not numbers.empty else 0


def whole_numbers(fig, *axes):
    """Whole-number ticks on count axes -- nobody scores 1.5 goals.

    Plotly steps its ticks in halves once a range gets small, so up to ten a tick
    is pinned to every unit; above that its own steps are whole already and only
    the formatting is fixed.  Averages and percentages are left alone.
    """
    for axis in axes:
        top = max((_axis_top(trace, axis) for trace in fig.data), default=0)
        settings = {'tickformat': ',d'}
        if top <= 10:
            settings.update(tick0=0, dtick=1)
        (fig.update_xaxes if axis == 'x' else fig.update_yaxes)(**settings)
    return fig


def count_axes(*axes):
    """Chart decorator: the named axes ('x', 'y') hold counts, so tick them in whole numbers."""
    def decorate(chart):
        @functools.wraps(chart)
        def wrapped():
            return whole_numbers(chart(), *axes)
        return wrapped
    return decorate


def bucket_counts(df):
    """Count events per time bucket, keeping empty buckets so the axis is stable."""
    labels = [minute_bucket(b, s) for b, s in zip(df['base_minute'], df['stoppage'])]
    counts = pd.Series(labels).value_counts()
    return pd.DataFrame({
        'bucket': MINUTE_BUCKETS,
        'count': [int(counts.get(b, 0)) for b in MINUTE_BUCKETS],
    })

# -----------------------------------------------------------------------------
# League tables, built from the match rows wrangle.py reconstructs
# -----------------------------------------------------------------------------

def league_table(venue=None, upto_md=None, md=None, form_games=5):
    """Standings from the team-match rows, optionally home-only or away-only.

    `upto_md` gives the cumulative table after that matchday; `md` gives that
    single matchday only.
    """
    data = team_matches_df()
    if venue is not None:
        data = data[data['venue'] == venue]
    if upto_md is not None:
        data = data[data['md'] <= upto_md]
    if md is not None:
        data = data[data['md'] == md]

    if data.empty:
        return pd.DataFrame(columns=['Pos', 'Team', 'P', 'W', 'D', 'L',
                                     'GF', 'GA', 'GD', 'Pts', 'Form'])

    grouped = data.groupby('team')
    table = pd.DataFrame({
        'Team': grouped.size().index,
        'P': grouped.size().values,
        'W': grouped['result'].apply(lambda s: (s == 'W').sum()).values,
        'D': grouped['result'].apply(lambda s: (s == 'D').sum()).values,
        'L': grouped['result'].apply(lambda s: (s == 'L').sum()).values,
        'GF': grouped['gf'].sum().values,
        'GA': grouped['ga'].sum().values,
        'Pts': grouped['points'].sum().values,
    })
    table['GD'] = table['GF'] - table['GA']

    form = (data.sort_values('md')
                .groupby('team')['result']
                .apply(lambda s: ' '.join(s.tail(form_games))))
    table['Form'] = table['Team'].map(form)

    table = table.sort_values(['Pts', 'GD', 'GF', 'Team'],
                              ascending=[False, False, False, True]).reset_index(drop=True)
    table.insert(0, 'Pos', range(1, len(table) + 1))
    return table[['Pos', 'Team', 'P', 'W', 'D', 'L', 'GF', 'GA', 'GD', 'Pts', 'Form']]


def results_table(md):
    """Every scoreline played on one matchday."""
    data = matches_df()
    played = data[data['md'] == md].sort_values('game') if md is not None else data.iloc[0:0]
    if played.empty:
        return pd.DataFrame(columns=['Home', 'Score', 'Away'])
    return pd.DataFrame({
        'Home': played['home'].values,
        'Score': [f"{h} - {a}" for h, a in zip(played['home_goals'], played['away_goals'])],
        'Away': played['away'].values,
    })

SOURCE_NOTE = ("Scorelines are reconstructed from the recorded goal events, so a "
               "match whose goals are missing from the source data shows as 0-0.")

# Both counters read the reactive slices, so they are only valid inside a render
# function or another reactive context.
def _unique_games(column, value):
    found = set()
    for df in (goals_df(), cautions_df(), subs_df()):
        found.update(df[df[column] == value]['game'].dropna().str.upper().unique())
    return found

# Helper function to count matches for a team across all dataframes
def count_team_matches(team):
    """Count unique games involving a team across all dataframes"""
    return len(_unique_games('team', team))

# Helper function to count matches in a matchday
def count_matchday_games(md):
    """Count unique games in a matchday"""
    return 0 if md is None else len(_unique_games('md', md))

# Head assets: favicon, Tailwind, and the scroll listener that tightens the bar.
#
# Tailwind's preflight is switched off on purpose. Shiny's cards, pills, tables
# and form controls are Bootstrap components, and preflight would strip their
# styling out from under them. Utilities still work; only the global reset is off.
ui.tags.head(
    ui.tags.link(
        rel="icon",
        type="image/png",
        href="https://lh3.googleusercontent.com/pw/AP1GczO8jLa3k1wKyHVCS02hp3FRiHo"
    ),
    ui.tags.script(src="https://cdn.tailwindcss.com"),
    ui.tags.script(
        """
        if (window.tailwind) {
            tailwind.config = {
                // Utilities are prefixed because Tailwind and Bootstrap share
                // several class names, and Tailwind's win by load order. The
                // damaging one is `collapse`: Bootstrap uses it on the navbar's
                // item container, Tailwind defines it as `visibility: collapse`,
                // and the whole nav disappears. `container`, `hidden`, `shadow`
                // and `rounded` collide the same way. Write utilities as
                // `tw-flex`, `tw-gap-2`, and Bootstrap keeps its own classes.
                prefix: 'tw-',
                corePlugins: { preflight: false },
                theme: { extend: { colors: {
                    brand: { DEFAULT: '#F5901F', dark: '#D97706', deep: '#0F172A' }
                } } }
            };
        }
        """
    ),
    ui.tags.script(
        """
        // Floating bar: hangs below the top edge, then tucks in on scroll.
        document.addEventListener('DOMContentLoaded', function () {
            var onScroll = function () {
                var bar = document.querySelector('.navbar');
                if (bar) bar.classList.toggle('navbar-scrolled', window.scrollY > 20);
            };
            window.addEventListener('scroll', onScroll, { passive: true });
            onScroll();
        });
        """
    ),
)


# -----------------------------------------------------------------------------
# Landing gate: pick a league, then a season, before the dashboard is usable.
# -----------------------------------------------------------------------------

entered = reactive.value(False)


@render.ui
def landing_overlay():
    """Full-screen chooser, shown until a competition has been picked.

    It deliberately does not read its own selects: they do not exist on the
    first paint, and reading an unset input would suppress the whole output and
    leave the gate invisible.  _landing_seasons keeps the season list current
    after that.
    """
    if entered():
        return None

    league = DEFAULT_LEAGUE
    return ui.tags.div(
        {"class": "landing-overlay"},
        ui.tags.div(
            {"class": "landing-card"},
            ui.tags.p({"class": "landing-eyebrow"}, "Football Statistics"),
            ui.tags.h1({"class": "landing-title"}, "Match Report Dashboard"),
            ui.tags.p(
                {"class": "landing-sub"},
                "Choose a competition and a season to explore goals, discipline, "
                "substitutions and form."
            ),
            ui.tags.div(
                {"class": "landing-fields"},
                ui.input_select(
                    "landing_league", "League",
                    choices={code: code for code in ALL_LEAGUES},
                    selected=league,
                ),
                ui.input_select(
                    "landing_season", "Season",
                    choices={s: s for s in seasons_for(league)},
                    selected=default_season(league),
                ),
            ),
            ui.input_action_button("enter_dashboard", "View dashboard",
                                   class_="landing-button"),
        ),
    )


@reactive.effect
@reactive.event(input.landing_league)
def _landing_seasons():
    """Keep the overlay's season list in step with the league picked above it."""
    options = seasons_for(input.landing_league())
    ui.update_select("landing_season",
                     choices={s: s for s in options},
                     selected=default_season(input.landing_league()))


@reactive.effect
@reactive.event(input.enter_dashboard)
def _enter_dashboard():
    """Copy the overlay's choice onto the navbar selects, then step aside.

    The navbar selects are the single source of truth: every reactive slice
    reads input.league()/input.season(), never the landing inputs.
    """
    league = input.landing_league() or DEFAULT_LEAGUE
    season = input.landing_season() or default_season(league) or ""
    ui.update_select("league", choices={c: c for c in ALL_LEAGUES}, selected=league)
    ui.update_select("season", choices={s: s for s in seasons_for(league)}, selected=season)
    entered.set(True)


@reactive.effect
@reactive.event(input.league)
def _navbar_seasons():
    """Switching league in the navbar re-offers that league's seasons."""
    options = seasons_for(input.league())
    if not options:
        return
    with reactive.isolate():
        current = _chosen("season", None)
    ui.update_select("season",
                     choices={s: s for s in options},
                     selected=current if current in options else default_season(input.league()))


with ui.navset_bar(
    title="",
    id="page",
    navbar_options=ui.navbar_options(position="fixed-top", theme="dark", bg="#F5901F"),
):
    
    # =============================================================================
    # PAGE 1: GENERAL OVERVIEW
    # =============================================================================
    with ui.nav_panel("General Overview"):
        with ui.navset_pill(id="overview_tab"):
            
            with ui.nav_panel("Summary"):
                # Key metrics row
                with ui.layout_columns(col_widths=[3, 3, 3, 3], style="margin: 20px 0;"):
                    with ui.div(class_="stat-card goals"):
                        @render.text
                        def total_goals_count():
                            return str(len(goals_df()))
                        ui.p("Total Goals")
                    with ui.div(class_="stat-card cards"):
                        @render.text
                        def total_cards_count():
                            return str(len(cautions_df()))
                        ui.p("Cards")
                    with ui.div(class_="stat-card subs"):
                        @render.text
                        def total_subs_count():
                            return str(len(subs_df()))
                        ui.p("Substitutions")
                    with ui.div(class_="stat-card matches"):
                        @render.text
                        def total_matches_count():
                            return str(len(matches_df()))
                        ui.p("Matches")

                # Charts row 1
                with ui.layout_columns(col_widths=[6, 6], style="margin: 20px 0;"):
                    with ui.card():
                        ui.tags.div("Goals per Team", class_="overview-card-header")
                        @render_plotly
                        @count_axes('x')
                        def goals_by_team():
                            team_goals = goals_df().groupby('team').size().reset_index(name='goals')
                            team_goals = team_goals.sort_values('goals', ascending=True)
                            # Map team colors
                            team_goals['color'] = team_goals['team'].map(TEAM_COLORS)
                            fig = px.bar(
                                team_goals, 
                                x='goals', 
                                y='team', 
                                orientation='h',
                                color='team',
                                color_discrete_map=TEAM_COLORS,
                                title='Total Goals Scored by Each Team'
                            )
                            fig.update_layout(
                                showlegend=False,
                                plot_bgcolor='rgba(0,0,0,0)',
                                paper_bgcolor='rgba(0,0,0,0)',
                                font=dict(size=12)
                            )
                            return fig
                    
                    with ui.card():
                        ui.tags.div("Cards Distribution", class_="overview-card-header")
                        @render_plotly
                        def cards_distribution():
                            if cautions_df().empty:
                                return empty_figure()
                            card_counts = cautions_df().groupby('caution_display').size().reset_index(name='count')
                            fig = px.pie(
                                card_counts, 
                                values='count', 
                                names='caution_display',
                                color='caution_display',
                                color_discrete_map=CAUTION_COLORS,
                                title='Distribution of Cards (Yellow/Red/Second Yellow)',
                                hole=0.4
                            )
                            fig.update_layout(
                                plot_bgcolor='rgba(0,0,0,0)',
                                paper_bgcolor='rgba(0,0,0,0)'
                            )
                            return fig

                # Charts row 2
                with ui.layout_columns(col_widths=[6, 6], style="margin: 20px 0;"):
                    with ui.card():
                        ui.tags.div("Goals by Matchday", class_="overview-card-header")
                        @render_plotly
                        @count_axes('x', 'y')
                        def goals_by_matchday():
                            md_goals = goals_df().groupby('md').size().reset_index(name='goals')
                            fig = px.line(
                                md_goals, 
                                x='md', 
                                y='goals',
                                markers=True,
                                title='Goals Scored Across Matchdays',
                                labels={'md': 'Matchday', 'goals': 'Goals'}
                            )
                            fig.update_traces(line_color='#2ecc71', line_width=3)
                            fig.update_layout(
                                plot_bgcolor='rgba(0,0,0,0)',
                                paper_bgcolor='rgba(0,0,0,0)'
                            )
                            return fig
                    
                    with ui.card():
                        ui.tags.div("Goals by Period (Half)", class_="overview-card-header")
                        @render_plotly
                        @count_axes('y')
                        def goals_by_period():
                            period_goals = goals_df().groupby('period').size().reset_index(name='goals')
                            period_goals['period'] = period_goals['period'].map({1: 'First Half', 2: 'Second Half'})
                            colors = ['#3498db', '#e74c3c']
                            fig = px.bar(
                                period_goals, 
                                x='period', 
                                y='goals',
                                color='period',
                                color_discrete_sequence=colors,
                                title='Goals by Match Period'
                            )
                            fig.update_layout(
                                showlegend=False,
                                plot_bgcolor='rgba(0,0,0,0)',
                                paper_bgcolor='rgba(0,0,0,0)'
                            )
                            return fig

                # Top scorers table
                with ui.layout_columns(col_widths=[12], style="margin: 20px 0;"):
                    with ui.card():
                        ui.tags.div("Top 15 Goal Scorers", class_="overview-card-header")
                        @render.table(escape=False)
                        def top_scorers():
                            scorer_goals = goals_df().groupby(['player', 'team']).size().reset_index(name='goals')
                            scorer_goals = scorer_goals.sort_values('goals', ascending=False).head(15)
                            scorer_goals.columns = ['Player', 'Team', 'Goals']
                            return logo_table(scorer_goals, clubs=['Team'])

            with ui.nav_panel("Detailed Analysis"):
                with ui.layout_columns(col_widths=[6, 6], style="margin: 20px 0;"):
                    with ui.card():
                        ui.tags.div("Cards per Team", class_="overview-card-header")
                        @render_plotly
                        @count_axes('x')
                        def cards_by_team():
                            team_cards = cautions_df().groupby('team').size().reset_index(name='cards')
                            team_cards = team_cards.sort_values('cards', ascending=True)
                            fig = px.bar(
                                team_cards, 
                                x='cards', 
                                y='team', 
                                orientation='h',
                                color='team',
                                color_discrete_map=TEAM_COLORS,
                                title='Total Cards Received by Each Team'
                            )
                            fig.update_layout(
                                showlegend=False,
                                plot_bgcolor='rgba(0,0,0,0)',
                                paper_bgcolor='rgba(0,0,0,0)'
                            )
                            return fig
                    
                    with ui.card():
                        ui.tags.div("When Goals Are Scored", class_="overview-card-header")
                        @render_plotly
                        @count_axes('y')
                        def goals_timing_profile():
                            # Standard football time buckets. Stoppage time gets its
                            # own bucket at the end of each half instead of being
                            # folded into the minutes that follow it.
                            counts = bucket_counts(goals_df())
                            counts['half'] = ['First Half'] * 4 + ['Second Half'] * 4
                            fig = px.bar(
                                counts,
                                x='bucket',
                                y='count',
                                color='half',
                                color_discrete_map={'First Half': '#3498db',
                                                    'Second Half': '#e74c3c'},
                                category_orders={'bucket': MINUTE_BUCKETS},
                                title='Goals by Period of the Match',
                                labels={'bucket': 'Minute', 'count': 'Goals', 'half': ''}
                            )
                            fig.update_layout(
                                plot_bgcolor='rgba(0,0,0,0)',
                                paper_bgcolor='rgba(0,0,0,0)'
                            )
                            return fig

                with ui.layout_columns(col_widths=[6, 6], style="margin: 20px 0;"):
                    with ui.card():
                        ui.tags.div("Substitution Timing Distribution", class_="overview-card-header")
                        @render_plotly
                        @count_axes('y')
                        def subs_timing():
                            fig = px.histogram(
                                subs_df(), 
                                x='minute',
                                nbins=15,
                                title='Substitutions by Minute of Match',
                                labels={'minute': 'Minute', 'count': 'Number of Substitutions'},
                                color_discrete_sequence=['#3498db']
                            )
                            fig.update_layout(
                                plot_bgcolor='rgba(0,0,0,0)',
                                paper_bgcolor='rgba(0,0,0,0)'
                            )
                            return fig
                    
                    with ui.card():
                        ui.tags.div("Team Comparison: Goals vs Cards", class_="overview-card-header")
                        @render_plotly
                        @count_axes('x', 'y')
                        def goals_vs_cards():
                            team_stats = pd.DataFrame({
                                'team': teams()
                            })
                            team_goals = goals_df().groupby('team').size().reset_index(name='goals')
                            team_cards = cautions_df().groupby('team').size().reset_index(name='cards')
                            team_stats = team_stats.merge(team_goals, on='team', how='left')
                            team_stats = team_stats.merge(team_cards, on='team', how='left')
                            team_stats = team_stats.fillna(0)
                            
                            fig = px.scatter(
                                team_stats,
                                x='goals',
                                y='cards',
                                size='goals',
                                hover_name='team',
                                color='team',
                                color_discrete_map=TEAM_COLORS,
                                title='Goals vs Cards (Team Comparison)',
                                labels={'goals': 'Goals Scored', 'cards': 'Cards Received'}
                            )
                            fig.update_layout(
                                plot_bgcolor='rgba(0,0,0,0)',
                                paper_bgcolor='rgba(0,0,0,0)'
                            )
                            return fig

            with ui.nav_panel("Comebacks & Collapses"):
                ui.tags.p(
                    "A team is 'in a losing position' once it goes behind at any point "
                    "in a match, and 'in a winning position' once it leads. Points from "
                    "a losing position are the points it still took; points dropped from "
                    "a winning position are the three it did not. Only teams with something "
                    "to show are listed: at least a point, a win or a defeat from the "
                    "position in question, and at least 2 points dropped after leading. "
                    + SOURCE_NOTE,
                    style="margin: 20px 10px 0 10px; color: #555;"
                )

                #: the least a team needs to appear: one point rescued from behind, or
                #: two dropped from ahead -- which is a single draw after leading
                MIN_COMEBACK_POINTS = 1
                MIN_COLLAPSE_POINTS = 2

                def at_least(column, minimum):
                    """Teams with at least `minimum` in one column, lowest first for a barh."""
                    data = comebacks_df()
                    return data[data[column] >= minimum].sort_values(column)

                with ui.layout_columns(col_widths=[6, 6], style="margin: 20px 0;"):
                    with ui.card():
                        ui.tags.div("Points Won From a Losing Position",
                                    class_="overview-card-header")
                        @render_plotly
                        @count_axes('x')
                        def points_from_losing():
                            data = at_least('points_from_losing', MIN_COMEBACK_POINTS)
                            if data.empty:
                                return empty_figure("No team has taken a point after going behind yet")
                            fig = px.bar(
                                data, x='points_from_losing', y='team', orientation='h',
                                color='team', color_discrete_map=TEAM_COLORS,
                                hover_data=['wins_from_losing', 'draws_from_losing',
                                            'matches_behind'],
                                title='Points Rescued After Going Behind',
                                labels={'points_from_losing': 'Points', 'team': ''}
                            )
                            fig.update_layout(
                                showlegend=False,
                                plot_bgcolor='rgba(0,0,0,0)',
                                paper_bgcolor='rgba(0,0,0,0)'
                            )
                            return fig

                    with ui.card():
                        ui.tags.div("Points Dropped From a Winning Position",
                                    class_="overview-card-header")
                        @render_plotly
                        @count_axes('x')
                        def points_dropped_from_winning():
                            data = at_least('points_dropped_from_winning', MIN_COLLAPSE_POINTS)
                            if data.empty:
                                return empty_figure("No team has dropped points after leading yet")
                            fig = px.bar(
                                data, x='points_dropped_from_winning', y='team',
                                orientation='h',
                                color='team', color_discrete_map=TEAM_COLORS,
                                hover_data=['losses_from_winning', 'draws_from_winning',
                                            'matches_ahead'],
                                title='Points Thrown Away After Leading',
                                labels={'points_dropped_from_winning': 'Points', 'team': ''}
                            )
                            fig.update_layout(
                                showlegend=False,
                                plot_bgcolor='rgba(0,0,0,0)',
                                paper_bgcolor='rgba(0,0,0,0)'
                            )
                            return fig

                with ui.layout_columns(col_widths=[6, 6], style="margin: 20px 0;"):
                    with ui.card():
                        ui.tags.div("Wins From a Losing Position",
                                    class_="overview-card-header")
                        @render_plotly
                        @count_axes('x')
                        def wins_from_losing():
                            data = at_least('wins_from_losing', 1)
                            if data.empty:
                                return empty_figure("No team has won after going behind yet")
                            fig = px.bar(
                                data, x='wins_from_losing', y='team', orientation='h',
                                color='team', color_discrete_map=TEAM_COLORS,
                                hover_data=['matches_behind'],
                                title='Matches Won After Going Behind',
                                labels={'wins_from_losing': 'Wins', 'team': ''}
                            )
                            fig.update_layout(
                                showlegend=False,
                                plot_bgcolor='rgba(0,0,0,0)',
                                paper_bgcolor='rgba(0,0,0,0)'
                            )
                            return fig

                    with ui.card():
                        ui.tags.div("Games Lost From a Winning Position",
                                    class_="overview-card-header")
                        @render_plotly
                        @count_axes('x')
                        def losses_from_winning():
                            data = at_least('losses_from_winning', 1)
                            if data.empty:
                                return empty_figure("No team has lost after leading yet")
                            fig = px.bar(
                                data, x='losses_from_winning', y='team', orientation='h',
                                color='team', color_discrete_map=TEAM_COLORS,
                                hover_data=['matches_ahead'],
                                title='Matches Lost After Leading',
                                labels={'losses_from_winning': 'Defeats', 'team': ''}
                            )
                            fig.update_layout(
                                showlegend=False,
                                plot_bgcolor='rgba(0,0,0,0)',
                                paper_bgcolor='rgba(0,0,0,0)'
                            )
                            return fig

                with ui.layout_columns(col_widths=[12], style="margin: 20px 0;"):
                    with ui.card():
                        ui.tags.div("Comeback & Collapse Summary",
                                    class_="overview-card-header")
                        @render.table(escape=False)
                        def comebacks_summary():
                            table = comebacks_df()
                            table = table[
                                (table['points_from_losing'] >= MIN_COMEBACK_POINTS)
                                | (table['points_dropped_from_winning'] >= MIN_COLLAPSE_POINTS)]
                            if table.empty:
                                return pd.DataFrame(
                                    {"": ["No comebacks or collapses recorded yet"]})
                            table = table.sort_values(
                                ['points_from_losing', 'wins_from_losing'],
                                ascending=False)
                            table = table[['team', 'matches', 'matches_behind',
                                           'points_from_losing', 'wins_from_losing',
                                           'draws_from_losing', 'matches_ahead',
                                           'points_dropped_from_winning',
                                           'losses_from_winning', 'draws_from_winning']]
                            table.columns = ['Team', 'P', 'Times Behind', 'Pts From Behind',
                                             'Wins From Behind', 'Draws From Behind',
                                             'Times Ahead', 'Pts Dropped', 'Lost From Ahead',
                                             'Drew From Ahead']
                            return logo_table(table, clubs=['Team'])

    # =============================================================================
    # PAGE 2: MATCHDAY ANALYSIS
    # =============================================================================
    with ui.nav_panel("Matchday Analysis"):
        with ui.layout_sidebar():
            with ui.sidebar():
                ui.h5("Filter by Matchday")
                ui.input_select("selected_matchday", "Select Matchday:", choices={})

                @reactive.effect
                def _refresh_matchdays():
                    """Repopulate the matchday list whenever the competition changes.

                    The current value is read in isolation: depending on the very
                    input this effect writes would make it retrigger itself.
                    """
                    available = matchdays()
                    with reactive.isolate():
                        current = _chosen("selected_matchday", None)
                    ui.update_select(
                        "selected_matchday",
                        choices={str(md): f"Matchday {md}" for md in available},
                        selected=(current if current in {str(m) for m in available}
                                  else (str(available[0]) if available else None)),
                    )

                ui.hr()
                ui.h5("Matchday Statistics")
                @render.text
                def matchday_stats():
                    """Display summary statistics for selected matchday"""
                    md = selected_md()
                    if md is None:
                        return "No matchdays in this season yet."
                    md_goals = len(goals_df()[goals_df()['md'] == md])
                    md_cards = len(cautions_df()[cautions_df()['md'] == md])
                    md_subs = len(subs_df()[subs_df()['md'] == md])
                    md_matches = count_matchday_games(md)
                    return f"Goals: {md_goals} | Cards: {md_cards} | Subs: {md_subs} | Matches: {md_matches}"
            
            with ui.navset_pill(id="matchday_tab"):
                
                with ui.nav_panel("Overview"):
                    with ui.layout_columns(col_widths=[3, 3, 3, 3], style="margin: 20px 0;"):
                        with ui.div(class_="stat-card goals"):
                            @render.text
                            def md_goals_count():
                                md_goals = len(goals_df()[goals_df()['md'] == selected_md()])
                                return str(md_goals)
                            ui.p("Goals")
                        with ui.div(class_="stat-card cards"):
                            @render.text
                            def md_cards_count():
                                md_cards = len(cautions_df()[cautions_df()['md'] == selected_md()])
                                return str(md_cards)
                            ui.p("Cards")
                        with ui.div(class_="stat-card subs"):
                            @render.text
                            def md_subs_count():
                                md_subs = len(subs_df()[subs_df()['md'] == selected_md()])
                                return str(md_subs)
                            ui.p("Substitutions")
                        with ui.div(class_="stat-card matches"):
                            @render.text
                            def md_matches_count():
                                return str(count_matchday_games(selected_md()))
                            ui.p("Matches")

                    with ui.layout_columns(col_widths=[6, 6], style="margin: 20px 0;"):
                        with ui.card():
                            ui.tags.div("Goals Distribution by Minute", class_="overview-card-header")
                            @render_plotly
                            def md_goals_timeline():
                                md_data = goals_df()[goals_df()['md'] == selected_md()].copy()
                                if md_data.empty:
                                    return empty_figure("No goals recorded on this matchday")
                                # period is 1/2, and a discrete colour map only
                                # applies to a categorical column
                                md_data['half'] = md_data['period'].map(
                                    {1: 'First Half', 2: 'Second Half'})
                                fig = px.scatter(
                                    md_data,
                                    x='minute',
                                    y='game',
                                    hover_data=['player', 'team'],
                                    color='half',
                                    color_discrete_map={'First Half': '#3498db',
                                                        'Second Half': '#e74c3c'},
                                    labels={'minute': 'Minute', 'game': '', 'half': ''},
                                    title=f'Goal Scorers Timeline - Matchday {input.selected_matchday()}'
                                )
                                fig.update_traces(marker=dict(size=12))
                                fig.update_layout(
                                    plot_bgcolor='rgba(0,0,0,0)',
                                    paper_bgcolor='rgba(0,0,0,0)'
                                )
                                return fig
                        
                        with ui.card():
                            ui.tags.div("Cards by Type", class_="overview-card-header")
                            @render_plotly
                            def md_cards_pie():
                                md_cards = cautions_df()[cautions_df()['md'] == selected_md()]
                                if md_cards.empty:
                                    return empty_figure("No cards on this matchday")
                                card_type_counts = md_cards['caution_display'].value_counts().reset_index()
                                card_type_counts.columns = ['type', 'count']
                                fig = px.pie(
                                    card_type_counts,
                                    values='count',
                                    names='type',
                                    color='type',
                                    color_discrete_map=CAUTION_COLORS,
                                    title=f'Card Types - Matchday {input.selected_matchday()}'
                                )
                                fig.update_layout(
                                    plot_bgcolor='rgba(0,0,0,0)',
                                    paper_bgcolor='rgba(0,0,0,0)'
                                )
                                return fig

                    with ui.layout_columns(col_widths=[12], style="margin: 20px 0;"):
                        with ui.card():
                            ui.tags.div("Matchday Goalscorers", class_="overview-card-header")
                            @render.table(escape=False)
                            def md_scorers_table():
                                md_data = goals_df()[goals_df()['md'] == selected_md()][['game', 'player', 'team', 'minute', 'period']]
                                md_data = md_data.sort_values('minute')
                                md_data.columns = ['Match', 'Player', 'Team', 'Minute', 'Half']
                                return logo_table(md_data, clubs=['Team'], matches=['Match'])

                with ui.nav_panel("Table & Results"):
                    with ui.layout_columns(col_widths=[12], style="margin: 20px 0;"):
                        with ui.card():
                            @render.ui
                            def md_results_header():
                                return ui.tags.div(
                                    f"Results - Matchday {input.selected_matchday()}",
                                    class_="overview-card-header")

                            @render.table(escape=False)
                            def md_results_table():
                                return logo_table(results_table(selected_md()),
                                                  clubs=['Home', 'Away'])

                            ui.tags.p(SOURCE_NOTE,
                                      style="margin: 10px 15px; color: #777; font-size: 13px;")

                    with ui.layout_columns(col_widths=[12], style="margin: 20px 0;"):
                        with ui.card():
                            @render.ui
                            def md_standings_header():
                                return ui.tags.div(
                                    f"League Table after Matchday {input.selected_matchday()}",
                                    class_="overview-card-header")

                            @render.table(escape=False)
                            def md_standings_table():
                                return logo_table(league_table(upto_md=selected_md()),
                                                  clubs=['Team'])

                    with ui.layout_columns(col_widths=[12], style="margin: 20px 0;"):
                        with ui.card():
                            @render.ui
                            def md_only_standings_header():
                                return ui.tags.div(
                                    f"Matchday {input.selected_matchday()} Only",
                                    class_="overview-card-header")

                            @render.table(escape=False)
                            def md_only_standings_table():
                                return logo_table(league_table(md=selected_md(), form_games=1),
                                                  clubs=['Team'])

                with ui.nav_panel("Match Details"):
                    with ui.card():
                        @render.ui
                        def md_details_header():
                            return ui.tags.div(
                                f"Venue & Officials - Matchday {input.selected_matchday()}",
                                class_="overview-card-header")

                        @render.table(escape=False)
                        def md_details_table():
                            info = match_info_df()
                            md = selected_md()
                            if info.empty or md is None:
                                return pd.DataFrame(columns=['Match'])
                            data = info[info['md'] == md].sort_values('game')
                            columns = ['game', 'date', 'kickoff', 'venue',
                                       'attendance', 'referee']
                            available = [c for c in columns if c in data.columns]
                            data = data[available]
                            data.columns = ['Match', 'Date', 'Kick-off', 'Venue',
                                            'Attendance', 'Referee'][:len(available)]
                            return logo_table(data, matches=['Match'])

                        ui.tags.p(
                            "Attendance is only printed on some reports, so blanks "
                            "here mean it was not recorded rather than nobody attended.",
                            style="margin: 10px 15px; color: #777; font-size: 13px;")

                    with ui.card():
                        @render.ui
                        def md_teamsheet_header():
                            return ui.tags.div(
                                f"Team Sheets - Matchday {input.selected_matchday()}",
                                class_="overview-card-header")

                        @render.table(escape=False)
                        def md_teamsheet_table():
                            squad = lineups_df()
                            md = selected_md()
                            if squad.empty or md is None:
                                return pd.DataFrame(columns=['Match'])
                            data = squad[(squad['md'] == md)
                                         & (squad['role'] == 'starting')]
                            data = data.sort_values(['game', 'team', 'shirt'])
                            data = data[['game', 'team', 'shirt', 'player',
                                         'minutes_played']]
                            data.columns = ['Match', 'Team', '#', 'Player', 'Minutes']
                            return logo_table(data, clubs=['Team'], matches=['Match'])

                with ui.nav_panel("Cards"):
                    with ui.card():
                        @render.ui
                        def md_cards_header():
                            return ui.tags.div(f"Cards Detail - Matchday {input.selected_matchday()}", class_="overview-card-header")
                        
                        @render.table(escape=False)
                        def md_cards_table():
                            md_cards = cautions_df()[cautions_df()['md'] == selected_md()][['game', 'player', 'team', 'caution', 'minute', 'double-caution']]
                            md_cards.columns = ['Match', 'Player', 'Team', 'Card Type', 'Minute', 'Double Caution']
                            return logo_table(md_cards, clubs=['Team'], matches=['Match'])

                with ui.nav_panel("Substitutions"):
                    with ui.card():
                        @render.ui
                        def md_subs_header():
                            return ui.tags.div(f"Substitutions Detail - Matchday {input.selected_matchday()}", class_="overview-card-header")
                        
                        @render.table(escape=False)
                        def md_subs_table():
                            md_subs = subs_df()[subs_df()['md'] == selected_md()][['game', 'in', 'out', 'team', 'minute']]
                            md_subs.columns = ['Match', 'Player In', 'Player Out', 'Team', 'Minute']
                            return logo_table(md_subs, clubs=['Team'], matches=['Match'])

    # =============================================================================
    # PAGE 3: HOME & AWAY FORM
    # =============================================================================
    with ui.nav_panel("Home & Away"):
        with ui.navset_pill(id="venue_tab"):

            with ui.nav_panel("Home Advantage"):
                with ui.layout_columns(col_widths=[3, 3, 3, 3], style="margin: 20px 0;"):
                    with ui.div(class_="stat-card goals"):
                        @render.text
                        def home_goals_total():
                            data = team_matches_df()
                            return str(int(data[data['venue'] == 'home']['gf'].sum()))
                        ui.p("Home Goals")
                    with ui.div(class_="stat-card goals"):
                        @render.text
                        def away_goals_total():
                            data = team_matches_df()
                            return str(int(data[data['venue'] == 'away']['gf'].sum()))
                        ui.p("Away Goals")
                    with ui.div(class_="stat-card matches"):
                        @render.text
                        def home_wins_total():
                            data = team_matches_df()
                            return str(int((data[data['venue'] == 'home']['result'] == 'W').sum()))
                        ui.p("Home Wins")
                    with ui.div(class_="stat-card matches"):
                        @render.text
                        def away_wins_total():
                            data = team_matches_df()
                            return str(int((data[data['venue'] == 'away']['result'] == 'W').sum()))
                        ui.p("Away Wins")

                with ui.layout_columns(col_widths=[6, 6], style="margin: 20px 0;"):
                    with ui.card():
                        ui.tags.div("Where the Results Go", class_="overview-card-header")
                        @render_plotly
                        def venue_outcomes():
                            home = team_matches_df()[team_matches_df()['venue'] == 'home']
                            if home.empty:
                                return empty_figure()
                            counts = pd.DataFrame({
                                'outcome': ['Home win', 'Draw', 'Away win'],
                                'matches': [int((home['result'] == 'W').sum()),
                                            int((home['result'] == 'D').sum()),
                                            int((home['result'] == 'L').sum())],
                            })
                            fig = px.pie(
                                counts, values='matches', names='outcome', hole=0.4,
                                color='outcome',
                                color_discrete_map={'Home win': '#2e8b57',
                                                    'Draw': '#95a5a6',
                                                    'Away win': '#e74c3c'},
                                title='Share of Matches by Outcome'
                            )
                            fig.update_layout(
                                plot_bgcolor='rgba(0,0,0,0)',
                                paper_bgcolor='rgba(0,0,0,0)'
                            )
                            return fig

                    with ui.card():
                        ui.tags.div("Goals & Cards by Venue", class_="overview-card-header")
                        @render_plotly
                        @count_axes('y')
                        def venue_totals():
                            data = pd.DataFrame({
                                'measure': ['Goals', 'Goals', 'Cards', 'Cards',
                                            'Substitutions', 'Substitutions'],
                                'venue': ['Home', 'Away'] * 3,
                                'count': [
                                    int((goals_df()['venue'] == 'home').sum()),
                                    int((goals_df()['venue'] == 'away').sum()),
                                    int((cautions_df()['venue'] == 'home').sum()),
                                    int((cautions_df()['venue'] == 'away').sum()),
                                    int((subs_df()['venue'] == 'home').sum()),
                                    int((subs_df()['venue'] == 'away').sum()),
                                ],
                            })
                            fig = px.bar(
                                data, x='measure', y='count', color='venue',
                                barmode='group',
                                color_discrete_map={'Home': '#2e8b57', 'Away': '#e74c3c'},
                                title='Home and Away Totals Across the Season',
                                labels={'measure': '', 'count': 'Events', 'venue': ''}
                            )
                            fig.update_layout(
                                plot_bgcolor='rgba(0,0,0,0)',
                                paper_bgcolor='rgba(0,0,0,0)'
                            )
                            return fig

                with ui.layout_columns(col_widths=[12], style="margin: 20px 0;"):
                    with ui.card():
                        ui.tags.div("Points at Home vs Away, by Team",
                                    class_="overview-card-header")
                        @render_plotly
                        @count_axes('x')
                        def venue_points_by_team():
                            points = (team_matches_df().groupby(['team', 'venue'])['points']
                                      .sum().reset_index())
                            order = (points[points['venue'] == 'home']
                                     .sort_values('points')['team'].tolist())
                            points['venue'] = points['venue'].map({'home': 'Home',
                                                                   'away': 'Away'})
                            fig = px.bar(
                                points, x='points', y='team', color='venue',
                                orientation='h', barmode='group',
                                color_discrete_map={'Home': '#2e8b57', 'Away': '#e74c3c'},
                                category_orders={'team': order},
                                title='Points Won at Home and Away',
                                labels={'points': 'Points', 'team': '', 'venue': ''}
                            )
                            fig.update_layout(
                                height=600,
                                plot_bgcolor='rgba(0,0,0,0)',
                                paper_bgcolor='rgba(0,0,0,0)'
                            )
                            return fig

            with ui.nav_panel("Home Form"):
                with ui.card():
                    ui.tags.div("Home Table", class_="overview-card-header")
                    @render.table(escape=False)
                    def home_form_table():
                        return logo_table(league_table(venue='home'), clubs=['Team'])

                    ui.tags.p("Home matches only. Form shows the last five home results, "
                              "oldest first. " + SOURCE_NOTE,
                              style="margin: 10px 15px; color: #777; font-size: 13px;")

                with ui.card():
                    ui.tags.div("Goals Scored at Home", class_="overview-card-header")
                    @render_plotly
                    @count_axes('x')
                    def home_goals_by_team():
                        data = (team_matches_df()[team_matches_df()['venue'] == 'home']
                                .groupby('team')['gf'].sum().reset_index()
                                .sort_values('gf'))
                        fig = px.bar(
                            data, x='gf', y='team', orientation='h',
                            color='team', color_discrete_map=TEAM_COLORS,
                            title='Home Goals by Team',
                            labels={'gf': 'Goals', 'team': ''}
                        )
                        fig.update_layout(
                            showlegend=False,
                            plot_bgcolor='rgba(0,0,0,0)',
                            paper_bgcolor='rgba(0,0,0,0)'
                        )
                        return fig

            with ui.nav_panel("Away Form"):
                with ui.card():
                    ui.tags.div("Away Table", class_="overview-card-header")
                    @render.table(escape=False)
                    def away_form_table():
                        return logo_table(league_table(venue='away'), clubs=['Team'])

                    ui.tags.p("Away matches only. Form shows the last five away results, "
                              "oldest first. " + SOURCE_NOTE,
                              style="margin: 10px 15px; color: #777; font-size: 13px;")

                with ui.card():
                    ui.tags.div("Goals Scored Away", class_="overview-card-header")
                    @render_plotly
                    @count_axes('x')
                    def away_goals_by_team():
                        data = (team_matches_df()[team_matches_df()['venue'] == 'away']
                                .groupby('team')['gf'].sum().reset_index()
                                .sort_values('gf'))
                        fig = px.bar(
                            data, x='gf', y='team', orientation='h',
                            color='team', color_discrete_map=TEAM_COLORS,
                            title='Away Goals by Team',
                            labels={'gf': 'Goals', 'team': ''}
                        )
                        fig.update_layout(
                            showlegend=False,
                            plot_bgcolor='rgba(0,0,0,0)',
                            paper_bgcolor='rgba(0,0,0,0)'
                        )
                        return fig

    # =============================================================================
    # PAGE 4: TEAM STATISTICS
    # =============================================================================
    with ui.nav_panel("Team Statistics"):
        with ui.layout_sidebar():
            with ui.sidebar():
                ui.h5("Select Team")
                ui.input_selectize("selected_team", "Team:", choices={},
                                   options={"render": ui.js_eval("window.clubRender")})

                @render.ui
                def team_crest():
                    """The chosen club's logo, when there is one for this season."""
                    team = selected_team()
                    url = club_logos().get(str(team).upper()) if team else None
                    if not url:
                        return None
                    return ui.div(ui.tags.img(src=url, alt=f"{team} logo"),
                                  class_="team-crest")

                @reactive.effect
                def _refresh_teams():
                    """Repopulate the team list whenever the competition changes.

                    Isolated read for the same reason as the matchday select.
                    """
                    available = teams()
                    with reactive.isolate():
                        current = _chosen("selected_team", None)
                    ui.update_selectize(
                        "selected_team",
                        choices={team: team for team in available},
                        selected=(current if current in available
                                  else (available[0] if available else None)),
                    )

                ui.hr()
                ui.h5("Team Summary")
                @render.text
                def team_summary():
                    """Display summary statistics for selected team"""
                    team = selected_team()
                    team_goals = len(goals_df()[goals_df()['team'] == team])
                    team_cards = len(cautions_df()[cautions_df()['team'] == team])
                    team_subs = len(subs_df()[subs_df()['team'] == team])
                    team_matches = count_team_matches(team)
                    return f"Goals: {team_goals} | Cards: {team_cards} | Subs: {team_subs} | Matches: {team_matches}"
            
            with ui.navset_pill(id="team_tab"):
                
                with ui.nav_panel("Performance"):
                    with ui.layout_columns(col_widths=[3, 3, 3, 3], style="margin: 20px 0;"):
                        with ui.div(class_="stat-card goals"):
                            @render.text
                            def team_goals_scored():
                                team_goals = len(goals_df()[goals_df()['team'] == selected_team()])
                                return str(team_goals)
                            ui.p("Goals Scored")
                        with ui.div(class_="stat-card cards"):
                            @render.text
                            def team_cards_received():
                                team_cards = len(cautions_df()[cautions_df()['team'] == selected_team()])
                                return str(team_cards)
                            ui.p("Cards Received")
                        with ui.div(class_="stat-card subs"):
                            @render.text
                            def team_subs_made():
                                team_subs = len(subs_df()[subs_df()['team'] == selected_team()])
                                return str(team_subs)
                            ui.p("Subs Made")
                        with ui.div(class_="stat-card matches"):
                            @render.text
                            def team_matches_played():
                                return str(count_team_matches(selected_team()))
                            ui.p("Matches Played")

                    with ui.layout_columns(col_widths=[6, 6], style="margin: 20px 0;"):
                        with ui.card():
                            @render.ui
                            def team_goals_period_header():
                                return ui.tags.div("Goals by Period", style=get_team_header_style(selected_team()))
                            
                            @render_plotly
                            @count_axes('y')
                            def team_goals_by_period():
                                team_data = goals_df()[goals_df()['team'] == selected_team()]
                                period_goals = team_data.groupby('period').size().reset_index(name='goals')
                                period_goals['period'] = period_goals['period'].map({1: 'First Half', 2: 'Second Half'})
                                colors = ['#3498db', '#e74c3c']
                                fig = px.bar(
                                    period_goals,
                                    x='period',
                                    y='goals',
                                    color='period',
                                    color_discrete_sequence=colors,
                                    title=f'Goals by Match Period - {selected_team()}'
                                )
                                fig.update_layout(
                                    showlegend=False,
                                    plot_bgcolor='rgba(0,0,0,0)',
                                    paper_bgcolor='rgba(0,0,0,0)'
                                )
                                return fig
                        
                        with ui.card():
                            @render.ui
                            def team_goals_timeline_header():
                                return ui.tags.div("Goal Timing Distribution", style=get_team_header_style(selected_team()))
                            
                            @render_plotly
                            @count_axes('y')
                            def team_goals_timeline():
                                team_data = goals_df()[goals_df()['team'] == selected_team()]
                                fig = px.histogram(
                                    team_data,
                                    x='minute',
                                    nbins=10,
                                    title=f'Goals by Minute - {selected_team()}',
                                    labels={'minute': 'Minute', 'count': 'Goals'},
                                    color_discrete_sequence=['#2ecc71']
                                )
                                fig.update_layout(
                                    plot_bgcolor='rgba(0,0,0,0)',
                                    paper_bgcolor='rgba(0,0,0,0)'
                                )
                                return fig

                    with ui.layout_columns(col_widths=[12], style="margin: 20px 0;"):
                        with ui.card():
                            @render.ui
                            def team_top_scorers_header():
                                return ui.tags.div(f"Top Scorers - {selected_team()}", style=get_team_header_style(selected_team()))
                            
                            @render.table
                            def team_top_scorers():
                                team_data = goals_df()[goals_df()['team'] == selected_team()]
                                scorers = team_data.groupby('player').size().reset_index(name='goals')
                                scorers = scorers.sort_values('goals', ascending=False)
                                scorers.columns = ['Player', 'Goals']
                                return scorers

                with ui.nav_panel("Staff"):
                    with ui.card():
                        @render.ui
                        def team_staff_header():
                            return ui.tags.div(f"Coaching Staff - {selected_team()}",
                                               style=get_team_header_style(selected_team()))

                        @render.table
                        def team_staff_table():
                            staff = staff_df()
                            staff = staff[staff['team'] == selected_team()]
                            if staff.empty:
                                return pd.DataFrame(columns=['Role', 'Name', 'Matches'])
                            table = (staff.groupby(['role', 'name']).size()
                                          .reset_index(name='matches')
                                          .sort_values(['role', 'matches'],
                                                       ascending=[True, False]))
                            table.columns = ['Role', 'Name', 'Matches']
                            return table

                with ui.nav_panel("Discipline"):
                    with ui.layout_columns(col_widths=[6, 6], style="margin: 20px 0;"):
                        with ui.card():
                            @render.ui
                            def team_cards_breakdown_header():
                                return ui.tags.div("Cards Breakdown", style=get_team_header_style(selected_team()))
                            
                            @render_plotly
                            def team_cards_breakdown():
                                team_cards = cautions_df()[cautions_df()['team'] == selected_team()]
                                if team_cards.empty:
                                    return empty_figure("No cards for this team")
                                card_counts = team_cards['caution_display'].value_counts().reset_index()
                                card_counts.columns = ['type', 'count']
                                fig = px.pie(
                                    card_counts,
                                    values='count',
                                    names='type',
                                    color='type',
                                    color_discrete_map=CAUTION_COLORS,
                                    title=f'Cards Breakdown - {selected_team()}',
                                    hole=0.4
                                )
                                fig.update_layout(
                                    plot_bgcolor='rgba(0,0,0,0)',
                                    paper_bgcolor='rgba(0,0,0,0)'
                                )
                                return fig
                        
                        with ui.card():
                            @render.ui
                            def team_cards_matchday_header():
                                return ui.tags.div("Cards by Matchday", style=get_team_header_style(selected_team()))
                            
                            @render_plotly
                            @count_axes('x', 'y')
                            def team_cards_by_matchday():
                                team_cards = cautions_df()[cautions_df()['team'] == selected_team()]
                                md_cards = team_cards.groupby('md').size().reset_index(name='cards')
                                fig = px.bar(
                                    md_cards,
                                    x='md',
                                    y='cards',
                                    title=f'Cards per Matchday - {selected_team()}',
                                    labels={'md': 'Matchday', 'cards': 'Cards'}
                                )
                                fig.update_traces(marker_color='#e74c3c')
                                fig.update_layout(
                                    plot_bgcolor='rgba(0,0,0,0)',
                                    paper_bgcolor='rgba(0,0,0,0)'
                                )
                                return fig

                    with ui.card():
                        @render.ui
                        def team_cards_table_header():
                            return ui.tags.div(f"All Cards Received - {selected_team()}", style=get_team_header_style(selected_team()))
                        
                        @render.table(escape=False)
                        def team_cards_table():
                            team_cards = cautions_df()[cautions_df()['team'] == selected_team()][['game', 'player', 'caution', 'minute', 'double-caution']]
                            team_cards.columns = ['Match', 'Player', 'Card Type', 'Minute', 'Double Caution']
                            return logo_table(team_cards, matches=['Match'])

                with ui.nav_panel("Substitutions"):
                    with ui.layout_columns(col_widths=[6, 6], style="margin: 20px 0;"):
                        with ui.card():
                            @render.ui
                            def team_subs_timing_header():
                                return ui.tags.div("Substitution Timing", style=get_team_header_style(selected_team()))
                            
                            @render_plotly
                            @count_axes('y')
                            def team_subs_timing():
                                team_subs = subs_df()[subs_df()['team'] == selected_team()]
                                team_color = TEAM_COLORS.get(selected_team(), '#3498db')
                                fig = px.histogram(
                                    team_subs,
                                    x='minute',
                                    nbins=10,
                                    title=f'Substitutions by Minute - {selected_team()}',
                                    labels={'minute': 'Minute', 'count': 'Substitutions'},
                                    color_discrete_sequence=[team_color]
                                )
                                fig.update_layout(
                                    plot_bgcolor='rgba(0,0,0,0)',
                                    paper_bgcolor='rgba(0,0,0,0)'
                                )
                                return fig
                        
                        with ui.card():
                            @render.ui
                            def team_players_substituted_header():
                                return ui.tags.div("Players Substituted On & Off", style=get_team_header_style(selected_team()))
                            
                            with ui.layout_column_wrap(width=1/2):
                                @render_plotly
                                @count_axes('x')
                                def team_players_subbed_off():
                                    team_subs = subs_df()[subs_df()['team'] == selected_team()]
                                    player_subs = team_subs['out'].value_counts().reset_index()
                                    player_subs.columns = ['Player', 'Substitutions']
                                    team_color = TEAM_COLORS.get(selected_team(), '#3498db')
                                    fig = px.bar(
                                        player_subs.head(10),
                                        x='Substitutions',
                                        y='Player',
                                        orientation='h',
                                        title='Most Taken Off',
                                        color_discrete_sequence=[team_color]
                                    )
                                    # remove y-axis label
                                    fig.update_yaxes(title_text='')
                                    # update x-axis label
                                    fig.update_xaxes(title_text='Times')
                                    #update layout
                                    fig.update_layout(
                                        showlegend=False,
                                        plot_bgcolor='rgba(0,0,0,0)',
                                        paper_bgcolor='rgba(0,0,0,0)'
                                    )
                                    return fig
                                
                                @render_plotly
                                @count_axes('x')
                                def team_players_subbed_on():
                                    team_subs = subs_df()[subs_df()['team'] == selected_team()]
                                    player_subs = team_subs['in'].value_counts().reset_index()
                                    player_subs.columns = ['Player', 'Substitutions']
                                    team_color = TEAM_COLORS.get(selected_team(), '#3498db')
                                    fig = px.bar(
                                        player_subs.head(10),
                                        x='Substitutions',
                                        y='Player',
                                        orientation='h',
                                        title='Most Taken On',
                                        color_discrete_sequence=[team_color]
                                    )
                                    # remove y-axis label
                                    fig.update_yaxes(title_text='')
                                    # update x-axis label
                                    fig.update_xaxes(title_text='Substituted')
                                    # update layout
                                    fig.update_layout(
                                        showlegend=False,
                                        plot_bgcolor='rgba(0,0,0,0)',
                                        paper_bgcolor='rgba(0,0,0,0)'
                                    )
                                    return fig

                    with ui.card():
                        @render.ui
                        def team_subs_table_header():
                            return ui.tags.div(f"All Substitutions - {selected_team()}", style=get_team_header_style(selected_team()))

                        @render.table(escape=False)
                        def team_subs_table():
                            team_subs = subs_df()[subs_df()['team'] == selected_team()][['game', 'in', 'out', 'minute']]
                            team_subs.columns = ['Match', 'Player In', 'Player Out', 'Minute']
                            return logo_table(team_subs, matches=['Match'])

    # =============================================================================
    # PAGE 5: PLAYERS
    # =============================================================================
    # Everything here rests on minutes played, which only became available once
    # the team sheets were extracted.
    with ui.nav_panel("Players"):
        with ui.navset_pill(id="player_tab"):

            with ui.nav_panel("Minutes & Usage"):
                with ui.layout_columns(col_widths=[3, 3, 3, 3], style="margin: 20px 0;"):
                    with ui.div(class_="stat-card matches"):
                        @render.text
                        def players_used_count():
                            return str(lineups_df()['player_id'].nunique())
                        ui.p("Players Registered")
                    with ui.div(class_="stat-card goals"):
                        @render.text
                        def players_appeared_count():
                            return str(len(player_profiles()))
                        ui.p("Players Used")
                    with ui.div(class_="stat-card subs"):
                        @render.text
                        def unused_subs_count():
                            squad = lineups_df()
                            return str(int((squad['minutes_played'] == 0).sum()))
                        ui.p("Unused Sub Slots")
                    with ui.div(class_="stat-card cards"):
                        @render.text
                        def minutes_total():
                            return f"{int(lineups_df()['minutes_played'].sum()):,}"
                        ui.p("Minutes Played")

                with ui.layout_columns(col_widths=[6, 6], style="margin: 20px 0;"):
                    with ui.card():
                        ui.tags.div("Most Minutes Played", class_="overview-card-header")
                        @render_plotly
                        @count_axes('x')
                        def minutes_leaders():
                            data = player_profiles().head(15).sort_values('minutes')
                            if data.empty:
                                return empty_figure()
                            fig = px.bar(
                                data, x='minutes', y='player', orientation='h',
                                color='team', color_discrete_map=TEAM_COLORS,
                                title='Minutes on the Pitch',
                                labels={'minutes': 'Minutes', 'player': '', 'team': ''}
                            )
                            fig.update_layout(
                                height=520,
                                plot_bgcolor='rgba(0,0,0,0)',
                                paper_bgcolor='rgba(0,0,0,0)'
                            )
                            return fig

                    with ui.card():
                        ui.tags.div("Squad Rotation", class_="overview-card-header")
                        @render_plotly
                        @count_axes('x')
                        def squad_rotation():
                            used = player_profiles()
                            if used.empty:
                                return empty_figure()
                            data = (used.groupby('team').size()
                                        .reset_index(name='players').sort_values('players'))
                            fig = px.bar(
                                data, x='players', y='team', orientation='h',
                                color='team', color_discrete_map=TEAM_COLORS,
                                title='Different Players Given Minutes',
                                labels={'players': 'Players used', 'team': ''}
                            )
                            fig.update_layout(
                                showlegend=False, height=520,
                                plot_bgcolor='rgba(0,0,0,0)',
                                paper_bgcolor='rgba(0,0,0,0)'
                            )
                            return fig

                with ui.layout_columns(col_widths=[12], style="margin: 20px 0;"):
                    with ui.card():
                        ui.tags.div("Appearances", class_="overview-card-header")
                        @render.table(escape=False)
                        def appearances_table():
                            data = player_profiles().copy()
                            if data.empty:
                                return data
                            data = data[['player', 'team', 'starts', 'sub_apps',
                                         'minutes', 'goals']]
                            data.columns = ['Player', 'Team', 'Starts', 'As Sub',
                                            'Minutes', 'Goals']
                            return logo_table(data.head(30), clubs=['Team'])

            with ui.nav_panel("Scoring Rates"):
                ui.tags.p(
                    f"Goals per 90 minutes. Only players with at least "
                    f"{MIN_MINUTES_FOR_RATE} minutes are ranked — below that a "
                    f"single goal distorts the rate beyond any meaning.",
                    style="margin: 20px 10px 0 10px; color: #555;"
                )
                with ui.layout_columns(col_widths=[7, 5], style="margin: 20px 0;"):
                    with ui.card():
                        ui.tags.div("Goals per 90", class_="overview-card-header")
                        @render_plotly
                        def goals_per_90_chart():
                            data = player_profiles()
                            data = data[(data['minutes'] >= MIN_MINUTES_FOR_RATE)
                                        & (data['goals'] > 0)]
                            if data.empty:
                                return empty_figure(
                                    "No player has enough minutes yet")
                            data = data.sort_values('goals_per_90').tail(15)
                            fig = px.bar(
                                data, x='goals_per_90', y='player', orientation='h',
                                color='team', color_discrete_map=TEAM_COLORS,
                                hover_data=['goals', 'minutes'],
                                title='Scoring Rate',
                                labels={'goals_per_90': 'Goals per 90',
                                        'player': '', 'team': ''}
                            )
                            fig.update_layout(
                                height=520,
                                plot_bgcolor='rgba(0,0,0,0)',
                                paper_bgcolor='rgba(0,0,0,0)'
                            )
                            return fig

                    with ui.card():
                        ui.tags.div("Minutes per Goal", class_="overview-card-header")
                        @render.table(escape=False)
                        def minutes_per_goal_table():
                            data = player_profiles()
                            data = data[(data['goals'] > 0)].copy()
                            if data.empty:
                                return pd.DataFrame(
                                    columns=['Player', 'Team', 'Goals', 'Minutes',
                                             'Mins/Goal'])
                            data['mins_per_goal'] = (
                                data['minutes'] / data['goals']).round(0).astype(int)
                            data = data.sort_values('mins_per_goal')
                            data = data[['player', 'team', 'goals', 'minutes',
                                         'mins_per_goal']]
                            data.columns = ['Player', 'Team', 'Goals', 'Minutes',
                                            'Mins/Goal']
                            return logo_table(data.head(20), clubs=['Team'])

            with ui.nav_panel("Compare"):
                ui.tags.p(
                    "Pick two to four players. Rates are per 90 minutes, so a "
                    "substitute is measured on the same scale as an ever-present "
                    "— but check the minutes row before reading much into a rate "
                    "built on a short sample.",
                    style="margin: 20px 10px 0 10px; color: #555;"
                )

                with ui.div(style="margin: 16px 10px;"):
                    ui.input_selectize(
                        "compare_players", "Players",
                        choices={}, multiple=True,
                        options={"maxItems": 4, "placeholder": "Choose players…",
                                 "render": ui.js_eval("window.playerRender")},
                    )

                @reactive.effect
                def _refresh_compare_players():
                    """Offer the players of the selected competition, busiest first."""
                    profiles = player_profiles()
                    choices = {row["player_id"]: player_label(row)
                               for _index, row in profiles.iterrows()}
                    with reactive.isolate():
                        current = [p for p in (input.compare_players() or [])
                                   if p in choices]
                    if not current:
                        current = list(choices)[:2]
                    ui.update_selectize("compare_players", choices=choices,
                                        selected=current)

                @reactive.calc
                def compared():
                    """The chosen players' profile rows, in the order picked."""
                    chosen = list(input.compare_players() or [])
                    profiles = player_profiles()
                    if not chosen or profiles.empty:
                        return profiles.iloc[0:0]
                    picked = profiles[profiles["player_id"].isin(chosen)]
                    order = {pid: i for i, pid in enumerate(chosen)}
                    return picked.assign(
                        _order=picked["player_id"].map(order)
                    ).sort_values("_order").drop(columns="_order")

                with ui.layout_columns(col_widths=[12], style="margin: 12px 0;"):
                    with ui.card():
                        ui.tags.div("Side by Side", class_="overview-card-header")
                        @render.table(escape=False)
                        def compare_table():
                            data = compared()
                            if data.empty:
                                return pd.DataFrame({"": ["Choose at least one player"]})
                            rows = [
                                ("Team", "team", None),
                                ("Matches", "matches", None),
                                ("Starts", "starts", None),
                                ("As substitute", "sub_apps", None),
                                ("Minutes", "minutes", None),
                                ("Goals", "goals", None),
                                ("Goals per 90", "goals_per_90", None),
                                ("Minutes per goal", None, "mins_per_goal"),
                                ("Yellow cards", "yellows", None),
                                ("Reds & second yellows", "reds", None),
                                ("Cards per 90", "cards_per_90", None),
                            ]
                            table = {"Metric": [label for label, _c, _d in rows]}
                            for _index, player in data.iterrows():
                                values = []
                                for _label, column, derived in rows:
                                    if derived == "mins_per_goal":
                                        values.append(
                                            int(player["minutes"] / player["goals"])
                                            if player["goals"] else "—")
                                    elif column == "team":
                                        values.append(club_html(player[column]))
                                    else:
                                        values.append(player[column])
                                table[html.escape(player_label(player))] = values
                            return pd.DataFrame(table)

                with ui.layout_columns(col_widths=[6, 6], style="margin: 20px 0;"):
                    with ui.card():
                        ui.tags.div("Per 90 Comparison", class_="overview-card-header")
                        @render_plotly
                        def compare_rates():
                            data = compared()
                            if data.empty:
                                return empty_figure("Choose players to compare")
                            tidy = pd.DataFrame({
                                "player": list(data.apply(player_label, axis=1)) * 2,
                                "measure": (["Goals per 90"] * len(data)
                                            + ["Cards per 90"] * len(data)),
                                "value": (list(data["goals_per_90"])
                                          + list(data["cards_per_90"])),
                            })
                            fig = px.bar(
                                tidy, x="measure", y="value", color="player",
                                barmode="group",
                                title="Output and Discipline per 90 Minutes",
                                labels={"measure": "", "value": "Per 90", "player": ""}
                            )
                            fig.update_layout(
                                plot_bgcolor='rgba(0,0,0,0)',
                                paper_bgcolor='rgba(0,0,0,0)'
                            )
                            return fig

                    with ui.card():
                        ui.tags.div("Workload", class_="overview-card-header")
                        @render_plotly
                        @count_axes('y')
                        def compare_workload():
                            data = compared()
                            if data.empty:
                                return empty_figure("Choose players to compare")
                            tidy = pd.DataFrame({
                                "player": list(data.apply(player_label, axis=1)) * 2,
                                "kind": (["Starts"] * len(data)
                                         + ["As substitute"] * len(data)),
                                "count": list(data["starts"]) + list(data["sub_apps"]),
                            })
                            fig = px.bar(
                                tidy, x="player", y="count", color="kind",
                                barmode="stack",
                                color_discrete_map={"Starts": "#1a5f7a",
                                                    "As substitute": "#F5901F"},
                                title="Appearances by Type",
                                labels={"player": "", "count": "Appearances", "kind": ""}
                            )
                            fig.update_layout(
                                plot_bgcolor='rgba(0,0,0,0)',
                                paper_bgcolor='rgba(0,0,0,0)'
                            )
                            return fig

                with ui.layout_columns(col_widths=[12], style="margin: 20px 0;"):
                    with ui.card():
                        ui.tags.div("When They Score", class_="overview-card-header")
                        @render_plotly
                        @count_axes('y')
                        def compare_goal_timing():
                            data = compared()
                            if data.empty:
                                return empty_figure("Choose players to compare")
                            frames = []
                            for _index, player in data.iterrows():
                                wanted = _norm_name(player["player"])
                                scored = goals_df()
                                scored = scored[
                                    scored["player"].map(_norm_name) == wanted]
                                counts = bucket_counts(scored)
                                counts["player"] = player_label(player)
                                frames.append(counts)
                            tidy = pd.concat(frames, ignore_index=True)
                            if tidy["count"].sum() == 0:
                                return empty_figure(
                                    "Neither player has scored in this season yet")
                            fig = px.bar(
                                tidy, x="bucket", y="count", color="player",
                                barmode="group",
                                category_orders={"bucket": MINUTE_BUCKETS},
                                title="Goals by Period of the Match",
                                labels={"bucket": "Minute", "count": "Goals",
                                        "player": ""}
                            )
                            fig.update_layout(
                                plot_bgcolor='rgba(0,0,0,0)',
                                paper_bgcolor='rgba(0,0,0,0)'
                            )
                            return fig

            with ui.nav_panel("Squads"):
                with ui.card():
                    @render.ui
                    def squad_header():
                        return ui.tags.div(f"Squad - {selected_team()}",
                                           style=get_team_header_style(selected_team()))

                    @render.table
                    def squad_table():
                        squad = lineups_df()
                        squad = squad[squad['team'] == selected_team()]
                        if squad.empty:
                            return pd.DataFrame(
                                columns=['Player', 'ID', 'Starts', 'As Sub',
                                         'Minutes', 'Captain', 'Keeper'])
                        grouped = squad.groupby(['player', 'player_id']).agg(
                            starts=('role', lambda s: (s == 'starting').sum()),
                            sub_apps=('role', lambda s: (s == 'substitute').sum()),
                            minutes=('minutes_played', 'sum'),
                            captain=('is_captain', lambda s: (s == 'yes').sum()),
                            keeper=('is_goalkeeper', lambda s: (s == 'yes').sum()),
                        ).reset_index().sort_values('minutes', ascending=False)
                        grouped['captain'] = grouped['captain'].map(
                            lambda n: "yes" if n else "")
                        grouped['keeper'] = grouped['keeper'].map(
                            lambda n: "yes" if n else "")
                        grouped.columns = ['Player', 'ID', 'Starts', 'As Sub',
                                           'Minutes', 'Captain', 'Keeper']
                        return grouped

                    ui.tags.p(
                        "Team chosen on the Team Statistics page. The ID column is the "
                        "player's registration number, which stays constant even when "
                        "the reports spell a name differently.",
                        style="margin: 10px 15px; color: #777; font-size: 13px;")

    # =============================================================================
    # PAGE 6: U21 TRACKER
    # =============================================================================
    # One row per U21 player per matchday (built by wrangle.py): the weekly U21
    # export where one exists, the team sheets otherwise.
    with ui.nav_panel("U21 Impact"):

        U21_SOURCE_NOTE = (
            "A matchday with a U21 export uses it — the export is the only source of "
            "assists. A matchday without one falls back to the match reports, where a "
            "player counts as U21 by the birth year in their registration number, and "
            "assists show as a dash. G+A per 90 needs at least "
            f"{MIN_MINUTES_FOR_RATE} minutes; Team PPG is the club's points per game "
            "in the matches the player appeared in.")

        def u21_number(value):
            """Whole numbers without '.0'; a blank (not recorded) as a dash."""
            if pd.isna(value):
                return "—"
            return int(value) if float(value).is_integer() else value

        def goals_assists(rows):
            """'goals / assists', with a dash when no export recorded assists."""
            assists = rows['assists']
            shown = "—" if assists.isna().all() else int(assists.sum())
            return f"{int(rows['goals'].sum())} / {shown}"

        @render.ui
        def u21_rule():
            """The season's age rule, as wrangle.py applied it to the data."""
            rows = u21_df()
            if rows.empty or 'u21_born_from' not in rows:
                return None
            born_from = pd.Timestamp(rows['u21_born_from'].iloc[0])
            return ui.tags.p(
                f"U21 in {rows['season'].iloc[0]}: players born on or after "
                f"{born_from.day} {born_from:%B %Y}.",
                style="margin: 20px 10px 0 10px; color: #555; font-weight: 600;")

        with ui.navset_pill(id="u21_tab"):

            with ui.nav_panel("Season"):
                with ui.layout_columns(col_widths=[3, 3, 3, 3], style="margin: 20px 0;"):
                    with ui.div(class_="stat-card matches"):
                        @render.text
                        def u21_players_count():
                            return str(len(u21_season()))
                        ui.p("U21 Players")
                    with ui.div(class_="stat-card goals"):
                        @render.text
                        def u21_used_count():
                            return str(int((u21_season()['apps'] > 0).sum()))
                        ui.p("Players Used")
                    with ui.div(class_="stat-card subs"):
                        @render.text
                        def u21_minutes_total():
                            return f"{int(u21_season()['minutes'].sum()):,}"
                        ui.p("U21 Minutes")
                    with ui.div(class_="stat-card cards"):
                        @render.text
                        def u21_contributions_count():
                            return goals_assists(u21_season())
                        ui.p("Goals / Assists")

                with ui.layout_columns(col_widths=[6, 6], style="margin: 20px 0;"):
                    with ui.card():
                        ui.tags.div("Most U21 Minutes", class_="overview-card-header")
                        @render_plotly
                        @count_axes('x')
                        def u21_minutes_leaders():
                            data = u21_season()
                            data = data[data['minutes'] > 0].head(15).sort_values('minutes')
                            if data.empty:
                                return empty_figure()
                            fig = px.bar(
                                data, x='minutes', y='player', orientation='h',
                                color='team', color_discrete_map=TEAM_COLORS,
                                hover_data=['apps', 'starts'],
                                title='Minutes on the Pitch',
                                labels={'minutes': 'Minutes', 'player': '', 'team': ''}
                            )
                            fig.update_layout(
                                height=520,
                                plot_bgcolor='rgba(0,0,0,0)',
                                paper_bgcolor='rgba(0,0,0,0)'
                            )
                            return fig

                    with ui.card():
                        ui.tags.div("Goal Contributions", class_="overview-card-header")
                        @render_plotly
                        @count_axes('x')
                        def u21_contributions_chart():
                            data = u21_season()
                            data = data[data['ga'] > 0]
                            if data.empty:
                                return empty_figure("No U21 goals or assists yet")
                            data = data.sort_values('ga').tail(15)
                            tidy = pd.DataFrame({
                                'player': list(data['player']) * 2,
                                'kind': ['Goals'] * len(data) + ['Assists'] * len(data),
                                'count': list(data['goals']) + list(data['assists'].fillna(0)),
                            })
                            fig = px.bar(
                                tidy, x='count', y='player', color='kind',
                                orientation='h', barmode='stack',
                                color_discrete_map={'Goals': '#2ecc71', 'Assists': '#3498db'},
                                category_orders={'player': list(data['player'])},
                                title='Goals and Assists',
                                labels={'count': '', 'player': '', 'kind': ''}
                            )
                            fig.update_layout(
                                height=520,
                                plot_bgcolor='rgba(0,0,0,0)',
                                paper_bgcolor='rgba(0,0,0,0)'
                            )
                            return fig

                with ui.layout_columns(col_widths=[12], style="margin: 20px 0;"):
                    with ui.card():
                        ui.tags.div("U21 Leaderboard", class_="overview-card-header")
                        @render.table(escape=False)
                        def u21_leaderboard():
                            data = u21_season()
                            if data.empty:
                                return pd.DataFrame({"": ["No U21 data for this season yet"]})
                            data = data[['player', 'team', 'position', 'birth_year', 'apps',
                                         'starts', 'sub_in', 'minutes', 'goals', 'assists',
                                         'ga_per_90', 'cards', 'team_ppg', 'debut_md']].copy()
                            for column in ('birth_year', 'assists', 'ga_per_90', 'team_ppg',
                                           'debut_md'):
                                data[column] = data[column].map(u21_number)
                            data.columns = ['Player', 'Club', 'Pos', 'Born', 'Apps', 'Starts',
                                            'As Sub', 'Minutes', 'G', 'A', 'G+A per 90',
                                            'Cards', 'Team PPG', 'Debut MD']
                            return logo_table(data, clubs=['Club'])

                        ui.tags.p(U21_SOURCE_NOTE,
                                  style="margin: 10px 15px; color: #777; font-size: 13px;")

            with ui.nav_panel("By Matchday"):
                with ui.div(style="margin: 16px 10px; max-width: 260px;"):
                    ui.input_select("u21_matchday", "Matchday", choices={})

                @reactive.calc
                def u21_matchdays():
                    return sorted(int(m) for m in u21_df()['md'].dropna().unique())

                @reactive.effect
                def _refresh_u21_matchdays():
                    """Offer the season's matchdays, the latest preselected.

                    Isolated read for the same reason as the matchday select.
                    """
                    available = u21_matchdays()
                    with reactive.isolate():
                        current = _chosen("u21_matchday", None)
                    ui.update_select(
                        "u21_matchday",
                        choices={str(md): f"Matchday {md}" for md in available},
                        selected=(current if current in {str(m) for m in available}
                                  else (str(available[-1]) if available else None)),
                    )

                def u21_md():
                    """The chosen matchday, or the latest before the select is filled."""
                    raw = _chosen("u21_matchday", None)
                    available = u21_matchdays()
                    if raw and int(raw) in available:
                        return int(raw)
                    return available[-1] if available else None

                @reactive.calc
                def u21_md_rows():
                    rows = u21_df()
                    md = u21_md()
                    return rows[rows['md'] == md] if md is not None else rows.iloc[0:0]

                with ui.layout_columns(col_widths=[3, 3, 3, 3], style="margin: 10px 0 20px 0;"):
                    with ui.div(class_="stat-card matches"):
                        @render.text
                        def u21_md_used():
                            return str(int((u21_md_rows()['apps'] > 0).sum()))
                        ui.p("U21s Played")
                    with ui.div(class_="stat-card subs"):
                        @render.text
                        def u21_md_minutes():
                            return f"{int(u21_md_rows()['minutes'].sum()):,}"
                        ui.p("U21 Minutes")
                    with ui.div(class_="stat-card goals"):
                        @render.text
                        def u21_md_contributions():
                            return goals_assists(u21_md_rows())
                        ui.p("Goals / Assists")
                    with ui.div(class_="stat-card cards"):
                        @render.text
                        def u21_md_debuts():
                            md = u21_md()
                            return "0" if md is None else str(
                                int((u21_season()['debut_md'] == md).sum()))
                        ui.p("Season Debuts")

                with ui.layout_columns(col_widths=[7, 5], style="margin: 0 0 20px 0;"):
                    with ui.card():
                        @render.ui
                        def u21_md_header():
                            md = u21_md()
                            title = "U21 Players" if md is None else f"U21 Players - Matchday {md}"
                            source = u21_md_rows()['source']
                            if not source.empty:
                                title += ("  ·  from the U21 export" if (source == 'xlsx').any()
                                          else "  ·  from the match reports")
                            return ui.tags.div(title, class_="overview-card-header")

                        @render.table(escape=False)
                        def u21_md_table():
                            rows = u21_md_rows()
                            played = rows[rows['apps'] > 0].sort_values(
                                ['minutes', 'goals'], ascending=False)
                            if played.empty:
                                return pd.DataFrame(
                                    {"": ["No U21 player appeared on this matchday"]})
                            return pd.DataFrame({
                                'Player': played['player'].map(html.escape),
                                'Club': played['team'].map(club_html),
                                'Role': np.where(played['starts'] > 0, 'Started', 'Sub'),
                                'Minutes': played['minutes'].astype(int),
                                'G': played['goals'].astype(int),
                                'A': played['assists'].map(u21_number),
                                'Cards': (played['yellows'] + played['reds_direct']
                                          + played['reds_second_yellow']).astype(int),
                            })

                    with ui.card():
                        ui.tags.div("U21 Minutes by Club", class_="overview-card-header")
                        @render_plotly
                        @count_axes('x')
                        def u21_md_clubs():
                            data = u21_md_rows().groupby('team')['minutes'].sum().reset_index()
                            data = data[data['minutes'] > 0].sort_values('minutes')
                            if data.empty:
                                return empty_figure("No U21 minutes on this matchday")
                            fig = px.bar(
                                data, x='minutes', y='team', orientation='h',
                                color='team', color_discrete_map=TEAM_COLORS,
                                title='Minutes Given to U21 Players',
                                labels={'minutes': 'Minutes', 'team': ''}
                            )
                            fig.update_layout(
                                showlegend=False,
                                plot_bgcolor='rgba(0,0,0,0)',
                                paper_bgcolor='rgba(0,0,0,0)'
                            )
                            return fig

            with ui.nav_panel("Clubs"):
                with ui.layout_columns(col_widths=[6, 6], style="margin: 20px 0;"):
                    with ui.card():
                        ui.tags.div("U21 Minutes by Club", class_="overview-card-header")
                        @render_plotly
                        @count_axes('x')
                        def u21_club_minutes():
                            data = (u21_season().groupby('team')['minutes'].sum()
                                    .reset_index().sort_values('minutes'))
                            if data.empty:
                                return empty_figure()
                            fig = px.bar(
                                data, x='minutes', y='team', orientation='h',
                                color='team', color_discrete_map=TEAM_COLORS,
                                title='Season Minutes Given to U21 Players',
                                labels={'minutes': 'Minutes', 'team': ''}
                            )
                            fig.update_layout(
                                showlegend=False, height=520,
                                plot_bgcolor='rgba(0,0,0,0)',
                                paper_bgcolor='rgba(0,0,0,0)'
                            )
                            return fig

                    with ui.card():
                        ui.tags.div("U21 Pool vs Players Used", class_="overview-card-header")
                        @render_plotly
                        @count_axes('x')
                        def u21_club_usage():
                            season = u21_season()
                            if season.empty:
                                return empty_figure()
                            data = season.groupby('team').agg(
                                pool=('player_key', 'size'),
                                used=('apps', lambda apps: int((apps > 0).sum())),
                            ).reset_index()
                            order = data.sort_values(['used', 'pool'])['team'].tolist()
                            tidy = data.melt(id_vars='team', value_vars=['pool', 'used'],
                                             var_name='kind', value_name='players')
                            tidy['kind'] = tidy['kind'].map({'pool': 'In the U21 pool',
                                                             'used': 'Appeared'})
                            fig = px.bar(
                                tidy, x='players', y='team', color='kind',
                                orientation='h', barmode='group',
                                color_discrete_map={'In the U21 pool': '#95a5a6',
                                                    'Appeared': '#F5901F'},
                                category_orders={'team': order},
                                title='U21 Players Available and Used',
                                labels={'players': 'Players', 'team': '', 'kind': ''}
                            )
                            fig.update_layout(
                                height=520,
                                plot_bgcolor='rgba(0,0,0,0)',
                                paper_bgcolor='rgba(0,0,0,0)'
                            )
                            return fig

                with ui.layout_columns(col_widths=[12], style="margin: 20px 0;"):
                    with ui.card():
                        ui.tags.div("U21 Share of Club Minutes", class_="overview-card-header")
                        @render_plotly
                        def u21_club_share():
                            squad = lineups_df()
                            if squad.empty:
                                return empty_figure("Needs the match reports for this season")
                            club = (squad.assign(team=squad['team'].astype(str).str.upper())
                                         .groupby(['md', 'team'])['minutes_played'].sum()
                                         .rename('club'))
                            u21 = u21_df().groupby(['md', 'team'])['minutes'].sum().rename('u21')
                            both = pd.concat([club, u21], axis=1).dropna(subset=['club'])
                            data = both.fillna(0).groupby(level='team').sum()
                            data['share'] = (100 * data['u21'] / data['club']).round(1)
                            data = data.reset_index().sort_values('share')
                            fig = px.bar(
                                data, x='share', y='team', orientation='h',
                                color='team', color_discrete_map=TEAM_COLORS,
                                hover_data=['u21', 'club'],
                                title='Share of Club Minutes Played by U21 Players',
                                labels={'share': '% of club minutes', 'team': '',
                                        'u21': 'U21 minutes', 'club': 'Club minutes'}
                            )
                            fig.update_layout(
                                showlegend=False, height=600,
                                plot_bgcolor='rgba(0,0,0,0)',
                                paper_bgcolor='rgba(0,0,0,0)'
                            )
                            return fig

                        ui.tags.p(
                            "Club minutes come from the team sheets, so only matchdays "
                            "covered by the match reports count here.",
                            style="margin: 10px 15px; color: #777; font-size: 13px;")

                with ui.layout_columns(col_widths=[12], style="margin: 20px 0;"):
                    with ui.card():
                        ui.tags.div("Club Summary", class_="overview-card-header")
                        @render.table(escape=False)
                        def u21_club_table():
                            season = u21_season()
                            if season.empty:
                                return pd.DataFrame({"": ["No U21 data for this season yet"]})
                            table = season.groupby('team').agg(
                                pool=('player_key', 'size'),
                                used=('apps', lambda apps: int((apps > 0).sum())),
                                minutes=('minutes', 'sum'),
                                starts=('starts', 'sum'),
                                goals=('goals', 'sum'),
                                assists=('assists', lambda a: a.sum(min_count=1)),
                            ).reset_index().sort_values('minutes', ascending=False)
                            table['assists'] = table['assists'].map(u21_number)
                            table.columns = ['Club', 'U21 Pool', 'Appeared', 'Minutes',
                                             'Starts', 'Goals', 'Assists']
                            return logo_table(table, clubs=['Club'])

            with ui.nav_panel("Trends"):
                ui.tags.p(
                    "Pick up to four U21 players to follow matchday by matchday.",
                    style="margin: 20px 10px 0 10px; color: #555;"
                )

                with ui.div(style="margin: 16px 10px;"):
                    ui.input_selectize(
                        "u21_compare", "Players",
                        choices={}, multiple=True,
                        options={"maxItems": 4, "placeholder": "Choose players…",
                                 "render": ui.js_eval("window.playerRender")},
                    )

                @reactive.effect
                def _refresh_u21_compare():
                    """Offer the season's U21 players, busiest first."""
                    choices = {row['player_key']: player_label(row)
                               for _index, row in u21_season().iterrows()}
                    with reactive.isolate():
                        current = [p for p in (_chosen("u21_compare", None) or [])
                                   if p in choices]
                    if not current:
                        current = list(choices)[:2]
                    ui.update_selectize("u21_compare", choices=choices, selected=current)

                @reactive.calc
                def u21_trend():
                    """Per-matchday and running totals for the chosen players."""
                    chosen = list(_chosen("u21_compare", None) or [])
                    rows = u21_df()
                    if not chosen or rows.empty:
                        return pd.DataFrame(columns=['md', 'player', 'minutes', 'ga',
                                                     'cum_minutes', 'cum_ga'])
                    mds = sorted(int(m) for m in rows['md'].unique())
                    labels = {row['player_key']: player_label(row)
                              for _index, row in u21_season().iterrows()}
                    frames = []
                    for key in chosen:
                        mine = rows[rows['player_key'] == key]
                        per_md = (mine.assign(ga=mine['goals'] + mine['assists'].fillna(0))
                                      .groupby('md')[['minutes', 'ga']].sum()
                                      .reindex(mds, fill_value=0))
                        per_md['cum_minutes'] = per_md['minutes'].cumsum()
                        per_md['cum_ga'] = per_md['ga'].cumsum()
                        per_md['player'] = labels.get(key, key)
                        frames.append(per_md.rename_axis('md').reset_index())
                    return pd.concat(frames, ignore_index=True)

                with ui.layout_columns(col_widths=[6, 6], style="margin: 12px 0;"):
                    with ui.card():
                        ui.tags.div("Running Minutes", class_="overview-card-header")
                        @render_plotly
                        @count_axes('y')
                        def u21_trend_minutes():
                            data = u21_trend()
                            if data.empty:
                                return empty_figure("Choose players to follow")
                            fig = px.line(
                                data, x='md', y='cum_minutes', color='player', markers=True,
                                title='Minutes Played, Season to Date',
                                labels={'md': 'Matchday', 'cum_minutes': 'Minutes',
                                        'player': ''}
                            )
                            fig.update_xaxes(dtick=1)
                            fig.update_layout(
                                plot_bgcolor='rgba(0,0,0,0)',
                                paper_bgcolor='rgba(0,0,0,0)'
                            )
                            return fig

                    with ui.card():
                        ui.tags.div("Running Goal Contributions",
                                    class_="overview-card-header")
                        @render_plotly
                        @count_axes('y')
                        def u21_trend_contributions():
                            data = u21_trend()
                            if data.empty:
                                return empty_figure("Choose players to follow")
                            fig = px.line(
                                data, x='md', y='cum_ga', color='player', markers=True,
                                title='Goals + Assists, Season to Date',
                                labels={'md': 'Matchday', 'cum_ga': 'G+A', 'player': ''}
                            )
                            fig.update_xaxes(dtick=1)
                            fig.update_layout(
                                plot_bgcolor='rgba(0,0,0,0)',
                                paper_bgcolor='rgba(0,0,0,0)'
                            )
                            return fig

                with ui.layout_columns(col_widths=[12], style="margin: 20px 0;"):
                    with ui.card():
                        ui.tags.div("Minutes per Matchday", class_="overview-card-header")
                        @render_plotly
                        @count_axes('y')
                        def u21_trend_per_md():
                            data = u21_trend()
                            if data.empty:
                                return empty_figure("Choose players to follow")
                            fig = px.bar(
                                data, x='md', y='minutes', color='player', barmode='group',
                                title='Minutes on Each Matchday',
                                labels={'md': 'Matchday', 'minutes': 'Minutes', 'player': ''}
                            )
                            fig.update_xaxes(dtick=1)
                            fig.update_layout(
                                plot_bgcolor='rgba(0,0,0,0)',
                                paper_bgcolor='rgba(0,0,0,0)'
                            )
                            return fig

    # =============================================================================
    # PAGE 7: OFFICIALS
    # =============================================================================
    with ui.nav_panel("Officials"):
        with ui.navset_pill(id="official_tab"):

            with ui.nav_panel("Referees"):
                with ui.layout_columns(col_widths=[6, 6], style="margin: 20px 0;"):
                    with ui.card():
                        ui.tags.div("Appointments", class_="overview-card-header")
                        @render_plotly
                        @count_axes('x')
                        def referee_appointments():
                            data = referee_record()
                            if data.empty:
                                return empty_figure("No officials recorded")
                            data = data.sort_values('matches')
                            fig = px.bar(
                                data, x='matches', y='referee', orientation='h',
                                color_discrete_sequence=['#1a5f7a'],
                                title='Matches Refereed',
                                labels={'matches': 'Matches', 'referee': ''}
                            )
                            fig.update_layout(
                                height=520,
                                plot_bgcolor='rgba(0,0,0,0)',
                                paper_bgcolor='rgba(0,0,0,0)'
                            )
                            return fig

                    with ui.card():
                        ui.tags.div("Cards per Match", class_="overview-card-header")
                        @render_plotly
                        def referee_cards():
                            data = referee_record()
                            if data.empty:
                                return empty_figure("No officials recorded")
                            data = data.sort_values('cards_per_match')
                            fig = px.bar(
                                data, x='cards_per_match', y='referee',
                                orientation='h',
                                hover_data=['matches', 'cards'],
                                color_discrete_sequence=['#e74c3c'],
                                title='Cards Shown per Match',
                                labels={'cards_per_match': 'Cards per match',
                                        'referee': ''}
                            )
                            fig.update_layout(
                                height=520,
                                plot_bgcolor='rgba(0,0,0,0)',
                                paper_bgcolor='rgba(0,0,0,0)'
                            )
                            return fig

                with ui.layout_columns(col_widths=[12], style="margin: 20px 0;"):
                    with ui.card():
                        ui.tags.div("Referee Record", class_="overview-card-header")
                        @render.table
                        def referee_table():
                            data = referee_record().copy()
                            if data.empty:
                                return data
                            data.columns = ['Referee', 'Matches', 'Cards',
                                            'Cards/Match']
                            return data

                        ui.tags.p(
                            "Card counts are every caution and dismissal recorded in "
                            "the match. With only a handful of appointments each so "
                            "far, treat the rates as a running tally rather than a "
                            "judgement.",
                            style="margin: 10px 15px; color: #777; font-size: 13px;")

            with ui.nav_panel("Appointments"):
                with ui.card():
                    ui.tags.div("Match Officials", class_="overview-card-header")
                    @render.table(escape=False)
                    def officials_table():
                        info = match_info_df()
                        if info.empty:
                            return pd.DataFrame(columns=['Match'])
                        columns = ['game', 'md', 'referee', 'assistant_1',
                                   'assistant_2', 'fourth_official', 'commissioner']
                        available = [c for c in columns if c in info.columns]
                        data = info[available].sort_values(['md', 'game'])
                        data.columns = ['Match', 'MD', 'Referee', '1st Assistant',
                                        '2nd Assistant', 'Fourth Official',
                                        'Commissioner'][:len(available)]
                        return logo_table(data, matches=['Match'])

    # =========================================================================
    # Competition switcher, pinned to the right of the bar
    # =========================================================================
    ui.nav_spacer()

    with ui.nav_control():
        with ui.div(class_="navbar-switcher"):
            ui.input_select(
                "league", None,
                choices={code: code for code in ALL_LEAGUES},
                selected=DEFAULT_LEAGUE,
            )
            ui.input_select(
                "season", None,
                choices={s: s for s in seasons_for(DEFAULT_LEAGUE)},
                selected=DEFAULT_SEASON,
            )


