"""
Match Report Data Extractor
Extracts game statistics from multiple StarTimes Uganda Premier League match report PDFs
and stores the data in CSV files (subs, cautions, goals, own_goals, penalties).

CONFIGURATION: Edit the paths below before running
================================================================================
"""

import re
import csv
import json
import os
import glob
from typing import List, Dict, Tuple, Set, Optional

try:
    import PyPDF2
    PDF_AVAILABLE = True
    USE_PDFPLUMBER = False
except ImportError:
    try:
        import pdfplumber
        PDF_AVAILABLE = True
        USE_PDFPLUMBER = True
    except ImportError:
        PDF_AVAILABLE = False
        USE_PDFPLUMBER = False


# =============================================================================
# CONFIGURATION - EDIT THESE PATHS
# =============================================================================
PDF_FOLDER = "D:\\cboobs\\UPLStats\\reports\\md1"      # Folder containing PDF match reports
JSON_FOLDER = "D:\\cboobs\\UPLStats\\reports\\jsons"    # Folder where JSON extractions are stored
CSV_FOLDER = "D:\\cboobs\\UPLStats\\reports\\csvs"      # Folder where final CSV files will be stored
# =============================================================================

# CSV column headers
SUBS_COLUMNS = ['game', 'in', 'out', 'min', 'club']
CAUTIONS_COLUMNS = ['game', 'player', 'team', 'caution', 'min', 'double-caution']
GOALS_COLUMNS = ['game', 'player', 'team', 'min', 'added_time']
OWN_GOALS_COLUMNS = ['game', 'player', 'team', 'min', 'added_time']
PENALTIES_COLUMNS = ['game', 'player', 'team', 'scored', 'min', 'added_time']


