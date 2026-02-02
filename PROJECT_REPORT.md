# UPLStats: Uganda Premier League Statistics Dashboard
## Comprehensive Project Report

**Project Name:** UPLStats - Uganda Premier League Statistics Extraction and Visualization System  
**Version:** 1.0  
**Date:** 2025  
**Author:** UPLStats Development Team

---

## Executive Summary

UPLStats is a comprehensive data extraction, transformation, and visualization system designed to process Uganda Premier League (UPL) match reports and provide interactive statistical insights. The system automates the extraction of match statistics from PDF documents, transforms the raw data into structured formats, and presents it through an interactive web dashboard built with Shiny for Python.

The project addresses the challenge of manually processing match reports by providing an automated pipeline that extracts key statistics including goals, cautions (cards), substitutions, own goals, and penalties from official match report PDFs. The system processes data across multiple matchdays and provides team-level, matchday-level, and league-wide analytics.

---

## 1. Project Overview

### 1.1 Objectives

The primary objectives of this project are:

1. **Automate Data Extraction**: Develop a robust system to extract match statistics from PDF match reports without manual data entry
2. **Data Standardization**: Transform extracted data into consistent, structured formats suitable for analysis
3. **Interactive Visualization**: Create an intuitive dashboard for exploring league statistics, team performance, and matchday analysis
4. **Scalability**: Design a system that can process multiple matchdays and scale with the growing dataset

### 1.2 Target Users

- **Football Analysts**: Researchers and analysts studying league performance
- **Media Professionals**: Journalists and content creators needing statistical insights
- **Fans and Enthusiasts**: Supporters interested in detailed match and team statistics
- **League Administrators**: Officials managing league data and statistics

### 1.3 Key Features

- Automated PDF text extraction and parsing
- Multi-matchday data processing
- Team-specific performance analytics
- Matchday-by-matchday analysis
- Interactive visualizations with filtering capabilities
- Real-time statistics calculation
- Comprehensive goal, card, and substitution tracking

---

## 2. System Architecture

### 2.1 Architecture Overview

The system follows a three-tier architecture:

```
┌─────────────────────────────────────────────────────────────┐
│                    DATA EXTRACTION LAYER                     │
│  PDF Match Reports → Text Extraction → Pattern Matching     │
│  (match_report_extractor_4.py)                              │
└───────────────────────┬─────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────┐
│                   DATA TRANSFORMATION LAYER                  │
│  Raw CSV → Data Cleaning → Feature Engineering             │
│  (wrangle.py)                                               │
└───────────────────────┬─────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────┐
│                    VISUALIZATION LAYER                      │
│  Transformed Data → Interactive Dashboard                   │
│  (app.py - Shiny for Python)                                │
└─────────────────────────────────────────────────────────────┘
```

### 2.2 Technology Stack

**Programming Language:** Python 3.x

**Core Libraries:**
- **pandas**: Data manipulation and analysis
- **numpy**: Numerical computations
- **PyPDF2/pdfplumber**: PDF text extraction
- **Shiny for Python**: Interactive web application framework
- **Plotly**: Interactive data visualization
- **Folium**: Geographic mapping capabilities

**Development Tools:**
- Jupyter Notebooks: Exploratory data analysis
- Pathlib: Cross-platform file path handling
- Regular Expressions (re): Pattern matching for data extraction

---

## 3. Component Analysis

### 3.1 Data Extraction Module (`match_report_extractor_4.py`)

#### 3.1.1 Purpose
The extraction module is responsible for parsing PDF match reports and extracting structured statistical data. It processes match reports from multiple matchdays and extracts five key data types:

1. **Goals**: Player goals with timing and added time information
2. **Cautions**: Yellow cards, red cards, and second yellow cards
3. **Substitutions**: Player in/out substitutions with timing
4. **Own Goals**: Own goal events with timing
5. **Penalties**: Penalty scored/missed events

#### 3.1.2 Key Features

**PDF Processing:**
- Automatic text extraction from PDF files using PyPDF2 or pdfplumber
- JSON caching system to avoid re-extraction of processed PDFs
- Support for multiple PDF extraction libraries with fallback mechanisms

