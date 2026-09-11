"""
Club names, shared by the extractors and the dashboard.

Kept free of heavy imports (no pdfplumber, no pandas) so the dashboard can map
a club-logo filename to the same short code the CSVs use.
"""

import re

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


def abbreviate(team_name):
    """Full club name -> the short code the CSVs use."""
    key = re.sub(r"[^A-Z0-9 ]", "", (team_name or "").upper())
    key = re.sub(r"\s+", " ", key).strip()
    if key in TEAM_ABBREVIATIONS:
        return TEAM_ABBREVIATIONS[key]
    stripped = re.sub(r"\b(FC|SC|CITY|UNITED|SAINTS|FOOTBALL|CLUB)\b", " ", key)
    stripped = re.sub(r"\s+", " ", stripped).strip()
    return (stripped or key).split(" ")[0]
