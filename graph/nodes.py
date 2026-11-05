import os
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env'))

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.messages import HumanMessage, AIMessage
from langchain_openai import ChatOpenAI
from graph.state import GoldState
from rag.retriever import retrieve_factor_context

llm = ChatOpenAI(
    model="gpt-4o",
    api_key=os.getenv("OPENAI_API_KEY"),
    temperature=0
)

llm_retry = ChatOpenAI(
    model="gpt-4o",
    api_key=os.getenv("OPENAI_API_KEY"),
    temperature=0.4
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

Score every factor that has real data, using the full -10 to +10 range. Use the explicit numeric bands below — do NOT default to 0 for mild signals. The Context section provides historical background; use it to interpret the current Data value, don't ignore it.

EXPLICIT SCORE BANDS (map numeric values deterministically):
- Real Yields: <0% = +7, 0-1% = +4, 1-2% = +1, 2-2.5% = -3, 2.5-3% = -5, >3% = -7
- USD Index (DXY): <95 = +5, 95-100 = +3, 100-102 = -3, 102-105 = -5, >105 = -7
- Fed Rate: <3% = +5, 3-4% = +3, 4-4.5% = -1, 4.5-5% = -3, >5% = -5
- 2Y Treasury: <3% = +4, 3-4% = +1, 4-4.5% = -2, 4.5-5% = -4, >5% = -6
- VIX: <13 = -5, 13-16 = -3, 16-20 = -1, 20-25 = +3, 25-35 = +6, >35 = +9
- Inflation Expectations (5Y breakeven): <2% = -3, 2-2.3% = -1, 2.3-2.6% = +2, 2.6-3% = +4, >3% = +6
- S&P 500 % change (today): >+1% = -3, 0 to +1% = -1, -1 to 0% = +1, -2 to -1% = +3, <-2% = +5
- Central Bank Buying: net buying trend = +4 to +7 depending on magnitude; neutral / slowing = 0 to +2; net selling = -3 to -5
- Geopolitical Risk: pick a sign based on the text — any active conflict / escalation = +3 to +8, de-escalation / calm = -2 to -4; mixed = +1 or +2, never 0

SCORE 0 ONLY IF the factor's Data field is literally missing or errored (contains "Data unavailable", "Too Many Requests", "Rate limited", "no usable content", or bare "N/A"). For every OTHER factor you MUST commit to a non-zero integer from the bands above.

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

Identify the bullish (safe-haven activating, score > 0) and bearish (safe-haven deactivating, score < 0) factors by weight x score.

IMPORTANT RULES:
- List up to 3 bullish factors, but ONLY ones with score > 0. If fewer than 3 have a positive score, list only those that do. If none have a positive score, write "none" after BULLISH_FACTORS:.
- List up to 3 bearish factors, but ONLY ones with score < 0. If fewer than 3 have a negative score, list only those that do. If none have a negative score, write "none" after BEARISH_FACTORS:.
- NEVER list a factor with score 0 (Neutral) in either list.

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


def _extract_number(s):
    import re
    if not isinstance(s, str):
        return None
    m = re.search(r'-?\d+\.?\d*', s)
    if not m:
        return None
    try:
        return float(m.group(0))
    except (ValueError, TypeError):
        return None


def _suggest_gold_score(factor_key, raw):
    v = _extract_number(raw)
    if v is None:
        return None
    if factor_key == "real_yields":
        # For GOLD: lower real yields = bullish
        if v < 0: return 7
        if v < 1: return 4
        if v < 2: return 1
        if v < 2.5: return -3
        if v < 3: return -5
        return -7
    if factor_key == "usd_index":
        # Stronger USD = gold-bearish
        if v < 95: return 5
        if v < 100: return 3
        if v < 102: return -3
        if v < 105: return -5
        return -7
    if factor_key == "fed_rate":
        if v < 3: return 5
        if v < 4: return 3
        if v < 4.5: return -1
        if v < 5: return -3
        return -5
    if factor_key == "treasury_2y":
        if v < 3: return 4
        if v < 4: return 1
        if v < 4.5: return -2
        if v < 5: return -4
        return -6
    if factor_key == "vix":
        # Higher VIX = safe-haven bid for gold
        if v < 13: return -5
        if v < 16: return -3
        if v < 20: return -1
        if v < 25: return 3
        if v < 35: return 6
        return 9
    if factor_key == "inflation_expectations":
        # 5Y breakeven — higher expectations = gold hedge bullish
        if v < 2: return -3
        if v < 2.3: return -1
        if v < 2.6: return 2
        if v < 3: return 4
        return 6
    if factor_key == "sp500_growth":
        # Negative S&P = gold safe-haven bid
        if v > 1: return -3
        if v > 0: return -1
        if v > -1: return 1
        if v > -2: return 3
        return 5
    return None


HINTABLE_FACTORS = {"real_yields", "usd_index", "fed_rate", "treasury_2y", "vix", "inflation_expectations", "sp500_growth"}


def generate_prediction(state: GoldState) -> dict:
    from tools.cache_utils import _looks_like_error
    rag_context = {
        key: retrieve_factor_context(query)
        for key, query in FACTOR_RAG_QUERIES.items()
    }

    prompt_inputs = {key: state.get(key, "N/A") for key in FACTOR_WEIGHTS}
    for key in FACTOR_WEIGHTS:
        prompt_inputs[f"{key}_context"] = rag_context.get(key, "N/A")

    rendered_messages = scoring_prompt.format_messages(**prompt_inputs)
    scoring_response = llm.invoke(rendered_messages)

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

    def _parse(raw):
        import re
        out = {}
        for line in raw.split("\n"):
            cleaned = re.sub(r'^[\s\-\*\d\.\`]*\**\s*', '', line).strip().rstrip('*').strip()
            for score_key, factor_key in score_map.items():
                if cleaned.startswith(score_key + ":"):
                    tail = cleaned.split(":", 1)[-1]
                    m = re.search(r'-?\d+', tail)
                    if m:
                        try:
                            out[factor_key] = max(-10, min(10, int(m.group(0))))
                        except (ValueError, TypeError):
                            out[factor_key] = 0
                    else:
                        out[factor_key] = 0
                    break
        return out

    scores = _parse(scoring_response.content)
    for key in FACTOR_WEIGHTS:
        if key not in scores:
            scores[key] = 0

    # Deterministic guardrail: force 0 only for truly missing data.
    from tools.cache_utils import _looks_like_error
    for factor_key in score_map.values():
        if _looks_like_error(str(state.get(factor_key, ""))):
            scores[factor_key] = 0

    # LLM self-correction loop: if LLM scored 0 for real-data factors,
    # hand it back its own response and ask to re-score. Max 2 retries.
    for attempt in range(2):
        zero_offenders = [
            (k, str(state.get(k, ""))[:150])
            for k in score_map.values()
            if scores.get(k, 0) == 0 and not _looks_like_error(str(state.get(k, "")))
        ]
        if not zero_offenders:
            break
        offender_list = "\n".join(f"- {k}: '{v}'" for k, v in zero_offenders)
        complaint = (
            f"YOUR PREVIOUS RESPONSE IS REJECTED. You scored {len(zero_offenders)} factors as 0 "
            f"despite them having REAL DATA. The EXPLICIT SCORE BANDS tell you exactly what "
            f"number to pick for each value — you MUST use them.\n\n"
            f"The following scores MUST be changed to a non-zero integer per the bands:\n"
            f"{offender_list}\n\n"
            f"Example: if USD Index is 101.42, the bands say USD 100-102 = -3. Pick -3, not 0. "
            f"If VIX is 16.61, the bands say VIX 16-20 = -1. Pick -1, not 0.\n\n"
            f"Re-output ALL 9 scores in the exact same format. Every factor above MUST be non-zero."
        )
        retry_response = llm_retry.invoke(
            rendered_messages
            + [AIMessage(content=scoring_response.content), HumanMessage(content=complaint)]
        )
        scoring_response = retry_response
        scores = _parse(retry_response.content)
        for key in FACTOR_WEIGHTS:
            if key not in scores:
                scores[key] = 0
        for factor_key in score_map.values():
            if _looks_like_error(str(state.get(factor_key, ""))):
                scores[factor_key] = 0

    # OPTION B: Python owns numeric-factor scores via band tables. Overrides
    # the LLM for these factors; text-heavy factors (geopolitical, central
    # bank buying) remain fully LLM-scored.
    for factor_key in HINTABLE_FACTORS:
        raw = str(state.get(factor_key, ""))
        if _looks_like_error(raw):
            continue
        python_score = _suggest_gold_score(factor_key, raw)
        if python_score is not None:
            scores[factor_key] = python_score

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