class MatchReportExtractor:
    """Extracts game statistics from match report PDF content."""
    
    def __init__(self, pdf_content: str, pdf_filename: str = "unknown"):
        """Initialize with extracted PDF content."""
        self.content = pdf_content
        self.pdf_filename = pdf_filename
        self.game = ""
        self.lhs_team = ""  # Left hand side team (Home)
        self.rhs_team = ""  # Right hand side team (Away)
        self.lhs_team_short = ""  # Short form (first word only)
        self.rhs_team_short = ""  # Short form (first word only)
        self.lhs_starting_players: Set[str] = set()
        self.rhs_starting_players: Set[str] = set()
        self.lhs_substitutes: Set[str] = set()
        self.rhs_substitutes: Set[str] = set()
        self.lhs_all_players: Set[str] = set()
        self.rhs_all_players: Set[str] = set()
        self.subs = []
        self.cautions = []
        self.goals = []
        self.own_goals = []
        self.penalties = []
    
    def _get_team_short(self, team: str) -> str:
        """Get short form of team name (first word only)."""
        return team.split()[0] if team else team
    
    def _clean_player_name(self, name: str) -> str:
        """Clean and normalize player name."""
        name = re.sub(r'\s+', ' ', name.strip())
        # Remove common suffixes/prefixes
        name = re.sub(r'\s*(GK|C|Format:.*)$', '', name).strip()
        return name
    
    def _is_likely_player_name(self, name: str) -> bool:
        """Check if a string is likely to be a player name."""
        if len(name) < 3 or len(name) > 30:
            return False
        
        # Skip common non-player words
        skip_words = {
            'GK', 'C', 'Captain', 'Period', 'Extra', 'Time', 'Start', 'End',
            'Substitutes', 'Player', 'Head', 'Coach', 'Assistant', 'Physiotherapist',
            'Team', 'Medic', 'Referee', 'Assistant', 'Fourth', 'Match', 'Commissioner',
            'Assessor', 'Attendance', 'Africa', 'Uganda', 'Period', 'Penalty', 'Shoot',
            'Out', 'Signatures', 'Kick', 'Outcome', 'NT', 'ST', 'XT', 'BM', 'BP',
            'AM', 'BET', 'HET', 'AET', 'PSO', 'Sunday', 'Monday', 'Tuesday',
            'Wednesday', 'Thursday', 'Friday', 'Saturday', 'January', 'February',
            'March', 'April', 'May', 'June', 'July', 'August', 'September',
            'October', 'November', 'December', 'Home', 'Away', 'HomeTeam',
            'AwayTeam', 'StarTimes', 'Premier', 'League', 'Report'
        }
        
        if name in skip_words:
            return False
        
        # Check if it looks like a real name (starts with capital, contains only letters and spaces)
        if not re.match(r'^[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*$', name):
            return False
        
        return True
    
    def _extract_players_from_section(self, section_text: str, is_substitute: bool = False) -> Set[str]:
        """Extract player names from a specific section of the PDF."""
        players = set()
        
        # Pattern 1: Player names with ID numbers in parentheses like "(042164M02)"
        id_pattern = r'\(([A-Z0-9]+)\)\s*([A-Za-z]+(?:\s+[A-Za-z]+)*)'
        for match in re.finditer(id_pattern, section_text):
            player_id = match.group(1)
            player_name = match.group(2)
            # Valid IDs have format like 6 digits + letter + 2 digits, or similar
            if re.match(r'^\d+[A-Z]\d+$', player_id) or re.match(r'^\d{6}$', player_id):
                if self._is_likely_player_name(player_name):
                    players.add(player_name)
        
        # Pattern 2: Names preceded by number markers like "23JumaMutebi" or "Player23"
        number_name_pattern = r'(?:^|[^A-Za-z])(\d{1,2})([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)'
        for match in re.finditer(number_name_pattern, section_text):
            number = match.group(1)
            player_name = match.group(2)
            # Player numbers are typically 1-99
            if 1 <= int(number) <= 99:
                if self._is_likely_player_name(player_name):
                    players.add(player_name)
        
        # Pattern 3: Look for names near "GK" (Goalkeeper) marker
        gk_pattern = r'([A-Za-z]+(?:\s+[A-Za-z]+)*)\s*GK'
        for match in re.finditer(gk_pattern, section_text):
            player_name = match.group(1)
            if self._is_likely_player_name(player_name):
                players.add(player_name)
        
        # Pattern 4: Names after "#Player" markers
        player_marker_pattern = r'#\s*Player\s*\d*\s*([A-Za-z]+(?:\s+[A-Za-z]+)*)'
        for match in re.finditer(player_marker_pattern, section_text):
            player_name = match.group(1)
            if self._is_likely_player_name(player_name):
                players.add(player_name)
        
        return players
    
    def _extract_teams_and_players(self) -> None:
        """Extract both teams and their players from the PDF content."""
        # Find team names
        team_pattern = r'([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\s*FC'
        teams_match = re.findall(team_pattern, self.content)
        
        if len(teams_match) >= 2:
            self.lhs_team = f"{teams_match[0]} FC"
            self.rhs_team = f"{teams_match[1]} FC"
            self.lhs_team_short = self._get_team_short(self.lhs_team)
            self.rhs_team_short = self._get_team_short(self.rhs_team)
            self.game = f"{self.lhs_team_short}-vs-{self.rhs_team_short}"
        else:
            # Fallback
            self.lhs_team = "HOME FC"
            self.rhs_team = "AWAY FC"
            self.lhs_team_short = "HOME"
            self.rhs_team_short = "AWAY"
            self.game = f"{self.lhs_team_short}-vs-{self.rhs_team_short}"
        
        # Find the MATCH EVENTS marker to separate lineups from events
        match_events_match = re.search(r'MATCH\s*EVENTS', self.content, re.IGNORECASE)
        
        if match_events_match:
            # Content before MATCH EVENTS contains starting lineups and substitutes
            lineup_content = self.content[:match_events_match.start()]
        else:
            lineup_content = self.content
        
        # Split content by team sections (using FC markers)
        fc_positions = [(m.start(), m.end()) for m in re.finditer(r'[A-Z][a-z]+\s*FC', self.content)]
        
        if len(fc_positions) >= 2:
            # First team section (before first FC)
            first_fc_start = fc_positions[0][0]
            second_fc_start = fc_positions[1][0]
            
            # Content between first FC and second FC is likely first team
            first_team_section = self.content[first_fc_start:second_fc_start]
            
            # Content after second FC to MATCH EVENTS is second team
            second_team_section = self.content[second_fc_start:]
            if match_events_match:
                second_team_section = second_team_section[:match_events_match.start() - second_fc_start]
            
            # Extract players from each team section
            self.lhs_all_players = self._extract_players_from_section(first_team_section)
            self.rhs_all_players = self._extract_players_from_section(second_team_section)
        else:
            # Fallback: try to extract players from entire content
            all_players = self._extract_players_from_section(self.content)
            self.lhs_all_players = all_players
            self.rhs_all_players = set()
    
    def extract_game_info(self) -> None:
        """Extract game name and teams from the Match Events title section."""
        self._extract_teams_and_players()
    
    def _parse_time(self, time_str: str) -> Tuple[str, str]:
        """Parse time string to extract minute and added time indicator."""
        time_str = time_str.strip()
        
        added_time_match = re.search(r"\+\d+'", time_str)
        if added_time_match:
            minute = re.sub(r"\(\+\d+'\)", "", time_str).strip().rstrip("'")
            return minute, "Yes"
        else:
            minute = time_str.strip().rstrip("'")
            return minute, "No"
    
    def _get_team(self, side: str, use_short: bool = True) -> str:
        """Get team name for a side."""
        if use_short:
            return self.lhs_team_short if side == "LHS" else self.rhs_team_short
        return self.lhs_team if side == "LHS" else self.rhs_team
    
    def _detect_side_from_content(self, text: str) -> str:
        """Detect which side (LHS or RHS) the text belongs to based on player names."""
        # Check for LHS (left side) players
        for player in self.lhs_all_players:
            if player in text:
                return "LHS"
        
        # Check for RHS (right side) players
        for player in self.rhs_all_players:
            if player in text:
                return "RHS"
        
        # Fallback: detect from pattern
        if re.match(r"\d+'", text.strip()):
            return "RHS"
        else:
            return "LHS"
    
    def extract_goals(self) -> None:
        """Extract goal data from Match Events Table."""
        match_events_match = re.search(r'MATCH\s*EVENTS\s*(.+?)(?:PENALTY\s*SHOOT-OUT|SIGNATURES)',
                                       self.content, re.IGNORECASE | re.DOTALL)
        
        if not match_events_match:
            return
        
        events_text = match_events_match.group(1)
        
        # Right side pattern: time'⊕ Player or time'? Player
        goal_pattern_right = r"(\d+)'\s*[⊕?*]\s*([A-Za-z]+)"
        
        # Left side pattern: Player ?time' (but distinguish from yellow cards)
        goal_pattern_left = r"([A-Za-z]+(?:\s+[A-Za-z]+)*)\s*\?(\d+)'(?:\(\+?\d+'?\))?"
        
        for match in re.finditer(goal_pattern_right, events_text, re.IGNORECASE):
            minute = match.group(1)
            player = match.group(2)
            full_match = match.group(0)
            
            if re.search(r"[A-Za-z]+\s+\?", full_match):
                continue
            
            side = self._detect_side_from_content(full_match)
            
            if side:
                _, added_time = self._parse_time(f"{minute}'")
                team = self._get_team(side)
                
                self.goals.append({
                    "game": self.game,
                    "player": player,
                    "team": team,
                    "min": minute,
                    "added_time": added_time
                })
        
        for match in re.finditer(goal_pattern_left, events_text, re.IGNORECASE):
            player = match.group(1).strip()
            minute = match.group(2)
            full_match = match.group(0)
            
            side = self._detect_side_from_content(player)
            
            if side and player in (self.lhs_all_players if side == "LHS" else self.rhs_all_players):
                _, added_time = self._parse_time(f"{minute}'")
                team = self._get_team(side)
                
                self.goals.append({
                    "game": self.game,
                    "player": player,
                    "team": team,
                    "min": minute,
                    "added_time": added_time
                })
    
    def extract_cautions(self) -> None:
        """Extract caution (yellow/red card) data from Match Events Table."""
        match_events_match = re.search(r'MATCH\s*EVENTS\s*(.+?)(?:PENALTY\s*SHOOT-OUT|SIGNATURES)',
                                       self.content, re.IGNORECASE | re.DOTALL)
        
        if not match_events_match:
            return
        
        events_text = match_events_match.group(1)
        
        yellow_pattern = r"([A-Za-z]+(?:\s+[A-Za-z]+)*)\s*\?(\d+)'(?:\(\+?\d+'?\))?"
        second_yellow_pattern = r"([A-Za-z]+(?:\s+[A-Za-z]+)*)\s*[½ᵥ]+(\d+)'(?:\(\+?\d+'?\))?"
        red_pattern = r"([A-Za-z]+(?:\s+[A-Za-z]+)*)\s*[⊃ᵣ]+(\d+)'(?:\(\+?\d+'?\))?"
        
        for match in re.finditer(yellow_pattern, events_text, re.IGNORECASE):
            player = match.group(1).strip()
            minute = match.group(2)
            full_match = match.group(0)
            
            side = self._detect_side_from_content(full_match)
            
            if side:
                team = self._get_team(side)
                
                self.cautions.append({
                    "game": self.game,
                    "player": player,
                    "team": team,
                    "caution": "yellow",
                    "min": minute,
                    "double-caution": "No"
                })
        
        for match in re.finditer(second_yellow_pattern, events_text, re.IGNORECASE):
            player = match.group(1).strip()
            minute = match.group(2)
            full_match = match.group(0)
            
            side = self._detect_side_from_content(full_match)
            
            if side:
                team = self._get_team(side)
                
                self.cautions.append({
                    "game": self.game,
                    "player": player,
                    "team": team,
                    "caution": "second yellow",
                    "min": minute,
                    "double-caution": "Yes"
                })
        
        for match in re.finditer(red_pattern, events_text, re.IGNORECASE):
            player = match.group(1).strip()
            minute = match.group(2)
            full_match = match.group(0)
            
            side = self._detect_side_from_content(full_match)
            
            if side:
                team = self._get_team(side)
                
                self.cautions.append({
                    "game": self.game,
                    "player": player,
                    "team": team,
                    "caution": "red",
                    "min": minute,
                    "double-caution": "No"
                })
    
    def extract_substitutions(self) -> None:
        """Extract substitution data from Match Events Table."""
        match_events_match = re.search(r'MATCH\s*EVENTS\s*(.+?)(?:PENALTY\s*SHOOT-OUT|SIGNATURES)',
                                       self.content, re.IGNORECASE | re.DOTALL)
        
        if not match_events_match:
            return
        
        events_text = match_events_match.group(1)
        
        substitution_pattern = r"(\d+)'\s*(?:\(\+?\d+'?\))?\s*in\s+([A-Za-z]+(?:\s+[A-Za-z]+)*),?\s*out\s+([A-Za-z]+(?:\s+[A-Za-z]+)*)"
        
        for match in re.finditer(substitution_pattern, events_text, re.IGNORECASE):
            minute = match.group(1)
            player_in = match.group(2).strip()
            player_out = match.group(3).strip()
            full_match = match.group(0)
            
            side = self._detect_side_from_content(full_match)
            
            if side:
                team = self._get_team(side)
                
                self.subs.append({
                    "game": self.game,
                    "in": player_in,
                    "out": player_out,
                    "min": minute,
                    "club": team
                })
    
    def extract_own_goals(self) -> None:
        """Extract own goal data from Match Events Table."""
        match_events_match = re.search(r'MATCH\s*EVENTS\s*(.+?)(?:PENALTY\s*SHOOT-OUT|SIGNATURES)',
                                       self.content, re.IGNORECASE | re.DOTALL)
        
        if not match_events_match:
            return
        
        events_text = match_events_match.group(1)
        
        own_goal_pattern = r"(\d+)'\s*[⊛*]\s*([A-Za-z]+)"
        
        for match in re.finditer(own_goal_pattern, events_text, re.IGNORECASE):
            minute = match.group(1)
            player = match.group(2)
            full_match = match.group(0)
            
            side = self._detect_side_from_content(full_match)
            
            if side:
                _, added_time = self._parse_time(f"{minute}'")
                team = self._get_team(side)
                
                self.own_goals.append({
                    "game": self.game,
                    "player": player,
                    "team": team,
                    "min": minute,
                    "added_time": added_time
                })
    
    def extract_penalties(self) -> None:
        """Extract penalty data from Match Events Table."""
        match_events_match = re.search(r'MATCH\s*EVENTS\s*(.+?)(?:PENALTY\s*SHOOT-OUT|SIGNATURES)',
                                       self.content, re.IGNORECASE | re.DOTALL)
        
        if not match_events_match:
            return
        
        events_text = match_events_match.group(1)
        
        penalty_scored_pattern = r"(\d+)'\s*[Pp]\s*([A-Za-z]+)"
        penalty_missed_pattern = r"(\d+)'\s*[Mm]\s*([A-Za-z]+)"
        
        for match in re.finditer(penalty_scored_pattern, events_text, re.IGNORECASE):
            minute = match.group(1)
            player = match.group(2)
            full_match = match.group(0)
            
            side = self._detect_side_from_content(full_match)
            
            if side:
                _, added_time = self._parse_time(f"{minute}'")
                team = self._get_team(side)
                
                self.penalties.append({
                    "game": self.game,
                    "player": player,
                    "team": team,
                    "scored": "Yes",
                    "min": minute,
                    "added_time": added_time
                })
        
        for match in re.finditer(penalty_missed_pattern, events_text, re.IGNORECASE):
            minute = match.group(1)
            player = match.group(2)
            full_match = match.group(0)
            
            side = self._detect_side_from_content(full_match)
            
            if side:
                _, added_time = self._parse_time(f"{minute}'")
                team = self._get_team(side)
                
                self.penalties.append({
                    "game": self.game,
                    "player": player,
                    "team": team,
                    "scored": "No",
                    "min": minute,
                    "added_time": added_time
                })
    
    def process(self) -> Tuple[List[Dict], List[Dict], List[Dict], List[Dict], List[Dict]]:
        """Process the match report and extract all data."""
        self.extract_game_info()
        self.extract_goals()
        self.extract_cautions()
        self.extract_substitutions()
        self.extract_own_goals()
        self.extract_penalties()
        
        return self.subs, self.cautions, self.goals, self.own_goals, self.penalties
    
    def print_extraction_report(self) -> None:
        """Print a detailed report of what was extracted from this PDF."""
        lhs_count = len(self.lhs_all_players)
        rhs_count = len(self.rhs_all_players)
        
        print(f"\n{'='*65}")
        print(f"EXTRACTION REPORT: {self.pdf_filename}")
        print(f"{'='*65}")
        
        print(f"\n📋 MATCH INFO:")
        print(f"   Game: {self.game}")
        print(f"   Home Team: {self.lhs_team} ({lhs_count} players)")
        print(f"   Away Team: {self.rhs_team} ({rhs_count} players)")
        
        print(f"\n⚽ GOALS ({len(self.goals)}):")
        if self.goals:
            for g in self.goals:
                print(f"   {g['min']}' - {g['player']} ({g['team']})")
        else:
            print("   None")
        
        print(f"\n🟨 CAUTIONS ({len(self.cautions)}):")
        if self.cautions:
            for c in self.cautions:
                print(f"   {c['min']}' - {c['player']} ({c['team']}) - {c['caution']}")
        else:
            print("   None")
        
        print(f"\n🔄 SUBSTITUTIONS ({len(self.subs)}):")
        if self.subs:
            for s in self.subs:
                print(f"   {s['min']}' - IN: {s['in']}, OUT: {s['out']} ({s['club']})")
        else:
            print("   None")
        
        print(f"\n🎯 OWN GOALS ({len(self.own_goals)}):")
        if self.own_goals:
            for og in self.own_goals:
                print(f"   {og['min']}' - {og['player']} ({og['team']})")
        else:
            print("   None")
        
        print(f"\n⚽ PENALTIES ({len(self.penalties)}):")
        if self.penalties:
            for p in self.penalties:
                scored_str = "SCORED" if p['scored'] == "Yes" else "MISSED"
                print(f"   {p['min']}' - {p['player']} ({p['team']}) - {scored_str}")
        else:
            print("   None")
        
        print(f"{'='*65}")


