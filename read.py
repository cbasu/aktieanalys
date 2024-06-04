#!/usr/bin/python3
import numpy as np
import pandas as pd
import itertools
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

for i, x in enumerate(df["Date"]):
    df["Date"][i] = pd.to_datetime(x).date()

new_dict = {date_val: [k2_val, k3_val, k4_val] 
            for date_val, k2_val, k3_val, k4_val in zip(df["Date"], df["Price"], df["Invest"], df["Norm_invest"])}

for key, val in new_dict.items():
    print(key, val)
