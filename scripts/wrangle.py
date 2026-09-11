import pandas as pd
import numpy as np
import os
import re
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from extract_u21 import (COUNT_COLUMNS as U21_COUNT_COLUMNS,  # noqa: E402
                         U21_COLUMNS as U21_EXPORT_COLUMNS, name_key, tidy_name,
                         u21_born_from)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
dataDIR = PROJECT_ROOT / "csvs/new"
outputDIR = PROJECT_ROOT / "csvs/transformed"
archiveDIR = PROJECT_ROOT / "csvs/transformed_archive"

GAME_SPLIT = re.compile(r"-VS-")

# every event table now carries the competition it belongs to
KEY_COLUMNS = ['league', 'season']


def archive_previous_output():
    """Move the pre-existing transformed CSVs aside, once.

    The old files were built from csvs/raw (UPL 2025/26, hand-typed) and predate
    the league/season columns, so they are kept for reference rather than
    overwritten.  Guarding on the archive's absence means re-running wrangle
    never buries the output of the run before it.
    """
    if archiveDIR.exists():
        return
    existing = sorted(p for p in outputDIR.glob("*.csv")) if outputDIR.exists() else []
    if not existing:
        return
    archiveDIR.mkdir(parents=True, exist_ok=True)
    for path in existing:
        shutil.move(str(path), str(archiveDIR / path.name))
    print(f"Archived {len(existing)} previous file(s) to {archiveDIR}")


archive_previous_output()
outputDIR.mkdir(parents=True, exist_ok=True)


def parse_minute_parts(v):
    """Split a raw minute cell into (base minute, stoppage minutes).

    '45(+2)' -> (45, 2), '90 + (1)' -> (90, 1), '65' -> (65, 0).

    The base is what a stoppage-time event should be *sorted and binned* by: a
    45(+2) goal belongs at the end of the first half, not at minute 47 where it
    would collide with a genuine 47th-minute event.
    """
    s = str(v).replace('(', '').replace(')', '')
    if s.strip().lower() == 'nan' or s.strip() == '':
        return (np.nan, np.nan)
    if '+' in s:
        left, right = s.split('+')
        return (int(left.strip()), int(right.strip()))
    return (int(s.strip()), 0)


def parse_minute(v):
    base, stoppage = parse_minute_parts(v)
    if pd.isna(base):
        return np.nan
    return base + stoppage

def df_transform(df, df_name):
    # Transform a dataframe by parsing minutes & adding period
    print(f"\n{'='*60}")
    print(f"Processing: {df_name}")
    print(f"{'='*60}")
    print(f"Initial shape: {df.shape}")
    print(f"\nFirst 3 rows before transformation:")
    print(df.head(3))

    # populate added_time
    # df['added_time'] = df['min'].astype(str).str.contains('(', regex=False).map({True: 'yes', False: 'no'})

    # parse minute values
    parts = df['min'].apply(parse_minute_parts)
    df['base_minute'] = [p[0] for p in parts]
    df['stoppage'] = [p[1] for p in parts]
    df['minute'] = (df['base_minute'] + df['stoppage']).astype('int64')
    df['base_minute'] = df['base_minute'].astype('int64')
    df['stoppage'] = df['stoppage'].astype('int64')

    # create period feature
    conditions = [
        (df['minute'] <= 45).fillna(False).astype(bool).to_numpy(),
        ((df['minute'] > 45) & (df['minute'] < 60) & (df['added_time'] == 'yes')).fillna(False).astype(bool).to_numpy(),
        ((df['minute'] > 45) & (df['minute'] <= 90) & (df['added_time'] == 'no')).fillna(False).astype(bool).to_numpy(),
        (df['minute'] > 90).fillna(False).astype(bool).to_numpy()
    ]
    choices = [1, 1, 2, 2]
    df['period'] = np.select(conditions, choices).astype('int64')

    # Get the index position of 'min' column
    min_col_idx = df.columns.get_loc('min')

    # reorder columns: remove 'min', insert 'minute' at its position, move 'added_time' and 'period' after
    cols = df.columns.tolist()
    cols.remove('min')
    cols.remove('added_time')
    cols.remove('minute')
    cols.remove('period')
    cols.remove('base_minute')
    cols.remove('stoppage')

    # insert minute at the original 'min' position
    cols.insert(min_col_idx, 'minute')
    # insert added_time after minute
    cols.insert(min_col_idx + 1, 'added_time')
    # insert period after added_time
    cols.insert(min_col_idx + 2, 'period')
    # keep the un-inflated minute and its stoppage alongside
    cols.insert(min_col_idx + 3, 'base_minute')
    cols.insert(min_col_idx + 4, 'stoppage')

    df = df[cols]

    print(f"\nFinal shape: {df.shape}")
    print(f"\nFirst 3 rows after transformation:")
    print(df.head(3))
    print(f"\nColumn order: {list(df.columns)}")
    print(f"\nSummary statistics for new columns:")
    print(df[['minute', 'added_time', 'period']].describe(include='all'))

    return df