def append_to_csv(data: List[Dict], filename: str, columns: List[str], csv_folder: str) -> None:
    """Append data to a CSV file in the specified folder."""
    os.makedirs(csv_folder, exist_ok=True)
    filepath = os.path.join(csv_folder, filename)
    file_exists = os.path.isfile(filepath) and os.path.getsize(filepath) > 0
    
    with open(filepath, 'a', newline='', encoding='utf-8') as f:
        if not file_exists:
            writer = csv.DictWriter(f, fieldnames=columns)
            writer.writeheader()
        
        if data:
            writer = csv.DictWriter(f, fieldnames=columns)
            writer.writerows(data)


def clear_csv_files(filenames: List[str], csv_folder: str) -> None:
    """Remove all CSV files in the specified folder."""
    for filename in filenames:
        filepath = os.path.join(csv_folder, filename)
        if os.path.exists(filepath):
            os.remove(filepath)


def find_json_for_pdf(pdf_path: str, json_folder: str) -> Optional[str]:
    """Find the JSON file for a given PDF."""
    pdf_basename = os.path.basename(pdf_path)
    base_name = os.path.splitext(pdf_basename)[0]
    
    # Try different JSON naming patterns
    json_patterns = [
        os.path.join(json_folder, f"{base_name}_extracted.json"),
        os.path.join(json_folder, f"{base_name}.json"),
        os.path.join(json_folder, f"{pdf_basename}_extracted.json"),
    ]
    
    for json_path in json_patterns:
        if os.path.exists(json_path):
            return json_path
    
    return None


