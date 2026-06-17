import os
import re
import pandas as pd
import yfinance as yf
import streamlit as st

# Set up Streamlit page configuration
st.set_page_config(layout="wide", page_title="Portfolio Tracker")
st.title("📈 Portfolio Dashboard")

# Input files
csv_file = "txn.csv"
output_file = "transactions_cleaned.csv"
exclude_file = "exclude.txt"  

def read_transactions(file_path):
    df = pd.read_csv(
        file_path, sep=";", encoding="utf-8-sig", decimal=",", thousands=" ", parse_dates=["Datum"]
    )
    df.columns = df.columns.str.strip()
    
    # --- ADD THIS LINE TO FIX THE SPACES ---
    if "Värdepapper/beskrivning" in df.columns:
        df["Värdepapper/beskrivning"] = df["Värdepapper/beskrivning"].astype(str).str.strip()
    # ----------------------------------------
    
    numeric_columns = ["Antal", "Kurs", "Belopp", "Courtage", "Valutakurs", "Resultat"]
    for col in numeric_columns:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    return df

# =========================================================
# READ & MERGE DATABASE
# =========================================================
if os.path.exists(csv_file):
    new_df = read_transactions(csv_file)
    incoming_rows = len(new_df)
else:
    st.error(f"Could not find input file: {csv_file}")
    st.stop()

if os.path.exists(output_file):
    old_df = pd.read_csv(output_file, parse_dates=["Datum"])
    old_rows = len(old_df)
else:
    old_df = pd.DataFrame()
    old_rows = 0

unique_columns = ["Datum", "Konto", "Typ av transaktion", "Värdepapper/beskrivning", "Antal", "Kurs", "Belopp", "ISIN"]

if old_df.empty:
    combined_df = new_df.copy()
else:
    for col in unique_columns:
        if col not in old_df.columns: old_df[col] = ""
        if col not in new_df.columns: new_df[col] = ""
    old_keys = old_df[unique_columns].astype(str).agg("|".join, axis=1)
    new_keys = new_df[unique_columns].astype(str).agg("|".join, axis=1)
    old_key_set = set(old_keys)
    mask_new = ~new_keys.isin(old_key_set)
    new_only_df = new_df[mask_new]
    combined_df = pd.concat([old_df, new_only_df], ignore_index=True)

combined_df = combined_df.sort_values(by="Datum")
combined_df.to_csv(output_file, index=False)

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
st.sidebar.write(f"Incoming rows: `{incoming_rows}`")
st.sidebar.write(f"Existing stored rows: `{old_rows}`")
st.sidebar.write(f"Total rows in database: `{len(combined_df)}`")

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
portfolio_df_input = combined_df[combined_df["Typ av transaktion"].str.lower().isin(["köp", "sälj"])]
portfolio = {}

for _, row in portfolio_df_input.iterrows():
    stock = row["Värdepapper/beskrivning"]
    if pd.isna(stock) or str(stock).strip().lower() in exclude_stocks:
        continue

    transaction_type = str(row["Typ av transaktion"]).lower()
    qty = 0.0 if pd.isna(row["Antal"]) else float(row["Antal"])
    kurs = 0.0 if pd.isna(row["Kurs"]) else float(row["Kurs"])
    courtage = 0.0 if pd.isna(row["Courtage"]) else float(row["Courtage"])
    belopp = 0.0 if pd.isna(row["Belopp"]) else abs(float(row["Belopp"]))
    valutakurs = 1.0 if pd.isna(row["Valutakurs"]) or row["Valutakurs"] == 0 else float(row["Valutakurs"])
    currency = "SEK" if pd.isna(row["Instrumentvaluta"]) else row["Instrumentvaluta"]

    if stock not in portfolio:
        portfolio[stock] = {
            "V": 0.0, "D": 0.0, "N": 0.0, "B": 0.0, "B_local": 0.0,
            "sell_value": 0.0, "buy_value_total": 0.0, "buy_shares_total": 0.0,
            "currency": currency
        }
    
    p = portfolio[stock]
    execution_total = ((abs(qty) * float(kurs) * valutakurs + abs(courtage)) / valutakurs)
    execution_price_per_share = execution_total / abs(qty) if qty != 0 else 0
    cost_per_share_sek = belopp / abs(qty) if qty != 0 else 0

    today = pd.Timestamp.now().normalize()
    days_elapsed = (today - pd.to_datetime(row["Datum"]).normalize()).days
    if days_elapsed <= 0: days_elapsed = 1

    if "köp" in transaction_type:
        nb = abs(qty)
        bb = cost_per_share_sek
        bb_local = execution_price_per_share
        
        N2, B2, B2_local, D2, V2 = p["N"], p["B"], p["B_local"], p["D"], p["V"]
        
        V3 = V2 + (nb * bb)
        N3 = N2 + nb
        B3 = ((B2 * N2) + (nb * bb)) / N3 if N3 > 0 else 0
        B3_local = ((B2_local * N2) + (nb * bb_local)) / N3 if N3 > 0 else 0
        D3 = ((B2 * N2 * D2) + (nb * bb * days_elapsed)) / V3 if V3 > 0 else 0.0
            
        p["V"], p["N"], p["B"], p["B_local"], p["D"] = V3, N3, B3, B3_local, D3
        p["buy_value_total"] += belopp
        p["buy_shares_total"] += nb
        
    elif "sälj" in transaction_type:
        ns = abs(qty)
        p["sell_value"] += belopp
        N1, B1 = p["N"], p["B"]
        if N1 > 0:
            p["N"] = max(N1 - ns, 0.0)
            p["V"] = p["N"] * B1
        if p["N"] == 0.0:
            p["V"], p["D"] = 0.0, 0.0

