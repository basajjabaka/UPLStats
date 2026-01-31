"""
Match Report Data Extractor
Extracts game statistics from a StarTimes Uganda Premier League match report PDF
and stores the data in CSV files (subs, cautions, goals, own_goals, penalties).

The script parses the Match Events Table and uses the legend symbols to identify
different types of events uniquely:

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
            self.lhs_team = "LUGAZI FC"
            self.rhs_team = "CALVARY FC"
            self.lhs_team_short = self._get_team_short(self.lhs_team)
            self.rhs_team_short = self._get_team_short(self.rhs_team)
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
    """Save data to a CSV file."""
    with open(filename, 'w', newline='', encoding='utf-8') as f:
        if data:
            writer = csv.DictWriter(f, fieldnames=columns)
            writer.writeheader()
            writer.writerows(data)
        else:
            writer = csv.writer(f)
            writer.writerow(columns)


def main():
    """Main function to extract match data and save to CSVs."""
    with open('match_report_extracted.json', 'r', encoding='utf-8') as f:
        content = json.load(f)
    
    if isinstance(content, dict):
        pdf_data = content.get('success_pdfs', [content])[0]
        raw_content = pdf_data.get('raw_content', str(content))
    else:
        raw_content = str(content)
    
    extractor = MatchReportExtractor(raw_content)
    subs, cautions, goals, own_goals, penalties = extractor.process()
    
    subs_columns = ['game', 'in', 'out', 'min', 'club']
    cautions_columns = ['game', 'player', 'team', 'caution', 'min', 'double-caution']
    goals_columns = ['game', 'player', 'team', 'min', 'added_time']
    own_goals_columns = ['game', 'player', 'team', 'min', 'added_time']
    penalties_columns = ['game', 'player', 'team', 'scored', 'min', 'added_time']
    
    save_to_csv(subs, 'subs.csv', subs_columns)
    save_to_csv(cautions, 'cautions.csv', cautions_columns)
    save_to_csv(goals, 'goals.csv', goals_columns)
    save_to_csv(own_goals, 'own_goals.csv', own_goals_columns)
    save_to_csv(penalties, 'penalties.csv', penalties_columns)
    
    print("Data extraction complete!")
    print(f"Substitutions: {len(subs)} entries")
    print(f"Cautions: {len(cautions)} entries")
    print(f"Goals: {len(goals)} entries")
    print(f"Own Goals: {len(own_goals)} entries")
    print(f"Penalties: {len(penalties)} entries")


if __name__ == "__main__":
    main()
