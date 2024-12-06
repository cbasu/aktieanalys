#!/usr/bin/env python3
#####################!/usr/bin/python3
import json
from datetime import datetime, timedelta
import yfinance as yf
import readline
import rlcompleter
from stockutils import utils
from tabulate import tabulate
import re

begin = "2021-01-01"
today = datetime.today().date()


exchange = {}

# This function will be called to complete the input
def completer(text, state):
    options = [i for i in commands if i.startswith(text)]
    if state < len(options):
        return options[state]
    else:
        return None

# Open the list and read line by line
with open('list.txt', 'r') as file:
    current_key = None
    for line in file:
        # Strip leading/trailing whitespace
        line = line.strip()
        # Replace comma followed by one or more spaces with a comma
        line = re.sub(r',\s+', ',', line)
        
        # Skip empty lines
        if not line:
            continue
        
        # Split the line into parts
        parts = line.split(' ', 2)  # Split only on the first two spaces
        
        key = parts[0]
        sym = parts[1]
        # Remove the square brackets and split the third part into a list
        names = parts[2].strip('[]').split(',')
        
        # Check if the current line contains a new key
        if key != current_key:
            current_key = key
            if current_key not in exchange:
                exchange[current_key] = {'symbol': [], 'name': []}
        
        # Append the name and val to the respective lists
        exchange[current_key]['symbol'].append(sym)
        exchange[current_key]['name'].append(names)

user_input = input("Run analysis (y/n): ")
if user_input == "y":
    
    #for stock in tickers:
    for key in exchange:
        tickers = exchange[key]["symbol"]
        for stock in tickers:
            start = begin
            end = today
            if key == "US":
                nam = stock
                file = "yfdata/"+nam+"."+key+".json"
            else:
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
            if key == "US":
                nam = stock+"."+key
            file = "yfdata/"+nam+".json"

            # Write the dictionary to a JSON file
            with open(file, 'w') as json_file:
                json.dump(d, json_file, indent=4)

table = []
#for stock in tickers:
for key in exchange:
    tickers = exchange[key]["symbol"] 
    for i, stock in enumerate(tickers):
        sname = exchange[key]["name"][i][0]
        nam = stock+"."+key
        fname = "yfdata/" + nam + ".json"
        d = utils.rd_d(fname)
        reco = utils.is_close_to_max_min(d["Slope60"])
        if reco == "neutral":
            continue
        table.append([sname, reco])

# Sort data by the 2nd column (index 1)
table = sorted(table, key=lambda x: x[1])
headers = ["Name", "Rec60"]
# Print the data in tabular format
print(tabulate(table, headers=headers, tablefmt="plain"))

commands=["exit"]
#for name in tickers:
for key in exchange:
    tickers = exchange[key]["symbol"] 
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
        
        tickers = exchange[key]["symbol"] 

        if inp in tickers:
            i = tickers.index(inp)
            print(exchange[key]["name"][i][0])
            fname = "yfdata/" + user_input + ".json"
            d = utils.rd_d(fname)
            #utils.scan_data(d)
            utils.plot(user_input, d)
    except Exception as e:
    # Print the error message
        print(f"An error occurred: {e}")
    #except:
    #    print("Name does not exist: ", user_input)

