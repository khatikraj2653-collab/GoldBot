from langgraph.graph import StateGraph, START, END
from graph.state import GoldState
from tools.macro_tools import get_real_yields, get_fed_rate, get_treasury_2y, get_inflation_expectations
from tools.market_tools import get_usd_index, get_vix, get_sp500_growth
from tools.external_tools import get_central_bank_gold_buying, get_geopolitical_risk


def fetch_real_yields_node(state: GoldState) -> dict:
    return {"real_yields": get_real_yields.invoke({})}

def fetch_fed_rate_node(state: GoldState) -> dict:
    return {"fed_rate": get_fed_rate.invoke({})}

def fetch_usd_index_node(state: GoldState) -> dict:
    return {"usd_index": get_usd_index.invoke({})}

def fetch_inflation_expectations_node(state: GoldState) -> dict:
    return {"inflation_expectations": get_inflation_expectations.invoke({})}


def build_macro_subgraph():
    subgraph = StateGraph(GoldState)
    subgraph.add_node("fetch_real_yields", fetch_real_yields_node)
    subgraph.add_node("fetch_fed_rate", fetch_fed_rate_node)
    subgraph.add_node("fetch_usd_index", fetch_usd_index_node)
    subgraph.add_node("fetch_inflation_expectations", fetch_inflation_expectations_node)

    subgraph.add_edge(START, "fetch_real_yields")
    subgraph.add_edge(START, "fetch_fed_rate")
    subgraph.add_edge(START, "fetch_usd_index")
    subgraph.add_edge(START, "fetch_inflation_expectations")
    subgraph.add_edge("fetch_real_yields", END)
    subgraph.add_edge("fetch_fed_rate", END)
    subgraph.add_edge("fetch_usd_index", END)
    subgraph.add_edge("fetch_inflation_expectations", END)

    return subgraph.compile()


def fetch_treasury_2y_node(state: GoldState) -> dict:
    return {"treasury_2y": get_treasury_2y.invoke({})}

def fetch_vix_node(state: GoldState) -> dict:
    return {"vix": get_vix.invoke({})}

def fetch_sp500_growth_node(state: GoldState) -> dict:
    return {"sp500_growth": get_sp500_growth.invoke({})}


def build_safe_haven_subgraph():
    subgraph = StateGraph(GoldState)
    subgraph.add_node("fetch_treasury_2y", fetch_treasury_2y_node)
    subgraph.add_node("fetch_vix", fetch_vix_node)
    subgraph.add_node("fetch_sp500_growth", fetch_sp500_growth_node)

    subgraph.add_edge(START, "fetch_treasury_2y")
    subgraph.add_edge(START, "fetch_vix")
    subgraph.add_edge(START, "fetch_sp500_growth")
    subgraph.add_edge("fetch_treasury_2y", END)
    subgraph.add_edge("fetch_vix", END)
    subgraph.add_edge("fetch_sp500_growth", END)

    return subgraph.compile()


def fetch_central_bank_buying_node(state: GoldState) -> dict:
    return {"central_bank_buying": get_central_bank_gold_buying.invoke({})}

def fetch_geopolitical_risk_node(state: GoldState) -> dict:
    return {"geopolitical_risk": get_geopolitical_risk.invoke({})}


def build_geopolitical_subgraph():
    subgraph = StateGraph(GoldState)
    subgraph.add_node("fetch_central_bank_buying", fetch_central_bank_buying_node)
    subgraph.add_node("fetch_geopolitical_risk", fetch_geopolitical_risk_node)

    subgraph.add_edge(START, "fetch_central_bank_buying")
    subgraph.add_edge(START, "fetch_geopolitical_risk")
    subgraph.add_edge("fetch_central_bank_buying", END)
    subgraph.add_edge("fetch_geopolitical_risk", END)

    return subgraph.compile()