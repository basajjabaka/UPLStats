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

# Convert all team names to UPPERCASE
goalsDF['team'] = goalsDF['team'].str.upper()
cautionsDF['team'] = cautionsDF['team'].str.upper()
subsDF['team'] = subsDF['team'].str.upper()

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
    "LUGAZI": "#90EE90"       # Light Green
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
    if row['caution'] == 'yellow' and str(row['double-caution']).lower() in ['yes', 'y', 'true']:
        return 'second_yellow'
    return row['caution']

cautionsDF['caution_display'] = cautionsDF.apply(get_caution_color, axis=1)

# Caution color mapping
CAUTION_COLORS = {
    'yellow': '#FFD700',
    'red': '#FF0000',
    'second_yellow': '#FF8C00'  # Orange for second yellow
}

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
                        ui.tags.div("Goals Heatmap by Minute", class_="overview-card-header")
                        @render_plotly
                        def goals_heatmap():
                            # Create minute bins
                            goalsDF['minute_bin'] = pd.cut(
                                goalsDF['minute'], 
                                bins=[0, 15, 30, 45, 60, 75, 90, 100],
                                labels=['0-15', '16-30', '31-45', '46-60', '61-75', '76-90', '90+']
                            )
                            minute_period = goalsDF.groupby(['minute_bin', 'period']).size().reset_index(name='count')
                            minute_period['period'] = minute_period['period'].map({1: 'First Half', 2: 'Second Half'})
                            fig = px.density_heatmap(
                                minute_period, 
                                x='minute_bin', 
                                y='period', 
                                z='count',
                                color_continuous_scale='Viridis',
                                title='Goal Scoring Intensity by Time Period'
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
    # PAGE 3: TEAM STATISTICS
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

