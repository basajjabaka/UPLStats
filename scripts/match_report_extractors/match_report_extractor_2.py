"""
Match Report Data Extractor
Extracts game statistics from multiple StarTimes Uganda Premier League match report PDFs
and stores the data in CSV files (subs, cautions, goals, own_goals, penalties).

The script processes all PDF files in a specified folder and appends the extracted data
to the same CSV files for each match.

SYMBOL IDENTIFICATION:
- Goal (⊕): Appears as "⊕" or "oplus" in extraction. Position: AFTER time', BEFORE player name
           Format: "11'⊕ SimonPeterOdeke" or "time'? Player" (goal indicator after time)
           
- Yellow Card (π): Appears as "π" or "pi" in extraction. Position: AFTER player name, BEFORE time'
                  Format: "Paul Wasswa ?19'" (player first, then ? symbol, then time)
                  
- Second Yellow (½ᵥ): Appears as "½ᵥ" or similar unicode. Format: similar to yellow card
                      Results in red card with double-caution = Yes
                      
- Red Card (⊃ᵣ): Appears as "⊃ᵣ" or similar. Format: similar to yellow card
               Direct red card with double-caution = No
               
- Own Goal (⊛): Appears as "⊛" or "*". Position: AFTER time', BEFORE player name
               Format: "time'⊛ Player"
               
- Substitution (↑↓): Appears as "↑↓" or "in/out" text. Format: "time in Player, out Player"
                    Example: "56'in Allan Kiggundu, out James Ssemambo"

KEY DIFFERENCES:
- Goals: time' SYMBOL Player (symbol comes AFTER time)
- Yellow Cards: Player SYMBOL time' (symbol comes AFTER player name, BEFORE time)

This script uses POSITION of symbols to distinguish between event types.
"""

import re
import csv
import json
import os
import glob
from typing import List, Dict, Tuple, Optional


