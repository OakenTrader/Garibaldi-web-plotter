import dash
from dash import html, dcc, Input, Output, dash_table
import pandas as pd
from src.loader import load_all_data
from src.pinger import start_pinging
from src.helpers.color import get_color as tag_to_colors
import os, threading
import colorsys
import hashlib
from functools import lru_cache
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
        zf.extractall(f"saves/{CAMPAIGN_NAME}")

    # Write lock file so workers don't re-download on restart
    with open("saves/lock", "w") as lf:
        lf.write("downloaded")

    # Debug: show what was extracted
    print("Extracted zip contents:")
    for root, dirs, files in os.walk(f"saves/{CAMPAIGN_NAME}"):
        print(f"  {root}/", dirs[:5], files[:5])

colors_df = pd.read_csv("tag_colors.csv")
dfs, players = load_all_data(CAMPAIGN_NAME)

ID_COLUMNS = ['id', 'tag', 'country', 'date']

# Every tag's colour is resolved once, here, rather than per plot. The old code
# did a linear scan of colors_df for every tag on every callback (~10ms/plot),
# and its fallback reads the local Victoria 3 install via user_variables.json --
# a path that does not exist on a server, so a tag missing from tag_colors.csv
# raised inside the callback rather than at startup.
def _fallback_color(tag):
    """Deterministic colour for a tag we have no definition for."""
    digest = int(hashlib.md5(tag.encode()).hexdigest()[:6], 16)
    r, g, b = colorsys.hsv_to_rgb((digest % 360) / 360, 0.65, 0.75)
    return f"rgb({int(r * 255)}, {int(g * 255)}, {int(b * 255)})"

_csv_colors = dict(zip(colors_df["tag"], colors_df["color"]))
TAG_COLORS = {}
for _tag in sorted({t for df in dfs.values() for t in df["tag"].unique()}):
    if _tag in _csv_colors:
        TAG_COLORS[_tag] = _csv_colors[_tag]
        continue
    try:
        TAG_COLORS[_tag] = tag_to_colors(_tag)
    except Exception as exc:   # no game files on the host, unknown tag, bad colour
        print(f"No color found for tag {_tag} ({exc}); using fallback")
        TAG_COLORS[_tag] = _fallback_color(_tag)

# (file, column) pairs, sorted so the dropdown order is stable across restarts --
# it was built from a set() before, so it changed on every boot. The dropdown
# value carries the file too, so two CSVs may share a column name without the
# callbacks having to guess which frame was meant.
STAT_INDEX = sorted(
    (file_key, column)
    for file_key, df in dfs.items()
    for column in df.columns.drop(ID_COLUMNS, errors='ignore')
)
STAT_OPTIONS = [
    {'label': f"{file_key.replace('.csv', '')}/{column}", 'value': f"{file_key}::{column}"}
    for file_key, column in STAT_INDEX
]
DEFAULT_STAT = next(
    (o['value'] for o in STAT_OPTIONS if o['value'].endswith("::GDP")),
    STAT_OPTIONS[0]['value'] if STAT_OPTIONS else None,
)


def resolve_stat(value):
    """Split a dropdown value back into the frame it came from and its column."""
    if not value or "::" not in value:
        return None, None
    file_key, column = value.split("::", 1)
    df = dfs.get(file_key)
    if df is None or column not in df.columns:
        return None, None
    return df, column

app = dash.Dash(__name__)
server = app.server

