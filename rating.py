import yfinance as yf
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- Piotroski F-Score Calculation (Full 9 Criteria) ---
def calculate_piotroski_f_score(info, prev_info=None):
    """
    Calculate Piotroski F-Score (0-9) using current and previous year's data.
    prev_info: dictionary with previous year's financials (if available).
    """
    score = 0
    explanations = []

    # 1. Positive Net Income
    if info.get('netIncomeToCommon', 0) > 0:
        score += 1
        explanations.append("Positive net income")
    else:
        explanations.append("Negative net income")

    # 2. Positive Operating Cash Flow
    if info.get('operatingCashflow', 0) > 0:
        score += 1
        explanations.append("Positive operating cash flow")
    else:
        explanations.append("Negative operating cash flow")

    # 3. Higher Return on Assets (ROA) than previous year
    try:
        roa = info.get('netIncomeToCommon', 0) / info.get('totalAssets', 1)
        prev_roa = prev_info.get('netIncomeToCommon', 0) / prev_info.get('totalAssets', 1) if prev_info else None
        if prev_roa is not None and roa > prev_roa:
            score += 1
            explanations.append("ROA improved")
        elif prev_roa is not None:
            explanations.append("ROA declined")
        else:
            explanations.append("ROA trend unavailable")
    except Exception:
        explanations.append("ROA calculation error")

    # 4. Operating Cash Flow > Net Income
    if info.get('operatingCashflow', 0) > info.get('netIncomeToCommon', 0):
        score += 1
        explanations.append("Operating cash flow > net income")
    else:
        explanations.append("Operating cash flow <= net income")

    # 5. Lower Leverage (long-term debt/assets) than previous year
    try:
        leverage = info.get('longTermDebt', 0) / info.get('totalAssets', 1)
        prev_leverage = prev_info.get('longTermDebt', 0) / prev_info.get('totalAssets', 1) if prev_info else None
        if prev_leverage is not None and leverage < prev_leverage:
            score += 1
            explanations.append("Leverage decreased")
        elif prev_leverage is not None:
            explanations.append("Leverage increased")
        else:
            explanations.append("Leverage trend unavailable")
    except Exception:
        explanations.append("Leverage calculation error")

    # 6. Higher Current Ratio than previous year
    try:
        cr = info.get('currentRatio', 0)
        prev_cr = prev_info.get('currentRatio', 0) if prev_info else None
        if prev_cr is not None and cr > prev_cr:
            score += 1
            explanations.append("Current ratio improved")
        elif prev_cr is not None:
            explanations.append("Current ratio declined")
        else:
            explanations.append("Current ratio trend unavailable")
    except Exception:
        explanations.append("Current ratio calculation error")

    # 7. No new shares issued (compare shares outstanding)
    shares = info.get('sharesOutstanding', 0)
    prev_shares = prev_info.get('sharesOutstanding', 0) if prev_info else None
    if prev_shares is not None and shares <= prev_shares:
        score += 1
        explanations.append("No new shares issued")
    elif prev_shares is not None:
        explanations.append("New shares issued")
    else:
        explanations.append("Share count trend unavailable")

    # 8. Higher Gross Margin than previous year
    gm = info.get('grossMargins', 0)
    prev_gm = prev_info.get('grossMargins', 0) if prev_info else None
    if prev_gm is not None and gm > prev_gm:
        score += 1
        explanations.append("Gross margin improved")
    elif prev_gm is not None:
        explanations.append("Gross margin declined")
    else:
        explanations.append("Gross margin trend unavailable")

    # 9. Higher Asset Turnover than previous year
    at = info.get('assetTurnover', 0)
    prev_at = prev_info.get('assetTurnover', 0) if prev_info else None
    if prev_at is not None and at > prev_at:
        score += 1
        explanations.append("Asset turnover improved")
    elif prev_at is not None:
        explanations.append("Asset turnover declined")
    else:
        explanations.append("Asset turnover trend unavailable")

    return score, explanations

# --- Other Risk Metric Calculations ---

def calculate_altman_z(info):
    try:
        total_assets = info.get('totalAssets', 0)
        total_current_assets = info.get('totalCurrentAssets', 0)
        total_current_liabilities = info.get('totalCurrentLiabilities', 0)
        retained_earnings = info.get('retainedEarnings', 0)
        ebit = info.get('ebit', 0)
        market_cap = info.get('marketCap', 0)
        total_liab = info.get('totalLiab', 0)
        total_revenue = info.get('totalRevenue', 0)
        if total_assets == 0 or total_liab == 0:
            return None, "Insufficient data for Altman Z-score."
        A = (total_current_assets - total_current_liabilities) / total_assets
        B = retained_earnings / total_assets
        C = ebit / total_assets
        D = market_cap / total_liab
        E = total_revenue / total_assets
        z = 1.2 * A + 1.4 * B + 3.3 * C + 0.6 * D + 1.0 * E
        if z > 2.99:
            zone = "Safe zone (low bankruptcy risk)"
        elif z > 1.81:
            zone = "Grey zone (some risk)"
        else:
            zone = "Distress zone (high bankruptcy risk)"
        return z, zone
    except Exception as e:
        return None, f"Error in Z-score calculation: {e}"