def extract_text_from_pdf(pdf_path: str) -> str:
    """Extract text content from a PDF file."""
    if not PDF_AVAILABLE:
        raise ImportError("No PDF library available. Please install PyPDF2 or pdfplumber: pip install PyPDF2 or pip install pdfplumber")
    
    try:
        if USE_PDFPLUMBER:
            # Use pdfplumber for better text extraction
            with pdfplumber.open(pdf_path) as pdf:
                text_parts = []
                for page in pdf.pages:
                    text = page.extract_text()
                    if text:
                        text_parts.append(text)
                return "\n".join(text_parts)
        else:
            # Use PyPDF2
            with open(pdf_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                text_parts = []
                for page in pdf_reader.pages:
                    text = page.extract_text()
                    if text:
                        text_parts.append(text)
                return "\n".join(text_parts)
    except Exception as e:
        raise Exception(f"Error extracting text from PDF {pdf_path}: {e}")


def create_json_from_pdf(pdf_path: str, json_folder: str) -> str:
    """Extract text from PDF and save as JSON file in the specified folder."""
    os.makedirs(json_folder, exist_ok=True)
    
    pdf_basename = os.path.basename(pdf_path)
    base_name = os.path.splitext(pdf_basename)[0]
    json_filename = f"{base_name}_extracted.json"
    json_path = os.path.join(json_folder, json_filename)
    
    # Extract text from PDF
    print(f"   📄 Extracting text from PDF...")
    raw_content = extract_text_from_pdf(pdf_path)
    
    # Create JSON structure matching expected format
    json_data = {
        "success_pdfs": [{
            "filename": pdf_basename,
            "raw_content": raw_content
        }]
    }
    
    # Save to JSON file
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(json_data, f, ensure_ascii=False, indent=2)
    
    print(f"   ✓ Created JSON file: {json_filename}")
    return json_path


def extract_pdf_content(pdf_path: str, json_folder: str) -> str:
    """Extract raw content from a PDF using its JSON file. Creates JSON if it doesn't exist."""
    json_path = find_json_for_pdf(pdf_path, json_folder)
    
    # If JSON doesn't exist, create it from PDF
    if not json_path or not os.path.exists(json_path):
        try:
            json_path = create_json_from_pdf(pdf_path, json_folder)
        except Exception as e:
            print(f"   ⚠ Error creating JSON from PDF: {e}")
            return ""
    
    # Read JSON file
    if json_path and os.path.exists(json_path):
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                content = json.load(f)
            
            if isinstance(content, dict):
                pdf_data = content.get('success_pdfs', [content])[0]
                raw_content = pdf_data.get('raw_content', str(content))
            else:
                raw_content = str(content)
            return raw_content
        except Exception as e:
            print(f"   ⚠ Error reading {json_path}: {e}")
            return ""
    else:
        print(f"   ⚠ Failed to create or find JSON file for {os.path.basename(pdf_path)}")
        return ""


def process_folder(pdf_folder: str, json_folder: str, csv_folder: str, clear_existing: bool = True) -> None:
    """Process all PDF files in a folder and append results to CSV files."""
    csv_files = ['subs.csv', 'cautions.csv', 'goals.csv', 'own_goals.csv', 'penalties.csv']
    
    # Clear existing CSV files if requested
    if clear_existing:
        print("Clearing existing CSV files...")
        clear_csv_files(csv_files, csv_folder)
    
    # Create folders if they don't exist
    os.makedirs(pdf_folder, exist_ok=True)
    os.makedirs(json_folder, exist_ok=True)
    os.makedirs(csv_folder, exist_ok=True)
    
    # Find all PDF files in the folder
    pdf_pattern = os.path.join(pdf_folder, '*.pdf')
    pdf_files = sorted(glob.glob(pdf_pattern))
    
    if not pdf_files:
        print(f"\n⚠ No PDF files found in folder: {pdf_folder}")
        print(f"Please place your PDF match reports in: {os.path.abspath(pdf_folder)}")
        return
    
    print(f"\n{'='*65}")
    print(f"MATCH REPORT DATA EXTRACTOR")
    print(f"{'='*65}")
    print(f"\n📁 PDF Folder: {os.path.abspath(pdf_folder)}")
    print(f"📁 JSON Folder: {os.path.abspath(json_folder)}")
    print(f"📁 CSV Folder: {os.path.abspath(csv_folder)}")
    print(f"\nFound {len(pdf_files)} PDF files to process")
    print("-" * 65)
    
    # Initialize totals
    total_subs = 0
    total_cautions = 0
    total_goals = 0
    total_own_goals = 0
    total_penalties = 0
    
    # Process each PDF file
    for idx, pdf_path in enumerate(pdf_files, 1):
        pdf_filename = os.path.basename(pdf_path)
        print(f"\n[{idx}/{len(pdf_files)}] Processing: {pdf_filename}")
        
        # Extract content from PDF
        raw_content = extract_pdf_content(pdf_path, json_folder)
        
        if not raw_content:
            continue
        
        # Create extractor and process
        extractor = MatchReportExtractor(raw_content, pdf_filename)
        subs, cautions, goals, own_goals, penalties = extractor.process()
        
        # Print detailed extraction report
        extractor.print_extraction_report()
        
        # Append data to CSV files
        append_to_csv(subs, 'subs.csv', SUBS_COLUMNS, csv_folder)
        append_to_csv(cautions, 'cautions.csv', CAUTIONS_COLUMNS, csv_folder)
        append_to_csv(goals, 'goals.csv', GOALS_COLUMNS, csv_folder)
        append_to_csv(own_goals, 'own_goals.csv', OWN_GOALS_COLUMNS, csv_folder)
        append_to_csv(penalties, 'penalties.csv', PENALTIES_COLUMNS, csv_folder)
        
        # Update totals
        total_subs += len(subs)
        total_cautions += len(cautions)
        total_goals += len(goals)
        total_own_goals += len(own_goals)
        total_penalties += len(penalties)
    
    # Print summary
    print(f"\n{'='*65}")
    print("EXTRACTION COMPLETE - OVERALL SUMMARY")
    print(f"{'='*65}")
    print(f"Total PDFs processed: {len(pdf_files)}")
    print(f"Total Substitutions: {total_subs}")
    print(f"Total Cautions: {total_cautions}")
    print(f"Total Goals: {total_goals}")
    print(f"Total Own Goals: {total_own_goals}")
    print(f"Total Penalties: {total_penalties}")
    print(f"\n📁 CSV files saved to: {os.path.abspath(csv_folder)}")
    for csv_file in csv_files:
        filepath = os.path.join(csv_folder, csv_file)
        if os.path.exists(filepath):
            file_size = os.path.getsize(filepath)
            row_count = sum(1 for _ in open(filepath, 'r', encoding='utf-8')) - 1
            print(f"   ✓ {csv_file}: {row_count} rows ({file_size} bytes)")
    print("=" * 65)


def main():
    """Main function - process all PDFs using configured paths."""
    print("\n" + "=" * 65)
    print("CONFIGURATION")
    print("=" * 65)
    print(f"PDF Folder: {PDF_FOLDER}")
    print(f"JSON Folder: {JSON_FOLDER}")
    print(f"CSV Folder: {CSV_FOLDER}")
    print("=" * 65)
    
    # Process all PDFs in the folder (append to existing CSV files)
    process_folder(PDF_FOLDER, JSON_FOLDER, CSV_FOLDER, clear_existing=False)


if __name__ == "__main__":
    main()
