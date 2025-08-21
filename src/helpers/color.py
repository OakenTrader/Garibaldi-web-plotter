"""
Functions that manage data plotting.
"""

import os, warnings, time
from src.helpers.utility import *
from random import randint
import numpy as np
import pandas as pd
import colorsys

# plt.rcParams.update({
#     'axes.facecolor': [0.1, 0.1, .1, 1],
#     'axes.edgecolor': 'white',
#     'axes.labelcolor': 'white',
#     'figure.facecolor': 'black',
#     'grid.color': 'gray',
#     'text.color': 'white',
#     'xtick.color': 'white',
#     'ytick.color': 'white',
#     'legend.facecolor': 'black',
#     'legend.edgecolor': 'white',
#     'lines.color': 'white',
#     'patch.edgecolor': 'white',
#     'savefig.facecolor': 'black',
#     'savefig.edgecolor': 'black'
# })

def get_color(tag):
    """
    Get a color of a tag (three letters defining a country) and its format
    """
    def_countries = load_def_multiple("country_definitions", "Common Directory")
    named_colors = load_def_multiple("named_colors", depth_add=1)["colors"]
    try:
        color = def_countries[tag]["color"]
        if isinstance(color, str) and color in named_colors:
            color = named_colors[color]
    except KeyError:
        color = {"field_type":"hsv360", "value":[randint(0, 359), 100, 50]}
        warnings.warn(f"No color provided for {tag}, used hsv360 {color['value']}")
        # raise KeyError(f"No color provided for {tag}")

    color_type = color["field_type"]
    if color_type == "list" or color_type == "rgb":
        color_type = "rgb"
        if any([float(v) > 0 for v in color["value"]]):
            colors = [float(v) / 255 for v in color["value"]]
        else:
            colors = [float(v) for v in color["value"]]
    elif color_type == "hsv":
        color_ = [float(v) for v in color["value"]]
        h, s, v = color_[0] / 360, color_[1] / 100, color_[2] / 100
        colors = list(colorsys.hsv_to_rgb(h, s, v))
    elif color_type == "hsv360":
        color_ = [float(v) for v in color["value"]]
        h, s, v = color_[0] / 360, color_[1] / 100, color_[2] / 100
        colors = list(colorsys.hsv_to_rgb(h, s, v))
    else:
        raise NotImplementedError(f"Currently supported only rgb and hsv360 values. Received {color_type} from {tag}")
    if any([v > 1 for v in colors]):
        raise ValueError(f"Value Error, got {color} from {tag} resulting in {colors}")
    colors = np.concatenate([colors, [1]])
    colors = f"rgb({int(colors[0] * 255)}, {int(colors[1] * 255)}, {int(colors[2] * 255)})"
    return colors