# extractor output -> transformed name. These carry a `min` column that needs
# parsing into minute / period / base_minute / stoppage.
csv_files = {'goalsNew.csv': 'goals.csv',
             'cautionsNew.csv': 'cautions.csv',
             'subsNew.csv': 'subs.csv'}

# Team sheets, staff and match headers need no minute parsing -- their minutes
# are already plain integers -- so they are copied through as they are.
passthrough_files = {'lineupsNew.csv': 'lineups.csv',
                     'staffNew.csv': 'staff.csv',
                     'matchInfoNew.csv': 'match_info.csv'}

frames = {}

for source_file, csv_file in csv_files.items():
    input_path = dataDIR / source_file

    if not input_path.exists():
        print(f"\nWarning: {source_file} not found in {dataDIR}")
        continue

    # read csv
    df = pd.read_csv(input_path)

    # drop rows with 3 or more missing values
    df = df[df.isna().sum(axis=1) < 3]

    # find column 'min'
    if 'min' not in df.columns:
        print(f"\nWarning: 'min' column not found in {csv_file}, skipping")
        continue

    # transform
    transformedDF = df_transform(df, csv_file)

    # drop nulls in transformedDF
    transformedDF = transformedDF[transformedDF.isna().sum(axis=1) < 3]

    # save with _transformed prefix
    output_filename = f"transformed_{csv_file}"
    output_path = outputDIR / output_filename
    transformedDF.to_csv(output_path, index=False)
    frames[csv_file.replace('.csv', '')] = transformedDF

    print(f"\n✓ Saved to: {output_path}")


for source_file, csv_file in passthrough_files.items():
    input_path = dataDIR / source_file
    if not input_path.exists():
        print(f"\nWarning: {source_file} not found in {dataDIR}")
        continue

    df = pd.read_csv(input_path)
    output_path = outputDIR / f"transformed_{csv_file}"
    df.to_csv(output_path, index=False)
    print(f"✓ Saved to: {output_path}  ({len(df)} rows)")


# =============================================================================
# MATCH RECONSTRUCTION
# =============================================================================
# The `game` key is always "<HOME>-vs-<AWAY>", so home/away and every scoreline
# can be rebuilt from the goal events.  Replaying those goals in order also
# tells us whether a team was ever ahead or ever behind during a match, which is
# what the comeback / collapse tables below are built from.

def normalise(df, columns=('game', 'team')):
    out = df.copy()
    for column in columns:
        if column in out.columns:
            out[column] = out[column].astype(str).str.strip().str.upper()
    return out


def matchday_by_game(frames, league, season):
    """One matchday per game, taking the most common label when they disagree."""
    stacked = []
    for df in frames.values():
        if {'game', 'md'} <= set(df.columns):
            part = normalise(df)[['game', 'md']].dropna()
            part['md'] = part['md'].astype(int)
            stacked.append(part)
    stacked = pd.concat(stacked, ignore_index=True)

    disagreements = stacked.groupby('game')['md'].nunique()
    disagreements = disagreements[disagreements > 1]
    for game in disagreements.index:
        labels = sorted(stacked[stacked['game'] == game]['md'].unique())
        print(f"  ! {league} {season}: {game} is tagged with matchdays {labels}; "
              f"using {labels[0]}")

    return stacked.groupby('game')['md'].agg(lambda s: sorted(s.mode())[0])


