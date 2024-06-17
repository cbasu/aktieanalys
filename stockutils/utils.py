import numpy as np
import itertools
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime
import os
import sys
import json
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
    
    #for i in range(len(d["Date"])-days+2):
    for i in range(len(d["Date"])):
        if i+days == len(d["Date"]):
            break
        d1 = split_data(name, i,i+days-1,d)
        d[key].append(d1["Slope"])

def plot(name, l, yi):
    x = np.arange(0, l).reshape(-1, 1)  # Reshape for sklearn
    y = np.array(yi)
    plt.scatter(x, y, color='blue', label='Data points')
    plt.title(name)
    plt.xlabel('date')
    plt.ylabel('slope')
    plt.legend()
    plt.show()

def plot1(name, d):
    l = len(d["Slope60"])
    ld = len(d["Date"])
    x = d["Date"][60-1:ld-1] 
    y = d["Slope60"]
    y2 = d["Close"][60-1:ld-1]
    fig, (ax1, ax2, ax3) = plt.subplots(1, 3, figsize=(15, 5))
    # Set a single title for the entire figure
    fig.suptitle('Overall Title for All Subplots', fontsize=16)
    ax1.plot(x, y)
    # Hide x-axis values and labels
    ax1.set_xticks([])
    ax1.set_xlabel('date')
    ax1.set_ylabel('Slope60')
# Create the second y-axis sharing the same x-axis
    ax1r = ax1.twinx()
    ax1r.plot(x, y2, 'g-', label='y2')  # 'b-' means blue solid line
    
    l = len(d["Slope120"])
    x = [i for i in range(l)]
    y = d["Slope120"]
    ax2.plot(x, y)
    ax2.set_title(name)
    ax2.set_xlabel('date')
    ax2.set_ylabel('Slope120')

    l = len(d["Slope360"])
    x = [i for i in range(l)]
    y = d["Slope360"]
    ax3.plot(x, y)
    ax3.set_title(name)
    ax3.set_xlabel('date')
    ax3.set_ylabel('Slope360')
# Adjust layout to prevent overlap
    plt.tight_layout()

# Show the plots
    plt.show()


def split_data(name, start, end, fd, plot="n"):
    pd = {}
    pd["Date"] = fd["Date"][start:end]
    pd["Volume"] = fd["Volume"][start:end]
    #avg = np.array(fd["Close"][start:end])
    avg = (np.array(fd["Open"][start:end]) + np.array(fd["High"][start:end]) + np.array(fd["Low"][start:end]) + np.array(fd["Close"][start:end])) / 4
    pd["Price"] = avg.tolist()
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
    
    if plot == "yi":
        y_pred = model.predict(x)
        plt.scatter(x, y, color='blue', label='Data points')
        plt.plot(x, y_pred, color='red', label='Regression line')
        plt.title(name)
        plt.xlabel('x')
        plt.ylabel('y')
        plt.legend()
        plt.show()

    return pd
