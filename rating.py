import yfinance as yf
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- Risk Metric Calculations ---

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

def calculate_piotroski_f_score(info):
    score = 0
    # Profitability
    if info.get('netIncomeToCommon', 0) > 0:
        score += 1
    if info.get('operatingCashflow', 0) > 0:
        score += 1
    if info.get('operatingCashflow', 0) > info.get('netIncomeToCommon', 0):
        score += 1
    # Liquidity
    if info.get('currentRatio', 0) > 1:
        score += 1
    # Efficiency
    if info.get('grossMargins', 0) > 0:
        score += 1
    if info.get('assetTurnover', 0) > 0:
        score += 1
    return score  # Max 6 in this simplified version

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

def score_financial_strength(info, adj):
    debt_to_equity = info.get("debtToEquity", 100) * adj["debt_factor"]
    quick_ratio = info.get("quickRatio", 1)
    current_ratio = info.get("currentRatio", 1)
    financial_score = min(9, (10 - debt_to_equity / 20 + quick_ratio * 3 + current_ratio * 2))
    details = {
        "debt_to_equity": debt_to_equity,
        "quick_ratio": quick_ratio,
        "current_ratio": current_ratio,
        "score": financial_score
    }
    return financial_score, details

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

def score_bankruptcy_and_risk(info):
    # Altman Z-score
    z_score, z_zone = calculate_altman_z(info)
    if z_score is None:
        z_score_component = 5
    elif z_score > 2.99:
        z_score_component = 10
    elif z_score > 1.81:
        z_score_component = 6
    else:
        z_score_component = 2

    # Cash Flow to Debt Ratio
    total_liab = info.get("totalLiab", 0)
    total_debt = info.get("totalDebt", total_liab)
    cashflow_from_ops = info.get("operatingCashflow", 0)
    cash_flow_to_debt = (cashflow_from_ops / total_debt) if total_debt else None
    if cash_flow_to_debt is None:
        cf_debt_component = 5
    elif cash_flow_to_debt >= 1.5:
        cf_debt_component = 10
    elif cash_flow_to_debt >= 1:
        cf_debt_component = 7
    elif cash_flow_to_debt >= 0.5:
        cf_debt_component = 4
    else:
        cf_debt_component = 1

    # Interest Coverage Ratio
    interest_coverage = calculate_interest_coverage(info)
    if interest_coverage is None:
        interest_coverage_component = 5
    elif interest_coverage > 3:
        interest_coverage_component = 10
    elif interest_coverage > 1.5:
        interest_coverage_component = 7
    elif interest_coverage > 1:
        interest_coverage_component = 4
    else:
        interest_coverage_component = 1

    # Debt-to-Capital Ratio
    debt_to_capital = calculate_debt_to_capital(info)
    if debt_to_capital is None:
        debt_to_capital_component = 5
    elif debt_to_capital < 0.4:
        debt_to_capital_component = 10
    elif debt_to_capital < 0.6:
        debt_to_capital_component = 7
    elif debt_to_capital < 0.8:
        debt_to_capital_component = 4
    else:
        debt_to_capital_component = 1

    # Piotroski F-Score (simplified, max 6)
    piotroski_score = calculate_piotroski_f_score(info)
    if piotroski_score >= 5:
        piotroski_component = 10
    elif piotroski_score >= 4:
        piotroski_component = 7
    elif piotroski_score >= 2:
        piotroski_component = 4
    else:
        piotroski_component = 1

    # Average all risk components
    risk_components = [
        z_score_component,
        cf_debt_component,
        interest_coverage_component,
        debt_to_capital_component,
        piotroski_component
    ]
    bankruptcy_risk_score = sum(risk_components) / len(risk_components)
    details = {
        "z_score": z_score,
        "z_zone": z_zone,
        "cash_flow_to_debt": cash_flow_to_debt,
        "interest_coverage": interest_coverage,
        "debt_to_capital": debt_to_capital,
        "piotroski_score": piotroski_score,
        "score": bankruptcy_risk_score
    }
    return bankruptcy_risk_score, details

# --- Main Analysis Function ---

def get_stock_rating(ticker):
    try:
        stock = yf.Ticker(ticker)
        info = stock.info

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
        financial_score, financial_details = score_financial_strength(info, adj)
        market_position_score, market_details = score_market_position(info)
        risk_score, risk_details = score_risk_volatility(info, adj)
        bankruptcy_risk_score, risk_metrics = score_bankruptcy_and_risk(info)

        # --- Weights ---
        weights = {
            "growth": 0.27,
            "valuation": 0.18,
            "financial": 0.18,
            "market": 0.18,
            "risk": 0.09,
            "bankruptcy": 0.10
        }

        final_score = round(
            growth_score * weights["growth"] +
            valuation_score * weights["valuation"] +
            financial_score * weights["financial"] +
            market_position_score * weights["market"] +
            risk_score * weights["risk"] +
            bankruptcy_risk_score * weights["bankruptcy"],
            1
        )

        currency = info.get("currency", "Unknown")

        # --- Output Formatting ---
        z_score_str = f"{risk_metrics['z_score']:.2f}" if risk_metrics['z_score'] is not None else "N/A"
        cash_flow_to_debt_str = f"{risk_metrics['cash_flow_to_debt']:.2f}" if risk_metrics['cash_flow_to_debt'] is not None else "N/A"
        interest_coverage_str = f"{risk_metrics['interest_coverage']:.2f}" if risk_metrics['interest_coverage'] is not None else "N/A"
        debt_to_capital_str = f"{risk_metrics['debt_to_capital']:.2f}" if risk_metrics['debt_to_capital'] is not None else "N/A"
        piotroski_score_str = f"{risk_metrics['piotroski_score']}/6"

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

Financial Strength: {financial_score}/10
- Debt to Equity: {financial_details['debt_to_equity']:.1f}%. {"Low debt level, strong balance sheet." if financial_details['debt_to_equity'] < 50 else "High debt."}
- Liquidity (Quick Ratio): {financial_details['quick_ratio']:.1f}. {"Good ability to pay." if financial_details['quick_ratio'] > 1 else "Weak liquidity."}
- Current Ratio: {financial_details['current_ratio']:.2f}
- Cash Flow to Debt Ratio: {cash_flow_to_debt_str} {"(Warning: <1)" if risk_metrics['cash_flow_to_debt'] is not None and risk_metrics['cash_flow_to_debt'] < 1 else ""}

Market Position: {market_position_score}/10
- Market Cap: {market_details['market_cap']} {currency}
- Recommendation Key: {market_details['recommendation_key']}

Risk & Volatility: {risk_score}/10
- Beta: {risk_details['beta']:.2f}. {"Stable stock with low volatility." if risk_details['beta'] < 1 else "Higher volatility than the market."}

Bankruptcy & Financial Risk: {bankruptcy_risk_score:.1f}/10
- Altman Z-Score: {z_score_str} ({risk_metrics['z_zone']})
- Cash Flow to Debt Ratio: {cash_flow_to_debt_str}
- Interest Coverage Ratio: {interest_coverage_str}
- Debt to Capital Ratio: {debt_to_capital_str}
- Piotroski F-Score: {piotroski_score_str}

Total Rating: {final_score}/10
"""
        return analysis

    except Exception as e:
        logging.error(f"An error occurred while analyzing {ticker}: {e}")
        return f"Error: An error occurred while analyzing {ticker}: {e}"

# Example call
if __name__ == "__main__":
    ticker = "MTRS.ST"  # Adjust ticker if needed
    analysis = get_stock_rating(ticker)
    print(analysis)