# =========================================================
# GENERATE OUTPUT DATA
# =========================================================
current_rows = []
closed_rows = []

for stock, data in portfolio.items():
    remaining_shares = data["N"]
    current_buy_value_sek = data["V"]
    sold_shares = data["buy_shares_total"] - remaining_shares
    avg_sell_price = data["sell_value"] / sold_shares if sold_shares > 0 else 0
    avg_buy_total = data["buy_value_total"] / data["buy_shares_total"] if data["buy_shares_total"] > 0 else 0

    if remaining_shares > 0:
        yahoo_symbol = find_yahoo_symbol(stock)
        live_price = get_live_stock_price(yahoo_symbol)

        if live_price is None:
            live_price_str = st.sidebar.text_input(f"Live Price for {stock}:", value="0.0")
            try:
                live_price = float(live_price_str.replace(",", ".").strip())
                if live_price == 0.0: live_price = None
            except ValueError:
                live_price = None

        pct_increase = None
        avg_years = None 
        pct_incr_year = None  
        current_value_sek = None
        if live_price is not None:
            fx_rate = get_live_exchange_rate(data["currency"], "SEK")
            current_value_sek = remaining_shares * live_price * fx_rate
            if current_buy_value_sek > 0:
                pct_increase = ((current_value_sek - current_buy_value_sek) / current_buy_value_sek) * 100
                avg_years = data["D"] / 365.25
                if pct_increase is not None and avg_years > 0:
                    pct_incr_year = pct_increase / avg_years

        current_rows.append({
            "Stock": stock, "Currency": data["currency"], "Number": round(remaining_shares, 4),
            "Average Buy": round(data["B_local"], 2), "Current Price": round(live_price, 2) if live_price else None,
            "Current Value (SEK)": round(current_value_sek, 2) if current_value_sek else None,
            "Buy Value (SEK)": round(current_buy_value_sek, 2), 
            "% Increase": round(pct_increase, 2) if pct_increase else None,
            "Duration (m)": round(avg_years*12, 2) if avg_years is not None else None, 
            "% Incr/Year": round(pct_incr_year, 2) if pct_incr_year is not None else 0.0,
            "_yahoo_symbol": yahoo_symbol, "_raw_D": data["D"]
        })
    elif remaining_shares == 0 and sold_shares > 0:
        closed_rows.append({
            "Stock": stock, "Currency": data["currency"], "Bought Shares": round(data["buy_shares_total"], 4),
            "Sold Shares": round(sold_shares, 4), "Average Buy Total": round(avg_buy_total, 2),
            "Average Sell Price": round(avg_sell_price, 2), "Total Buy Value": round(data["buy_value_total"], 2), "Total Sell Value": round(data["sell_value"], 2)
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
    days_duration = row_item["_raw_D"] # Use the raw days from portfolio engine

    if not ysymb or buy_val <= 0 or num_shares <= 0:
        st.warning("⚠️ Insufficient data to calculate historical % increase.")
        return

    cost_basis_per_share = buy_val / num_shares
    
    # Calculate the exact start date based on duration
    start_date = pd.Timestamp.now() - pd.Timedelta(days=int(days_duration))

    with st.spinner(f"Fetching historical data for {ysymb}..."):
        # Fetch data starting from the acquisition date
        hist = yf.Ticker(ysymb).history(start=start_date)

    if hist.empty:
        st.error(f"❌ No historical price data found since {start_date.date()}.")
        return

    fx_rate = get_live_exchange_rate(row_item["Currency"], "SEK")
    
    # Calculate Pct Increase
    hist['Pct_Increase'] = (((hist['Close'] * fx_rate) - cost_basis_per_share) / cost_basis_per_share) * 100
    
    # Calculate "Days from Baseline" for the X-axis
    hist['Days_From_Baseline'] = (hist.index.tz_localize(None) - start_date.normalize()).days
    
    # Set index to Days_From_Baseline for the x-axis
    plot_df = hist.set_index('Days_From_Baseline')
    
    st.line_chart(plot_df['Pct_Increase'])

# =========================================================
# FIXED TAB NAVIGATION STRUCTURE
# =========================================================
tab1, tab2 = st.tabs(["💼 Current Holdings", "🔒 Closed Trades"])

with tab1:
    if selected_stock_trend:
        st.markdown("---")
        render_historical_chart(selected_stock_trend)
        if st.button("❌ Hide Chart Trend View", use_container_width=False):
            st.query_params.clear()
            st.rerun()
        st.markdown("---")

    st.subheader("Your Active Positions")
    if not current_portfolio_df.empty:
        col1, col2 = st.columns(2)
        with col1:
            currencies = ["All"] + list(current_portfolio_df["Currency"].unique())
            selected_curr = st.selectbox("Filter table by Currency:", currencies, key="curr_filter")
        with col2:
            available_stocks = current_portfolio_df["Stock"].unique()
            if selected_curr != "All":
                available_stocks = current_portfolio_df[current_portfolio_df["Currency"] == selected_curr]["Stock"].unique()
            selected_stocks = st.multiselect("Search / Filter Table Stocks:", sorted(available_stocks))
        
        filtered_df = current_portfolio_df.copy()
        if selected_curr != "All":
            filtered_df = filtered_df[filtered_df["Currency"] == selected_curr]
        if selected_stocks:
            filtered_df = filtered_df[filtered_df["Stock"].isin(selected_stocks)]
            
        valid_prices_df = filtered_df.dropna(subset=["Current Value (SEK)"])
        total_buy_sek = valid_prices_df["Buy Value (SEK)"].sum()
        total_current_sek = valid_prices_df["Current Value (SEK)"].sum()
        total_gain_sek = total_current_sek - total_buy_sek
        total_pct_gain = (total_gain_sek / total_buy_sek * 100) if total_buy_sek > 0 else 0.0

        st.markdown("### 📊 Portfolio Summary")
        m_col1, m_col2, m_col3, m_col4 = st.columns(4)
        m_col1.metric(label="Total Cost Basis (SEK)", value=f"{total_buy_sek:,.2f}".replace(",", " "))
        m_col2.metric(label="Total Current Value (SEK)", value=f"{total_current_sek:,.2f}".replace(",", " "))
        m_col3.metric(label="Total Gain / Loss (SEK)", value=f"{total_gain_sek:,.2f}".replace(",", " "), delta=f"{total_gain_sek:,.2f}".replace(",", " "))
        m_col4.metric(label="Total Return", value=f"{total_pct_gain:.2f}%", delta=f"{total_pct_gain:.2f}%")
        st.markdown("---")

        # 1. Clear up instructions - show only once
        st.info("💡 Click the 📈 View icon in the 'Trend' column to generate the chart for that stock.")

        # 1. Prepare data for the interactive editor
        # We drop the internal columns immediately so they never reach the editor
        display_df = filtered_df.drop(columns=['_yahoo_symbol', '_raw_D'], errors='ignore')

        # 2. Add a helper column for the link (keeping it separate from the data)
        display_df['Trend'] = display_df['Stock'].apply(lambda x: f"?view_trend={x}")
        display_df['Trend_Label'] = "📈 View"

        # 3. Render the interactive table
        st.data_editor(
            display_df,
            use_container_width=True,
            hide_index=True,
            disabled=True,
            column_order=["Stock", "Currency", "Number", "Average Buy", "Current Price", "Current Value (SEK)", "Buy Value (SEK)", "% Increase", "Duration (m)", "% Incr/Year", "Trend"],
            column_config={
                "Stock": st.column_config.TextColumn("Stock"),
                "Trend": st.column_config.LinkColumn(
                    "Trend",
                    help="Click to view growth trend chart",
                    display_text="Trend_Label", # This displays the icon instead of the URL
                ),
                "Trend_Label": None, # Hide the helper label column
                "% Increase": st.column_config.NumberColumn(
                    "% Increase",
                    format="%.2f%%"
                ),
                "% Incr/Year": st.column_config.NumberColumn(format="%.2f%%"),
                "Average Buy": st.column_config.NumberColumn(format="%.2f"),
                "Current Price": st.column_config.NumberColumn(format="%.2f"),
                "Current Value (SEK)": st.column_config.NumberColumn(format="%.2f"),
                "Buy Value (SEK)": st.column_config.NumberColumn(format="%.2f"),
            },
        )



        
    else:
        st.write("No open positions.")

with tab2:
    st.subheader("Your Historical Closed Positions")
    if not closed_portfolio_df.empty:
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
            
        st.dataframe(filtered_closed_df, use_container_width=True, hide_index=True)
    else:
        st.write("No closed positions.")