def build_season_matches(frames, league, season):
    """One row per match, plus one row per team per match, for one competition."""
    goals = normalise(frames['goals'])
    md_lookup = matchday_by_game(frames, league, season)

    matches, team_matches = [], []
    unmatched = []

    for game, md in md_lookup.items():
        sides = GAME_SPLIT.split(game)
        if len(sides) != 2:
            print(f"  ! cannot split game key {game!r} into home-vs-away; skipped")
            continue
        home, away = (s.strip() for s in sides)

        # replay the goals in the order they were scored
        played = goals[goals['game'] == game].sort_values(
            ['base_minute', 'stoppage'], kind='mergesort')
        home_goals = away_goals = 0
        home_led = away_led = False
        for team in played['team']:
            if team == home:
                home_goals += 1
            elif team == away:
                away_goals += 1
            else:
                unmatched.append((game, team))
                continue
            if home_goals > away_goals:
                home_led = True
            elif away_goals > home_goals:
                away_led = True

        matches.append({
            'league': league, 'season': season,
            'game': game, 'md': md, 'home': home, 'away': away,
            'home_goals': home_goals, 'away_goals': away_goals,
            'total_goals': home_goals + away_goals,
        })

        for team, opponent, venue, gf, ga, led, trailed in (
            (home, away, 'home', home_goals, away_goals, home_led, away_led),
            (away, home, 'away', away_goals, home_goals, away_led, home_led),
        ):
            result = 'W' if gf > ga else ('D' if gf == ga else 'L')
            points = {'W': 3, 'D': 1, 'L': 0}[result]
            team_matches.append({
                'league': league, 'season': season,
                'game': game, 'md': md, 'team': team, 'opponent': opponent,
                'venue': venue, 'gf': gf, 'ga': ga, 'gd': gf - ga,
                'result': result, 'points': points,
                'was_ahead': bool(led), 'was_behind': bool(trailed),
                # points actually taken in a match the team trailed in
                'points_from_losing': points if trailed else 0,
                # points thrown away in a match the team led in
                'points_dropped_from_winning': (3 - points) if led else 0,
                'win_from_behind': bool(trailed and result == 'W'),
                'draw_from_behind': bool(trailed and result == 'D'),
                'loss_from_ahead': bool(led and result == 'L'),
                'draw_from_ahead': bool(led and result == 'D'),
            })

    if unmatched:
        print(f"\n  ! {len(unmatched)} goal(s) credited to a team that is not in "
              f"the game key, e.g. {unmatched[:3]}")

    return pd.DataFrame(matches), pd.DataFrame(team_matches)


def build_matches(frames):
    """Reconstruct matches one competition at a time.

    Every league and season is rebuilt independently so that a game key which
    happens to recur across competitions -- the same two clubs meeting in a
    different season, say -- never has its goals pooled into one scoreline.
    """
    competitions = sorted({
        (str(row['league']), str(row['season']))
        for df in frames.values()
        for row in df[KEY_COLUMNS].to_dict('records')
    })

    matches, team_matches = [], []
    for league, season in competitions:
        slice_ = {name: df[(df['league'] == league) & (df['season'] == season)]
                  for name, df in frames.items()}
        season_matches, season_team_matches = build_season_matches(slice_, league, season)
        matches.append(season_matches)
        team_matches.append(season_team_matches)
        print(f"  {league} {season}: {len(season_matches)} matches")

    return pd.concat(matches, ignore_index=True), pd.concat(team_matches, ignore_index=True)


print(f"\n{'='*60}")
print("Reconstructing matches from goal events")
print(f"{'='*60}")

SORT_KEYS = KEY_COLUMNS + ['md', 'game']
matchesDF, teamMatchesDF = build_matches(frames)
matchesDF = matchesDF.sort_values(SORT_KEYS).reset_index(drop=True)
teamMatchesDF = teamMatchesDF.sort_values(SORT_KEYS + ['venue']).reset_index(drop=True)

