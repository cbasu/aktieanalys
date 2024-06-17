#!/usr/bin/python3
import pandas as pd
import json
from datetime import datetime
from stockutils import utils
from pathlib import Path
import readline
import rlcompleter

# This function will be called to complete the input
def completer(text, state):
    options = [i for i in commands if i.startswith(text)]
    if state < len(options):
        return options[state]
    else:
        return None

excel_file = pd.ExcelFile("aktier.xlsx")

# Get the sheet names
sheet_names = excel_file.sheet_names
del excel_file

for name in sheet_names:
    if name == "list" or name == "portfolio-table":
        continue
    df = pd.read_excel("aktier.xlsx", sheet_name=name, skiprows=3)
    file_path = "data/"+name+".json"
    d = utils.rd_d(file_path)

    if "Date" not in df:
        utils.analyse(name, 60, d)
        utils.analyse(name, 120, d)
        utils.analyse(name, 360, d)
    else:
        start = len(df["Date"])
# Convert Date column to string format
        df["Date"] = df["Date"].apply(lambda x: x.strftime('%Y-%m-%d'))
# append dataframe to dictionary
        d = utils.append_df2d(df,d)

        utils.analyse(name, 60, d)
        utils.analyse(name, 120, d)
        utils.analyse(name, 360, d)


# Write the dictionary to a JSON file
    with open(file_path, 'w') as json_file:
        json.dump(d, json_file, indent=4)

a = []
for name in sheet_names:
    file_path = "data/"+name+".json"
    d = utils.rd_d(file_path)
    a.append(len(d["Date"])

directory = Path('data')
json_files = list(directory.rglob('*.json'))

commands=["exit"]
# Print the list of .json files
for file in json_files:
    name = str(file).split('/')[-1].split('.')[0]
    commands.append(name)

# Configure readline to use the completer function
readline.set_completer(completer)
# Use tab for completion
readline.parse_and_bind("tab: complete")

# Simple loop to take user input
while True:
    user_input = input("Enter: ")
    if user_input == 'exit':
        break
    name = "data/" + user_input + ".json"
    d = utils.rd_d(name)
    utils.plot1(name, d)
