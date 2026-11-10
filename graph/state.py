from typing import TypedDict, Annotated

# Each factor is set by exactly one subgraph in a parallel fan-out. When a
# subgraph finishes, LangGraph emits every field it holds — including empty
# strings for the factors the OTHER subgraphs owned. Plain "last write wins"
# then overwrites real data with those empties, which leaves generate_prediction
# with only one subgraph's factors populated (seen live 2026-11-09: only the
# safe-haven group reached scoring; macro and geopolitical factors arrived
# empty and were scored 0). Keeping the first non-empty write prevents that
# without needing output-key filters on every subgraph.
def _keep_non_empty_str(old: str, new: str) -> str:
    return new if new else (old or "")


def _keep_non_empty_dict(old: dict, new: dict) -> dict:
    return new if new else (old or {})


class GoldState(TypedDict):
    # Macro factors
    real_yields: Annotated[str, _keep_non_empty_str]
    usd_index: Annotated[str, _keep_non_empty_str]
    fed_rate: Annotated[str, _keep_non_empty_str]
    inflation_expectations: Annotated[str, _keep_non_empty_str]

    # Safe Haven factors
    treasury_2y: Annotated[str, _keep_non_empty_str]
    vix: Annotated[str, _keep_non_empty_str]
    sp500_growth: Annotated[str, _keep_non_empty_str]

    # Geopolitical factors
    central_bank_buying: Annotated[str, _keep_non_empty_str]
    geopolitical_risk: Annotated[str, _keep_non_empty_str]

    # Final output
    prediction: Annotated[str, _keep_non_empty_str]
    scores: Annotated[dict, _keep_non_empty_dict]
