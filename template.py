import os
from pathlib import Path
import logging

logging.basicConfig(level=logging.INFO, format='[%(asctime)s]: %(message)s:')


# List of folders to create
foldersList = [
    ".github/workflows",
    f"notebooks",
    f"scripts",
    f"models",
    f"visuals",
    f"logs",
    f"reports",
    f"csvs",
]

# List of files to create in root directory
filesList = [
    "app.py",
    "main.py",
    "requirements.txt"
]

# Create folders
for folderPath in foldersList:
    os.makedirs(folderPath, exist_ok=True)
    logging.info(f"Creating Directory: {folderPath}")

# Create root-level files
for fileName in filesList:
    if not os.path.exists(fileName) or os.path.getsize(fileName) == 0:
        with open(fileName, "w") as f:
            pass
        logging.info(f"Creating empty file: {fileName}")
    else:
        logging.info(f"{fileName} already exists.")