def calculate_interest_coverage(info):
    ebit = info.get('ebit', 0)
    interest_expense = info.get('interestExpense', 0)
    if interest_expense:
        return ebit / abs(interest_expense)
    else:
        return None

def calculate_debt_to_capital(info):
    total_debt = info.get('totalDebt', None)
    total_equity = info.get('totalStockholderEquity', None)
    if total_debt is not None and total_equity is not None and (total_debt + total_equity) != 0:
        return total_debt / (total_debt + total_equity)
    else:
        return None

# --- Scoring Functions ---

def score_profitability(info):
    revenue_growth = info.get("revenueGrowth", 0) * 100
    profit_margin = info.get("profitMargins", 0) * 100
    roe = info.get("returnOnEquity", 0) * 100
    gross_profit_margin = (info.get('grossProfits', 0) / info.get('totalRevenue', 1)) * 100 if info.get('totalRevenue') else 0
    operating_margin = info.get('operatingMargins', 0) * 100
    payout_ratio = info.get('payoutRatio', 0) * 100
    growth_score = min(7, (revenue_growth / 3 + profit_margin / 3 + roe / 10 + gross_profit_margin/10 + operating_margin/10))
    details = {
        "revenue_growth": revenue_growth,
        "profit_margin": profit_margin,
        "roe": roe,
        "gross_profit_margin": gross_profit_margin,
        "operating_margin": operating_margin,
        "payout_ratio": payout_ratio,
        "score": growth_score
    }
    return growth_score, details

def score_valuation(info, adj):
    pe_ratio = info.get("trailingPE", 100) * adj["pe_factor"]
    ps_ratio = info.get("priceToSalesTrailing12Months", 10)
    pb_ratio = info.get("priceToBook", 10)
    eps = info.get("trailingEps", 0)
    forward_pe = info.get("forwardPE", 100) * adj["pe_factor"]
    free_cashflow = info.get("freeCashflow", 0)
    peg_ratio = info.get("pegRatio", 1)
    valuation_score = max(4, 10 - (pe_ratio / 20 + ps_ratio / 10 + pb_ratio/15 + (5/eps if eps != 0 else 0) + forward_pe/20 + peg_ratio/10))
    details = {
        "pe_ratio": pe_ratio,
        "ps_ratio": ps_ratio,
        "pb_ratio": pb_ratio,
        "eps": eps,
        "forward_pe": forward_pe,
        "free_cashflow": free_cashflow,
        "peg_ratio": peg_ratio,
        "score": valuation_score
    }
    return valuation_score, details

def score_financial_strength(info, adj, prev_info=None):
    # --- Classic metrics ---
    debt_to_equity = info.get("debtToEquity", 100) * adj["debt_factor"]
    quick_ratio = info.get("quickRatio", 1)
    current_ratio = info.get("currentRatio", 1)
    # --- Solvency metrics ---
    total_liab = info.get("totalLiab", 0)
    total_debt = info.get("totalDebt", total_liab)
    cashflow_from_ops = info.get("operatingCashflow", 0)
    cash_flow_to_debt = (cashflow_from_ops / total_debt) if total_debt else None
    # --- Risk metrics ---
    z_score, z_zone = calculate_altman_z(info)
    interest_coverage = calculate_interest_coverage(info)
    debt_to_capital = calculate_debt_to_capital(info)
    piotroski_score, piotroski_expl = calculate_piotroski_f_score(info, prev_info)
    # --- Scoring ---
    score = 10
    # Debt to Equity (lower is better)
    score -= min(debt_to_equity / 20, 3)
    # Quick Ratio (higher is better)
    score += min((quick_ratio - 1) * 2, 2)
    # Current Ratio (higher is better)
    score += min((current_ratio - 1.5) * 2, 2)
    # Cash Flow to Debt (higher is better)
    if cash_flow_to_debt is not None:
        if cash_flow_to_debt >= 1.5:
            score += 2
        elif cash_flow_to_debt >= 1:
            score += 1
        elif cash_flow_to_debt >= 0.5:
            score -= 1
        else:
            score -= 2
    # Altman Z-score (higher is better)
    if z_score is not None:
        if z_score > 2.99:
            score += 1
        elif z_score > 1.81:
            score += 0
        else:
            score -= 2
    # Interest Coverage (higher is better)
    if interest_coverage is not None:
        if interest_coverage > 3:
            score += 1
        elif interest_coverage > 1.5:
            score += 0
        elif interest_coverage > 1:
            score -= 1
        else:
            score -= 2
    # Debt to Capital (lower is better)
    if debt_to_capital is not None:
        if debt_to_capital < 0.4:
            score += 1
        elif debt_to_capital < 0.6:
            score += 0
        elif debt_to_capital < 0.8:
            score -= 1
        else:
            score -= 2
    # Piotroski F-Score (higher is better, now out of 9)
    if piotroski_score >= 7:
        score += 2
    elif piotroski_score >= 5:
        score += 1
    elif piotroski_score >= 3:
        score -= 1
    else:
        score -= 2
    score = max(1, min(10, score))
    details = {
        "debt_to_equity": debt_to_equity,
        "quick_ratio": quick_ratio,
        "current_ratio": current_ratio,
        "cash_flow_to_debt": cash_flow_to_debt,
        "z_score": z_score,
        "z_zone": z_zone,
        "interest_coverage": interest_coverage,
        "debt_to_capital": debt_to_capital,
        "piotroski_score": piotroski_score,
        "piotroski_explanations": piotroski_expl,
        "score": score
    }
    return score, details

