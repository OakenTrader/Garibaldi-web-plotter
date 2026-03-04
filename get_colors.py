from src.helpers.color import get_color
from src.helpers.utility import load_def_multiple
import pandas as pd

# Get a list of all uppercase alphabets
def get_uppercase_alphabets():
    return [chr(i) for i in range(ord('A'), ord('Z') + 1)]
all_tags = [a+b+c for a in get_uppercase_alphabets() for b in get_uppercase_alphabets() for c in get_uppercase_alphabets()]
print(get_uppercase_alphabets())
print(all_tags)

def_countries = load_def_multiple("country_definitions", "Common Directory")
print(def_countries.keys())
count = 0
tag_colors = {}
for tag in def_countries.keys():
    try:
        color = get_color(tag)
        print(f"{tag}: {color}")
        if "REPLACE" in color:
            tag = tag.replace("REPLACE:", "")
        tag_colors[tag] = color
        count += 1
    except KeyError:
        print(f"{tag} not found in definitions")
print(f"Total tags processed: {count}")
# Make a pandas DataFrame from the tag_colors dictionary and save it to a CSV file
df = pd.DataFrame(list(tag_colors.items()), columns=['tag', 'color'])
df.to_csv("tag_colors.csv", index=False)