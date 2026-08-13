import yfinance as yf
from langchain_core.tools import tool
from tools.cache_utils import cached_tool, TTL_SLOW, TTL_FAST

yf.set_tz_cache_location("D:\\yf_cache")


@tool
@cached_tool(TTL_SLOW)
def get_usd_index() -> str:
    """Fetches the current USD Index (DXY) value as a dollar strength signal."""
    try:
        dxy = yf.Ticker("DX-Y.NYB")
        price = dxy.info.get('regularMarketPrice')
        return f"USD Index (DXY): {price}"
    except Exception as e:
        return f"USD Index: Data unavailable ({str(e)})"


@tool
@cached_tool(TTL_FAST)
def get_vix() -> str:
    """Fetches the current VIX (CBOE Volatility Index) value as a market fear signal."""
    try:
        vix = yf.Ticker("^VIX")
        price = vix.info.get('regularMarketPrice')
        return f"VIX: {price}"
    except Exception as e:
        return f"VIX: Data unavailable ({str(e)})"


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
        change = ((hist['Close'].iloc[-1] - hist['Close'].iloc[0]) / hist['Close'].iloc[0]) * 100
        return f"S&P 500 1-month change: {round(change, 2)}%"
    except Exception as e:
        return f"S&P 500 Growth: Data unavailable ({str(e)})"