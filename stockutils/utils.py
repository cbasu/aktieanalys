import numpy as np
import itertools
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime
import os
import sys
import json
import re
from sklearn.linear_model import LinearRegression

# Define a function to suppress stdout
class SuppressOutput:
    def __enter__(self):
        self._original_stdout = sys.stdout
        self._original_stderr = sys.stdout
        sys.stdout = open(os.devnull, 'w')
        sys.stderr = open(os.devnull, 'w')

    def __exit__(self, exc_type, exc_val, exc_tb):
        sys.stdout.close()
        sys.stderr.close()
        sys.stdout = self._original_stdout
        sys.stderr = self._original_stderr


def rd_d(f):
    try:
    # Read the JSON file into a dictionary
        with open(f, 'r') as json_file:
            d = json.load(json_file)
    except:
        d = {}

    return d

def group_contiguous_elements(lst):
    if not lst:
        return []

    list2d = []
    current_group = [lst[0]]

    for i in range(1, len(lst)):
        if lst[i] == lst[i - 1] + 1:
            current_group.append(lst[i])
        else:
            list2d.append(current_group)
            current_group = [lst[i]]
    
    list2d.append(current_group)  # Append the last group

    return list2d

def merge_ranges(xi, xr):

    merge_list = [False] * len(xi)
    for i in range(1, len(xi)):
        first = xi[i][0]
        prevlast = xi[i-1][len(xi[i-1])-1]
        for j in range(len(xr)):
            if prevlast < xr[j][0] < first:
                merge_list[i] = False
                break
            else:
                merge_list[i] = True
    
    lst = []
    sublst = [0]
    for i in range(1, len(merge_list)):
        if merge_list[i]:
            sublst.append(i)
        else:
            lst.append(sublst)
            sublst = [i]
    lst.append(sublst)

    merged_xi = []
    for sublist in lst:
        subx = []
        for i in sublist:
            subx += xi[i]
        merged_xi.append(subx)
    return merged_xi

def scan_data(data):
    DAYS=60
    ld = len(data["Date"])
    x = data["Date"][DAYS-1:ld] 
    y = data["Slope60"]
    ymax = max(y)
    ymin = min(y)
    
    # Calculate the range of the dataset
    data_range = ymax - ymin
    
    # Calculate the threshold based on the percentage of the range
    threshold = (5 / 100.0) * data_range   ## 2%
    xmin_i = []
    xmax_i = []
    for i in range(len(x)):
        valm = abs(y[i] - ymin)
        valM = abs(y[i] - ymax)
        #print(valm, valM, threshold)
        if valm <= threshold:
            xmin_i.append(i) 

        if valM <= threshold:
            xmax_i.append(i) 

    xmin_i = group_contiguous_elements(xmin_i)
    xmax_i = group_contiguous_elements(xmax_i)

    xmin_i = merge_ranges(xmin_i, xmax_i)
    xmax_i = merge_ranges(xmax_i, xmin_i)
    
    for indices in xmin_i:
        v = 0
        timestamp = 0
        for ind in indices:
            v += data["Adj Close"][ind+DAYS-1] 
            date = datetime.strptime(data["Date"][ind+DAYS-1], "%Y-%m-%d")
            timestamp += date.timestamp()

        v = v / len(indices)
        timestamp = timestamp / len(indices)
        date = datetime.fromtimestamp(timestamp)
        date = date.strftime("%Y-%m-%d")
        print (x[indices[0]], x[indices[len(indices)-1]], v, date)
    
    print("MAX")
    for xxx in xmax_i:
        print (xxx[0], xxx[len(xxx)-1], x[xxx[0]], x[xxx[len(xxx)-1]])
  

    



def is_close_to_max_min(data, threshold_percentage=5):
    # Calculate the minimum and maximum of the dataset
    min_value = min(data)
    max_value = max(data)
    value = data[len(data)-1]
    
    # Calculate the range of the dataset
    data_range = max_value - min_value
    
    # Calculate the threshold based on the percentage of the range
    threshold2 = (2 / 100.0) * data_range
    threshold5 = (5 / 100.0) * data_range
    threshold10 = (10 / 100.0) * data_range
    
    # Determine if the value is close to the minimum or maximum
    reco = "neutral"
    valm = abs(value - min_value)
    valM = abs(value - max_value)
    if valm <= threshold2:
        reco = "+++"
    elif valm <= threshold5:
        reco = "++"
    elif valm <= threshold10:
        reco = "+"
    if valM <= threshold2:
        reco = "---"
    elif valM <= threshold5:
        reco = "--"
    elif valM <= threshold10:
        reco = "-"
    return reco    


def append_yf2d(df, d):
    if df.empty:
        return d
    # Reset the index to move the date from the index to a column
    df.reset_index(inplace=True)
    # Convert Date column to string format
    df["Date"] = df["Date"].apply(lambda x: x.strftime('%Y-%m-%d'))
    if not d:
        d = df.to_dict(orient='list')
        return d
    l = len(d["Date"])
    ldate = datetime.strptime(d["Date"][l-1], "%Y-%m-%d")
    df_start = len(df["Date"])
    for i,dt in enumerate(df["Date"]):
        dt = datetime.strptime(dt, "%Y-%m-%d")
        if dt > ldate:
            df_start = i
            break
    if df_start >= len(df["Date"]):
        return d
    nd = {}
    for col in df.columns:
        nd[col] = df[col].iloc[df_start:].tolist()
    for key in nd:
        d[key] += nd[key]

    return d

