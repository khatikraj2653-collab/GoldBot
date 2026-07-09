import os
from langchain_core.tools import tool
from fredapi import Fred
from dotenv import load_dotenv

load_dotenv()
fred = Fred(api_key=os.getenv("FRED_API_KEY"))


@tool
def get_real_yields() -> str:
    """Fetches the 10-Year Treasury Inflation-Protected Security (TIPS) real yield from FRED."""
    try:
        value = fred.get_series('DFII10').iloc[-1]
        return f"Real Yields (10Y TIPS): {round(float(value), 2)}%"
    except Exception as e:
        return f"Real Yields: Data unavailable ({str(e)})"


@tool
def get_fed_rate() -> str:
    """Fetches the current Federal Funds Rate from FRED."""
    try:
        value = fred.get_series('FEDFUNDS').iloc[-1]
        return f"Fed Rate: {round(float(value), 2)}%"
    except Exception as e:
        return f"Fed Rate: Data unavailable ({str(e)})"


@tool
def get_treasury_2y() -> str:
    """Fetches the 2-Year Treasury Constant Maturity Rate from FRED."""
    try:
        value = fred.get_series('DGS2').iloc[-1]
        return f"2-Year Treasury Yield: {round(float(value), 2)}%"
    except Exception as e:
        return f"2-Year Treasury Yield: Data unavailable ({str(e)})"


@tool
def get_inflation_expectations() -> str:
    """Fetches the 5-Year Breakeven Inflation Rate from FRED, a market-based measure of expected inflation."""
    try:
        value = fred.get_series('T5YIE').iloc[-1]
        return f"5-Year Breakeven Inflation Expectations: {round(float(value), 2)}%"
    except Exception as e:
        return f"Inflation Expectations: Data unavailable ({str(e)})"