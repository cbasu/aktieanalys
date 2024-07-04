#!/usr/bin/env python3
#####################!/usr/bin/python3
import json
from datetime import datetime, timedelta
import yfinance as yf
import readline
import rlcompleter
from stockutils import utils
from tabulate import tabulate

begin = "2021-01-01"
today = datetime.today().date()

exchange = {
        "ST": ['8TRA', 'AAK', 'AZA', 'ABB', 'ATCO-B', 'ATRLJ-B', 'AXFO', 'BOL', 'BONAV-B', 'CARE', 'COIC', 'DOM', 'EKTA-B', 'ELUX-B', 'EPI-A', 'EQT', 'ERIC-B', 'ESSITY-B', 'HM-B', 'HTRO', 'INDU-C', 'INVE-B', 'JM', 'LUMI', 'MEKO', 'NIBE-B', 'NMAN', 'PEAB-B', 'REJL-B', 'SAND', 'SAVE', 'SHB-B', 'SKF-B', 'SSAB-B', 'SWED-A', 'TEL2-B', 'TELIA', 'TROAX', 'VIVA', 'VOLCAR-B', 'VOLV-B'],
        #"ST": ['EQT', 'SAVE'],
        "OL": ['PROT']
    }

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
    
    #for stock in tickers:
    for key in exchange:
        tickers = exchange[key]
        for stock in tickers:
            start = begin
            end = today
            nam = stock+"."+key
            file = "yfdata/"+nam+".json"
            d = utils.rd_d(file)
            if d:
                start = d["Date"][len(d["Date"])-1]
                date_object = datetime.strptime(start, "%Y-%m-%d")
                date_object = date_object + timedelta(days=1)
                start = date_object.strftime("%Y-%m-%d")

            # Fetch historical stock data
            df = yf.download(nam, start=start, end=end)
            d = utils.append_yf2d(df, d)
        
            utils.analyse(stock, 60, d)
            utils.analyse(stock, 120, d)
            utils.analyse(stock, 360, d)

            # Write the dictionary to a JSON file
            with open(file, 'w') as json_file:
                json.dump(d, json_file, indent=4)

table = []
#for stock in tickers:
for key in exchange:
    tickers = exchange[key]
    for stock in tickers:
        nam = stock+"."+key
        fname = "yfdata/" + nam + ".json"
        d = utils.rd_d(fname)
        reco = utils.is_close_to_max_min(d["Slope60"])
        if reco == "neutral":
            continue
        table.append([nam, reco])

# Sort data by the 2nd column (index 1)
table = sorted(table, key=lambda x: x[1])
headers = ["Name", "Rec60"]
# Print the data in tabular format
print(tabulate(table, headers=headers, tablefmt="plain"))

commands=["exit"]
#for name in tickers:
for key in exchange:
    tickers = exchange[key]
    for stock in tickers:
        nam = stock+"."+key
        commands.append(nam)

# Configure readline to use the completer function
readline.set_completer(completer)
# Use tab for completion
readline.parse_and_bind("tab: complete")

# Simple loop to take user input
while True:
    user_input = input("Enter: ")
    if user_input == 'exit':
        break
    try:
        inp = user_input.split('.')[0]
        key = user_input.split('.')[1]
        
        tickers = exchange[key]
        if inp in tickers:
            fname = "yfdata/" + user_input + ".json"
            d = utils.rd_d(fname)
            utils.plot(user_input, d)
    except:
        print("Name does not exist: ", user_input)

