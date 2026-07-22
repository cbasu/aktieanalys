import os
import re
import glob
import pandas as pd
import yfinance as yf
import streamlit as st

# Set up Streamlit page configuration
st.set_page_config(layout="wide", page_title="Portfolio Tracker")
st.title("📈 Portfolio Dashboard")

# Input configuration (reading year-wise files sequentially from 'txndata')
txndata_folder = "txndata"  # Folder containing txn-xx.csv files
exclude_file = "exclude.txt"  

def read_transactions(file_path):
    df = pd.read_csv(
        file_path, sep=";", encoding="utf-8-sig", decimal=",", thousands=" ", parse_dates=["Datum"]
    )
    df.columns = df.columns.str.strip()
    
    if "Värdepapper/beskrivning" in df.columns:
        df["Värdepapper/beskrivning"] = df["Värdepapper/beskrivning"].astype(str).str.strip()
    
    numeric_columns = ["Antal", "Kurs", "Belopp", "Courtage", "Valutakurs", "Resultat"]
    for col in numeric_columns:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    return df

# =========================================================
# READ & SEQUENTIALLY CONCATENATE YEAR-WISE DATA
# =========================================================
all_dfs = []
incoming_rows = 0

if os.path.exists(txndata_folder):
    # Find all transaction files matching txn-*.csv inside the folder
    pattern = os.path.join(txndata_folder, "txn-*.csv")
    txn_files = sorted(glob.glob(pattern))  # Sorted sequentially by filename (earliest year first)
    
    if txn_files:
        for file_path in txn_files:
            df_year = read_transactions(file_path)
            incoming_rows += len(df_year)
            all_dfs.append(df_year)
        combined_df = pd.concat(all_dfs, ignore_index=True) if all_dfs else pd.DataFrame()
    else:
        st.error(f"No transaction files matching 'txn-*.csv' found inside folder: {txndata_folder}")
        st.stop()
else:
    st.error(f"Could not find transaction data folder: {txndata_folder}")
    st.stop()

# =========================================================
# READ EXCLUSION LIST
# =========================================================
exclude_stocks = set()
if os.path.exists(exclude_file):
    with open(exclude_file, "r", encoding="utf-8") as f:
        exclude_stocks = {line.strip().lower() for line in f if line.strip()}

# =========================================================
# SIDEBAR COMPONENTS & REFRESH BUTTON
# =========================================================
st.sidebar.header("🔄 Market Data Control")

if st.sidebar.button("♻️ Reload Live Prices", use_container_width=True):
    st.cache_data.clear()  
    st.toast("Cache cleared! Fetching fresh live market prices...", icon="🔄")

st.sidebar.markdown("---")
st.sidebar.header("📊 Database Sync Status")
st.sidebar.write(f"Total loaded rows: `{incoming_rows}`")
st.sidebar.write(f"Total rows in processed frame: `{len(combined_df)}`")

