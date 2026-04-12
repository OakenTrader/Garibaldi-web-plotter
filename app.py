import dash
from dash import html, dcc, Input, Output, dash_table
import pandas as pd
import plotly.express as px
from src.loader import load_all_data
from src.pinger import start_pinging
from src.helpers.color import get_color as tag_to_colors
import os, threading
import gdown
import zipfile

FILE_ID = os.getenv("FILE_ID")
CAMPAIGN_NAME = os.getenv("CAMPAIGN_NAME", "data")
url = f"https://drive.google.com/uc?id={FILE_ID}"

if not "saves" in os.listdir("."):
    os.mkdir("saves")
if FILE_ID and "lock" not in os.listdir("saves/"):
    output = f"./saves/{CAMPAIGN_NAME}.zip"
    gdown.download(url, output, quiet=False)

    with zipfile.ZipFile(output, "r") as zf:
        zf.extractall("saves")

    # Write lock file so workers don't re-download on restart
    with open("saves/lock", "w") as lf:
        lf.write("downloaded")

    # Debug: show what was extracted
    print("Extracted zip contents:")
    for root, dirs, files in os.walk(f"saves/{CAMPAIGN_NAME}"):
        print(f"  {root}/", dirs[:5], files[:5])

colors_df = pd.read_csv("tag_colors.csv")
dfs, players = load_all_data(CAMPAIGN_NAME)
# get only the first entry of dfs dict
key1 = list(dfs.keys())
print(colors_df.head())

# Collect all unique data labels from all dfs
all_data_labels = dict()
for key, df in dfs.items():
    all_data_labels[key] = set(df.columns.drop(['id', 'tag', 'country', 'date'], errors='ignore'))
# all_data_labels = sorted(all_data_labels)

app = dash.Dash(__name__)
server = app.server

app.layout = html.Div([
    html.H1("Garibaldi Web Plotter"),

    dcc.Dropdown(
        id='data-label-dropdown',
        options=[{'label': f"{group.replace('.csv', '')}/{label}", 'value': label}for (group, labels) in all_data_labels.items() for label in labels],
        value="GDP"
    ),
    # html.Div([
    #     html.Label("Show player lines only:"),
    #     dcc.Checklist(
    #         id='player-lines-checkbox',
    #         options=[{'label': '', 'value': 'players_only'}],
    #         value=['players_only'],
    #         inline=True
    #     )
    # ], style={'width': '50vw', 'display': 'inline-block', 'verticalAlign': 'top'}),
    dcc.Graph(id='time-series-plot'),
    dash_table.DataTable(
        id='country-values-table',
        editable=True,
        filter_action="native",
        sort_action="native",
        sort_mode="multi",
        column_selectable="single",
        row_selectable="multi",
        selected_columns=[],
        selected_rows=[],
        page_action="native",
        page_current= 0,
        page_size= 20,
    )
])

# Get all unique countries from all dfs
all_countries = set()
for df in dfs.values():
    all_countries.update(df['country'].unique())
all_countries = sorted(all_countries)

@app.callback(
    Output('country-values-table', 'data'),
    Output('country-values-table', 'columns'),
    Input('data-label-dropdown', 'value')
)
def update_country_table(selected_label):
    # Find the first df that contains the selected label
    for df in dfs.values():
        if selected_label in df.columns:
            plot_df = df
            break
    else:
        return [], []

    latest_date = plot_df['date'].max()
    latest_df = plot_df[plot_df['date'] == latest_date]
    # Only keep columns we need
    # table_df = latest_df[['country', selected_label]].drop_duplicates()
    table_df = latest_df.sort_values(selected_label, ascending=False)

    return table_df.to_dict('records'), [{"name": i, "id": i, "deletable": True, "selectable": True} for i in table_df.columns]

@app.callback(
    Output('time-series-plot', 'figure'),
    Input('data-label-dropdown', 'value'),
    # Input('player-lines-checkbox', 'value'),
    Input('country-values-table', 'derived_virtual_selected_rows'),
    Input('country-values-table', 'derived_virtual_data')
)
# def update_plot(selected_label, player_lines_value, selected_rows, table_data):
def update_plot(selected_label, selected_rows, table_data):
    # Find the first df that contains the selected label
    for df in dfs.values():
        if selected_label in df.columns:
            plot_df = df
            plot_df = plot_df.sort_values(['date', selected_label], ascending=[False, False])
            break
    else:
        return px.line(title="No data available for selected label.")

    # player_ids = set(str(pid) for pid in players.keys())
    # show_players_only = 'players_only' in (player_lines_value or [])

    # if show_players_only:
    #     plot_df = plot_df[plot_df['id'].astype(str).isin(player_ids)]

    # Filter by selected countries from table
    if selected_rows is not None and table_data is not None and len(selected_rows) > 0:
        selected_countries = [table_data[i]['country'] for i in selected_rows if 'country' in table_data[i]]
        plot_df = plot_df[plot_df['country'].isin(selected_countries)]

    # Compute the last value of each country for sorting (for player lines only if filtered)
    last_values = (
        plot_df.sort_values('date')
        .groupby('country')[selected_label]
        .last()
        .sort_values(ascending=False)
    )
    plot_df['country'] = pd.Categorical(
        plot_df['country'],
        categories=last_values.index.tolist(),
        ordered=True
    )

    unique_tags = plot_df[["tag", "country"]].drop_duplicates().values.tolist()
    color_map = {}
    for tag, country in unique_tags:
        try:
            color = colors_df.loc[colors_df["tag"] == tag, "color"].iloc[0]
        except IndexError:
            print("No color found for tag:", tag)
            color = tag_to_colors(tag)
        color_map[country] = color
    # color_map = {country: colors_df.loc[df["tag"] == tag, "color"].iloc[0] for tag, country in unique_tags}

    fig = px.line(
        plot_df,
        x="date",
        y=selected_label,
        markers=True,
        labels="country",
        color="country",
        line_group="id",
        title=f"Country over time by {selected_label}",
        color_discrete_map=color_map
    )

    fig.update_layout(
        legend_title='country',
        width=1600,
        height=1200
    )
    return fig

if __name__ == "__main__":
    app.run(port=5000)
    # Start the pinger in a separate thread or process
    threading.Thread(target=start_pinging, daemon=True).start()

