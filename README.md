# GoldBot

9-factor AI-powered gold safe-haven analyzer using LangGraph, RAG, and MCP.

**Live app:** https://goldbot-raj.streamlit.app/

## Stack
- Streamlit (frontend)
- LangGraph (agent orchestration)
- RAG pipeline + MCP tools
- SQLite (checkpointing / factor cache)

## Run locally
```bash
pip install -r requirements.txt
streamlit run frontend/app.py
```
