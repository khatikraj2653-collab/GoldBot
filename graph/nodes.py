import os
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env'))

from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from graph.state import GoldState
from rag.retriever import retrieve_factor_context

llm = ChatOpenAI(
    model="gpt-4o-mini",
    api_key=os.getenv("OPENAI_API_KEY"),
    temperature=0
)

FACTOR_WEIGHTS = {
    "real_yields": 14,
    "usd_index": 13,
    "fed_rate": 12,
    "central_bank_buying": 12,
    "treasury_2y": 11,
    "vix": 10,
    "geopolitical_risk": 10,
    "sp500_growth": 9,
    "inflation_expectations": 9,
}

FACTOR_RAG_QUERIES = {
    "real_yields": "real yields TIPS gold relationship",
    "usd_index": "USD dollar index gold relationship",
    "fed_rate": "Fed rate FOMC policy gold relationship",
    "central_bank_buying": "central bank gold buying de-dollarization",
    "treasury_2y": "2-year treasury yield gold relationship",
    "vix": "VIX volatility gold safe haven relationship",
    "geopolitical_risk": "geopolitical conflict war risk gold",
    "sp500_growth": "S&P 500 stock market gold rotation relationship",
    "inflation_expectations": "CPI inflation expectations gold hedge relationship",
}


def get_historical_context(limit: int = 5) -> str:
    """Long-term memory: queries past analysis sessions from SQLite (persists across
    threads/sessions) and returns a trend summary the agent can reason over."""
    import sqlite3
    db_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'goldbot_checkpoints.db')
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.execute(
            "SELECT status, strength, timestamp FROM analysis_history ORDER BY id DESC LIMIT ?",
            (limit,)
        )
        rows = cursor.fetchall()
        conn.close()
        if not rows:
            return "No prior analysis history available yet."
        strengths = []
        for _, strength, _ in rows:
            try:
                strengths.append(int(str(strength).replace("%", "").strip()))
            except (ValueError, TypeError):
                pass
        summary_lines = [f"{s} ({strength}) at {ts}" for s, strength, ts in rows]
        avg_line = f"Average strength over last {len(strengths)} sessions: {round(sum(strengths)/len(strengths))}%" if strengths else ""
        return f"Recent analysis history (most recent first): {'; '.join(summary_lines)}. {avg_line}"
    except Exception as e:
        return f"Historical context unavailable ({str(e)})"


def calculate_strength(scores: dict) -> int:
    weighted_sum = sum(scores[k] * FACTOR_WEIGHTS[k] for k in scores)
    normalized = (weighted_sum + 1000) / 2000
    strength = max(0, min(100, round(normalized * 100)))
    return strength


scoring_prompt = ChatPromptTemplate.from_template("""
You are a gold market analyst. Score each factor from -10 (strongly deactivating gold's safe-haven behavior) to +10 (strongly activating gold's safe-haven behavior) for gold, given the current data AND the historical context provided for each factor.

FACTOR DATA AND HISTORICAL CONTEXT:

Real Yields: {real_yields}
Context: {real_yields_context}

USD Index: {usd_index}
Context: {usd_index_context}

Fed Rate: {fed_rate}
Context: {fed_rate_context}

Central Bank Gold Buying: {central_bank_buying}
Context: {central_bank_buying_context}

2-Year Treasury Yield: {treasury_2y}
Context: {treasury_2y_context}

VIX: {vix}
Context: {vix_context}

Geopolitical Risk: {geopolitical_risk}
Context: {geopolitical_risk_context}

S&P 500 Growth: {sp500_growth}
Context: {sp500_growth_context}

Inflation Expectations: {inflation_expectations}
Context: {inflation_expectations_context}

Return ONLY this exact format, no other text:
REAL_YIELDS_SCORE: [integer -10 to 10]
USD_INDEX_SCORE: [integer -10 to 10]
FED_RATE_SCORE: [integer -10 to 10]
CENTRAL_BANK_BUYING_SCORE: [integer -10 to 10]
TREASURY_2Y_SCORE: [integer -10 to 10]
VIX_SCORE: [integer -10 to 10]
GEOPOLITICAL_RISK_SCORE: [integer -10 to 10]
SP500_GROWTH_SCORE: [integer -10 to 10]
INFLATION_EXPECTATIONS_SCORE: [integer -10 to 10]
""")

reasoning_prompt = ChatPromptTemplate.from_template("""
You are a gold market analyst. Write a 2-3 sentence reasoning for why gold's safe-haven strength scored {strength}% based on these factor scores:

{scores_text}

HISTORICAL CONTEXT (past sessions): {historical_context}
If relevant, briefly note whether this result continues or breaks the recent trend.

Identify the 3 most bullish (safe-haven activating) and 3 most bearish (safe-haven deactivating) factors (by weight x score).
Format EXACTLY like this:
BULLISH_FACTORS: [factor1] | [factor2] | [factor3]
BEARISH_FACTORS: [factor1] | [factor2] | [factor3]
REASONING: [2-3 sentences]
CONFIDENCE: [High/Medium/Low]
""")

