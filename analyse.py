#!/usr/bin/python3
import json
from datetime import datetime, timedelta
import yfinance as yf
from pathlib import Path
import readline
import rlcompleter
from stockutils import utils

begin = "2021-01-01"
today = datetime.today().date()

tickers=["BOL", "BONAV-B", "CARE", "INVE-B", "TEL2-B", "EKTA-B", "EPI-A","SHB-A", "PEAB-B", "ERIC-B", "SSAB-B", "VOLV-B", "VOLCAR-B", "PEAB-B", "DOM"]
#tickers=["CARE.ST"]

# This function will be called to complete the input
def completer(text, state):
    options = [i for i in commands if i.startswith(text)]
    if state < len(options):
        return options[state]
    else:
        return None

user_input = input("Run analysis (y/n): ")
if user_input == "y":
    for stock in tickers:
        print(stock)
        start = begin
        end = today
        file = "yfdata/"+stock+".json"
        d = utils.rd_d(file)
        if d:
            start = d["Date"][len(d["Date"])-1]
            date_object = datetime.strptime(start, "%Y-%m-%d")
            date_object = date_object + timedelta(days=1)
            start = date_object.strftime("%Y-%m-%d")

        # Fetch historical stock data
        df = yf.download(stock+".ST", start=start, end=end)
        d = utils.append_yf2d(df, d)
        
        utils.analyse(stock, 60, d)
        utils.analyse(stock, 120, d)
        utils.analyse(stock, 360, d)

        # Write the dictionary to a JSON file
        with open(file, 'w') as json_file:
            json.dump(d, json_file, indent=4)

a = []
for stock in tickers:
    file = "yfdata/"+stock+".json"
    d = utils.rd_d(file)
    a.append(len(d["Date"]))

directory = Path('yfdata')
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
    name = "yfdata/" + user_input + ".json"
    d = utils.rd_d(name)
    utils.plot1(name, d)

