#!/usr/bin/python3
import json
from datetime import datetime, timedelta
import yfinance as yf
import readline
import rlcompleter
from stockutils import utils

begin = "2021-01-01"
today = datetime.today().date()

tickers = ['8TRA', 'ABB', 'ATRLJ-B', 'BOL', 'BONAV-B', 'CARE', 'DOM', 'EKTA-B', 'EPI-A', 'ERIC-B', 'INDU-C', 'INVE-B', 'JM', 'NIBE-B', 'PEAB-B', 'REJL-B', 'SHB-B', 'SSAB-B', 'SWED-A', 'TEL2-B', 'TELIA', 'VIVA', 'VOLCAR-B', 'VOLV-B']
#tickers = ['8TRA']


#sorted_list = sorted(tickers)
#print(sorted_list)
#exit(1)

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
        
for stock in tickers:
    fname = "yfdata/" + stock + ".json"
    d = utils.rd_d(fname)
    reco = utils.is_close_to_max_min(d["Slope60"])
    print(stock, reco)

commands=["exit"]
for name in tickers:
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
    if user_input in tickers:
        fname = "yfdata/" + user_input + ".json"
        d = utils.rd_d(fname)
        utils.plot(user_input, d)
    else:
        print("Name does not exist: ", user_input)

