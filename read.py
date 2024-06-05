#!/usr/bin/python3
import numpy as np
import pandas as pd
import itertools
from sklearn.linear_model import LinearRegression
import matplotlib.pyplot as plt

def split_data(start, end, fd):
    pd = {}
    pd["Date"] = fd["Date"][start:end]
    #pd["Open"] = fd["Open"][start:end]
    #pd["High"] = fd["High"][start:end]
    #pd["Low"] = fd["Low"][start:end]
    #pd["Close"] = fd["Close"][start:end]
    pd["Volume"] = fd["Volume"][start:end]
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

    #y_pred = model.predict(x)
    #plt.scatter(x, y, color='blue', label='Data points')
    #plt.plot(x, y_pred, color='red', label='Regression line')
    #plt.xlabel('x')
    #plt.ylabel('y')
    #plt.legend()
    #plt.show()

    return pd

df = pd.read_excel('aktier.xlsx', sheet_name = "boliden",skiprows=3)

np_avg = (np.array(df["Open"]) + np.array(df["High"]) + np.array(df["Low"]) + np.array(df["Close"])) / 4
df["Price"] = np_avg.tolist()
del np_avg
df["Trade"] = np.multiply(df["Volume"],df["Price"])
df["Acc_vol"] = list(itertools.accumulate(df["Volume"]))
df["Acc_trade"] = list(itertools.accumulate(df["Trade"]))
df["Avg_price"] = np.divide(df["Acc_trade"], df["Acc_vol"])
np_diff = np.array(df["Price"]) - np.array(df["Avg_price"])
np_invst = np_diff * np.array(df["Volume"])
df["Invest"] = list(itertools.accumulate(np_invst.tolist()))
del np_diff 
del np_invst

data = np.array(df["Invest"])
norm_data = (data - data.mean()) / data.std()
df["Norm_invest"] = norm_data.tolist()
del data
del norm_data

#for i, x in enumerate(df["Date"]):
#    df["Date"][i] = pd.to_datetime(x).date()

df1 = split_data(0,60,df)


#for val in df1["Avg_price"]:
#    print(val)

new_dict = {date_val: [k2_val, k3_val, k4_val] 
            for date_val, k2_val, k3_val, k4_val in zip(df["Date"], df["Price"], df["Invest"], df["Norm_invest"])}

#for key, val in new_dict.items():
#    print(key,val)
