import os
import sqlite3
import streamlit as st
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.sqlite import SqliteSaver
from graph.state import GoldState
from graph.nodes import generate_prediction
from graph.subgraphs import build_macro_subgraph, build_safe_haven_subgraph, build_geopolitical_subgraph

# Wipe any stale error rows cached under the old behaviour on first import.
try:
    from tools.cache_utils import purge_error_cache
    _purged = purge_error_cache()
    if _purged:
        print(f"[cache] purged {_purged} stale error rows", flush=True)
except Exception as _e:
    print(f"[cache] purge skipped: {_e}", flush=True)


@st.cache_resource(show_spinner=False)
def build_graph():
    db_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'goldbot_checkpoints.db')
    conn = sqlite3.connect(db_path, check_same_thread=False)
    checkpointer = SqliteSaver(conn)
    graph = StateGraph(GoldState)

    graph.add_node("fetch_macro", build_macro_subgraph())
    graph.add_node("fetch_safe_haven", build_safe_haven_subgraph())
    graph.add_node("fetch_geopolitical", build_geopolitical_subgraph())
    graph.add_node("generate_prediction", generate_prediction)

    graph.add_edge(START, "fetch_macro")
    graph.add_edge(START, "fetch_safe_haven")
    graph.add_edge(START, "fetch_geopolitical")
    graph.add_edge("fetch_macro", "generate_prediction")
    graph.add_edge("fetch_safe_haven", "generate_prediction")
    graph.add_edge("fetch_geopolitical", "generate_prediction")
    graph.add_edge("generate_prediction", END)

    return graph.compile(checkpointer=checkpointer)


app = build_graph()