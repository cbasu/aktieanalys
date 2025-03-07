import yfinance as yf
import json
import os
import re
from datetime import datetime

exchange = {}

def get_stock_news(ticker_symbol):
    ticker = yf.Ticker(ticker_symbol)
    return ticker.news

def load_existing_data(filename):
    try:
        with open(filename, 'r') as file:
            return json.load(file)
    except FileNotFoundError:
        return []

def save_news_to_file(news_list, filename):
    with open(filename, 'w') as file:
        json.dump(news_list, file, indent=4)

def process_stock_news(ticker_symbol, directory="yfnews", file_extension="news.json"):
    #print(f"Processing news for {ticker_symbol}...")
    
    # Ensure the directory exists
    os.makedirs(directory, exist_ok=True)
    
    filename = os.path.join(directory, f"{ticker_symbol}_{file_extension}")
    
    # Load existing data
    existing_data = load_existing_data(filename)
    existing_ids = {item['id'] for item in existing_data}
    
    # Fetch new news
    all_news = get_stock_news(ticker_symbol)
    
    # Filter out existing news
    new_items = [item for item in all_news if item['id'] not in existing_ids]
    
    if new_items:
        # Append new items to existing data
        updated_data = new_items + existing_data
        save_news_to_file(updated_data, filename)
        #print(f"Added {len(new_items)} new news items for {ticker_symbol}")
    #else:
        #print(f"No new news items for {ticker_symbol}")
    
    return len(new_items)

def display_news(stock_symbol, directory="yfnews", file_extension="news.json"):
    filename = os.path.join(directory, f"{stock_symbol}_{file_extension}")
    news_data = load_existing_data(filename)
    
    if not news_data:
        print(f"No news found for {stock_symbol}")
        return
    
    print(f"\nTotal news items for {stock_symbol}: {len(news_data)}")
    
    while True:
        try:
            news_no = int(input(f"Enter news number (1-{len(news_data)}) to view, or 0 to go back: "))
            if news_no == 0:
                break
            if 1 <= news_no <= len(news_data):
                item = news_data[news_no - 1]
                content = item.get('content', {})
                print("\n" + "="*50)
                print(f"Title: {content.get('title', 'N/A')}")
                print(f"Published: {content.get('pubDate', 'N/A')}")
                print(f"Summary: {content.get('summary', 'N/A')}")
                print(f"URL: {content.get('canonicalUrl', {}).get('url', 'N/A')}")
                print("="*50 + "\n")
            else:
                print("Invalid news number. Please try again.")
        except ValueError:
            print("Invalid input. Please enter a number.")


#def display_news(stock_symbol, directory="yfnews", file_extension="news.json"):
#    filename = os.path.join(directory, f"{stock_symbol}_{file_extension}")
#    news_data = load_existing_data(filename)
#
#    if not news_data:
#        print(f"No news found for {stock_symbol}")
#        return
#
#    print(f"\nDisplaying news for {stock_symbol}:")
#    for item in news_data:
#        content = item.get('content', {})
#        print(f"Title: {content.get('title', 'N/A')}")
#        print(f"Published: {content.get('pubDate', 'N/A')}")
#        print(f"Summary: {content.get('summary', 'N/A')[:100]}...")  # Display first 100 characters of summary
#        print("---")
#
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

stock_list = [ ]
for key in exchange:
    tickers = exchange[key]["symbol"]
    for stock in tickers:
        if key == "US":
            nam = stock
        else:
            nam = stock+"."+key
        stock_list.append(nam)

user_input = input("Get news (y/n): ")
if user_input == "y":
    
    for stock in stock_list:
        new_items_count = process_stock_news(stock)
        print(f"Total new items for {stock}: {new_items_count}")
        #print("---")

while True:
    stock_symbol = input("\nEnter name (or 'quit' to exit): ").upper()
    if stock_symbol == 'QUIT':
        break
    if stock_symbol in stock_list:
        display_news(stock_symbol)
    else:
        print(f"No data available for {stock_symbol}")

#if __name__ == "__main__":
#    main()
#
