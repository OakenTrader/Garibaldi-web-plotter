import os
import pandas as pd
from datetime import datetime

def load_all_data(campaign_name="data"):
    data_rows = {}
    data_dir = f"data/{campaign_name}"
    for folder in sorted(os.listdir(data_dir)):
        if not folder.startswith(f"{campaign_name}_"):
            continue
        folder_path = os.path.join(data_dir, folder)
        # Extract date from folder name
        try:
            date_str = folder.replace(f"{campaign_name}_", "")
            date = datetime.strptime(date_str, "%Y_%m_%d")
        except Exception:
            continue  # skip folders that don't match pattern

        # Load CSVs inside this folder
        data_path = os.path.join(folder_path, "data")
        for fname in os.listdir(data_path):
            if not fname.endswith(".csv"):
                continue
            fpath = os.path.join(data_path, fname)
            df = pd.read_csv(fpath)
            df["date"] = date
            if fname not in data_rows:
                data_rows[fname] = []
            data_rows[fname].append(df)

    # Combine all into one DataFrame
    full_df = {}
    for key, data_row in data_rows.items():
        data_rows[key] = pd.concat(data_row, ignore_index=True)
        full_df[key] = data_rows[key]

    return full_df