app.layout = html.Div([
    html.H1("Garibaldi Web Plotter"),

    dcc.Dropdown(
        id='data-label-dropdown',
        options=STAT_OPTIONS,
        value=DEFAULT_STAT
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
    # Sized by the viewport instead of a fixed 1600x1200 canvas, so the browser
    # is not rasterising ~2MP of plot on every switch.
    dcc.Graph(id='time-series-plot', style={'height': '70vh'}, responsive=True),
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
    plot_df, column = resolve_stat(selected_label)
    if plot_df is None:
        return [], []

    latest_date = plot_df['date'].max()
    latest_df = plot_df[plot_df['date'] == latest_date]
    table_df = latest_df.sort_values(column, ascending=False)

    # Each record's "id" is the country id the save uses, which DataTable adopts
    # as the row id -- that is what lets the plot callback take
    # derived_virtual_selected_row_ids instead of the whole table body.
    return table_df.to_dict('records'), [{"name": i, "id": i, "deletable": True, "selectable": True} for i in table_df.columns]

def _empty_figure(message):
    return {"data": [], "layout": {"title": {"text": message}, "autosize": True}}


@lru_cache(maxsize=256)
def build_figure(selected_label, selected_ids):
    """Assemble the figure for one stat and selection.

    Returned dicts are cached and shared between requests, so callers must treat
    them as read-only.

    Built as a plain dict rather than through ``px.line``: Dash accepts a bare
    ``{"data": ..., "layout": ...}`` and skips graph_objects' per-property
    validation, which was ~85% of this callback's cost (101ms -> 24ms here).
    """
    plot_df, column = resolve_stat(selected_label)
    if plot_df is None:
        return _empty_figure("No data available for selected label.")

    if selected_ids:
        plot_df = plot_df[plot_df['id'].isin(selected_ids)]
    if plot_df.empty:
        return _empty_figure(f"No rows for {column} in the current selection.")

    # Date order only. The old sort also ordered by value, which a time series
    # never needs -- the line is drawn in row order along the x axis.
    plot_df = plot_df.sort_values('date')

    # One trace per country *id*, labelled with that id's most recent name, and
    # ordered so the highest final value leads the legend. Grouping on id rather
    # than name keeps a country's line unbroken across an in-game rename.
    grouped = dict(tuple(plot_df.groupby('id', sort=False)))
    last_values = plot_df.groupby('id')[column].last().sort_values(ascending=False)
    last_names = plot_df.groupby('id')['country'].last()
    last_tags = plot_df.groupby('id')['tag'].last()

    # WebGL only once SVG would mean tens of thousands of nodes; below that,
    # plain scatter keeps crisp text and full image-export fidelity.
    trace_type = "scattergl" if len(plot_df) > 5000 else "scatter"

    traces = []
    for country_id in last_values.index:
        group = grouped[country_id]
        name = last_names.get(country_id, str(country_id))
        color = TAG_COLORS.get(last_tags.get(country_id), "rgb(128, 128, 128)")
        traces.append({
            "type": trace_type,
            "mode": "lines+markers",
            "name": name,
            "x": group['date'].to_numpy(),
            "y": group[column].to_numpy(),
            "line": {"color": color},
            "marker": {"color": color, "size": 5},
            "hovertemplate": f"{name}<br>%{{x|%Y-%m}}<br>{column}=%{{y:,.4g}}<extra></extra>",
        })

    return {
        "data": traces,
        "layout": {
            "title": {"text": f"Country over time by {column}"},
            "xaxis": {"title": {"text": "date"}},
            "yaxis": {"title": {"text": column}},
            "legend": {"title": {"text": "country"}},
            "autosize": True,
            "margin": {"l": 70, "r": 20, "t": 50, "b": 50},
            "hovermode": "closest",
        },
    }


@app.callback(
    Output('time-series-plot', 'figure'),
    Input('data-label-dropdown', 'value'),
    # Selection arrives as row ids, not as the table's contents. Taking
    # derived_virtual_data here made the browser re-upload the whole table body
    # on every plot, and -- because no callback produces that prop -- made Dash
    # fire this callback twice per dropdown change: once immediately with the
    # *previous* stat's rows, then again once DataTable recomputed them.
    Input('country-values-table', 'derived_virtual_selected_row_ids'),
)
def update_plot(selected_label, selected_row_ids):
    # Sorted tuple so the cache key does not depend on click order.
    return build_figure(selected_label, tuple(sorted(selected_row_ids or ())))

if __name__ == "__main__":
    app.run(port=5000)
    # Start the pinger in a separate thread or process
    threading.Thread(target=start_pinging, daemon=True).start()