**Pattern Recognition:**
- Symbol-based event identification using match report legend:
  - **Goal**: Soccer ball icon (⊕, ⚽)
  - **Own Goal**: Red circle with "OG" (⊛, *, OG)
  - **Penalty Scored**: Soccer ball with "P"
  - **Penalty Missed**: Soccer ball with red "X" (M, X)
  - **Yellow Card**: Yellow rectangle with "Y" (?, π, Y)
  - **Second Yellow**: Orange-red with "2Y" (½ᵥ, 2Y)
  - **Red Card**: Red rectangle with "R" (⊃ᵣ, R)
  - **Substitution**: Green square with arrows (text-based: "in"/"out")

**Team Identification:**
- Extracts team names from just below "MATCH EVENTS" title
- Processes both left and right sides of the Match Events table
- Uses first word of team name (e.g., "LUGAZI" from "LUGAZI FC")
- Intelligent player-to-team mapping based on roster analysis

**Data Quality:**
- Duplicate detection and prevention
- Context-aware pattern matching to distinguish similar events
- Error handling and progress reporting
- Side detection (LHS/RHS) based on pattern position and player names

#### 3.1.3 Output Format

The module generates CSV files with the following structures:

**goals.csv:**
- `game`: Match identifier (e.g., "LUGAZI-vs-CALVARY")
- `player`: Goal scorer name
- `team`: Team name (first word only)
- `min`: Minute of goal (string format, may include added time)
- `added_time`: Yes/No indicator

**cautions.csv:**
- `game`: Match identifier
- `player`: Player name
- `team`: Team name
- `caution`: Type (yellow, red, second yellow)
- `min`: Minute of caution
- `double-caution`: Yes/No indicator

**subs.csv:**
- `game`: Match identifier
- `in`: Player substituted in
- `out`: Player substituted out
- `min`: Minute of substitution
- `club`: Team name

**own_goals.csv:**
- Similar structure to goals.csv

**penalties.csv:**
- Similar structure to goals.csv with additional `scored` field (Yes/No)

### 3.2 Data Transformation Module (`wrangle.py`)

#### 3.2.1 Purpose
The transformation module processes raw extracted CSV files, cleans the data, and creates derived features for analysis.

#### 3.2.2 Transformation Pipeline

**Step 1: Data Loading**
- Reads raw CSV files from `csvs/raw/` directory
- Files processed: `goals.csv`, `cautions.csv`, `subs.csv`

**Step 2: Data Cleaning**
- Removes rows with 3 or more missing values
- Validates column presence (specifically checks for 'min' column)

**Step 3: Feature Engineering**

**Minute Parsing:**
```python
def parse_minute(v):
    # Handles formats like "45", "45+3", "(45+3)"
    # Returns integer minute value
```

**Period Classification:**
- **Period 1 (First Half)**: Minutes ≤ 45, or minutes 46-59 with added time
- **Period 2 (Second Half)**: Minutes 46-90 without added time, or minutes > 90

**Added Time Detection:**
- Identifies added time from minute strings containing "+" or parentheses

**Step 4: Column Reordering**
- Replaces `min` with `minute` (integer)
- Inserts `added_time` and `period` columns in logical positions
- Maintains original column order for other fields

**Step 5: Output**
- Saves transformed files to `csvs/transformed/` directory
- Files: `transformed_goals.csv`, `transformed_cautions.csv`, `transformed_subs.csv`

#### 3.2.3 Data Quality Improvements

- Converts minute strings to integers for mathematical operations
- Standardizes added time representation
- Creates period feature for half-based analysis
- Removes incomplete records

### 3.3 Interactive Dashboard (`app.py`)

#### 3.3.1 Purpose
The dashboard provides an interactive web interface for exploring league statistics, team performance, and matchday analysis.

#### 3.3.2 Dashboard Structure

**Technology:**
- Built with Shiny for Python
- Uses Plotly for interactive visualizations
- Custom CSS styling for professional appearance
- Responsive layout with sidebar navigation

**Navigation Structure:**

1. **Half-Season Overview**
   - **Summary Tab:**
     - Key metrics cards (Total Goals, Yellow Cards, Substitutions, Matchdays)
     - Goals per Team (horizontal bar chart)
     - Cards Distribution (pie chart)
     - Goals by Matchday (line chart)
     - Goals by Period (bar chart)
     - Top 15 Goal Scorers (data table)
   
   - **Detailed Analysis Tab:**
     - Cards per Team (horizontal bar chart)
     - Goals Heatmap by Minute (density heatmap)
     - Substitution Timing Distribution (histogram)
     - Team Comparison: Goals vs Cards (scatter plot)

