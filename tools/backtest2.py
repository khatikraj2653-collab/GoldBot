import os
import sys
from datetime import datetime
import pandas as pd
import yfinance as yf
from fredapi import Fred
from dotenv import load_dotenv

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env'))

from graph.nodes import generate_prediction
from tools.gdelt_historical import get_geopolitical_risk_historical, get_central_bank_buying_historical

fred = Fred(api_key=os.getenv("FRED_API_KEY"))

# ---------- Curated event dates (Backtest 2: cross-event generalization) ----------
EVENT_DATES = [
    (datetime(2025, 9, 17), "FOMC meeting"),
    (datetime(2025, 10, 29), "FOMC meeting"),
    (datetime(2025, 11, 20), "VIX spike (26.4)"),
    (datetime(2025, 12, 10), "FOMC meeting"),
    (datetime(2026, 1, 8), "Iran protest crackdown / internet shutdown"),
    (datetime(2026, 1, 28), "FOMC meeting"),
    (datetime(2026, 2, 28), "US-Israel strikes on Iran begin (war outbreak)"),
    (datetime(2026, 3, 18), "FOMC meeting (during Iran war / Hormuz blockade)"),
    (datetime(2026, 4, 29), "FOMC meeting"),
    (datetime(2026, 6, 17), "FOMC meeting (first Warsh-chaired)"),
]

# ---------- Historical Tier-1 fetchers ----------
def fred_value_as_of(series_id, as_of_date):
    try:
        series = fred.get_series(series_id)
        series = series[series.index <= pd.Timestamp(as_of_date)]
        if series.empty:
            return None
        return float(series.iloc[-1])
    except Exception:
        return None

def yf_close_as_of(ticker_symbol, as_of_date, lookback_days=10):
    try:
        t = yf.Ticker(ticker_symbol)
        start = as_of_date - pd.Timedelta(days=lookback_days)
        end = as_of_date + pd.Timedelta(days=1)
        hist = t.history(start=start, end=end)
        if hist.empty:
            return None
        return float(hist['Close'].iloc[-1])
    except Exception:
        return None

def sp500_growth_as_of(as_of_date):
    try:
        t = yf.Ticker("^GSPC")
        start = as_of_date - pd.Timedelta(days=35)
        end = as_of_date + pd.Timedelta(days=1)
        hist = t.history(start=start, end=end)
        if len(hist) < 2:
            return None
        change = ((hist['Close'].iloc[-1] - hist['Close'].iloc[0]) / hist['Close'].iloc[0]) * 100
        return round(change, 2)
    except Exception:
        return None

# ---------- MA50 point-in-time ground truth ----------
def gold_price_vs_ma50(as_of_date):
    try:
        t = yf.Ticker("GC=F")
        start = as_of_date - pd.Timedelta(days=80)
        end = as_of_date + pd.Timedelta(days=1)
        hist = t.history(start=start, end=end)
        if len(hist) < 50:
            return None, None
        ma50 = hist['Close'].rolling(50).mean().iloc[-1]
        price = hist['Close'].iloc[-1]
        return round(float(price), 2), round(float(ma50), 2)
    except Exception:
        return None, None

def sp500_price_vs_ma50(as_of_date):
    try:
        t = yf.Ticker("^GSPC")
        start = as_of_date - pd.Timedelta(days=80)
        end = as_of_date + pd.Timedelta(days=1)
        hist = t.history(start=start, end=end)
        if len(hist) < 50:
            return None, None
        ma50 = hist['Close'].rolling(50).mean().iloc[-1]
        price = hist['Close'].iloc[-1]
        return round(float(price), 2), round(float(ma50), 2)
    except Exception:
        return None, None

def classify_regime_ma(gold_price, gold_ma50, sp_price, sp_ma50):
    if None in (gold_price, gold_ma50, sp_price, sp_ma50):
        return "UNKNOWN"
    gold_above = gold_price > gold_ma50
    sp_above = sp_price > sp_ma50
    if gold_above and not sp_above:
        return "SAFE_HAVEN_CONFIRMED"
    elif not gold_above and sp_above:
        return "SAFE_HAVEN_REJECTED"
    else:
        return "AMBIGUOUS"