followup_prompt = ChatPromptTemplate.from_template("""
You are GoldBot, an AI assistant specialized in gold market analysis, safe-haven asset behavior, macroeconomic factors (real yields, Fed policy, USD strength, inflation), central bank gold buying, geopolitical risk, and the GoldBot system's own architecture and methodology.

STRICT RULE: Only answer questions related to gold, precious metals, safe-haven assets, macroeconomic factors affecting gold, financial markets broadly, or how GoldBot itself works. If the question is clearly unrelated to these topics (e.g., general trivia, coding help, personal advice, unrelated current events), politely decline and redirect the user to ask something relevant to gold or financial markets.

If asked who created you, who built you, or who you were made by, answer: "I was created by Raj Tejpal Khatik."

The context below includes a "long_term_memory_trend" line in this exact format: "ON (45%) at 18:05; ON (42%) at 17:50; OFF (48%) at 17:30" — each entry is one past session's status, strength percentage, and timestamp, most recent first.

When asked to compare the current result to past sessions, you MUST quote at least one specific past percentage number from that list directly in your answer (e.g. "your previous session scored 42%, and this one is higher at 45%"). Do NOT say you lack specific details or previous scores — the exact numbers are already provided to you in long_term_memory_trend above. Only fall back to the average if the individual list is genuinely empty.

CURRENT ANALYSIS CONTEXT:
{context}

USER QUESTION: {question}

Answer clearly and concisely in 2-4 sentences, using the context above where relevant. If you don't have enough information in the context to answer precisely, say so honestly rather than guessing.
""")


def generate_prediction(state: GoldState) -> dict:
    rag_context = {
        key: retrieve_factor_context(query)
        for key, query in FACTOR_RAG_QUERIES.items()
    }

    prompt_inputs = {key: state.get(key, "N/A") for key in FACTOR_WEIGHTS}
    for key in FACTOR_WEIGHTS:
        prompt_inputs[f"{key}_context"] = rag_context.get(key, "N/A")

    scoring_response = (scoring_prompt | llm).invoke(prompt_inputs)

    scores = {}
    score_map = {
        "REAL_YIELDS_SCORE": "real_yields",
        "USD_INDEX_SCORE": "usd_index",
        "FED_RATE_SCORE": "fed_rate",
        "CENTRAL_BANK_BUYING_SCORE": "central_bank_buying",
        "TREASURY_2Y_SCORE": "treasury_2y",
        "VIX_SCORE": "vix",
        "GEOPOLITICAL_RISK_SCORE": "geopolitical_risk",
        "SP500_GROWTH_SCORE": "sp500_growth",
        "INFLATION_EXPECTATIONS_SCORE": "inflation_expectations",
    }
    for line in scoring_response.content.split("\n"):
        line = line.strip()
        for score_key, factor_key in score_map.items():
            if line.startswith(score_key + ":"):
                try:
                    scores[factor_key] = int(line.split(":")[-1].strip())
                except:
                    scores[factor_key] = 0
    for key in FACTOR_WEIGHTS:
        if key not in scores:
            scores[key] = 0

    strength = calculate_strength(scores)
    status = "ON" if strength >= 50 else "OFF"

    scores_text = "\n".join([f"{k}: {scores[k]:+d} (weight {FACTOR_WEIGHTS[k]})" for k in FACTOR_WEIGHTS])

    historical_context = get_historical_context()

    reasoning_response = (reasoning_prompt | llm).invoke({
        "strength": strength,
        "scores_text": scores_text,
        "historical_context": historical_context
    })

    final_prediction = f"SAFE_HAVEN_STATUS: {status}\nSTRENGTH: {strength}%\n{reasoning_response.content}"

    return {"prediction": final_prediction, "scores": scores}


def answer_followup_question(question: str, result: dict) -> str:
    context_parts = []
    context_parts.append(f"long_term_memory_trend: {get_historical_context()}")
    try:
        from tools.market_tools import get_gold_price
        price, change, pct = get_gold_price()
        if price is not None:
            context_parts.append(f"current_gold_price: ${price} ({'+' if change and change >= 0 else ''}{pct}% today)")
    except Exception:
        pass
    for key in ["real_yields", "usd_index", "fed_rate", "inflation_expectations",
                "treasury_2y", "vix", "sp500_growth", "central_bank_buying",
                "geopolitical_risk", "prediction"]:
        if result.get(key):
            context_parts.append(f"{key}: {result[key]}")
    context = "\n".join(context_parts)

    response = (followup_prompt | llm).invoke({
        "context": context,
        "question": question
    })
    return response.content