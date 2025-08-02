import dash
from dash import html, dcc, Input, Output
import pandas as pd
import plotly.express as px
from loader import load_all_data  # move loader function here

dfs = {}
dfs = load_all_data("vanilla1_9")
# get only the first entry of dfs dict
print(dfs.keys())
key1 = list(dfs.keys())
# dfs = {key1: dfs[key1]}

# Collect all unique data labels from all dfs
all_data_labels = set()
for df in dfs.values():
    all_data_labels.update(df.columns.drop(['id', 'tag', 'country', 'date'], errors='ignore'))
all_data_labels = sorted(all_data_labels)

app = dash.Dash(__name__)
server = app.server

app.layout = html.Div([
    html.H1("Time-Series Data Viewer"),

    dcc.Dropdown(
        id='data-label-dropdown',
        options=[{'label': label, 'value': label} for label in all_data_labels],
        value=all_data_labels[0] if all_data_labels else None
    ),

    dcc.Graph(id='time-series-plot')
])

@app.callback(
    Output('time-series-plot', 'figure'),
    Input('data-label-dropdown', 'value')
)
def update_plot(selected_label):
    # Find the first df that contains the selected label
    for df in dfs.values():
        if selected_label in df.columns:
            plot_df = df
            # Sort the dataframe by the x-axis value ('date') before plotting
            plot_df = plot_df.sort_values('date')
            break
    else:
        return px.line(title="No data available for selected label.")

    # Compute the last value of each country for sorting
    last_values = (
        plot_df.sort_values('date')
        .groupby('country')[selected_label]
        .last()
        .sort_values(ascending=False)
    )
    # Set the country column as a categorical with the sorted order
    plot_df['country'] = pd.Categorical(
        plot_df['country'],
        categories=last_values.index.tolist(),
        ordered=True
    )
    print(plot_df['country'])
    print(plot_df)

    fig = px.line(
        plot_df,
        x='date',
        y=selected_label,
        markers=True,
        color='country',
        title=f"Country over time by {selected_label}"
    )
    fig.update_layout(
        legend_title='country',
        width=1600,   # Set the width of the plot
        height=1200   # Set the height of the plot
    )
    return fig

if __name__ == "__main__":
    app.run()
