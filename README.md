# GoldBot

9-factor AI-powered gold safe-haven analyzer using LangGraph, RAG, and MCP.

**Live app:** https://goldbot-raj.streamlit.app/

## Stack
- Streamlit (frontend)
- LangGraph (agent orchestration)
- RAG pipeline + MCP tools
- SQLite (checkpointing / factor cache)

## Architecture

```mermaid
flowchart TD
    START([START]) --> fetch_macro
    START --> fetch_safe_haven
    START --> fetch_geopolitical

    subgraph fetch_macro["fetch_macro (subgraph)"]
        direction TB
        m_start([START]) --> fetch_real_yields
        m_start --> fetch_fed_rate
        m_start --> fetch_usd_index
        m_start --> fetch_inflation_expectations
        fetch_real_yields --> m_end([END])
        fetch_fed_rate --> m_end
        fetch_usd_index --> m_end
        fetch_inflation_expectations --> m_end
    end

    subgraph fetch_safe_haven["fetch_safe_haven (subgraph)"]
        direction TB
        s_start([START]) --> fetch_treasury_2y
        s_start --> fetch_vix
        s_start --> fetch_sp500_growth
        fetch_treasury_2y --> s_end([END])
        fetch_vix --> s_end
        fetch_sp500_growth --> s_end
    end

    subgraph fetch_geopolitical["fetch_geopolitical (subgraph)"]
        direction TB
        g_start([START]) --> fetch_central_bank_buying
        g_start --> fetch_geopolitical_risk
        fetch_central_bank_buying --> g_end([END])
        fetch_geopolitical_risk --> g_end
    end

    fetch_macro --> generate_prediction
    fetch_safe_haven --> generate_prediction
    fetch_geopolitical --> generate_prediction
    generate_prediction --> END([END])
```

The top-level `StateGraph` fans out from `START` into three parallel subgraphs — `fetch_macro`, `fetch_safe_haven`, and `fetch_geopolitical` — each of which itself fans out to fetch its individual factors in parallel (real yields, Fed rate, USD index, inflation expectations; 2Y treasury, VIX, S&P 500 growth; central bank buying, geopolitical risk). All three subgraphs feed into `generate_prediction`, which combines the 9 factors (using RAG-retrieved context and weighted scoring) into the final gold outlook before the graph ends.

## Run locally
```bash
pip install -r requirements.txt
streamlit run frontend/app.py
```
