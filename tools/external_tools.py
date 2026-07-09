import os
import re
import json
import asyncio
import threading
from langchain_core.tools import tool
from langchain_mcp_adapters.client import MultiServerMCPClient
from dotenv import load_dotenv

load_dotenv()

TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")

# --- Persistent background event loop for caching the Tavily MCP client ---
_loop = None
_loop_ready = threading.Event()
_mcp_tool = None
_mcp_init_lock = asyncio.Lock()


def _ensure_background_loop():
    global _loop
    if _loop is not None:
        return
    def run_loop():
        global _loop
        _loop = asyncio.new_event_loop()
        asyncio.set_event_loop(_loop)
        _loop_ready.set()
        _loop.run_forever()
    thread = threading.Thread(target=run_loop, daemon=True)
    thread.start()
    _loop_ready.wait()


async def _get_cached_tavily_tool():
    global _mcp_tool
    async with _mcp_init_lock:
        if _mcp_tool is not None:
            return _mcp_tool
        client = MultiServerMCPClient({
            "tavily": {
                "url": f"https://mcp.tavily.com/mcp/?tavilyApiKey={TAVILY_API_KEY}",
                "transport": "streamable_http",
            }
        })
        tools = await client.get_tools()
        _mcp_tool = next(t for t in tools if t.name == "tavily_search")
        return _mcp_tool


async def _tavily_search_async(query: str, max_results: int = 5) -> str:
    search_tool = await _get_cached_tavily_tool()
    result = await search_tool.ainvoke({"query": query, "max_results": max_results})

    parsed = json.loads(result[0]["text"])
    contents = [r.get("content", "") for r in parsed.get("results", []) if r.get("content")]
    if not contents:
        raise ValueError("Tavily returned no usable content")

    combined = " ".join(contents)
    combined = re.sub(r'!\[[^\]]*\]\([^\)]*\)', '', combined)
    combined = re.sub(r'\(https?://[^\)]*\)', '', combined)
    combined = re.sub(r'\[([^\]]+)\]\([^\)]*\)', r'\1', combined)
    combined = re.sub(r'https?://\S+', '', combined)
    combined = re.sub(r'[\[\]]', '', combined)
    combined = re.sub(r'[()]', '', combined)
    combined = re.sub(r'\s+', ' ', combined).strip()

    return combined


def sentence_truncate(text: str, limit: int = 1000) -> str:
    """Truncates at the nearest sentence boundary near `limit`, avoiding mid-sentence cuts."""
    text = str(text)
    if len(text) <= limit:
        return text
    window = text[:limit + 100]
    for punct in ['. ', '! ', '? ']:
        idx = window.rfind(punct, 0, limit + 100)
        if idx != -1 and idx > limit * 0.5:
            return window[:idx + 1].strip()
    return text[:limit].rsplit(' ', 1)[0].strip() + "..."


def tavily_search(query: str, max_results: int = 5) -> str:
    if not TAVILY_API_KEY:
        raise ValueError("TAVILY_API_KEY not set")
    _ensure_background_loop()
    future = asyncio.run_coroutine_threadsafe(_tavily_search_async(query, max_results), _loop)
    return future.result(timeout=30)


@tool
def get_central_bank_gold_buying() -> str:
    """Searches for recent central bank gold purchasing activity and de-dollarization trends."""
    try:
        result = tavily_search("central bank gold buying reserves 2026 de-dollarization")
        return f"Central Bank Gold Buying: {sentence_truncate(result)}"
    except Exception as e:
        return f"Central Bank Gold Buying: Data unavailable ({str(e)})"


@tool
def get_geopolitical_risk() -> str:
    """Searches for current geopolitical conflict and war risk signals affecting safe-haven demand."""
    try:
        result = tavily_search("geopolitical conflict war risk 2026 safe haven gold")
        return f"Geopolitical Risk: {sentence_truncate(result)}"
    except Exception as e:
        return f"Geopolitical Risk: Data unavailable ({str(e)})"


