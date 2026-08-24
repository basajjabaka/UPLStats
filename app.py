from pathlib import Path
import pandas as pd
import numpy as np
import plotly.express as px
import folium as fl
from folium.plugins import HeatMap
from shiny import reactive
from shiny.express import render, input, ui
from shinywidgets import render_plotly, render_altair, render_widget
import matplotlib.pyplot as plt


# css styling
ui.tags.style(
    """
    .headercontainer {
        display: flex;
        align-items: center;
        justify-content: center;
        height: 60px;
        background: #00008B;
        border-radius: 0 0 15px 15px;
        box-shadow: 0 4px 15px rgba(0,0,0,0.3);
        margin-bottom: 20px;
    }

    .logocontainer {
        margin-right: 15px;
        height: 100% !important;
        padding: 10px;
    }

    .logocontainer img {
        height: 50px;
    }

    .titlecontainer h2 {
        color: white;
        font-weight: bold;
        font-size: 28px;
        text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
        padding: 10px;
        margin: 0;
    }

    body {
        background: linear-gradient(135deg, #f5f7fa 0%, #e4e8ec 100%);
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
    }

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
goalsDF = pd.read_csv(inputDIR / "transformed_goals.csv")
cautionsDF = pd.read_csv(inputDIR / "transformed_cautions.csv")
subsDF = pd.read_csv(inputDIR / "transformed_subs.csv")

# match-level tables rebuilt from the goal events by wrangle.py
matchesDF = pd.read_csv(inputDIR / "transformed_matches.csv")
teamMatchesDF = pd.read_csv(inputDIR / "transformed_team_matches.csv")
comebacksDF = pd.read_csv(inputDIR / "transformed_comebacks.csv")

# Convert all team names to UPPERCASE
goalsDF['team'] = goalsDF['team'].str.upper()
cautionsDF['team'] = cautionsDF['team'].str.upper()
subsDF['team'] = subsDF['team'].str.upper()

# Which side of the "HOME-vs-AWAY" key each event belongs to
def add_venue(df):
    """Tag every event row as home or away, from the game key."""
    home = df['game'].astype(str).str.upper().str.split('-VS-').str[0].str.strip()
    df['venue'] = np.where(df['team'].astype(str).str.upper() == home, 'home', 'away')
    return df

for _df in (goalsDF, cautionsDF, subsDF):
    add_venue(_df)

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
    "MBARARA": "#1E90FF"      # Dodger Blue
}

# get unique teams and matchdays
all_teams = set()
for col, df in [('team', goalsDF), ('team', cautionsDF), ('team', subsDF)]:
    teams = df[col].dropna().astype(str).unique()
    all_teams.update(teams)

all_teams = sorted([t for t in all_teams if t.lower() != 'nan' and t.strip() != ''])

all_matchdays = sorted([int(md) for md in goalsDF['md'].unique() if pd.notna(md)])

# Helper function for team-colored headers
def get_team_header_style(team):
    """Generate header style based on team color"""
    color = TEAM_COLORS.get(team, "#1a5f7a")
    return f"background: {color} !important; color: white; border-radius: 15px 15px 0 0 !important; font-weight: bold; font-size: 16px; padding: 15px;"

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

cautionsDF['caution_display'] = cautionsDF.apply(get_caution_color, axis=1)

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
    data = teamMatchesDF
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
    played = matchesDF[matchesDF['md'] == md].sort_values('game')
    if played.empty:
        return pd.DataFrame(columns=['Home', 'Score', 'Away'])
    return pd.DataFrame({
        'Home': played['home'].values,
        'Score': [f"{h} - {a}" for h, a in zip(played['home_goals'], played['away_goals'])],
        'Away': played['away'].values,
    })

SOURCE_NOTE = ("Scorelines are reconstructed from the recorded goal events, so a "
               "match whose goals are missing from the source data shows as 0-0.")

# Helper function to count matches for a team across all dataframes
def count_team_matches(team):
    """Count unique games involving a team across all dataframes"""
    games_in_goals = set(goalsDF[goalsDF['team'] == team]['game'].dropna().str.upper().unique())
    games_in_cautions = set(cautionsDF[cautionsDF['team'] == team]['game'].dropna().str.upper().unique())
    games_in_subs = set(subsDF[subsDF['team'] == team]['game'].dropna().str.upper().unique())
    all_games = games_in_goals | games_in_cautions | games_in_subs
    return len(all_games)

# Helper function to count matches in a matchday
def count_matchday_games(md):
    """Count unique games in a matchday"""
    games_in_goals = set(goalsDF[goalsDF['md'] == md]['game'].dropna().str.upper().unique())
    games_in_cautions = set(cautionsDF[cautionsDF['md'] == md]['game'].dropna().str.upper().unique())
    games_in_subs = set(subsDF[subsDF['md'] == md]['game'].dropna().str.upper().unique())
    all_games = games_in_goals | games_in_cautions | games_in_subs
    return len(all_games)

# Header
with ui.div(class_="headercontainer"):
    # with ui.div(class_="logocontainer"):
    #     ui.img(src="https://lh3.googleusercontent.com/pw/AP1GczO8jLa3k1wKyHVCS02hp3FRiHo", alt="UPL Logo")
    with ui.div(class_="titlecontainer"):
        ui.h2("#UPL Midseason Statistics Dashboard 2025/26")

# Main navigation
# ui.page_opts(
#     title="#UPL Midseason Stats",
#     fillable=True,
# )

# Add favicon
ui.tags.head(
    ui.tags.link(
        rel="icon",
        type="image/png",
        href="https://lh3.googleusercontent.com/pw/AP1GczO8jLa3k1wKyHVCS02hp3FRiHo"
    )
)

with ui.navset_bar(title="#UPL Midseason Stats", id="page", position="fixed-bottom"):
    
    # =============================================================================
    # PAGE 1: HALF-SEASON OVERVIEW
    # =============================================================================
    with ui.nav_panel("Half-season Overview"):
        with ui.navset_pill(id="overview_tab"):
            
            with ui.nav_panel("Summary"):
                # Key metrics row
                with ui.layout_columns(col_widths=[3, 3, 3, 3], style="margin: 20px 0;"):
                    with ui.div(class_="stat-card goals"):
                        ui.h3(str(len(goalsDF)))
                        ui.p("Total Goals")
                    with ui.div(class_="stat-card cards"):
                        ui.h3(str(len(cautionsDF[cautionsDF['caution'] == 'yellow'])))
                        ui.p("Yellow Cards")
                    with ui.div(class_="stat-card subs"):
                        ui.h3(str(len(subsDF)))
                        ui.p("Substitutions")
                    with ui.div(class_="stat-card matches"):
                        ui.h3(str(len(all_matchdays)))
                        ui.p("Matchdays")

                # Charts row 1
                with ui.layout_columns(col_widths=[6, 6], style="margin: 20px 0;"):
                    with ui.card():
                        ui.tags.div("Goals per Team", class_="overview-card-header")
                        @render_plotly
                        def goals_by_team():
                            team_goals = goalsDF.groupby('team').size().reset_index(name='goals')
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
                            card_counts = cautionsDF.groupby('caution_display').size().reset_index(name='count')
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
                        def goals_by_matchday():
                            md_goals = goalsDF.groupby('md').size().reset_index(name='goals')
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
                        def goals_by_period():
                            period_goals = goalsDF.groupby('period').size().reset_index(name='goals')
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
                        @render.table
                        def top_scorers():
                            scorer_goals = goalsDF.groupby(['player', 'team']).size().reset_index(name='goals')
                            scorer_goals = scorer_goals.sort_values('goals', ascending=False).head(15)
                            scorer_goals.columns = ['Player', 'Team', 'Goals']
                            return scorer_goals

            with ui.nav_panel("Detailed Analysis"):
                with ui.layout_columns(col_widths=[6, 6], style="margin: 20px 0;"):
                    with ui.card():
                        ui.tags.div("Cards per Team", class_="overview-card-header")
                        @render_plotly
                        def cards_by_team():
                            team_cards = cautionsDF.groupby('team').size().reset_index(name='cards')
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
                        def goals_timing_profile():
                            # Standard football time buckets. Stoppage time gets its
                            # own bucket at the end of each half instead of being
                            # folded into the minutes that follow it.
                            counts = bucket_counts(goalsDF)
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
                        def subs_timing():
                            fig = px.histogram(
                                subsDF, 
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
                        def goals_vs_cards():
                            team_stats = pd.DataFrame({
                                'team': all_teams
                            })
                            team_goals = goalsDF.groupby('team').size().reset_index(name='goals')
                            team_cards = cautionsDF.groupby('team').size().reset_index(name='cards')
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
                    "a winning position are the three it did not. " + SOURCE_NOTE,
                    style="margin: 20px 10px 0 10px; color: #555;"
                )

                with ui.layout_columns(col_widths=[6, 6], style="margin: 20px 0;"):
                    with ui.card():
                        ui.tags.div("Points Won From a Losing Position",
                                    class_="overview-card-header")
                        @render_plotly
                        def points_from_losing():
                            data = comebacksDF.sort_values('points_from_losing')
                            fig = px.bar(
                                data, x='points_from_losing', y='team', orientation='h',
                                color='team', color_discrete_map=TEAM_COLORS,
                                text='points_from_losing',
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
                        def points_dropped_from_winning():
                            data = comebacksDF.sort_values('points_dropped_from_winning')
                            fig = px.bar(
                                data, x='points_dropped_from_winning', y='team',
                                orientation='h',
                                color='team', color_discrete_map=TEAM_COLORS,
                                text='points_dropped_from_winning',
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
                        def wins_from_losing():
                            data = comebacksDF.sort_values('wins_from_losing')
                            fig = px.bar(
                                data, x='wins_from_losing', y='team', orientation='h',
                                color='team', color_discrete_map=TEAM_COLORS,
                                text='wins_from_losing',
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
                        def losses_from_winning():
                            data = comebacksDF.sort_values('losses_from_winning')
                            fig = px.bar(
                                data, x='losses_from_winning', y='team', orientation='h',
                                color='team', color_discrete_map=TEAM_COLORS,
                                text='losses_from_winning',
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
                        @render.table
                        def comebacks_summary():
                            table = comebacksDF.copy()
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
                            return table

    # =============================================================================
    # PAGE 2: MATCHDAY ANALYSIS
    # =============================================================================
    with ui.nav_panel("Matchday Analysis"):
        with ui.layout_sidebar():
            with ui.sidebar():
                ui.h5("Filter by Matchday")
                ui.input_select(
                    "selected_matchday", 
                    "Select Matchday:",
                    choices={str(md): f"Matchday {md}" for md in all_matchdays},
                    selected=str(all_matchdays[0]) if all_matchdays else None
                )
                ui.hr()
                ui.h5("Matchday Statistics")
                @render.text
                def matchday_stats():
                    """Display summary statistics for selected matchday"""
                    md = float(input.selected_matchday())
                    md_goals = len(goalsDF[goalsDF['md'] == md])
                    md_cards = len(cautionsDF[cautionsDF['md'] == md])
                    md_subs = len(subsDF[subsDF['md'] == md])
                    md_matches = count_matchday_games(int(md))
                    return f"Goals: {md_goals} | Cards: {md_cards} | Subs: {md_subs} | Matches: {md_matches}"
            
            with ui.navset_pill(id="matchday_tab"):
                
                with ui.nav_panel("Overview"):
                    with ui.layout_columns(col_widths=[3, 3, 3, 3], style="margin: 20px 0;"):
                        with ui.div(class_="stat-card goals"):
                            @render.text
                            def md_goals_count():
                                md_goals = len(goalsDF[goalsDF['md'] == float(input.selected_matchday())])
                                return str(md_goals)
                            ui.p("Goals")
                        with ui.div(class_="stat-card cards"):
                            @render.text
                            def md_cards_count():
                                md_cards = len(cautionsDF[cautionsDF['md'] == float(input.selected_matchday())])
                                return str(md_cards)
                            ui.p("Cards")
                        with ui.div(class_="stat-card subs"):
                            @render.text
                            def md_subs_count():
                                md_subs = len(subsDF[subsDF['md'] == float(input.selected_matchday())])
                                return str(md_subs)
                            ui.p("Substitutions")
                        with ui.div(class_="stat-card matches"):
                            @render.text
                            def md_matches_count():
                                return str(count_matchday_games(int(input.selected_matchday())))
                            ui.p("Matches")

                    with ui.layout_columns(col_widths=[6, 6], style="margin: 20px 0;"):
                        with ui.card():
                            ui.tags.div("Goals Distribution by Minute", class_="overview-card-header")
                            @render_plotly
                            def md_goals_timeline():
                                md_data = goalsDF[goalsDF['md'] == float(input.selected_matchday())]
                                fig = px.scatter(
                                    md_data,
                                    x='minute',
                                    y='game',
                                    size='minute',
                                    hover_data=['player', 'team'],
                                    color='period',
                                    color_discrete_map={1: '#3498db', 2: '#e74c3c'},
                                    title=f'Goal Scorers Timeline - Matchday {input.selected_matchday()}'
                                )
                                fig.update_layout(
                                    plot_bgcolor='rgba(0,0,0,0)',
                                    paper_bgcolor='rgba(0,0,0,0)'
                                )
                                return fig
                        
                        with ui.card():
                            ui.tags.div("Cards by Type", class_="overview-card-header")
                            @render_plotly
                            def md_cards_pie():
                                md_cards = cautionsDF[cautionsDF['md'] == float(input.selected_matchday())]
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
                            @render.table
                            def md_scorers_table():
                                md_data = goalsDF[goalsDF['md'] == float(input.selected_matchday())][['game', 'player', 'team', 'minute', 'period']]
                                md_data = md_data.sort_values('minute')
                                md_data.columns = ['Match', 'Player', 'Team', 'Minute', 'Half']
                                return md_data

                with ui.nav_panel("Table & Results"):
                    with ui.layout_columns(col_widths=[12], style="margin: 20px 0;"):
                        with ui.card():
                            @render.ui
                            def md_results_header():
                                return ui.tags.div(
                                    f"Results - Matchday {input.selected_matchday()}",
                                    class_="overview-card-header")

                            @render.table
                            def md_results_table():
                                return results_table(int(input.selected_matchday()))

                            ui.tags.p(SOURCE_NOTE,
                                      style="margin: 10px 15px; color: #777; font-size: 13px;")

                    with ui.layout_columns(col_widths=[12], style="margin: 20px 0;"):
                        with ui.card():
                            @render.ui
                            def md_standings_header():
                                return ui.tags.div(
                                    f"League Table after Matchday {input.selected_matchday()}",
                                    class_="overview-card-header")

                            @render.table
                            def md_standings_table():
                                return league_table(upto_md=int(input.selected_matchday()))

                    with ui.layout_columns(col_widths=[12], style="margin: 20px 0;"):
                        with ui.card():
                            @render.ui
                            def md_only_standings_header():
                                return ui.tags.div(
                                    f"Matchday {input.selected_matchday()} Only",
                                    class_="overview-card-header")

                            @render.table
                            def md_only_standings_table():
                                return league_table(md=int(input.selected_matchday()),
                                                    form_games=1)

                with ui.nav_panel("Cards"):
                    with ui.card():
                        @render.ui
                        def md_cards_header():
                            return ui.tags.div(f"Cards Detail - Matchday {input.selected_matchday()}", class_="overview-card-header")
                        
                        @render.table
                        def md_cards_table():
                            md_cards = cautionsDF[cautionsDF['md'] == float(input.selected_matchday())][['game', 'player', 'team', 'caution', 'minute', 'double-caution']]
                            md_cards.columns = ['Match', 'Player', 'Team', 'Card Type', 'Minute', 'Double Caution']
                            return md_cards

                with ui.nav_panel("Substitutions"):
                    with ui.card():
                        @render.ui
                        def md_subs_header():
                            return ui.tags.div(f"Substitutions Detail - Matchday {input.selected_matchday()}", class_="overview-card-header")
                        
                        @render.table
                        def md_subs_table():
                            md_subs = subsDF[subsDF['md'] == float(input.selected_matchday())][['game', 'in', 'out', 'team', 'minute']]
                            md_subs.columns = ['Match', 'Player In', 'Player Out', 'Team', 'Minute']
                            return md_subs

    # =============================================================================
    # PAGE 3: HOME & AWAY FORM
    # =============================================================================
    with ui.nav_panel("Home & Away"):
        with ui.navset_pill(id="venue_tab"):

            with ui.nav_panel("Home Advantage"):
                with ui.layout_columns(col_widths=[3, 3, 3, 3], style="margin: 20px 0;"):
                    with ui.div(class_="stat-card goals"):
                        ui.h3(str(int(teamMatchesDF[teamMatchesDF['venue'] == 'home']['gf'].sum())))
                        ui.p("Home Goals")
                    with ui.div(class_="stat-card goals"):
                        ui.h3(str(int(teamMatchesDF[teamMatchesDF['venue'] == 'away']['gf'].sum())))
                        ui.p("Away Goals")
                    with ui.div(class_="stat-card matches"):
                        ui.h3(str(int((teamMatchesDF[teamMatchesDF['venue'] == 'home']['result'] == 'W').sum())))
                        ui.p("Home Wins")
                    with ui.div(class_="stat-card matches"):
                        ui.h3(str(int((teamMatchesDF[teamMatchesDF['venue'] == 'away']['result'] == 'W').sum())))
                        ui.p("Away Wins")

                with ui.layout_columns(col_widths=[6, 6], style="margin: 20px 0;"):
                    with ui.card():
                        ui.tags.div("Where the Results Go", class_="overview-card-header")
                        @render_plotly
                        def venue_outcomes():
                            home = teamMatchesDF[teamMatchesDF['venue'] == 'home']
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
                        def venue_totals():
                            data = pd.DataFrame({
                                'measure': ['Goals', 'Goals', 'Cards', 'Cards',
                                            'Substitutions', 'Substitutions'],
                                'venue': ['Home', 'Away'] * 3,
                                'count': [
                                    int((goalsDF['venue'] == 'home').sum()),
                                    int((goalsDF['venue'] == 'away').sum()),
                                    int((cautionsDF['venue'] == 'home').sum()),
                                    int((cautionsDF['venue'] == 'away').sum()),
                                    int((subsDF['venue'] == 'home').sum()),
                                    int((subsDF['venue'] == 'away').sum()),
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
                        def venue_points_by_team():
                            points = (teamMatchesDF.groupby(['team', 'venue'])['points']
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
                    @render.table
                    def home_form_table():
                        return league_table(venue='home')

                    ui.tags.p("Home matches only. Form shows the last five home results, "
                              "oldest first. " + SOURCE_NOTE,
                              style="margin: 10px 15px; color: #777; font-size: 13px;")

                with ui.card():
                    ui.tags.div("Goals Scored at Home", class_="overview-card-header")
                    @render_plotly
                    def home_goals_by_team():
                        data = (teamMatchesDF[teamMatchesDF['venue'] == 'home']
                                .groupby('team')['gf'].sum().reset_index()
                                .sort_values('gf'))
                        fig = px.bar(
                            data, x='gf', y='team', orientation='h',
                            color='team', color_discrete_map=TEAM_COLORS, text='gf',
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
                    @render.table
                    def away_form_table():
                        return league_table(venue='away')

                    ui.tags.p("Away matches only. Form shows the last five away results, "
                              "oldest first. " + SOURCE_NOTE,
                              style="margin: 10px 15px; color: #777; font-size: 13px;")

                with ui.card():
                    ui.tags.div("Goals Scored Away", class_="overview-card-header")
                    @render_plotly
                    def away_goals_by_team():
                        data = (teamMatchesDF[teamMatchesDF['venue'] == 'away']
                                .groupby('team')['gf'].sum().reset_index()
                                .sort_values('gf'))
                        fig = px.bar(
                            data, x='gf', y='team', orientation='h',
                            color='team', color_discrete_map=TEAM_COLORS, text='gf',
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
                ui.input_select(
                    "selected_team",
                    "Team:",
                    choices={team: team for team in sorted(all_teams)},
                    selected=all_teams[0] if all_teams else None
                )
                ui.hr()
                ui.h5("Team Summary")
                @render.text
                def team_summary():
                    """Display summary statistics for selected team"""
                    team = input.selected_team()
                    team_goals = len(goalsDF[goalsDF['team'] == team])
                    team_cards = len(cautionsDF[cautionsDF['team'] == team])
                    team_subs = len(subsDF[subsDF['team'] == team])
                    team_matches = count_team_matches(team)
                    return f"Goals: {team_goals} | Cards: {team_cards} | Subs: {team_subs} | Matches: {team_matches}"
            
            with ui.navset_pill(id="team_tab"):
                
                with ui.nav_panel("Performance"):
                    with ui.layout_columns(col_widths=[3, 3, 3, 3], style="margin: 20px 0;"):
                        with ui.div(class_="stat-card goals"):
                            @render.text
                            def team_goals_scored():
                                team_goals = len(goalsDF[goalsDF['team'] == input.selected_team()])
                                return str(team_goals)
                            ui.p("Goals Scored")
                        with ui.div(class_="stat-card cards"):
                            @render.text
                            def team_cards_received():
                                team_cards = len(cautionsDF[cautionsDF['team'] == input.selected_team()])
                                return str(team_cards)
                            ui.p("Cards Received")
                        with ui.div(class_="stat-card subs"):
                            @render.text
                            def team_subs_made():
                                team_subs = len(subsDF[subsDF['team'] == input.selected_team()])
                                return str(team_subs)
                            ui.p("Subs Made")
                        with ui.div(class_="stat-card matches"):
                            @render.text
                            def team_matches_played():
                                return str(count_team_matches(input.selected_team()))
                            ui.p("Matches Played")

                    with ui.layout_columns(col_widths=[6, 6], style="margin: 20px 0;"):
                        with ui.card():
                            @render.ui
                            def team_goals_period_header():
                                return ui.tags.div("Goals by Period", style=get_team_header_style(input.selected_team()))
                            
                            @render_plotly
                            def team_goals_by_period():
                                team_data = goalsDF[goalsDF['team'] == input.selected_team()]
                                period_goals = team_data.groupby('period').size().reset_index(name='goals')
                                period_goals['period'] = period_goals['period'].map({1: 'First Half', 2: 'Second Half'})
                                colors = ['#3498db', '#e74c3c']
                                fig = px.bar(
                                    period_goals,
                                    x='period',
                                    y='goals',
                                    color='period',
                                    color_discrete_sequence=colors,
                                    title=f'Goals by Match Period - {input.selected_team()}'
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
                                return ui.tags.div("Goal Timing Distribution", style=get_team_header_style(input.selected_team()))
                            
                            @render_plotly
                            def team_goals_timeline():
                                team_data = goalsDF[goalsDF['team'] == input.selected_team()]
                                fig = px.histogram(
                                    team_data,
                                    x='minute',
                                    nbins=10,
                                    title=f'Goals by Minute - {input.selected_team()}',
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
                                return ui.tags.div(f"Top Scorers - {input.selected_team()}", style=get_team_header_style(input.selected_team()))
                            
                            @render.table
                            def team_top_scorers():
                                team_data = goalsDF[goalsDF['team'] == input.selected_team()]
                                scorers = team_data.groupby('player').size().reset_index(name='goals')
                                scorers = scorers.sort_values('goals', ascending=False)
                                scorers.columns = ['Player', 'Goals']
                                return scorers

                with ui.nav_panel("Discipline"):
                    with ui.layout_columns(col_widths=[6, 6], style="margin: 20px 0;"):
                        with ui.card():
                            @render.ui
                            def team_cards_breakdown_header():
                                return ui.tags.div("Cards Breakdown", style=get_team_header_style(input.selected_team()))
                            
                            @render_plotly
                            def team_cards_breakdown():
                                team_cards = cautionsDF[cautionsDF['team'] == input.selected_team()]
                                card_counts = team_cards['caution_display'].value_counts().reset_index()
                                card_counts.columns = ['type', 'count']
                                fig = px.pie(
                                    card_counts,
                                    values='count',
                                    names='type',
                                    color='type',
                                    color_discrete_map=CAUTION_COLORS,
                                    title=f'Cards Breakdown - {input.selected_team()}',
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
                                return ui.tags.div("Cards by Matchday", style=get_team_header_style(input.selected_team()))
                            
                            @render_plotly
                            def team_cards_by_matchday():
                                team_cards = cautionsDF[cautionsDF['team'] == input.selected_team()]
                                md_cards = team_cards.groupby('md').size().reset_index(name='cards')
                                fig = px.bar(
                                    md_cards,
                                    x='md',
                                    y='cards',
                                    title=f'Cards per Matchday - {input.selected_team()}',
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
                            return ui.tags.div(f"All Cards Received - {input.selected_team()}", style=get_team_header_style(input.selected_team()))
                        
                        @render.table
                        def team_cards_table():
                            team_cards = cautionsDF[cautionsDF['team'] == input.selected_team()][['game', 'player', 'caution', 'minute', 'double-caution']]
                            team_cards.columns = ['Match', 'Player', 'Card Type', 'Minute', 'Double Caution']
                            return team_cards

                with ui.nav_panel("Substitutions"):
                    with ui.layout_columns(col_widths=[6, 6], style="margin: 20px 0;"):
                        with ui.card():
                            @render.ui
                            def team_subs_timing_header():
                                return ui.tags.div("Substitution Timing", style=get_team_header_style(input.selected_team()))
                            
                            @render_plotly
                            def team_subs_timing():
                                team_subs = subsDF[subsDF['team'] == input.selected_team()]
                                team_color = TEAM_COLORS.get(input.selected_team(), '#3498db')
                                fig = px.histogram(
                                    team_subs,
                                    x='minute',
                                    nbins=10,
                                    title=f'Substitutions by Minute - {input.selected_team()}',
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
                                return ui.tags.div("Players Substituted On & Off", style=get_team_header_style(input.selected_team()))
                            
                            with ui.layout_column_wrap(width=1/2):
                                @render_plotly
                                def team_players_subbed_off():
                                    team_subs = subsDF[subsDF['team'] == input.selected_team()]
                                    player_subs = team_subs['out'].value_counts().reset_index()
                                    player_subs.columns = ['Player', 'Substitutions']
                                    team_color = TEAM_COLORS.get(input.selected_team(), '#3498db')
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
                                def team_players_subbed_on():
                                    team_subs = subsDF[subsDF['team'] == input.selected_team()]
                                    player_subs = team_subs['in'].value_counts().reset_index()
                                    player_subs.columns = ['Player', 'Substitutions']
                                    team_color = TEAM_COLORS.get(input.selected_team(), '#3498db')
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
                            return ui.tags.div(f"All Substitutions - {input.selected_team()}", style=get_team_header_style(input.selected_team()))
                        
                        @render.table
                        def team_subs_table():
                            team_subs = subsDF[subsDF['team'] == input.selected_team()][['game', 'in', 'out', 'minute']]
                            team_subs.columns = ['Match', 'Player In', 'Player Out', 'Minute']
                            return team_subs