class MatchReportExtractor:
    """Extracts game statistics from match report PDF content."""
    
    def __init__(self, pdf_content: str):
        """Initialize with extracted PDF content."""
        self.content = pdf_content
        self.game = ""
        self.lhs_team = ""  # Left hand side team
        self.rhs_team = ""  # Right hand side team
        self.lhs_team_short = ""  # Short form (first word only)
        self.rhs_team_short = ""  # Short form (first word only)
        self.subs = []
        self.cautions = []
        self.goals = []
        self.own_goals = []
        self.penalties = []
        
        # Define player lists for each team - based on roster in PDF
        # LUGAZI FC players (from starting lineup and substitutes)
        self.lugazi_players = [
            "JumaMutebi", "Ayiko Richard", "DausonMafumu", "Moses Ojoaza Buga",
            "SharifSaaka", "David Bagoole", "AbdulKalanzi", "PaulWasswaAmos Etoju",
            "RogersAtube", "Juma Ssajjabi", "Allan Batali Igama", "Tusaba Najib Gwaidho",
            "Joseph Othieno", "Edrine Junior", "Yusuf Mafabi",
            "Emmanuel Derrick Were", "Ashiraf Mulindi", "Mubaraka Mitala",
            "Derrick Mwanje", "Alfred Leku", "Lumumba Norman Eluzai Brown",
            "Freedom Mungudit", "Amos Etoju", "Juma Ssajabi", "Steven Nyalimo",
            "Edrine Junior Owachgiu"
        ]
        
        # CALVARY FC players (from starting lineup and substitutes)
        self.calvary_players = [
            "Hadji Shukuru", "Christopher Agotre", "Julius Ocen", "BashirAsiku",
            "SimonPeterOdeke", "JamesSsemambo", "Haron Odongo", "Steven Nyalimo",
            "Daniel Opio", "ANDREWKIWANUKA", "JuniorEmmanuel Ojok",
            "Allan Kiggundu", "Stephen Oriokot", "Saidi Sukuru", "Christopher Agotre"
        ]
    
    def _get_team_short(self, team: str) -> str:
        """Get short form of team name (first word only)."""
        return team.split()[0] if team else team
    
    def extract_game_info(self) -> None:
        """Extract game name from the Match Events title section."""
        teams_match = re.search(r'(LUGAZI\s*FC)\s*(CALVARY\s*FC)', self.content, re.IGNORECASE)
        if teams_match:
            self.lhs_team = "LUGAZI FC"
            self.rhs_team = "CALVARY FC"
            self.lhs_team_short = self._get_team_short(self.lhs_team)
            self.rhs_team_short = self._get_team_short(self.rhs_team)
            self.game = f"{self.lhs_team_short}-vs-{self.rhs_team_short}"
        else:
            # Try to extract any team names from the content
            # Look for patterns like "TEAM1 FC TEAM2 FC" or similar
            team_pattern = re.findall(r'([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\s*FC', self.content)
            if len(team_pattern) >= 2:
                self.lhs_team = f"{team_pattern[0]} FC"
                self.rhs_team = f"{team_pattern[1]} FC"
                self.lhs_team_short = self._get_team_short(self.lhs_team)
                self.rhs_team_short = self._get_team_short(self.rhs_team)
                self.game = f"{self.lhs_team_short}-vs-{self.rhs_team_short}"
            else:
                # Fallback - use unknown teams
                self.lhs_team = "UNKNOWN1 FC"
                self.rhs_team = "UNKNOWN2 FC"
                self.lhs_team_short = "UNKNOWN1"
                self.rhs_team_short = "UNKNOWN2"
                self.game = f"{self.lhs_team_short}-vs-{self.rhs_team_short}"
    
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
        # Check for LUGAZI players
        for player in self.lugazi_players:
            if player in text:
                return "LHS"
        
        # Check for CALVARY players
        for player in self.calvary_players:
            if player in text:
                return "RHS"
        
        return None
    
    def extract_goals(self) -> None:
        """Extract goal data from Match Events Table.
        
        GOAL SYMBOL IDENTIFICATION:
        - Goal symbol (⊕) appears AFTER time', BEFORE player name
        - Format: "11'⊕ SimonPeterOdeke" or "time'? Player"
        - KEY: The symbol comes AFTER the time, creating pattern: time'SYMBOL Player
        
        This is DISTINCT from yellow cards where pattern is: Player SYMBOL time'
        """
        match_events_match = re.search(r'MATCH\s*EVENTS\s*(.+?)(?:PENALTY\s*SHOOT-OUT|SIGNATURES)', 
                                       self.content, re.IGNORECASE | re.DOTALL)
        
        if not match_events_match:
            return
        
        events_text = match_events_match.group(1)
        
        # Goal pattern: time' followed by goal indicator, THEN player name
        # Pattern: "11'⊕ SimonPeterOdeke" or "time'? Player" where ? is goal symbol
        # The GOAL symbol comes AFTER time, BEFORE player
        # NOT "Player ?time'" which is a yellow card
        
        # Pattern 1: Explicit goal symbol (⊕)
        goal_pattern_oplus = r"(\d+)'\s*⊕\s*([A-Za-z]+)"
        
        # Pattern 2: Question mark as goal indicator (after time, before player)
        # But we must exclude "Player ?time'" patterns (yellow cards)
        goal_pattern_question = r"(\d+)'\s*\?\s*([A-Za-z]+)"
        
        for match in re.finditer(goal_pattern_oplus, events_text, re.IGNORECASE):
            minute = match.group(1)
            player = match.group(2)
            full_match = match.group(0)
            
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
        
        # Check for question mark goal pattern, but skip if it looks like yellow card
        for match in re.finditer(goal_pattern_question, events_text, re.IGNORECASE):
            minute = match.group(1)
            player = match.group(2)
            full_match = match.group(0)
            
            # If the context suggests this is a yellow card (Player ?time' format), skip it
            # Yellow cards have player name BEFORE the ? symbol
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
    
    def extract_cautions(self) -> None:
        """Extract caution (yellow/red card) data from Match Events Table.
        
        YELLOW CARD SYMBOL IDENTIFICATION:
        - Yellow card symbol (π) appears AFTER player name, BEFORE time'
        - Format: "Paul Wasswa ?19'" (player first, then ? symbol, then time)
        - KEY: The symbol comes AFTER player name, creating pattern: Player SYMBOL time'
        
        This is DISTINCT from goals where pattern is: time'SYMBOL Player
        """
        match_events_match = re.search(r'MATCH\s*EVENTS\s*(.+?)(?:PENALTY\s*SHOOT-OUT|SIGNATURES)', 
                                       self.content, re.IGNORECASE | re.DOTALL)
        
        if not match_events_match:
            return
        
        events_text = match_events_match.group(1)
        
        # Yellow card pattern: Player name followed by ? then time'
        # Pattern: "Paul Wasswa ?19'" or "Player ?time'"
        # The SYMBOL comes AFTER player name, BEFORE time'
        yellow_pattern = r"([A-Za-z]+(?:\s+[A-Za-z]+)*)\s*\?(\d+)'(?:\(\+?\d+'?\))?"
        
        # Second yellow pattern
        second_yellow_pattern = r"([A-Za-z]+(?:\s+[A-Za-z]+)*)\s*[½ᵥ]+(\d+)'(?:\(\+?\d+'?\))?"
        
        # Red card pattern
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
        """Extract substitution data from Match Events Table.
        
        SUBSTITUTION SYMBOL IDENTIFICATION:
        - Substitution indicator: "in Player, out Player" pattern
        - Format: "56'in Allan Kiggundu, out James Ssemambo"
        - The "in" and "out" keywords identify substitutions
        """
        match_events_match = re.search(r'MATCH\s*EVENTS\s*(.+?)(?:PENALTY\s*SHOOT-OUT|SIGNATURES)', 
                                       self.content, re.IGNORECASE | re.DOTALL)
        
        if not match_events_match:
            return
        
        events_text = match_events_match.group(1)
        
        # Substitution pattern: time in Player, out Player
        # Format: "56'in Allan Kiggundu, out James Ssemambo"
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
        """Extract own goal data from Match Events Table.
        
        OWN GOAL SYMBOL IDENTIFICATION:
        - Own goal symbol (⊛) appears AFTER time', BEFORE player name
        - Format: "time'⊛ Player" or "time'* Player"
        - Same position pattern as regular goals
        """
        match_events_match = re.search(r'MATCH\s*EVENTS\s*(.+?)(?:PENALTY\s*SHOOT-OUT|SIGNATURES)', 
                                       self.content, re.IGNORECASE | re.DOTALL)
        
        if not match_events_match:
            return
        
        events_text = match_events_match.group(1)
        
        # Own goal pattern: time' followed by ⊛ or * symbol, then player name
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
        """Extract penalty data from Match Events Table.
        
        PENALTY SYMBOL IDENTIFICATION:
        - Penalty scored: ℰₚᵃ (appears as P in extraction)
        - Penalty missed: ℰₓ^★ (appears as M in extraction)
        - Format: "time'P Player" (scored) or "time'M Player" (missed)
        """
        match_events_match = re.search(r'MATCH\s*EVENTS\s*(.+?)(?:PENALTY\s*SHOOT-OUT|SIGNATURES)', 
                                       self.content, re.IGNORECASE | re.DOTALL)
        
        if not match_events_match:
            return
        
        events_text = match_events_match.group(1)
        
        # Penalty scored pattern
        penalty_scored_pattern = r"(\d+)'\s*[Pp]\s*([A-Za-z]+)"
        
        # Penalty missed pattern  
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
        self.extract_goals()  # Extract goals first (before cautions)
        self.extract_cautions()
        self.extract_substitutions()
        self.extract_own_goals()
        self.extract_penalties()
        
        return self.subs, self.cautions, self.goals, self.own_goals, self.penalties