matchesDF.to_csv(outputDIR / "transformed_matches.csv", index=False)
teamMatchesDF.to_csv(outputDIR / "transformed_team_matches.csv", index=False)
print(f"\n✓ Saved to: {outputDIR / 'transformed_matches.csv'}  ({len(matchesDF)} matches)")
print(f"✓ Saved to: {outputDIR / 'transformed_team_matches.csv'}  ({len(teamMatchesDF)} rows)")


# =============================================================================
# COMEBACKS & COLLAPSES
# =============================================================================
# "From a losing position" means the team was behind at some point in the match,
# whatever the final result.  "From a winning position" means it was ahead at
# some point.  Points dropped from a winning position is 3 minus the points
# actually taken, so a draw after leading costs 2 and a defeat after leading
# costs 3.

def comeback_table(team_matches):
    grouped = team_matches.groupby(KEY_COLUMNS + ['team'])
    table = pd.DataFrame({
        'matches': grouped.size(),
        'matches_behind': grouped['was_behind'].sum(),
        'points_from_losing': grouped['points_from_losing'].sum(),
        'wins_from_losing': grouped['win_from_behind'].sum(),
        'draws_from_losing': grouped['draw_from_behind'].sum(),
        'matches_ahead': grouped['was_ahead'].sum(),
        'points_dropped_from_winning': grouped['points_dropped_from_winning'].sum(),
        'losses_from_winning': grouped['loss_from_ahead'].sum(),
        'draws_from_winning': grouped['draw_from_ahead'].sum(),
    }).reset_index()
    return table.sort_values('points_from_losing', ascending=False).reset_index(drop=True)


comebacksDF = comeback_table(teamMatchesDF)
comebacksDF.to_csv(outputDIR / "transformed_comebacks.csv", index=False)
print(f"✓ Saved to: {outputDIR / 'transformed_comebacks.csv'}")


def announce(question, table, column, ascending=False, subset=None, unit=""):
    """Print the answer to one question, with the chasing pack for context."""
    data = table if subset is None else table[subset]
    if data.empty:
        print(f"\n{question}\n   (no team qualifies)")
        return
    ranked = data.sort_values([column, 'team'], ascending=[ascending, True])
    best = ranked.iloc[0]
    tied = ranked[ranked[column] == best[column]]['team'].tolist()
    print(f"\n{question}")
    print(f"   -> {', '.join(tied)}  ({int(best[column])}{unit})")
    for _, row in ranked.head(5).iterrows():
        print(f"      {row['team']:<10} {int(row[column]):>3}{unit}   "
              f"(behind in {int(row['matches_behind'])}, ahead in {int(row['matches_ahead'])} "
              f"of {int(row['matches'])})")


# One set of answers per competition; pooling leagues would compare teams that
# never played each other.
for (league, season), table in comebacksDF.groupby(KEY_COLUMNS):
    table = table.reset_index(drop=True)
    print(f"\n{'='*60}")
    print(f"COMEBACKS & COLLAPSES - {league} {season}")
    print(f"{'='*60}")

    announce("Most points earned from a losing position:",
             table, 'points_from_losing', unit=" pts")
    announce("Most wins from a losing position:",
             table, 'wins_from_losing')
    announce("Most points lost from a winning position:",
             table, 'points_dropped_from_winning', unit=" pts")
    announce("Most games lost from a winning position:",
             table, 'losses_from_winning')
    announce("Fewest wins from a losing position (of teams that went behind at all):",
             table, 'wins_from_losing', ascending=True,
             subset=table['matches_behind'] > 0)


# =============================================================================
# U21 TRACKER
# =============================================================================
# One row per U21 player per matchday, from two sources:
#   * the U21 export (csvs/new/u21New.csv) -- the official list, and the only
#     source of assists, penalties and own goals;
#   * the match reports' team sheets, for any matchday without an export, with
#     the birth year read from the last two digits of the registration id
#     (036912M08 -> 2008).
# Both are held to one age rule, u21_born_from() in extract_u21.py: born on or
# after 1 January, 21 years before the season starts.  An export row whose
# birth year is known and falls before that is left out and reported.  Where
# both sources exist for a matchday the export wins, and the minutes the
# reports give the same player are kept alongside it as a cross-check.

