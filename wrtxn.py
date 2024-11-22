#!/usr/bin/env python3
import pandas as pd
import re

exchange = {}

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


# Read old txn
file_path = 'yfdata/data.csv'
try:
    #df_old = pd.read_csv(file_path, sep=' ', header=None, names=['Datum', 'Typ av transaktion', 'Värdepapper/beskrivning'])
    df_old = pd.read_csv(file_path)
except FileNotFoundError:
    df_old = pd.DataFrame()

# Read the CSV file
file_path = 'txn.csv'
df = pd.read_csv(file_path, sep=';')

# Filter the DataFrame with multiple conditions
df = df[(df['Typ av transaktion'].str.contains('Köp')) | (df['Typ av transaktion'].str.contains('Sälj'))]

df['Typ av transaktion'] = df['Typ av transaktion'].replace('Köp', 'BUY')
df['Typ av transaktion'] = df['Typ av transaktion'].replace('Sälj', 'SELL')
#df = df.drop(columns=['Valuta', 'Konto', 'Courtage', 'Valuta', 'ISIN', 'Resultat', 'Belopp', 'Antal', 'Kurs'])
df = df.drop(columns=['Valutakurs', 'Konto', 'Courtage (SEK)', 'ISIN', 'Resultat', 'Belopp', 'Antal', 'Kurs'])

df = pd.concat([df_old, df], axis=0)
df = df.drop_duplicates()

# Convert the 'Date' column to datetime format
df['Datum'] = pd.to_datetime(df['Datum'])
# Sort the DataFrame by the 'Datum' column in ascending order
df = df.sort_values(by='Datum')
start_date = pd.to_datetime('2024-06-01')
# Filter the DataFrame
df = df[df['Datum'] >= start_date]
df['Datum'] = df['Datum'].dt.strftime('%Y-%m-%d')

df.to_csv('yfdata/data.csv', index=False)
# Display the filtered DataFrame

output_file = "txn.txt"
with open(output_file, 'w') as file:
    for index, row in df.iterrows():
        found = False
        for key in exchange:
            for ind, names in enumerate(exchange[key]['name']):
                if row['Värdepapper/beskrivning'] in names:
                    nm = exchange[key]['symbol'][ind] + "." + key
                    #file.write(f"{row['Datum']}", nm, row['Typ av transaktion'])
                    print(f"{row['Datum']}", nm, row['Typ av transaktion'], file=file)
                    found = True
                    break  # Breaks the inner loop
            if found:
                break  # Breaks the outer loop
        if not found:
            print(row['Värdepapper/beskrivning']," is not found in the list.txt file")

#print(df)

