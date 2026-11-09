"""Reproduces, in CI with no secrets, what reaches generate_prediction when
the parallel subgraphs finish. Stubs every external fetcher so the real graph
and state code run unchanged, then prints the merged state.

Run from the repo root:
    python -m tests.debug_graph_state
"""
import json
import os
import sys
import tempfile
from unittest.mock import MagicMock, patch


def _stub_tool(name: str):
    t = MagicMock()
    t.invoke = MagicMock(return_value=f"<{name} fake data>")
    t.name = name
    return t


STUBS = {
    "tools.macro_tools": [
        "get_real_yields", "get_fed_rate", "get_treasury_2y", "get_inflation_expectations",
    ],
    "tools.market_tools": [
        "get_usd_index", "get_vix", "get_sp500_growth",
    ],
    "tools.external_tools": [
        "get_central_bank_gold_buying", "get_geopolitical_risk",
    ],
}


def install_stubs():
    import types

    # dotenv is not installed in CI; nodes.py calls load_dotenv at import.
    dotenv_mod = types.ModuleType("dotenv")
    dotenv_mod.load_dotenv = lambda *a, **kw: None
    sys.modules["dotenv"] = dotenv_mod

    # rag.retriever is imported by graph.nodes; the recorder replaces
    # generate_prediction so retrieve_factor_context is never called.
    rag_pkg = types.ModuleType("rag")
    rag_pkg.__path__ = []
    sys.modules["rag"] = rag_pkg
    rag_r = types.ModuleType("rag.retriever")
    rag_r.retrieve_factor_context = lambda *a, **kw: ""
    sys.modules["rag.retriever"] = rag_r

    for mod_name, attrs in STUBS.items():
        mod = types.ModuleType(mod_name)
        for a in attrs:
            setattr(mod, a, _stub_tool(a))
        # A dummy _looks_like_error so graph.nodes can import it from cache_utils.
        if mod_name == "tools.macro_tools":
            pass
        sys.modules[mod_name] = mod
    cache_mod = types.ModuleType("tools.cache_utils")
    cache_mod._looks_like_error = lambda s: False
    cache_mod.purge_error_cache = lambda: 0
    sys.modules["tools.cache_utils"] = cache_mod
    pkg = types.ModuleType("tools")
    pkg.__path__ = []
    sys.modules.setdefault("tools", pkg)

    # ChatOpenAI is built at import time inside graph.nodes; stub it out entirely so
    # no API key is required and no network call happens.
    class _FakeLLM:
        def invoke(self, *a, **kw):
            return MagicMock(content="\n".join([
                "REAL_YIELDS_SCORE: -3",
                "USD_INDEX_SCORE: -2",
                "FED_RATE_SCORE: -1",
                "CENTRAL_BANK_BUYING_SCORE: 4",
                "TREASURY_2Y_SCORE: -2",
                "VIX_SCORE: 1",
                "GEOPOLITICAL_RISK_SCORE: 3",
                "SP500_GROWTH_SCORE: -1",
                "INFLATION_EXPECTATIONS_SCORE: 2",
            ]))

        def __or__(self, other):
            return self

    lco = types.ModuleType("langchain_openai")
    lco.ChatOpenAI = lambda *a, **kw: _FakeLLM()
    sys.modules["langchain_openai"] = lco

    # Minimal streamlit stub — graph.workflow does `import streamlit as st` but
    # never actually uses it before compile().
    st_stub = types.ModuleType("streamlit")
    sys.modules.setdefault("streamlit", st_stub)


def main():
    install_stubs()

    captured = {}

    def recorder(state):
        captured["state_keys"] = sorted(state.keys())
        captured["per_field"] = {
            k: ("<empty>" if state.get(k) in (None, "") else str(state.get(k))[:60])
            for k in sorted(state.keys())
        }
        return {"prediction": "stub", "scores": {}}

    # Patch BEFORE importing workflow, because workflow.py does
    # `from graph.nodes import generate_prediction` and the compiled graph
    # captures that reference at build time.
    import graph.nodes as graph_nodes
    graph_nodes.generate_prediction = recorder

    from graph.workflow import build_graph

    os.chdir(tempfile.mkdtemp(prefix="gb-"))
    app = build_graph()
    app.invoke({}, config={"configurable": {"thread_id": "debug-1"}})

    # The FACTOR_WEIGHTS keys are the ones that MUST reach generate_prediction
    # with real data for scoring to work.
    expected = [
        "real_yields", "usd_index", "fed_rate", "inflation_expectations",
        "treasury_2y", "vix", "sp500_growth",
        "central_bank_buying", "geopolitical_risk",
    ]
    reached = {
        k: captured.get("per_field", {}).get(k, "<MISSING from state>")
        for k in expected
    }
    missing = [k for k, v in reached.items() if v in ("<empty>", "<MISSING from state>")]

    print("=" * 70)
    print("What reached generate_prediction (all keys):")
    for k, v in captured["per_field"].items():
        print(f"  {k:30s} = {v}")
    print("=" * 70)
    print("Factors needed for scoring:")
    for k in expected:
        v = reached[k]
        ok = "OK  " if v not in ("<empty>", "<MISSING from state>") else "FAIL"
        print(f"  [{ok}] {k:28s} = {v}")
    print("=" * 70)
    print(f"RESULT: {len(expected) - len(missing)}/{len(expected)} factors carried real data.")
    if missing:
        print("MISSING:", ", ".join(missing))
        sys.exit(2)


if __name__ == "__main__":
    main()