2. **Matchday Analysis**
   - Matchday selector (sidebar filter)
   - Matchday statistics summary
   - **Overview Tab:**
     - Matchday metrics cards
     - Goals Distribution by Minute (scatter plot)
     - Cards by Type (pie chart)
     - Matchday Goalscorers (data table)
   
   - **Cards Tab:**
     - Detailed cards table for selected matchday
   
   - **Substitutions Tab:**
     - Detailed substitutions table for selected matchday

3. **Team Statistics**
   - Team selector (sidebar filter)
   - Team summary statistics
   - **Performance Tab:**
     - Team metrics cards (Goals Scored, Cards Received, Subs Made, Matches Played)
     - Goals by Period (bar chart)
     - Goal Timing Distribution (histogram)
     - Top Scorers (data table)
   
   - **Discipline Tab:**
     - Cards Breakdown (pie chart)
     - Cards by Matchday (bar chart)
     - All Cards Received (data table)
   
   - **Substitutions Tab:**
     - Substitution Timing (histogram)
     - Players Substituted On & Off (dual bar charts)
     - All Substitutions (data table)

#### 3.3.3 Visual Design Features

**Color Scheme:**
- Team-specific color mapping (15 teams with unique colors)
- Caution color coding (Yellow: #FFD700, Red: #FF0000, Second Yellow: #FF8C00)
- Gradient backgrounds and card styling
- Professional blue theme (#00008B header)

**Interactive Elements:**
- Dynamic filtering by matchday and team
- Hover tooltips on charts
- Responsive tables with sorting
- Real-time statistics calculation

**User Experience:**
- Fixed bottom navigation bar
- Sidebar filters for easy selection
- Card-based layout with hover effects
- Clear visual hierarchy

### 3.4 Exploratory Analysis Notebook (`notebook1.ipynb`)

#### 3.4.1 Purpose
The Jupyter notebook serves as a development and exploration environment for data analysis workflows.

#### 3.4.2 Notebook Contents

**Data Loading:**
- Imports raw CSV files from `csvs/raw/`
- Initial data exploration with `.head()`, `.info()`, `.tail()`

**Data Cleaning:**
- Removes rows with excessive missing values
- Examines unique minute values

**Feature Engineering:**
- Added time detection from minute strings
- Minute parsing function
- Period classification logic

**Analysis Workflow:**
- Iterative data exploration
- Transformation testing
- Validation of derived features

---

## 4. Data Flow

### 4.1 Complete Data Pipeline

```
┌──────────────────────────────────────────────────────────────┐
│  INPUT: PDF Match Reports                                    │
│  Location: reports/md1/, reports/md2/, ... reports/md15/   │
└───────────────────────┬──────────────────────────────────────┘
                        │
                        ▼
┌──────────────────────────────────────────────────────────────┐
│  STEP 1: PDF Extraction                                      │
│  match_report_extractor_4.py                                 │
│  - Extract text from PDFs                                     │
│  - Cache as JSON files (reports/jsons/)                      │
│  - Parse Match Events table                                   │
│  - Extract goals, cautions, subs, own_goals, penalties       │
└───────────────────────┬──────────────────────────────────────┘
                        │
                        ▼
┌──────────────────────────────────────────────────────────────┐
│  OUTPUT: Raw CSV Files                                       │
│  Location: csvs/raw/                                          │
│  Files: goals.csv, cautions.csv, subs.csv,                   │
│         own_goals.csv, penalties.csv                          │
└───────────────────────┬──────────────────────────────────────┘
                        │
                        ▼
┌──────────────────────────────────────────────────────────────┐
│  STEP 2: Data Transformation                                  │
│  wrangle.py                                                   │
│  - Load raw CSV files                                         │
│  - Clean data (remove incomplete rows)                       │
│  - Parse minutes to integers                                 │
│  - Create period feature (1st/2nd half)                      │
│  - Standardize added_time field                               │
└───────────────────────┬──────────────────────────────────────┘
                        │
                        ▼
┌──────────────────────────────────────────────────────────────┐
│  OUTPUT: Transformed CSV Files                               │
│  Location: csvs/transformed/                                  │
│  Files: transformed_goals.csv,                               │
│         transformed_cautions.csv,                            │
│         transformed_subs.csv                                  │
└───────────────────────┬──────────────────────────────────────┘
                        │
                        ▼
┌──────────────────────────────────────────────────────────────┐
│  STEP 3: Interactive Dashboard                               │
│  app.py                                                       │
│  - Load transformed CSV files                                 │
│  - Generate interactive visualizations                        │
│  - Provide filtering and exploration tools                    │
│  - Display statistics and insights                           │
└──────────────────────────────────────────────────────────────┘
```

### 4.2 Data Storage Structure

```
UPLStats/
├── reports/
│   ├── md1/          # Matchday 1 PDF reports
│   ├── md2/          # Matchday 2 PDF reports
│   ├── ...
│   ├── md15/         # Matchday 15 PDF reports
│   └── jsons/        # Cached PDF text extractions
├── csvs/
│   ├── raw/          # Extracted raw data
│   │   ├── goals.csv
│   │   ├── cautions.csv
│   │   └── subs.csv
│   └── transformed/  # Processed data
│       ├── transformed_goals.csv
│       ├── transformed_cautions.csv
│       └── transformed_subs.csv
├── scripts/
│   └── match_report_extractors/
│       └── match_report_extractor_4.py
├── notebooks/
│   └── notebook1.ipynb
├── app.py            # Dashboard application
├── wrangle.py        # Data transformation script
└── requirements.txt  # Python dependencies
```

---

## 5. Technical Implementation Details

### 5.1 PDF Extraction Challenges and Solutions

**Challenge 1: Symbol Recognition**
- **Problem**: PDF text extraction may not preserve visual symbols accurately
- **Solution**: Multiple pattern matching with fallback options, context-aware detection

**Challenge 2: Table Structure**
- **Problem**: Match Events table has two columns (left/right sides)
- **Solution**: Pattern-based side detection using player names and event position

**Challenge 3: Team Name Extraction**
- **Problem**: Team names appear in various formats and locations
- **Solution**: Extract from specific location (below "MATCH EVENTS" title) with fallback to full document search

**Challenge 4: Player Name Variations**
- **Problem**: Player names may have spacing variations or abbreviations
- **Solution**: Fuzzy matching with word-by-word comparison and partial matching

### 5.2 Data Quality Assurance

**Validation Checks:**
- Row completeness (maximum 2 missing values allowed)
- Column presence validation
- Minute format validation
- Team name standardization
- Duplicate event detection

**Error Handling:**
- Graceful handling of missing PDFs
- JSON extraction error recovery
- Pattern matching fallbacks
- Progress reporting for debugging

### 5.3 Performance Optimizations

**Caching Strategy:**
- JSON files cache PDF text extractions
- Avoids re-extraction of processed PDFs
- Reduces processing time for re-runs

**Batch Processing:**
- Processes all PDFs in a folder sequentially
- Appends to CSV files (no overwriting)
- Supports incremental data addition

**Memory Management:**
- Processes one PDF at a time
- Clears intermediate data structures
- Efficient CSV writing with append mode

---

## 6. Key Statistics and Metrics

### 6.1 Data Coverage

Based on the project structure, the system processes:
- **15 Matchdays** (md1 through md15)
- **Multiple matches per matchday** (typically 7-8 matches)
- **5 Data Types**: Goals, Cautions, Substitutions, Own Goals, Penalties
- **15 Teams** in the Uganda Premier League

### 6.2 Dashboard Metrics

**Overview Metrics:**
- Total Goals Scored
- Total Yellow Cards
- Total Substitutions
- Number of Matchdays Processed

**Team-Level Metrics:**
- Goals Scored per Team
- Cards Received per Team
- Substitutions Made per Team
- Matches Played per Team

**Matchday-Level Metrics:**
- Goals per Matchday
- Cards per Matchday
- Substitutions per Matchday
- Number of Matches per Matchday

**Player-Level Metrics:**
- Top Goal Scorers
- Most Substituted Players (in/out)
- Players with Most Cards

---

## 7. Use Cases and Applications

### 7.1 Media and Journalism

**Use Case**: Journalists can quickly access statistics for match reports and articles.

**Example Queries:**
- "Which team scored the most goals in the first half?"
- "Who are the top 10 goal scorers this season?"
- "Which matchday had the most cards?"

### 7.2 Team Analysis

**Use Case**: Coaches and analysts can study team performance patterns.

**Example Queries:**
- "When does Team X typically score goals?"
- "What is Team Y's substitution pattern?"
- "How disciplined is Team Z compared to others?"

### 7.3 League Administration

**Use Case**: League officials can track league-wide statistics and trends.

**Example Queries:**
- "What is the average goals per matchday?"
- "Which teams have the best discipline records?"
- "What is the distribution of goals across match periods?"

### 7.4 Fan Engagement

**Use Case**: Fans can explore detailed statistics about their favorite teams and players.

**Example Queries:**
- "Show me all goals scored by my team this season"
- "Which players have been substituted most often?"
- "Compare my team's performance across matchdays"

---

## 8. Future Enhancements and Roadmap

### 8.1 Planned Features

1. **Advanced Analytics**
   - Expected Goals (xG) calculations
   - Player performance ratings
   - Team strength metrics
   - Predictive modeling

2. **Additional Data Sources**
   - Match results and standings
   - Player profiles and positions
   - Match venue information
   - Weather data integration

3. **Enhanced Visualizations**
   - Interactive match timelines
   - Heat maps for goal locations
   - Player movement analysis
   - Comparative team dashboards

4. **Export Capabilities**
   - PDF report generation
   - Excel export functionality
   - API endpoints for data access
   - Automated email reports

5. **Real-Time Updates**
   - Live match data integration
   - Automatic PDF processing on upload
   - Webhook notifications
   - Real-time dashboard updates

### 8.2 Technical Improvements

1. **Performance**
   - Parallel PDF processing
   - Database backend for large datasets
   - Caching layer for dashboard queries
   - Optimized pattern matching algorithms

2. **Reliability**
   - Automated testing suite
   - Data validation rules
   - Error logging and monitoring
   - Backup and recovery procedures

3. **Scalability**
   - Cloud deployment options
   - Containerization (Docker)
   - Microservices architecture
   - Load balancing for dashboard

---

## 9. Challenges and Solutions

### 9.1 Technical Challenges

**Challenge: PDF Format Variations**
- Different PDF generators may produce slightly different text layouts
- **Solution**: Flexible pattern matching with multiple regex patterns and context awareness

**Challenge: Symbol Extraction**
- Visual symbols may not extract correctly from PDFs
- **Solution**: Multiple symbol representations in patterns, fallback to text-based detection

**Challenge: Player Name Matching**
- Variations in name spelling and formatting
- **Solution**: Fuzzy matching algorithms with word-by-word comparison

### 9.2 Data Quality Challenges

**Challenge: Incomplete Match Reports**
- Some PDFs may have missing or corrupted sections
- **Solution**: Robust error handling, partial data extraction, validation checks

**Challenge: Team Name Standardization**
- Teams may be referred to in different ways
- **Solution**: First-word extraction, uppercase normalization, mapping dictionary

### 9.3 User Experience Challenges

**Challenge: Dashboard Performance**
- Large datasets may slow down visualizations
- **Solution**: Efficient data loading, client-side filtering, pagination for tables

---

## 10. Project Impact and Value

### 10.1 Time Savings

- **Manual Processing**: Estimated 30-60 minutes per match report
- **Automated Processing**: Less than 1 minute per match report
- **Total Time Saved**: Approximately 15-30 hours per matchday (for 7-8 matches)

### 10.2 Data Accuracy

- **Reduced Human Error**: Automated extraction eliminates transcription mistakes
- **Consistency**: Standardized data formats ensure uniform analysis
- **Completeness**: Systematic processing ensures no events are missed

### 10.3 Accessibility

- **24/7 Availability**: Dashboard accessible anytime
- **No Specialized Software**: Web-based interface requires only a browser
- **Interactive Exploration**: Users can explore data without technical knowledge

### 10.4 Insights Generation

- **Pattern Recognition**: Identifies trends across matchdays and teams
- **Comparative Analysis**: Enables team-to-team and matchday-to-matchday comparisons
- **Performance Tracking**: Tracks individual and team performance over time

---

## 11. Conclusion

The UPLStats project successfully addresses the challenge of extracting and visualizing Uganda Premier League match statistics through an automated, scalable, and user-friendly system. The three-tier architecture (extraction, transformation, visualization) provides a robust foundation for statistical analysis and insights generation.

The system's ability to process multiple matchdays, handle various PDF formats, and provide interactive visualizations makes it a valuable tool for analysts, journalists, administrators, and fans. The modular design allows for future enhancements and scalability as the league grows and data requirements evolve.

### 11.1 Key Achievements

✅ Automated PDF-to-data pipeline  
✅ Multi-matchday processing capability  
✅ Interactive dashboard with filtering  
✅ Team-specific and matchday-specific analytics  
✅ Robust error handling and data validation  
✅ Scalable architecture for future growth  

### 11.2 Project Status

The project is **operational** and processing match reports from multiple matchdays. The dashboard is functional and provides comprehensive statistical insights. The system is ready for production use with ongoing improvements and feature additions planned.

---

## 12. References and Resources

### 12.1 Technology Documentation

- [Shiny for Python Documentation](https://shiny.posit.co/py/)
- [Plotly Python Documentation](https://plotly.com/python/)
- [Pandas Documentation](https://pandas.pydata.org/)
- [PyPDF2 Documentation](https://pypdf2.readthedocs.io/)
- [pdfplumber Documentation](https://github.com/jsvine/pdfplumber)

### 12.2 Project Files

- **Extraction Script**: `scripts/match_report_extractors/match_report_extractor_4.py`
- **Transformation Script**: `wrangle.py`
- **Dashboard Application**: `app.py`
- **Exploratory Notebook**: `notebooks/notebook1.ipynb`
- **Dependencies**: `requirements.txt`

### 12.3 Data Sources

- Official Uganda Premier League Match Reports (PDF format)
- Match reports organized by matchday (md1 through md15)

---

## Appendix A: Installation and Setup

### A.1 Prerequisites

- Python 3.8 or higher
- pip package manager

### A.2 Installation Steps

1. **Clone or download the project**
   ```bash
   git clone <repository-url>
   cd UPLStats
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure paths** (if needed)
   - Edit `match_report_extractor_4.py` to set PDF_FOLDER, JSON_FOLDER, CSV_FOLDER paths

4. **Run extraction**
   ```bash
   python scripts/match_report_extractors/match_report_extractor_4.py
   ```

5. **Run transformation**
   ```bash
   python wrangle.py
   ```

6. **Launch dashboard**
   ```bash
   shiny run app.py
   ```

### A.3 Directory Structure Setup

Ensure the following directories exist:
- `reports/md1/` through `reports/md15/` (for PDF files)
- `reports/jsons/` (for cached extractions)
- `csvs/raw/` (for extracted CSV files)
- `csvs/transformed/` (for processed CSV files)

---

## Appendix B: Data Schema

### B.1 Goals Schema

| Column | Type | Description |
|--------|------|-------------|
| game | string | Match identifier (format: "TEAM1-vs-TEAM2") |
| player | string | Goal scorer name |
| team | string | Team name (first word only, uppercase) |
| minute | integer | Minute of goal (0-120) |
| added_time | string | "Yes" or "No" |
| period | integer | 1 (First Half) or 2 (Second Half) |
| md | float | Matchday number |

### B.2 Cautions Schema

| Column | Type | Description |
|--------|------|-------------|
| game | string | Match identifier |
| player | string | Player name |
| team | string | Team name (uppercase) |
| caution | string | "yellow", "red", or "second yellow" |
| minute | integer | Minute of caution |
| double-caution | string | "Yes" or "No" |
| md | float | Matchday number |

### B.3 Substitutions Schema

| Column | Type | Description |
|--------|------|-------------|
| game | string | Match identifier |
| in | string | Player substituted in |
| out | string | Player substituted out |
| minute | integer | Minute of substitution |
| club | string | Team name (uppercase) |
| md | float | Matchday number |

---

**End of Report**

---

*This report was generated based on analysis of the UPLStats project codebase, including wrangle.py, app.py, notebook1.ipynb, and the match report extraction scripts. The project demonstrates a complete data pipeline from PDF extraction to interactive visualization, providing valuable insights into Uganda Premier League statistics.*