U21_KEYS = KEY_COLUMNS + ['md']
U21_EXPORT_ONLY = ['own_goals', 'assists', 'penalties']
U21_OUTPUT_COLUMNS = (U21_KEYS + ['source', 'player_key', 'player_id', 'player', 'team',
                                  'position', 'jersey', 'birth_year', 'u21_born_from']
                      + U21_COUNT_COLUMNS + ['report_minutes', 'team_points',
                                             'team_matches'])
LINEUP_FIELDS = ['league', 'season', 'game', 'md', 'team', 'shirt', 'player',
                 'player_id', 'role', 'is_goalkeeper', 'on_minute', 'off_minute',
                 'minutes_played']


def birth_year(player_id):
    """'036912M08' -> 2008: a registration id ends in the two-digit birth year.

    Years above 30 are read as 19xx, which holds until the class of 2031 turns
    professional.
    """
    text = str(player_id).strip()
    if len(text) < 2 or not text[-2:].isdigit():
        return np.nan
    yy = int(text[-2:])
    return 2000 + yy if yy <= 30 else 1900 + yy


def u21_cutoff(season):
    """'2026/27' -> 2005, the earliest birth year still U21 that season.

    The cutoff date is always 1 January, so comparing years is exact.
    """
    return u21_born_from(season).year


def read_optional(path, columns, **kwargs):
    """A CSV that may not exist yet, as an empty frame with the expected columns."""
    return pd.read_csv(path, **kwargs) if path.exists() else pd.DataFrame(columns=columns)


def report_totals(lineups, goals, cautions):
    """Per player per matchday for everyone on a team sheet, keyed on the id.

    Goals and cautions carry only a printed name, so each is matched back to
    that match's team sheet for the registration id.
    """
    group = U21_KEYS + ['player_id']
    if lineups.empty:
        return pd.DataFrame(columns=group + ['player', 'team', 'jersey', 'position']
                            + U21_COUNT_COLUMNS)

    squad = lineups.copy()
    squad['game'] = squad['game'].astype(str).str.upper()
    squad['team'] = squad['team'].astype(str).str.upper()
    # a starter, or a substitute who came on -- even one sent on in stoppage
    # time, who is credited with 0 minutes but still made an appearance
    squad['started'] = squad['role'] == 'starting'
    squad['came_on'] = (squad['role'] == 'substitute') & squad['on_minute'].notna()
    squad['appeared'] = squad['started'] | squad['came_on']
    # only starters carry an off minute: the extractor does not record a
    # substitute being taken off again, so his minutes run on to 90
    squad['went_off'] = squad['started'] & squad['off_minute'].notna()
    squad['keeper'] = squad['is_goalkeeper'] == 'yes'

    lookup = dict(zip(zip(squad['game'], squad['player'].map(name_key)),
                      squad['player_id']))
    totals = squad.groupby(group).agg(
        player=('player', 'last'), team=('team', 'last'), jersey=('shirt', 'last'),
        keeper=('keeper', 'any'), apps=('appeared', 'sum'),
        minutes=('minutes_played', 'sum'), starts=('started', 'sum'),
        sub_in=('came_on', 'sum'), sub_out=('went_off', 'sum'))

    caution = cautions['caution'].astype(str).str.lower()
    for label, events in (('goals', goals),
                          ('yellows', cautions[caution == 'yellow']),
                          ('reds_direct', cautions[caution == 'red']),
                          ('reds_second_yellow', cautions[caution == 'second yellow'])):
        ids = [lookup.get((str(game).upper(), name_key(player)))
               for game, player in zip(events['game'], events['player'])]
        keyed = events.assign(player_id=ids).dropna(subset=['player_id'])
        totals[label] = keyed.groupby(group).size()

    totals = totals.reset_index()
    counts = [c for c in U21_COUNT_COLUMNS if c not in U21_EXPORT_ONLY]
    totals[counts] = totals[counts].fillna(0).astype(int)
    for column in U21_EXPORT_ONLY:
        totals[column] = np.nan                  # the reports do not record these
    totals['player'] = totals['player'].map(tidy_name)
    totals['position'] = np.where(totals['keeper'], 'Goalkeeper', '')
    totals['jersey'] = pd.to_numeric(totals['jersey'], errors='coerce').map(
        lambda n: '' if pd.isna(n) else str(int(n)))
    return totals.drop(columns='keeper')


