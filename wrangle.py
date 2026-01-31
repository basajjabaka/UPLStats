import pandas as pd 
import numpy as np 
import os
from pathlib import Path

dataDIR = Path(__file__).resolve().parent / "csvs/raw"
outputDIR = Path(__file__).resolve().parent / "csvs/transformed"
outputDIR.mkdir(parents=True, exist_ok=True)

def parse_minute(v):
    s = str(v).replace('(', '').replace(')', '')
    if s.strip().lower() == 'nan' or s.strip() == '':
        return np.nan
    if '+' in s:
        left, right = s.split('+')
        return int(left) + int(right)
    return int(s)

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
    df['minute'] = df['min'].apply(parse_minute).astype('int64')
    
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
    
    # insert minute at the original 'min' position
    cols.insert(min_col_idx, 'minute')
    # insert added_time after minute
    cols.insert(min_col_idx + 1, 'added_time')
    # insert period after added_time
    cols.insert(min_col_idx + 2, 'period')
    
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
    
    print(f"\n✓ Saved to: {output_path}")

print(f"\n{'='*60}")
print("All transformations complete!")
print(f"{'='*60}")
