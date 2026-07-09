import os
import sqlite3
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.sqlite import SqliteSaver
from graph.state import GoldState
from graph.nodes import generate_prediction
from graph.subgraphs import build_macro_subgraph, build_safe_haven_subgraph, build_geopolitical_subgraph


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