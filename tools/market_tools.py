import os
import yfinance as yf
from langchain_core.tools import tool
from tools.cache_utils import cached_tool, TTL_SLOW, TTL_FAST

yf.set_tz_cache_location("D:\\yf_cache")


def _last_close(symbol: str, period: str = "5d"):
    """Reliable last-close helper: yfinance .info is often None / rate-limited
    on Streamlit Cloud IPs, so always prefer .history()."""
    try:
        hist = yf.Ticker(symbol).history(period=period, interval="1d")
        if hist is None or hist.empty:
            return None
        closes = hist["Close"].dropna()
        if closes.empty:
            return None
        return float(closes.iloc[-1])
    except Exception:
        return None


@tool
@cached_tool(TTL_SLOW)
def get_usd_index() -> str:
    """Fetches the current USD Index (DXY) value as a dollar strength signal.
    Tries .info, then .history, then FRED's trade-weighted USD index."""
    # 1) yfinance .info (live)
    try:
        price = yf.Ticker("DX-Y.NYB").info.get('regularMarketPrice')
        if isinstance(price, (int, float)) and price > 0:
            return f"USD Index (DXY): {round(price, 2)}"
    except Exception:
        pass
    # 2) yfinance .history last close (cloud-safe)
    price = _last_close("DX-Y.NYB")
    if price is not None:
        return f"USD Index (DXY): {round(price, 2)} (last close)"
    # 3) FRED trade-weighted USD index as last resort
    try:
        from fredapi import Fred
        fred = Fred(api_key=os.getenv("FRED_API_KEY"))
        val = fred.get_series('DTWEXBGS').dropna().iloc[-1]
        return f"USD Index (FRED trade-weighted): {round(float(val), 2)}"
    except Exception as e:
        return f"USD Index: Data unavailable ({str(e)})"


@tool
@cached_tool(TTL_FAST)
def get_vix() -> str:
    """Fetches the current VIX (CBOE Volatility Index) value as a market fear signal."""
    # 1) .info first (live)
    try:
        price = yf.Ticker("^VIX").info.get('regularMarketPrice')
        if isinstance(price, (int, float)) and price > 0:
            return f"VIX: {round(price, 2)}"
    except Exception:
        pass
    # 2) .history last close
    price = _last_close("^VIX")
    if price is not None:
        return f"VIX: {round(price, 2)} (last close)"
    return "VIX: Data unavailable (Yahoo did not return a price)"


def get_gold_price():
    """Fetches the current gold futures price (not an @tool, used only for the UI ticker).
    Uses history() instead of the heavier .info endpoint, which is unreliable on
    cloud-hosted IPs (Yahoo Finance frequently blocks/rate-limits .info there)."""
    try:
        hist = yf.Ticker("GC=F").history(period="5d", interval="1d")
        closes = hist["Close"].dropna()
        if len(closes) < 2:
            return None, None, None
        price = round(float(closes.iloc[-1]), 2)
        prev = round(float(closes.iloc[-2]), 2)
        change = round(price - prev, 2)
        pct = round((change / prev) * 100, 2) if prev else 0
        return price, change, pct
    except Exception:
        return None, None, None


@tool
def get_sp500_growth() -> str:
    """Fetches the 1-month percentage change of the S&P 500 index."""
    try:
        sp500 = yf.Ticker("^GSPC")
        hist = sp500.history(period="1mo")
        if hist is None or hist.empty or len(hist) < 2:
            return "S&P 500 Growth: Data unavailable (no history)"
        change = ((hist['Close'].iloc[-1] - hist['Close'].iloc[0]) / hist['Close'].iloc[0]) * 100
        return f"S&P 500 1-month change: {round(change, 2)}%"
    except Exception as e:
        return f"S&P 500 Growth: Data unavailable ({str(e)})"