def append_df2d(df, d):
    ld = datetime.strptime("2000-01-01", "%Y-%m-%d")
    if not d:
        d = df.to_dict(orient='list')
        return d

    nd = {}
    l = len(d["Date"])
    ldate = datetime.strptime(d["Date"][l-1], "%Y-%m-%d")
    start_ind = len(df["Date"])

    for i,dt in enumerate(df["Date"]):
        dt = datetime.strptime(dt, "%Y-%m-%d")
        if dt > ldate:
            start_ind = i
            break
    
    if start_ind >= len(df["Date"]):
        return d
    
    for col in df.columns:
        nd[col] = df[col].iloc[start_ind:].tolist()
    for key in nd:
        d[key] += nd[key]
    return d

def analyse(name, days, d):
    if days == 60:
        key = "Slope60"
    elif days == 120:
        key = "Slope120"
    elif days == 360:
        key = "Slope360"
    else:
        key = "Slope"
    d[key]=[]
    
    for i in range(len(d["Date"])):
        if i+days == len(d["Date"])+1:
            break
        d1 = slope(i,i+days,d)
        d[key].append(d1["Slope"])


def plot_i(name, ax, x, y1, y2, xname, y1name):
    ax.plot(x, y1)
    #ax.set_xlim(min(x), max(x)+4)
    # Hide x-axis values and labels
    ax.set_xticks([])
    ax.set_xlabel(xname)
    ax.set_ylabel(y1name)
    # Create the second y-axis sharing the same x-axis
    axr = ax.twinx()
    axr.plot(x, y2, 'g-', label='price')
    bdate = []
    sdate = []
    with open("txn.txt", 'r') as file:
        for line in file:
            if re.search(name, line):
                words = line.split()
                if words[2] == "BUY":
                    bdate.append(words[0])
                elif words[2] == "SELL":
                    sdate.append(words[0])
    yval = []
    xval = []
    if bdate:
        for dat in bdate:
            try:
                i = x.index(dat)
                yval.append(y2[i])
                xval.append(dat)
            except:
                pass
    if xval:
        axr.scatter(xval, yval, label='Graph 2', color='k', marker='+', s=100, linewidths=2)
    
    xval = []
    yval = []
    if sdate:
        for dat in sdate:
            try:
                i = x.index(dat)
                yval.append(y2[i])
                xval.append(dat)
            except:
                pass
    if xval:
        axr.scatter(xval, yval, label='Graph 3', color='r', marker='_', s=100, linewidths=2)

def plot(name, d):
    ld = len(d["Date"])
    l = len(d["Slope60"])
    fig, (ax1, ax2, ax3) = plt.subplots(1, 3, figsize=(15, 5))
    fig.suptitle(name, fontsize=12)
    x = d["Date"][60-1:ld] 
    y = d["Slope60"]
    y2 = d["Adj Close"][60-1:ld]
    # Set a single title for the entire figure
    plot_i(name, ax1, x, y, y2, "date", "slope60")

    l = len(d["Slope120"])
    x = d["Date"][120-1:ld] 
    y = d["Slope120"]
    y2 = d["Adj Close"][120-1:ld]
    plot_i(name, ax2, x, y, y2, "date", "slope120")

    l = len(d["Slope360"])
    x = d["Date"][360-1:ld] 
    y = d["Slope360"]
    y2 = d["Adj Close"][360-1:ld]
    plot_i(name, ax3, x, y, y2, "date", "slope360")
    # Adjust layout to prevent overlap
    plt.tight_layout()
    # Show the plots
    plt.show()

def slope(start, end, fd):
    pd = {}
    pd["Date"] = fd["Date"][start:end]
    pd["Volume"] = fd["Volume"][start:end]
    pd["Price"] = fd["Adj Close"][start:end]
    #avg = (np.array(fd["Open"][start:end]) + np.array(fd["High"][start:end]) + np.array(fd["Low"][start:end]) + np.array(fd["Close"][start:end])) / 4
    #pd["Price"] = avg.tolist()
    pd["Trade"] = np.multiply(pd["Volume"],pd["Price"])
    acc_vol = list(itertools.accumulate(pd["Volume"]))
    acc_trade = list(itertools.accumulate(pd["Trade"]))
    pd["Avg_price"] = np.divide(acc_trade, acc_vol)
    diff = np.array(pd["Price"]) - np.array(pd["Avg_price"])
    invst = diff * np.array(pd["Volume"])
    pd["Invest"] = list(itertools.accumulate(invst.tolist()))
    invst = np.array(pd["Invest"])
    norm_invst = (invst - invst.mean()) / invst.std()
    pd["Norm_invest"] = norm_invst.tolist()
    x = np.arange(start, end).reshape(-1, 1)  # Reshape for sklearn
    y = norm_invst
    # Create a linear regression model
    model = LinearRegression()
    # Fit the model
    model.fit(x, y)
    # Get the coefficients
    pd["Intercept"] = model.intercept_
    pd["Slope"] = model.coef_[0]

    return pd