def link_export_ids(export, lineups, aliases):
    """Registration id for each export row, found on the team sheets.

    Tried in order: an id the export itself carries; csvs/u21_aliases.csv; the
    same name at the same club that season; the same name anywhere that
    season; and last the same name anywhere in the league's history -- taken
    only when that id's birth year makes the player U21, which is what stops a
    senior namesake from being picked up.  Unmatched rows get ''.
    """
    if export.empty:
        return pd.Series(dtype=str)
    sheet = lineups[['league', 'season', 'team', 'player', 'player_id']].copy()
    sheet['team'] = sheet['team'].astype(str).str.upper()
    sheet['name_key'] = sheet['player'].map(name_key)

    def unique_id(keys):
        if sheet.empty:
            return {}
        found = sheet.groupby(keys)['player_id'].agg(
            lambda ids: ids.iloc[0] if ids.nunique() == 1 else None)
        return found.dropna().to_dict()

    by_team = unique_id(['league', 'season', 'team', 'name_key'])
    by_season = unique_id(['league', 'season', 'name_key'])
    by_league = unique_id(['league', 'name_key'])
    alias = {(r.league, r.season, str(r.team).upper(), name_key(r.player)): r.player_id
             for r in aliases.itertuples()}

    def resolve(row):
        given = str(row.player_id).strip()
        if given and given.lower() != 'nan':
            return given
        team_key = (row.league, row.season, row.team, row.name_key)
        found = (alias.get(team_key) or by_team.get(team_key)
                 or by_season.get((row.league, row.season, row.name_key)))
        if found:
            return found
        earlier = by_league.get((row.league, row.name_key))
        if earlier and birth_year(earlier) >= u21_cutoff(row.season):
            return earlier
        return ''

    return export.apply(resolve, axis=1)


def build_u21(export, lineups, goals, cautions, team_matches, aliases):
    """The U21 matchday table, plus the discrepancies worth a human look."""
    reports = report_totals(lineups, goals, cautions)
    reports['birth_year'] = reports['player_id'].map(birth_year)

    export = export.copy()
    export['player_id'] = link_export_ids(export, lineups, aliases)
    export['birth_year'] = export['player_id'].map(birth_year)
    stated = pd.to_datetime(export['date_of_birth'], errors='coerce', dayfirst=True).dt.year
    export['birth_year'] = stated.fillna(export['birth_year'])
    # an unknown birth year compares False, so only a known over-age row goes
    over_age = export['birth_year'] < export['season'].map(u21_cutoff)
    export, too_old = export[~over_age].copy(), export[over_age]
    export['source'] = 'xlsx'
    export = export.merge(
        reports[U21_KEYS + ['player_id', 'minutes']].rename(
            columns={'minutes': 'report_minutes'}),
        on=U21_KEYS + ['player_id'], how='left')

    # the reports stand in for a matchday only when it has no export
    covered = set(zip(export['league'], export['season'], export['md']))
    u21_by_id = reports[reports['birth_year'] >= reports['season'].map(u21_cutoff)]
    is_covered = pd.Series(
        [key in covered for key in zip(u21_by_id['league'], u21_by_id['season'],
                                        u21_by_id['md'])],
        index=u21_by_id.index, dtype=bool)
    not_listed = u21_by_id[is_covered & (u21_by_id['apps'] > 0)
                           & ~u21_by_id['player_id'].isin(export['player_id'])]
    from_reports = u21_by_id[~is_covered].assign(
        source='reports', report_minutes=lambda d: d['minutes'],
        name_key=lambda d: d['player'].map(name_key))

    rows = pd.concat([export, from_reports], ignore_index=True)
    rows['player_id'] = rows['player_id'].fillna('').astype(str)
    rows['player_key'] = np.where(rows['player_id'] != '', rows['player_id'],
                                  'name:' + rows['name_key'].astype(str))

    points = team_matches.assign(team=team_matches['team'].astype(str).str.upper())
    points = points.groupby(U21_KEYS + ['team']).agg(
        team_points=('points', 'sum'), team_matches=('game', 'nunique')).reset_index()
    rows = rows.merge(points, on=U21_KEYS + ['team'], how='left')

    rows['u21_born_from'] = rows['season'].map(lambda s: u21_born_from(s).isoformat())
    disagree = export[export['report_minutes'].notna()
                      & ((export['minutes'] - export['report_minutes']).abs() > 1)]
    rows = rows[U21_OUTPUT_COLUMNS].sort_values(U21_KEYS + ['team', 'player'])
    return rows.reset_index(drop=True), disagree, not_listed, too_old