def score_market_position(info):
    market_cap = info.get("marketCap")
    recommendation_key = info.get("recommendationKey")
    market_position_score = 5
    if market_cap:
        if market_cap > 100e9:
            market_position_score += 3
        elif market_cap > 10e9:
            market_position_score += 2
        else:
            market_position_score += 1
    if recommendation_key == "buy":
        market_position_score += 2
    elif recommendation_key == "strongBuy":
        market_position_score += 3
    elif recommendation_key == "underperform":
        market_position_score -= 2
    elif recommendation_key == "sell":
        market_position_score -= 3
    market_position_score = max(1, market_position_score)
    details = {
        "market_cap": market_cap,
        "recommendation_key": recommendation_key,
        "score": market_position_score
    }
    return market_position_score, details

def score_risk_volatility(info, adj):
    beta = info.get("beta", 1.2) * adj["beta_factor"]
    risk_score = max(5, 10 - beta * 4)
    details = {
        "beta": beta,
        "score": risk_score
    }
    return risk_score, details

# --- Main Analysis Function ---

def get_stock_rating(ticker):
    try:
        stock = yf.Ticker(ticker)
        info = stock.info
        # Try to get previous annual data for Piotroski F-Score trends
        prev_info = None
        try:
            hist = stock.get_financials(freq='annual')
            if hist is not None and len(hist.columns) > 1:
                # Use the previous year's data if available
                prev_info = {k: hist[k][1] for k in hist.index if len(hist[k]) > 1}
        except Exception:
            prev_info = None

        if not info:
            logging.warning(f"No information found for ticker: {ticker}")
            return f"Error: No information found for ticker {ticker}."
        sector = info.get("sector", "Unknown Sector")
        sector_adjustments = {
            "Technology": {"pe_factor": 1.5, "debt_factor": 1.2, "beta_factor": 1.1},
            "Financial Services": {"pe_factor": 0.8, "debt_factor": 0.7, "beta_factor": 1.2},
            "Healthcare": {"pe_factor": 1.2, "debt_factor": 1.0, "beta_factor": 0.9},
            "Consumer Defensive": {"pe_factor": 1.0, "debt_factor": 0.9, "beta_factor": 0.8},
            "Consumer Cyclical": {"pe_factor": 1.3, "debt_factor": 1.1, "beta_factor": 1.3},
            "Industrials": {"pe_factor": 1.1, "debt_factor": 1.0, "beta_factor": 1.0},
            "Basic Materials": {"pe_factor": 0.9, "debt_factor": 1.3, "beta_factor": 1.1},
            "Real Estate": {"pe_factor": 0.7, "debt_factor": 0.6, "beta_factor": 0.7},
            "Utilities": {"pe_factor": 0.9, "debt_factor": 0.8, "beta_factor": 0.6},
            "Energy": {"pe_factor": 0.7, "debt_factor": 1.3, "beta_factor": 1.3},
            "Communication Services": {"pe_factor": 1.2, "debt_factor": 1.1, "beta_factor": 1.0}
        }
        adj = sector_adjustments.get(sector, {"pe_factor": 1.0, "debt_factor": 1.0, "beta_factor": 1.0})

        # --- Scoring ---
        growth_score, growth_details = score_profitability(info)
        valuation_score, valuation_details = score_valuation(info, adj)
        financial_score, financial_details = score_financial_strength(info, adj, prev_info)
        market_position_score, market_details = score_market_position(info)
        risk_score, risk_details = score_risk_volatility(info, adj)

        # --- Weights ---
        weights = {
            "growth": 0.27,
            "valuation": 0.18,
            "financial": 0.28,  # increased to reflect its importance
            "market": 0.18,
            "risk": 0.09
        }

        final_score = round(
            growth_score * weights["growth"] +
            valuation_score * weights["valuation"] +
            financial_score * weights["financial"] +
            market_position_score * weights["market"] +
            risk_score * weights["risk"],
            1
        )

        currency = info.get("currency", "Unknown")

        # --- Output Formatting ---
        z_score_str = f"{financial_details['z_score']:.2f}" if financial_details['z_score'] is not None else "N/A"
        cash_flow_to_debt_str = f"{financial_details['cash_flow_to_debt']:.2f}" if financial_details['cash_flow_to_debt'] is not None else "N/A"
        interest_coverage_str = f"{financial_details['interest_coverage']:.2f}" if financial_details['interest_coverage'] is not None else "N/A"
        debt_to_capital_str = f"{financial_details['debt_to_capital']:.2f}" if financial_details['debt_to_capital'] is not None else "N/A"
        piotroski_score_str = f"{financial_details['piotroski_score']}/9"

        analysis = f"""
Fundamental Analysis for {ticker} ({sector}):

Profitability & Growth: {growth_score}/10
- Revenue Growth: {growth_details['revenue_growth']:.1f}%. {"Strong growth above 10%." if growth_details['revenue_growth'] > 10 else "Stable but moderate growth."}
- Profit Margin: {growth_details['profit_margin']:.1f}%. {"High and profitable business." if growth_details['profit_margin'] > 15 else "Marginal profit margin."}
- Return on Equity (ROE): {growth_details['roe']:.1f}%. {"Effective use of capital." if growth_details['roe'] > 15 else "Low return."}
- Gross Profit Margin: {growth_details['gross_profit_margin']:.1f}%
- Operating Margin: {growth_details['operating_margin']:.1f}%
- Payout Ratio: {growth_details['payout_ratio']:.1f}%

Valuation: {valuation_score}/10
- P/E Ratio: {valuation_details['pe_ratio']:.1f}. {"Highly valued stock." if valuation_details['pe_ratio'] > 30 else "Attractively valued."}
- P/S Ratio: {valuation_details['ps_ratio']:.1f}. {"High valuation relative to sales." if valuation_details['ps_ratio'] > 5 else "Reasonably valued."}
- P/B Ratio: {valuation_details['pb_ratio']:.1f}
- EPS: {valuation_details['eps']:.2f}
- Forward PE: {valuation_details['forward_pe']:.2f}
- Free Cash Flow: {valuation_details['free_cashflow']}
- PEG Ratio: {valuation_details['peg_ratio']}

Financial Strength (inc. Bankruptcy Risk): {financial_score}/10
- Debt to Equity: {financial_details['debt_to_equity']:.1f}%. {"Low debt level, strong balance sheet." if financial_details['debt_to_equity'] < 50 else "High debt."}
- Liquidity (Quick Ratio): {financial_details['quick_ratio']:.1f}. {"Good ability to pay." if financial_details['quick_ratio'] > 1 else "Weak liquidity."}
- Current Ratio: {financial_details['current_ratio']:.2f}
- Cash Flow to Debt Ratio: {cash_flow_to_debt_str} {"(Warning: <1)" if financial_details['cash_flow_to_debt'] is not None and financial_details['cash_flow_to_debt'] < 1 else ""}
- Altman Z-Score: {z_score_str} ({financial_details['z_zone']})
- Interest Coverage Ratio: {interest_coverage_str}
- Debt to Capital Ratio: {debt_to_capital_str}
- Piotroski F-Score: {piotroski_score_str}
  {"; ".join(financial_details['piotroski_explanations'])}

Market Position: {market_position_score}/10
- Market Cap: {market_details['market_cap']} {currency}
- Recommendation Key: {market_details['recommendation_key']}

Risk & Volatility: {risk_score}/10
- Beta: {risk_details['beta']:.2f}. {"Stable stock with low volatility." if risk_details['beta'] < 1 else "Higher volatility than the market."}

Total Rating: {final_score}/10
"""
        return analysis
    except Exception as e:
        logging.error(f"An error occurred while analyzing {ticker}: {e}")
        return f"Error: An error occurred while analyzing {ticker}: {e}"

# Example call
if __name__ == "__main__":
    #ticker = "RDNT" # Adjust ticker if needed
    ticker = "COLO-B.CO" # Adjust ticker if needed
    analysis = get_stock_rating(ticker)
    print(analysis)