def save_to_csv(data: List[Dict], filename: str, columns: List[str]) -> None:
    """Save data to a CSV file (overwrites existing file)."""
    with open(filename, 'w', newline='', encoding='utf-8') as f:
        if data:
            writer = csv.DictWriter(f, fieldnames=columns)
            writer.writeheader()
            writer.writerows(data)
        else:
            writer = csv.writer(f)
            writer.writerow(columns)


def append_to_csv(data: List[Dict], filename: str, columns: List[str]) -> None:
    """Append data to an existing CSV file, creating file with header if it doesn't exist."""
    file_exists = os.path.isfile(filename) and os.path.getsize(filename) > 0
    
    with open(filename, 'a', newline='', encoding='utf-8') as f:
        if not file_exists:
            # File doesn't exist or is empty - write header
            writer = csv.DictWriter(f, fieldnames=columns)
            writer.writeheader()
        
        if data:
            writer = csv.DictWriter(f, fieldnames=columns)
            writer.writerows(data)


def clear_csv_files(filenames: List[str]) -> None:
    """Clear all CSV files (remove content but keep headers)."""
    for filename in filenames:
        if os.path.exists(filename):
            os.remove(filename)


def extract_pdf_content(pdf_path: str) -> str:
    """Extract raw content from a PDF file using the PDF extraction tool output."""
    json_path = pdf_path.replace('.pdf', '_extracted.json')
    
    # Check if JSON file exists
    if os.path.exists(json_path):
        with open(json_path, 'r', encoding='utf-8') as f:
            content = json.load(f)
        
        if isinstance(content, dict):
            pdf_data = content.get('success_pdfs', [content])[0]
            raw_content = pdf_data.get('raw_content', str(content))
        else:
            raw_content = str(content)
        return raw_content
    else:
        # JSON file doesn't exist - need to run extraction
        # For now, return empty string - user needs to run extraction first
        print(f"Warning: No extracted JSON file found for {pdf_path}")
        print(f"Please run PDF extraction first and save to {json_path}")
        return ""