# ---------- Build historical state ----------
def build_historical_state(as_of_date):
    real_yields = fred_value_as_of('DFII10', as_of_date)
    fed_rate = fred_value_as_of('FEDFUNDS', as_of_date)
    treasury_2y = fred_value_as_of('DGS2', as_of_date)
    inflation_exp = fred_value_as_of('T5YIE', as_of_date)
    usd_index = yf_close_as_of('DX-Y.NYB', as_of_date)
    vix = yf_close_as_of('^VIX', as_of_date)
    sp500_growth = sp500_growth_as_of(as_of_date)

    def fmt(label, val, unit="%"):
        return f"{label}: Data unavailable" if val is None else f"{label}: {round(val, 2)}{unit}"

    state = {
        "real_yields": fmt("Real Yields (10Y TIPS)", real_yields),
        "usd_index": "USD Index (DXY): Data unavailable" if usd_index is None else f"USD Index (DXY): {round(usd_index, 3)}",
        "fed_rate": fmt("Fed Rate", fed_rate),
        "treasury_2y": fmt("2-Year Treasury Yield", treasury_2y),
        "vix": "VIX: Data unavailable" if vix is None else f"VIX: {round(vix, 1)}",
        "sp500_growth": "S&P 500 1-month change: Data unavailable" if sp500_growth is None else f"S&P 500 1-month change: {sp500_growth}%",
        "inflation_expectations": fmt("5-Year Breakeven Inflation Expectations", inflation_exp),
        "central_bank_buying": get_central_bank_buying_historical(as_of_date),
        "geopolitical_risk": get_geopolitical_risk_historical(as_of_date),
    }
    tier1_values = [real_yields, fed_rate, treasury_2y, inflation_exp, usd_index, vix, sp500_growth]
    return state, tier1_values

# ---------- Main backtest loop ----------
def run_backtest():
    results = []
    skipped = 0

    for i, (as_of_date, event_label) in enumerate(EVENT_DATES):
        print(f"\n[{i+1}/{len(EVENT_DATES)}] Testing date: {as_of_date.date()} ({event_label})")

        state, tier1_values = build_historical_state(as_of_date)

        if sum(v is None for v in tier1_values) > 2:
            print("  SKIPPED - too many missing Tier-1 factors")
            skipped += 1
            continue

        try:
            prediction_result = generate_prediction(state)
            print(f"  [SCORES] {prediction_result['scores']}")
        except Exception as e:
            print(f"  SKIPPED - generate_prediction failed: {e}")
            skipped += 1
            continue

        predicted_status = "ON" if "SAFE_HAVEN_STATUS: ON" in prediction_result["prediction"] else "OFF"
        strength_line = [l for l in prediction_result["prediction"].split("\n") if l.startswith("STRENGTH:")]
        predicted_strength = strength_line[0].split(":")[-1].strip() if strength_line else "N/A"

        gold_price, gold_ma50 = gold_price_vs_ma50(as_of_date)
        sp_price, sp_ma50 = sp500_price_vs_ma50(as_of_date)
        regime_truth = classify_regime_ma(gold_price, gold_ma50, sp_price, sp_ma50)

        price_direction_correct = None
        if gold_price is not None and gold_ma50 is not None:
            price_direction_correct = (predicted_status == "ON" and gold_price > gold_ma50) or (predicted_status == "OFF" and gold_price <= gold_ma50)

        regime_correct = None
        if regime_truth in ("SAFE_HAVEN_CONFIRMED", "SAFE_HAVEN_REJECTED"):
            regime_correct = (predicted_status == "ON" and regime_truth == "SAFE_HAVEN_CONFIRMED") or (predicted_status == "OFF" and regime_truth == "SAFE_HAVEN_REJECTED")

        results.append({
            "date": as_of_date.date().isoformat(),
            "event": event_label,
            "predicted_status": predicted_status,
            "predicted_strength": predicted_strength,
            "gold_price": gold_price,
            "gold_ma50": gold_ma50,
            "sp500_price": sp_price,
            "sp500_ma50": sp_ma50,
            "regime_ground_truth": regime_truth,
            "price_direction_correct": price_direction_correct,
            "regime_correct": regime_correct,
        })

        print(f"  Predicted: {predicted_status} ({predicted_strength}) | Gold vs MA50: {gold_price} vs {gold_ma50} | Regime: {regime_truth}")

    df = pd.DataFrame(results)
    df.to_csv("backtest2_results.csv", index=False)

    valid_price = df["price_direction_correct"].dropna()
    valid_regime = df["regime_correct"].dropna()

    print("\n" + "="*50)
    print("BACKTEST 2 SUMMARY (Cross-Event Generalization)")
    print(f"Total events tested: {len(EVENT_DATES)}")
    print(f"Skipped (missing data): {skipped}")
    print(f"Valid predictions: {len(df)}")
    print(f"Price direction accuracy: {valid_price.mean()*100:.1f}% ({valid_price.sum()}/{len(valid_price)})")
    print(f"Regime classification accuracy: {valid_regime.mean()*100:.1f}% ({valid_regime.sum()}/{len(valid_regime)})")
    print(f"Ambiguous regime dates (excluded): {(df['regime_ground_truth']=='AMBIGUOUS').sum()}")
    print("="*50)
    print("\nSaved to backtest2_results.csv")

if __name__ == "__main__":
    run_backtest()