# =========================================================
# STOCK SYMBOL MAPPING & UTILITIES (CACHED)
# =========================================================
symbol_map = {}
list_file = "list.txt"
if os.path.exists(list_file):
    with open(list_file, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line: continue
            match = re.match(r"^([A-Z]{1,2})\s+([^\s]+)\s+\[(.*)\]$", line)
            if not match: continue
            market, symbol, aliases = match.group(1), match.group(2), match.group(3)
            yahoo_symbol = symbol if market == "US" else f"{symbol}.{market}"
            alias_list = [a.strip().lower() for a in aliases.split(",")]
            alias_list.append(symbol.lower())
            for alias in alias_list:
                symbol_map[alias] = yahoo_symbol

def find_yahoo_symbol(stock_name):
    if pd.isna(stock_name): return None
    return symbol_map.get(str(stock_name).strip().lower(), None)

@st.cache_data(ttl=300)
def get_live_stock_price(yahoo_symbol):
    if not yahoo_symbol: return None
    try:
        ticker = yf.Ticker(yahoo_symbol)
        price = ticker.fast_info.get("lastPrice")
        if price is not None and str(yahoo_symbol).upper().endswith(".L"):
            price = price / 100.0
        return price
    except:
        return None

@st.cache_data(ttl=300)
def get_live_exchange_rate(from_currency, to_currency="SEK"):
    if pd.isna(from_currency) or from_currency.strip().upper() == to_currency:
        return 1.0
    pair = f"{from_currency.strip().upper()}{to_currency}=X"
    try:
        ticker = yf.Ticker(pair)
        rate = ticker.fast_info.get("lastPrice")
        if rate is not None: return float(rate)
    except:
        pass
    return 1.0

def fetch_weekly_historical_prices(yahoo_symbol, start_date):
    try:
        ticker = yf.Ticker(yahoo_symbol)
        hist = ticker.history(start=start_date, interval="1wk")
        if hist.empty:
            return None
        hist.index = hist.index.tz_localize(None)
        if str(yahoo_symbol).upper().endswith(".L"):
            hist["Close"] = hist["Close"] / 100.0
        return hist["Close"]
    except:
        return None

# =========================================================
# BUILD PORTFOLIO ENGINE (MOVING METHOD MODEL)
# =========================================================
portfolio_df_input = combined_df[combined_df["Typ av transaktion"].str.lower().isin(["köp", "sälj"])].sort_values("Datum")
portfolio = {} 
today = pd.Timestamp.now().normalize()

for _, row in portfolio_df_input.iterrows():
    stock = row["Värdepapper/beskrivning"]
    if pd.isna(stock) or str(stock).strip().lower() in exclude_stocks: continue

    transaction_type = str(row["Typ av transaktion"]).lower()
    n = abs(float(row["Antal"])) if not pd.isna(row["Antal"]) else 0.0
    b = float(row["Kurs"]) if not pd.isna(row["Kurs"]) else 0.0
    d = pd.to_datetime(row["Datum"]).normalize()
    t = max((today - d).days, 0)
    
    if stock not in portfolio:
        portfolio[stock] = {"N": 0.0, "W": 0.0, "T": 0.0, "B": 0.0, "BF": 0.0, "currency": row.get("Instrumentvaluta", "SEK")}
    
    p = portfolio[stock]

    if "köp" in transaction_type:
        # Get the historical exchange rate from the row, default to 1.0 if not found/NaN
        fx_val = float(row["Valutakurs"]) if ("Valutakurs" in row and not pd.isna(row["Valutakurs"])) else 1.0

        W_old, T_old, N_old = p["W"], p["T"], p["N"]
        N_new = N_old + n

        # Multiply by the exchange rate so W_new is stored in SEK
        W_new = W_old + (n * b * fx_val)

        T_new = ((W_old * T_old) + (n * b * t)) / W_new if W_new > 0 else t
        B_new = W_new / N_new if N_new > 0 else 0
        p["N"], p["W"], p["T"], p["B"] = N_new, W_new, T_new, B_new
    elif "sälj" in transaction_type:
        p["BF"] += n * (b - p["B"])
        p["W"] = p["W"] - (n * p["B"])
        p["N"] = max(p["N"] - n, 0.0)
        if p["N"] <= 0: p["W"], p["N"], p["T"], p["B"] = 0.0, 0.0, 0.0, 0.0


# =========================================================
# GENERATE OUTPUT DATA
# =========================================================
current_rows = []
closed_rows = []

for stock, data in portfolio.items():
    remaining_shares = data["N"]
    
    if remaining_shares > 0:
        yahoo_symbol = find_yahoo_symbol(stock)
        live_price = get_live_stock_price(yahoo_symbol)

        # Handle manual entry if live price is missing
        if live_price is None:
            live_price_str = st.sidebar.text_input(f"Live Price for {stock}:", value="0.0")
            try:
                live_price = float(live_price_str.replace(",", ".").strip())
                if live_price == 0.0: live_price = None
            except ValueError:
                live_price = None

        current_value_sek = None
        pct_increase = None
        pct_incr_year = 0.0  # Initialize variable
        
        if live_price is not None:
            fx_rate = get_live_exchange_rate(data["currency"], "SEK")
            current_value_sek = remaining_shares * live_price * fx_rate
            buy_val_sek = remaining_shares * data["B"]
            
            if buy_val_sek > 0:
                pct_increase = ((current_value_sek - buy_val_sek) / buy_val_sek) * 100
                years = data["T"] / 365.25
                if years > 0:
                    pct_incr_year = pct_increase / years

        current_rows.append({
            "Stock": stock, 
            "Currency": data["currency"], 
            "Number": round(remaining_shares, 4),
            "Average Buy": round(data["B"], 2), 
            "Current Price": round(live_price, 2) if live_price else None,
            "Current Value (SEK)": round(current_value_sek, 2) if current_value_sek is not None else None,
            "Buy Value (SEK)": round(remaining_shares * data["B"], 2), 
            "% Increase": round(pct_increase, 2) if pct_increase is not None else None,
            "% Incr/Year": round(pct_incr_year, 2),
            "Duration (m)": round(data["T"] / 30.44, 2), 
            "_yahoo_symbol": yahoo_symbol, 
            "_raw_D": data["T"]
        })
    
    # Capture Realized Profit
    if data["BF"] != 0:
        closed_rows.append({
            "Stock": stock, 
            "Currency": data["currency"], 
            "Total Buy Value": round(data["W"], 2), 
            "Total Sell Value": round(data["W"] + data["BF"], 2), 
            "Realized Gain/Loss": round(data["BF"], 2)
        })

current_portfolio_df = pd.DataFrame(current_rows)
closed_portfolio_df = pd.DataFrame(closed_rows)

# =========================================================
# URL QUERY PARAMETER HANDLING
# =========================================================
query_params = st.query_params
selected_stock_trend = query_params.get("view_trend", None)

time_unit = st.sidebar.radio("Choose Chart X-Axis Unit:", ["Months from Duration Baseline", "Days from Duration Baseline"], horizontal=False, key="global_chart_time_unit")

def render_historical_chart(stock_name):
    st.markdown(f"### 📊 Historical % Increase Trend: **{stock_name}**")
    matched_records = current_portfolio_df[current_portfolio_df["Stock"] == stock_name]
    
    if matched_records.empty:
        st.error(f"Data error: No portfolio records found for {stock_name}.")
        return

    row_item = matched_records.iloc[0]
    ysymb = row_item["_yahoo_symbol"]
    buy_val = row_item["Buy Value (SEK)"]
    num_shares = row_item["Number"]
    days_duration = row_item["_raw_D"]

    if not ysymb or buy_val <= 0 or num_shares <= 0:
        st.warning("⚠️ Insufficient data to calculate historical % increase.")
        return

    cost_basis_per_share = buy_val / num_shares
    start_date = pd.Timestamp.now() - pd.Timedelta(days=int(days_duration))

    with st.spinner(f"Fetching historical data for {ysymb}..."):
        hist = yf.Ticker(ysymb).history(start=start_date)

    if hist.empty:
        st.error(f"❌ No historical price data found since {start_date.date()}.")
        return

    fx_rate = get_live_exchange_rate(row_item["Currency"], "SEK")
    
    hist['Pct_Increase'] = (((hist['Close'] * fx_rate) - cost_basis_per_share) / cost_basis_per_share) * 100
    hist['Days_From_Baseline'] = (hist.index.tz_localize(None) - start_date.normalize()).days
    
    plot_df = hist.set_index('Days_From_Baseline')
    st.line_chart(plot_df['Pct_Increase'])

# =========================================================
# FIXED TAB NAVIGATION STRUCTURE
# =========================================================
tab1, tab2 = st.tabs(["💼 Current Holdings", "🔒 Closed Trades"])

with tab1:
    st.subheader("Your Active Positions")
    
    if not current_portfolio_df.empty:
        all_stocks_list = sorted(current_portfolio_df["Stock"].unique())
        curr_options = ["All"] + list(current_portfolio_df["Currency"].unique())

        f_col1, f_col2 = st.columns([3, 1])
        with f_col1:
            stock_search = st.multiselect("🔍 Filter by Stock Name", all_stocks_list, key="filter_stock")
        with f_col2:
            curr_search = st.selectbox("💱 Currency", curr_options, key="filter_curr")

        filtered_df = current_portfolio_df.copy()
        if stock_search:
            filtered_df = filtered_df[filtered_df["Stock"].isin(stock_search)]
        if curr_search != "All":
            filtered_df = filtered_df[filtered_df["Currency"] == curr_search]
            
        valid_prices_df = filtered_df.dropna(subset=["Current Value (SEK)"])
        total_buy_sek = valid_prices_df["Buy Value (SEK)"].sum()
        total_current_sek = valid_prices_df["Current Value (SEK)"].sum()
        total_gain_sek = total_current_sek - total_buy_sek
        total_pct_gain = (total_gain_sek / total_buy_sek * 100) if total_buy_sek > 0 else 0.0

        st.markdown("### 📊 Portfolio Summary")
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Cost Basis (SEK)", f"{total_buy_sek:,.0f}".replace(",", " "))
        m2.metric("Current Value (SEK)", f"{total_current_sek:,.0f}".replace(",", " "))
        m3.metric("Gain/Loss (SEK)", f"{total_gain_sek:,.0f}".replace(",", " "), delta=f"{total_gain_sek:,.0f}".replace(",", " "))
        m4.metric("Total Return", f"{total_pct_gain:.2f}%", delta=f"{total_pct_gain:.2f}%")
        
        st.markdown("---")

        display_df = filtered_df.drop(columns=['_yahoo_symbol', '_raw_D'], errors='ignore')
        st.dataframe(display_df, use_container_width=True, hide_index=True)

        st.markdown("### 📈 View Trend Chart")
        
        def update_view():
            st.query_params["view_trend"] = st.session_state.trend_selector
            
        st.selectbox(
            "Select a stock to view its trend:", 
            [""] + list(display_df["Stock"].unique()),
            key="trend_selector",
            on_change=update_view
        )

        if selected_stock_trend:
            st.markdown("---")
            render_historical_chart(selected_stock_trend)
            if st.button("❌ Hide Chart Trend View", use_container_width=False):
                st.query_params.clear()
                st.rerun()
            st.markdown("---")
    else:
        st.write("No open positions.")


with tab2:
    st.subheader("Your Historical Closed Positions")
    if not closed_portfolio_df.empty:
        closed_portfolio_df["Realized Gain/Loss"] = closed_portfolio_df["Total Sell Value"] - closed_portfolio_df["Total Buy Value"]
        closed_portfolio_df["% Realized Gain"] = (closed_portfolio_df["Realized Gain/Loss"] / closed_portfolio_df["Total Buy Value"]) * 100
        
        total_realized_gain = closed_portfolio_df["Realized Gain/Loss"].sum()
        total_invested = closed_portfolio_df["Total Buy Value"].sum()
        total_realized_pct = (total_realized_gain / total_invested * 100) if total_invested > 0 else 0.0

        st.markdown("### 📊 Realized Summary")
        m1, m2, m3 = st.columns(3)
        m1.metric("Total Invested (SEK)", f"{total_invested:,.0f}".replace(",", " "))
        m2.metric("Total Realized Gain/Loss (SEK)", f"{total_realized_gain:,.0f}".replace(",", " "), delta=f"{total_realized_gain:,.0f}".replace(",", " "))
        m3.metric("Total Realized Return", f"{total_realized_pct:.2f}%", delta=f"{total_realized_pct:.2f}%")
        
        st.markdown("---")
        
        col1_c, col2_c = st.columns(2)
        with col1_c:
            currencies_c = ["All"] + list(closed_portfolio_df["Currency"].unique())
            selected_curr_c = st.selectbox("Filter closed by Currency:", currencies_c, key="curr_filter_closed")
        with col2_c:
            available_stocks_c = closed_portfolio_df["Stock"].unique()
            if selected_curr_c != "All":
                available_stocks_c = closed_portfolio_df[closed_portfolio_df["Currency"] == selected_curr_c]["Stock"].unique()
            selected_stocks_c = st.multiselect("Search / Select Closed Stocks:", sorted(available_stocks_c), key="stock_filter_closed")
            
        filtered_closed_df = closed_portfolio_df.copy()
        if selected_curr_c != "All":
            filtered_closed_df = filtered_closed_df[filtered_closed_df["Currency"] == selected_curr_c]
        if selected_stocks_c:
            filtered_closed_df = filtered_closed_df[filtered_closed_df["Stock"].isin(selected_stocks_c)]
            
        st.dataframe(
            filtered_closed_df.style.format({
                "Total Buy Value": "{:,.2f}",
                "Total Sell Value": "{:,.2f}",
                "Realized Gain/Loss": "{:,.2f}",
                "% Realized Gain": "{:.2f}%"
            }), 
            use_container_width=True, 
            hide_index=True
        )
    else:
        st.write("No closed positions.")
