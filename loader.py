import os, json
import pandas as pd
from datetime import datetime

allowed_columns = ["id", "tag", "country", "date", "GDP", "GDP per capita", "debt_percentage", "population", "literacy", "standard of living", "construction", "avg_cost", "innovation", "capped_innovation", "naval_innovation", "military_innovation", "army_experience", "ratio", "total", "army projection", "navy projection", "total_techs", "production_techs", "military_techs", "society_techs", "tech_points", "researching"]

def load_all_data(campaign_name="data"):
    data_rows = {}
    data_dir = f"saves/{campaign_name}"
    players = dict()
    for folder in sorted(os.listdir(data_dir)):
        if not folder.startswith(f"{campaign_name}_"):
            continue
        folder_path = os.path.join(data_dir, folder)
        with open(os.path.join(folder_path, "metadata.json"), "r") as f:
            metadata = json.load(f)
            players.update({p[0]:p[2] for p in metadata["players"]})
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
            """TODO We are now restricting the data to only players"""
            df = df[df['id'].isin(players.keys())]
            df = df[[col for col in df.columns if col in allowed_columns]]
            if fname not in data_rows:
                data_rows[fname] = []
            data_rows[fname].append(df)

    # Combine all into one DataFrame
    full_df = {}
    for key, data_row in data_rows.items():
        data_rows[key] = pd.concat(data_row, ignore_index=True)
        full_df[key] = data_rows[key]
    return full_df, players