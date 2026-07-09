from typing import TypedDict, Annotated

class GoldState(TypedDict):
    # Macro factors
    real_yields: Annotated[str, lambda old, new: new]
    usd_index: Annotated[str, lambda old, new: new]
    fed_rate: Annotated[str, lambda old, new: new]
    inflation_expectations: Annotated[str, lambda old, new: new]

    # Safe Haven factors
    treasury_2y: Annotated[str, lambda old, new: new]
    vix: Annotated[str, lambda old, new: new]
    sp500_growth: Annotated[str, lambda old, new: new]

    # Geopolitical factors
    central_bank_buying: Annotated[str, lambda old, new: new]
    geopolitical_risk: Annotated[str, lambda old, new: new]

    # Final output
    prediction: Annotated[str, lambda old, new: new]
    scores: Annotated[dict, lambda old, new: new]