import pandas as pd
import numpy as np
import os
import re
from pathlib import Path

dataDIR = Path(__file__).resolve().parent / "csvs/raw"
outputDIR = Path(__file__).resolve().parent / "csvs/transformed"
outputDIR.mkdir(parents=True, exist_ok=True)

GAME_SPLIT = re.compile(r"-VS-")


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

# List of csv files to process
csv_files = ['goals.csv', 'cautions.csv', 'subs.csv']

frames = {}

for csv_file in csv_files:
    input_path = dataDIR / csv_file

    if not input_path.exists():
        print(f"\nWarning: {csv_file} not found in {dataDIR}")
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


def matchday_by_game(frames):
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
        print(f"  ! {game} is tagged with matchdays {labels}; using {labels[0]}")

    return stacked.groupby('game')['md'].agg(lambda s: sorted(s.mode())[0])


def build_matches(frames):
    """One row per match, plus one row per team per match with form flags."""
    goals = normalise(frames['goals'])
    md_lookup = matchday_by_game(frames)

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


print(f"\n{'='*60}")
print("Reconstructing matches from goal events")
print(f"{'='*60}")

matchesDF, teamMatchesDF = build_matches(frames)
matchesDF = matchesDF.sort_values(['md', 'game']).reset_index(drop=True)
teamMatchesDF = teamMatchesDF.sort_values(['md', 'game', 'venue']).reset_index(drop=True)

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
    grouped = team_matches.groupby('team')
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


print(f"\n{'='*60}")
print("COMEBACKS & COLLAPSES")
print(f"{'='*60}")

announce("Most points earned from a losing position:",
         comebacksDF, 'points_from_losing', unit=" pts")
announce("Most wins from a losing position:",
         comebacksDF, 'wins_from_losing')
announce("Most points lost from a winning position:",
         comebacksDF, 'points_dropped_from_winning', unit=" pts")
announce("Most games lost from a winning position:",
         comebacksDF, 'losses_from_winning')
announce("Fewest wins from a losing position (of teams that went behind at all):",
         comebacksDF, 'wins_from_losing', ascending=True,
         subset=comebacksDF['matches_behind'] > 0)

print(f"\n{'='*60}")
print("All transformations complete!")
print(f"{'='*60}")