def process_folder(pdf_folder: str, clear_existing: bool = True) -> None:
    """Process all PDF files in a folder and append results to CSV files.
    
    Args:
        pdf_folder: Path to folder containing PDF match reports
        clear_existing: If True, clears existing CSV files before processing
    """
    # Define CSV column headers
    subs_columns = ['game', 'in', 'out', 'min', 'club']
    cautions_columns = ['game', 'player', 'team', 'caution', 'min', 'double-caution']
    goals_columns = ['game', 'player', 'team', 'min', 'added_time']
    own_goals_columns = ['game', 'player', 'team', 'min', 'added_time']
    penalties_columns = ['game', 'player', 'team', 'scored', 'min', 'added_time']
    
    csv_files = ['subs.csv', 'cautions.csv', 'goals.csv', 'own_goals.csv', 'penalties.csv']
    
    # Clear existing CSV files if requested
    if clear_existing:
        print("Clearing existing CSV files...")
        clear_csv_files(csv_files)
    
    # Find all PDF files in the folder
    pdf_pattern = os.path.join(pdf_folder, '*.pdf')
    pdf_files = sorted(glob.glob(pdf_pattern))
    
    if not pdf_files:
        print(f"No PDF files found in folder: {pdf_folder}")
        return
    
    print(f"Found {len(pdf_files)} PDF files to process")
    print("-" * 50)
    
    # Initialize totals
    total_subs = 0
    total_cautions = 0
    total_goals = 0
    total_own_goals = 0
    total_penalties = 0
    
    # Process each PDF file
    for idx, pdf_path in enumerate(pdf_files, 1):
        pdf_filename = os.path.basename(pdf_path)
        print(f"\nProcessing [{idx}/{len(pdf_files)}]: {pdf_filename}")
        
        # Extract content from PDF
        raw_content = extract_pdf_content(pdf_path)
        
        if not raw_content:
            print(f"  Skipping - no content extracted")
            continue
        
        # Create extractor and process
        extractor = MatchReportExtractor(raw_content)
        subs, cautions, goals, own_goals, penalties = extractor.process()
        
        # Append data to CSV files
        append_to_csv(subs, 'subs.csv', subs_columns)
        append_to_csv(cautions, 'cautions.csv', cautions_columns)
        append_to_csv(goals, 'goals.csv', goals_columns)
        append_to_csv(own_goals, 'own_goals.csv', own_goals_columns)
        append_to_csv(penalties, 'penalties.csv', penalties_columns)
        
        # Update totals
        subs_count = len(subs)
        cautions_count = len(cautions)
        goals_count = len(goals)
        own_goals_count = len(own_goals)
        penalties_count = len(penalties)
        
        print(f"  Game: {extractor.game}")
        print(f"  Substitutions: {subs_count}")
        print(f"  Cautions: {cautions_count}")
        print(f"  Goals: {goals_count}")
        print(f"  Own Goals: {own_goals_count}")
        print(f"  Penalties: {penalties_count}")
        
        total_subs += subs_count
        total_cautions += cautions_count
        total_goals += goals_count
        total_own_goals += own_goals_count
        total_penalties += penalties_count
    
    # Print summary
    print("\n" + "=" * 50)
    print("EXTRACTION COMPLETE - SUMMARY")
    print("=" * 50)
    print(f"Total PDFs processed: {len(pdf_files)}")
    print(f"Total Substitutions: {total_subs}")
    print(f"Total Cautions: {total_cautions}")
    print(f"Total Goals: {total_goals}")
    print(f"Total Own Goals: {total_own_goals}")
    print(f"Total Penalties: {total_penalties}")
    print("\nCSV files updated:")
    for csv_file in csv_files:
        if os.path.exists(csv_file):
            file_size = os.path.getsize(csv_file)
            print(f"  ✓ {csv_file} ({file_size} bytes)")


def main():
    """Main function - process all PDFs in the default folder."""
    # Default folder containing PDF match reports
    pdf_folder = "match_reports"  # Change this to your folder path
    
    print("=" * 60)
    print("MATCH REPORT DATA EXTRACTOR")
    print("=" * 60)
    print(f"\nProcessing PDFs from folder: {pdf_folder}")
    
    # Process all PDFs in the folder
    process_folder(pdf_folder, clear_existing=True)


if __name__ == "__main__":
    main()