print(f"\n{'='*60}")
print("U21 tracker")
print(f"{'='*60}")

u21Export = read_optional(dataDIR / "u21New.csv", U21_EXPORT_COLUMNS,
                          dtype={'player_id': str, 'jersey': str, 'date_of_birth': str})
for column in ('player_id', 'jersey', 'position', 'date_of_birth'):
    u21Export[column] = u21Export[column].fillna('')
u21DF, u21Disagree, u21NotListed, u21OverAge = build_u21(
    u21Export,
    read_optional(outputDIR / "transformed_lineups.csv", LINEUP_FIELDS),
    frames.get('goals', pd.DataFrame(columns=['league', 'season', 'game', 'md', 'player'])),
    frames.get('cautions', pd.DataFrame(columns=['league', 'season', 'game', 'md',
                                                 'player', 'caution'])),
    teamMatchesDF,
    read_optional(PROJECT_ROOT / "csvs/u21_aliases.csv",
                  ['league', 'season', 'team', 'player', 'player_id']),
)
u21DF.to_csv(outputDIR / "transformed_u21_matchday.csv", index=False)
print(f"✓ Saved to: {outputDIR / 'transformed_u21_matchday.csv'}  ({len(u21DF)} rows)")

for (league, season), part in u21DF.groupby(KEY_COLUMNS):
    listed = part[part['source'] == 'xlsx']
    export_mds = ", ".join(str(int(m)) for m in sorted(listed['md'].unique())) or "-"
    report_mds = ", ".join(
        str(int(m)) for m in sorted(part.loc[part['source'] == 'reports', 'md'].unique())) or "-"
    born_from = u21_born_from(season)
    print(f"  {league} {season} (born on or after {born_from.day} {born_from:%B %Y}): "
          f"{part['player_key'].nunique()} players; "
          f"export md {export_mds}; reports md {report_mds}")
    if not listed.empty:
        linked = listed.drop_duplicates('player_key')
        print(f"    linked to a registration id: "
              f"{int((linked['player_id'] != '').sum())} of {len(linked)} listed players")

if not u21Disagree.empty:
    print(f"\n  ! {len(u21Disagree)} U21 export row(s) disagree with the match reports "
          f"on minutes by more than 1:")
    for row in u21Disagree.head(10).itertuples():
        print(f"      md{row.md} {row.player} ({row.team}): export {row.minutes}, "
              f"reports {int(row.report_minutes)}")
if not u21NotListed.empty:
    print(f"\n  ! {len(u21NotListed)} player(s) U21 by birth year played on a matchday "
          f"with an export but are not on it, e.g. "
          f"{u21NotListed['player'].head(5).tolist()}")
if not u21OverAge.empty:
    print(f"\n  ! {len(u21OverAge)} U21 export row(s) left out, born before the "
          f"season's cutoff:")
    for row in u21OverAge.head(10).itertuples():
        print(f"      {row.season} md{row.md} {row.player} ({row.team}): born "
              f"{int(row.birth_year)}, cutoff {u21_cutoff(row.season)}")

print(f"\n{'='*60}")
print("All transformations complete!")
print(f"{'='*60}")
