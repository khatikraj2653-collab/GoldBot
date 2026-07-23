import os
import sys
import time
import sqlite3
import json
from zoneinfo import ZoneInfo
from datetime import datetime

UK_TZ = ZoneInfo("Europe/London")

def uk_time_str():
    return datetime.now(UK_TZ).strftime("%Y-%m-%d %H:%M")
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import streamlit as st
import base64

with open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'static', 'robot_b64.txt'), 'r') as f:
    ROBOT_IMG = f.read()
from dotenv import load_dotenv
from graph.workflow import app
from tools.market_tools import get_gold_price

load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), '.env'))
os.environ["LANGCHAIN_TRACING_V2"] = os.getenv("LANGCHAIN_TRACING_V2", "true")
os.environ["LANGCHAIN_API_KEY"] = os.getenv("LANGCHAIN_API_KEY", "")
os.environ["LANGCHAIN_PROJECT"] = os.getenv("LANGCHAIN_PROJECT", "GoldBot")


def get_db_path():
    return os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'goldbot_checkpoints.db')


def init_history_table():
    conn = sqlite3.connect(get_db_path())
    conn.execute("""
        CREATE TABLE IF NOT EXISTS analysis_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            status TEXT,
            strength TEXT,
            timestamp TEXT,
            result_json TEXT
        )
    """)
    conn.commit()
    conn.close()


def save_history(status, strength, timestamp, result):
    conn = sqlite3.connect(get_db_path())
    conn.execute(
        "INSERT INTO analysis_history (status, strength, timestamp, result_json) VALUES (?, ?, ?, ?)",
        (status, strength, timestamp, json.dumps(result))
    )
    conn.commit()
    conn.close()


def load_history(limit=10):
    conn = sqlite3.connect(get_db_path())
    cursor = conn.execute(
        "SELECT id, status, strength, timestamp FROM analysis_history ORDER BY id DESC LIMIT ?",
        (limit,)
    )
    rows = cursor.fetchall()
    conn.close()
    return [{"id": r[0], "status": r[1], "strength": r[2], "time": r[3]} for r in rows]


def load_history_detail(history_id):
    conn = sqlite3.connect(get_db_path())
    cursor = conn.execute("SELECT result_json FROM analysis_history WHERE id = ?", (history_id,))
    row = cursor.fetchone()
    conn.close()
    return json.loads(row[0]) if row else None


init_history_table()

st.set_page_config(page_title="GoldBot", page_icon="🪙", layout="wide", initial_sidebar_state="expanded")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=Space+Grotesk:wght@500;600;700;800&display=swap');

html, body, [data-testid="stAppViewContainer"], [data-testid="stMain"] {
    background: #1A1712 !important;
    font-family: 'Inter', sans-serif !important;
}
[data-testid="stAppViewContainer"]::before {
    content: '';
    position: fixed; top: 0; left: 0; right: 0; bottom: 0;
    background-image:
        linear-gradient(rgba(255,190,60,0.03) 1px, transparent 1px),
        linear-gradient(90deg, rgba(255,190,60,0.03) 1px, transparent 1px);
    background-size: 44px 44px;
    pointer-events: none; z-index: 0;
}
#MainMenu, footer, header { visibility: hidden; }
[data-testid="stToolbar"] { display: none; }
.block-container { padding: 0 !important; padding-bottom: 60px !important; max-width: 100% !important; }

[data-testid="stSidebar"] {
    background: #1A1712 !important;
    border-right: 1px solid #7A5C1E !important;
    min-width: 240px !important; max-width: 240px !important;
    transform: none !important;
    visibility: visible !important;
}
[data-testid="collapsedControl"] { display: none !important; }
[data-testid="stSidebar"] * { color: #FFFFFF !important; }

.stButton > button {
    font-family: 'Inter', sans-serif !important; font-weight: 600 !important;
    border-radius: 10px !important; border: none !important;
    background: linear-gradient(135deg, #B8860B, #FFD700) !important;
    color: #1A1712 !important;
}
.stButton > button:hover { opacity: 0.9 !important; transform: translateY(-1px) !important; }

.semi-card {
    background: #2A2318; border: 1px solid #4A3D22;
    border-radius: 12px; padding: 14px 16px; margin-bottom: 10px;
}
.card-key {
    font-size: 0.65rem; font-weight: 700; text-transform: uppercase;
    letter-spacing: 0.1em; color: #FFD700; margin-bottom: 5px;
}
.card-val { font-size: 0.8rem; color: #E8DCC0; }

.sec-label {
    font-size: 0.65rem; font-weight: 700; text-transform: uppercase;
    letter-spacing: 0.12em; color: #FFD700; margin: 18px 0 10px;
    display: flex; align-items: center; gap: 8px;
}
.sec-label::after { content: ''; flex: 1; height: 1px; background: rgba(255,190,60,0.1); }

.metric-card { border: 1px solid rgba(180,130,20,0.3); border-radius: 12px; padding: 18px 20px; text-align: center; }
.metric-num-on { font-family: 'Space Grotesk', sans-serif; font-size: 1.8rem; font-weight: 700; color: #34D399; }
.metric-num-off { font-family: 'Space Grotesk', sans-serif; font-size: 1.8rem; font-weight: 700; color: #F87171; }
.metric-lbl { font-size: 0.62rem; font-weight: 700; text-transform: uppercase; color: #999; margin-bottom: 8px; }
.bar-track { height: 5px; background: rgba(80,60,20,1); border-radius: 3px; margin-top: 10px; overflow: hidden; }
.bar-fill { height: 100%; border-radius: 3px; background: linear-gradient(90deg,#B8860B,#FFD700); }

.toggle-switch{
    width:64px;height:32px;border-radius:16px;
    position:relative;margin:0 auto;
    transition:background 0.3s ease;
}
.toggle-on{background:linear-gradient(135deg,#059669,#34D399);box-shadow:0 0 16px rgba(52,211,153,0.5);}
.toggle-off{background:linear-gradient(135deg,#991B1B,#F87171);box-shadow:0 0 16px rgba(248,113,113,0.4);}
.toggle-flip{background:linear-gradient(135deg,#B8860B,#FFD700);animation:toggle-flicker 1s ease-in-out infinite;}
@keyframes toggle-flicker{
    0%,100%{background:linear-gradient(135deg,#059669,#34D399);}
    50%{background:linear-gradient(135deg,#991B1B,#F87171);}
}
.toggle-knob{
    width:26px;height:26px;border-radius:50%;
    background:#FFFFFF;position:absolute;top:3px;
    box-shadow:0 2px 6px rgba(0,0,0,0.3);
    transition:left 0.3s ease;
}
.toggle-on .toggle-knob{left:35px;}
.toggle-off .toggle-knob{left:3px;}
.toggle-flip .toggle-knob{animation:knob-slide 1s ease-in-out infinite;}
@keyframes knob-slide{
    0%,100%{left:3px;}
    50%{left:35px;}
}

.hero-wrap { display: flex; flex-direction: column; align-items: center; justify-content: center; padding: 40px 20px 20px; position: relative; z-index: 5; }
.hero-badge {
    display: inline-flex; align-items: center; gap: 7px;
    background: rgba(180,130,20,0.15); border: 1px solid rgba(255,190,60,0.3);
    border-radius: 20px; padding: 5px 14px; font-size: 10.5px; font-weight: 600;
    color: #FFD700; margin-bottom: 20px; letter-spacing: 0.05em;
}
.bdot { width: 7px; height: 7px; border-radius: 50%; background: #FFD700; box-shadow: 0 0 8px rgba(255,215,0,0.9); animation: blink 1.8s ease-in-out infinite; display: inline-block; }
@keyframes blink { 0%,100%{opacity:0.3;} 50%{opacity:1;} }
.gold-icon { font-size: 70px; margin-bottom: 10px; animation: gold-bounce 3s ease-in-out infinite; filter: drop-shadow(0 0 24px rgba(255,215,0,0.5)); }
@keyframes gold-bounce { 0%,100% { transform: translateY(0) rotate(0deg); } 50% { transform: translateY(-8px) rotate(-3deg); } }
.hero-greeting { font-family: 'Space Grotesk', sans-serif; font-size: 1.8rem; font-weight: 700; color: #FFFFFF; margin-bottom: 8px; text-align: center; }
.hero-greeting em { font-style: normal; background: linear-gradient(135deg,#FFD700,#FFA500); -webkit-background-clip: text; -webkit-text-fill-color: transparent; background-clip: text; }
.hero-sub { font-size: 0.85rem; color: #C9B27A; margin-bottom: 20px; text-align: center; line-height: 1.7; max-width: 600px; }
@keyframes bounce{0%,100%{transform:translateY(0) rotate(0deg);}50%{transform:translateY(-10px) rotate(-3deg);}}
.robot-img{animation:bounce 3s ease-in-out infinite;}
.robot-wrap-outer{position:relative;display:inline-block;}
.robot-wrap-outer::before{
    content:'';
    position:absolute;
    top:50%;left:50%;
    width:220px;height:220px;
    transform:translate(-50%,-50%);
    background:radial-gradient(circle,rgba(255,215,0,0.55) 0%,rgba(255,190,60,0.3) 40%,rgba(255,165,0,0.1) 65%,transparent 80%);
    border-radius:50%;
    z-index:-1;
    animation:shine-pulse 3s ease-in-out infinite;
}
@keyframes shine-pulse{
    0%,100%{opacity:0.6;transform:translate(-50%,-50%) scale(1);}
    50%{opacity:1;transform:translate(-50%,-50%) scale(1.1);}
}
.robot-cloud{
    position:absolute;top:-10px;right:-180px;
    background:rgba(40,30,10,0.95);border:1px solid rgba(255,190,60,0.4);
    border-radius:50px;padding:10px 20px;font-size:13px;font-weight:600;
    color:#FFF3D6;white-space:nowrap;opacity:0;
    animation:gold-cloud-cycle 45s ease-in-out infinite;
}
.robot-cloud::before{
    content:'';position:absolute;width:14px;height:14px;border-radius:50%;
    background:rgba(40,30,10,0.95);border:1px solid rgba(255,190,60,0.4);
    left:10px;bottom:-18px;
}
.robot-cloud::after{
    content:'';position:absolute;width:7px;height:7px;border-radius:50%;
    background:rgba(40,30,10,0.95);border:1px solid rgba(255,190,60,0.4);
    left:0px;bottom:-28px;
}
.robot-cloud:nth-child(1){animation-delay:0s;}
.robot-cloud:nth-child(2){animation-delay:3s;}
.robot-cloud:nth-child(3){animation-delay:6s;}
.robot-cloud:nth-child(4){animation-delay:9s;}
.robot-cloud:nth-child(5){animation-delay:12s;}
.robot-cloud:nth-child(6){animation-delay:15s;}
.robot-cloud:nth-child(7){animation-delay:18s;}
.robot-cloud:nth-child(8){animation-delay:21s;}
.robot-cloud:nth-child(9){animation-delay:24s;}
.robot-cloud:nth-child(10){animation-delay:27s;}
.robot-cloud:nth-child(11){animation-delay:30s;}
.robot-cloud:nth-child(12){animation-delay:33s;}
.robot-cloud:nth-child(13){animation-delay:36s;}
.robot-cloud:nth-child(14){animation-delay:39s;}
.robot-cloud:nth-child(15){animation-delay:42s;}
@keyframes gold-cloud-cycle{
    0%{opacity:0;transform:translateY(6px);}
    3%{opacity:1;transform:translateY(0);}
    9%{opacity:1;transform:translateY(0);}
    12%{opacity:0;transform:translateY(-6px);}
    100%{opacity:0;}
}
.gb-antenna-ball{width:12px;height:12px;border-radius:50%;background:radial-gradient(circle at 35% 30%,#FFEE99,#FFD700);box-shadow:0 0 14px rgba(255,215,0,0.9);}
.gb-antenna-stick{width:4px;height:16px;background:linear-gradient(to bottom,#E8D8B0,#B8A060);border-radius:3px;}
.gb-head{width:110px;height:95px;background:radial-gradient(circle at 38% 28%,#FFFFFF,#FFF3D6 55%,#E8D8A8);border-radius:38px;position:relative;display:flex;align-items:center;justify-content:center;box-shadow:inset -3px -3px 12px rgba(180,130,20,0.1),0 4px 20px rgba(0,0,0,0.3);}
.gb-head::before{content:'';position:absolute;top:10px;left:16px;width:32px;height:9px;background:rgba(255,255,255,0.55);border-radius:6px;transform:rotate(-10deg);}
.gb-visor{width:84px;height:32px;background:linear-gradient(135deg,#FFD700 0%,#FFA500 50%,#B8860B 100%);border-radius:11px;display:flex;align-items:center;justify-content:center;gap:12px;box-shadow:0 0 18px rgba(255,190,60,0.65);}
.gb-eye{width:13px;height:13px;border-radius:50%;background:radial-gradient(circle at 35% 30%,#FFFFCC,#FFD700);box-shadow:0 0 10px rgba(255,220,0,0.95);}
.gb-neck{width:28px;height:12px;background:linear-gradient(to bottom,#F5E8C8,#D8C8A0);border-radius:5px;margin:1px 0;}
.gb-body{width:100px;height:85px;background:radial-gradient(circle at 36% 28%,#FFFFFF,#FFF0D8 55%,#D8C8A8);border-radius:26px;position:relative;display:flex;align-items:center;justify-content:center;box-shadow:inset -2px -2px 10px rgba(180,130,20,0.08),0 4px 18px rgba(0,0,0,0.25);}
.gb-screen{width:52px;height:34px;background:linear-gradient(135deg,#2A1F08,#3A2A0A);border-radius:8px;border:1.5px solid rgba(255,190,60,0.4);display:flex;flex-direction:column;align-items:center;justify-content:center;gap:4px;}
.gb-bar1{width:32px;height:3px;background:linear-gradient(90deg,#FFD700,#FFEE88);border-radius:2px;}
.gb-bar2{width:24px;height:3px;background:linear-gradient(90deg,#B8860B,#FFD700);border-radius:2px;opacity:0.7;}
.gb-armL{position:absolute;left:-26px;top:14px;width:22px;height:50px;background:radial-gradient(circle at 40% 30%,#FFFFFF,#F5E8C8 60%,#D8C8A0);border-radius:11px;}
.gb-armR{position:absolute;right:-26px;top:14px;width:22px;height:50px;background:radial-gradient(circle at 40% 30%,#FFFFFF,#F5E8C8 60%,#D8C8A0);border-radius:11px;}
.gb-legs{display:flex;gap:12px;margin-top:3px;}
.gb-leg{width:24px;height:32px;background:radial-gradient(circle at 40% 30%,#FFF3D6,#D8C8A0);border-radius:10px;}
.gb-feet{display:flex;gap:8px;margin-top:2px;}
.gb-foot{width:32px;height:14px;background:linear-gradient(to right,#4A3510,#2A1F08);border-radius:7px;box-shadow:0 3px 8px rgba(0,0,0,0.4);}            

.reasoning-card {
    background: rgba(40,30,10,0.55); border-left: 2px solid #FFD700;
    border-radius: 0 10px 10px 0; padding: 12px 16px;
    font-size: 0.8rem; color: #D4C094; line-height: 1.75; margin-top: 8px;
}
</style>
""", unsafe_allow_html=True)


def smart_truncate(text, limit: int = 1200) -> str:
    text = str(text)
    if len(text) <= limit:
        return text
    window = text[:limit + 80]
    for punct in ['. ', '! ', '? ']:
        idx = window.rfind(punct, 0, limit + 80)
        if idx != -1 and idx > limit * 0.5:
            return window[:idx + 1].strip()
    return text[:limit].rsplit(' ', 1)[0].strip() + "..."


def score_badge(key, scores, result=None):
    score = scores.get(key)
    if result is not None:
        raw = str(result.get(key, ""))
        if "Data unavailable" in raw or "no usable content" in raw.lower():
            score = 0
    if score is None:
        return ""
    if score > 0:
        color, label = "#34D399", "Bullish"
    elif score < 0:
        color, label = "#F87171", "Bearish"
    else:
        color, label = "#888", "Neutral"
    sign = "+" if score > 0 else ""
    return f"<div style='margin-top:6px;font-size:0.75rem;font-weight:600'><span style='color:#888'>Score: </span><span style='color:{color}'>{sign}{score}</span><span style='color:{color}'>&nbsp;&nbsp;{label}</span></div>"


if "result" not in st.session_state:
    st.session_state.result = None
if "history" not in st.session_state:
    st.session_state.history = load_history()
if "thread_id" not in st.session_state:
    st.session_state.thread_id = f"session_{int(time.time())}"

with st.sidebar:
    st.markdown("""
    <div style='display:flex;align-items:center;gap:10px;margin-bottom:4px'>
        <div style='width:32px;height:32px;border-radius:8px;background:linear-gradient(135deg,#B8860B,#FFD700);display:flex;align-items:center;justify-content:center;font-size:15px'>🪙</div>
        <span style='font-family:Space Grotesk,sans-serif;font-size:16px;font-weight:700;color:#FFF3D6'>GoldBot</span>
    </div>
    <div style='font-size:0.72rem;color:#AAAAAA;margin-bottom:18px'>9-Factor Safe Haven Analyser</div>
    """, unsafe_allow_html=True)

    st.page_link("app.py", label="Home", use_container_width=True)

    if st.button("+ New Analysis", use_container_width=True):
        st.session_state.result = None
        st.rerun()

    st.markdown("<hr style='border-color:rgba(255,190,60,0.1);margin:14px 0'>", unsafe_allow_html=True)
    st.markdown("<div style='font-size:0.65rem;color:#AAAAAA;text-transform:uppercase;letter-spacing:0.1em;margin-bottom:10px'>HISTORY</div>", unsafe_allow_html=True)

    if st.session_state.history:
        for item in st.session_state.history[:10]:
            label = f"{item['status']}  {item.get('strength','?')}  {item['time']}"
            if st.button(label, key=f"hist_{item['id']}", use_container_width=True):
                result_r = load_history_detail(item['id'])
                if result_r is not None:
                    st.session_state.result = result_r
                    st.rerun()


if not st.session_state.result:
    robot_img_tag = f"""<div class='robot-wrap-outer'>
        <img class='robot-img' src='data:image/png;base64,{ROBOT_IMG}' width='180' style='border-radius:24px;filter:drop-shadow(0 0 24px rgba(255,190,60,0.4)) sepia(1) hue-rotate(0deg) saturate(2.5);margin-bottom:16px;'/>
        <div class='robot-cloud'>Gold: Safe Haven? 🪙</div>
        <div class='robot-cloud'>9 live factors ⚡</div>
        <div class='robot-cloud'>RAG-grounded 📚</div>
        <div class='robot-cloud'>Ask me anything 👋</div>
        <div class='robot-cloud'>Real yields tracked 📉</div>
        <div class='robot-cloud'>No hallucination 🎯</div>
        <div class='robot-cloud'>Central bank buying 🏛️</div>
        <div class='robot-cloud'>Warsh Shock tested 🔬</div>
        <div class='robot-cloud'>USD Index live 💵</div>
        <div class='robot-cloud'>VIX monitored 😨</div>
        <div class='robot-cloud'>Fed policy tracked 🏦</div>
        <div class='robot-cloud'>Geopolitical risk 🌏</div>
        <div class='robot-cloud'>Strength % scored 📊</div>
        <div class='robot-cloud'>Deterministic weighting ⚖️</div>
        <div class='robot-cloud'>GoldBot for gold 🪙</div>
    </div>"""
    st.markdown(f"""
    <div class='hero-wrap'>
        <div class='hero-badge'><span class='bdot'></span> LIVE · 9-Factor Safe Haven Analysis</div>
        {robot_img_tag}
        <div class='hero-greeting'>Hi! I am <em>GoldBot</em></div>
        <div class='hero-sub'>
            AI-powered gold safe-haven analyser · 9 real-time factors<br>
            Macro · Safe Haven Signals · Geopolitical
        </div>
    </div>
    """, unsafe_allow_html=True)
else:
    col_h1, col_h2 = st.columns([5, 1])
    with col_h1:
        st.markdown("""
        <div style='padding:24px 32px 0'>
            <div style='font-family:Space Grotesk,sans-serif;font-size:1.3rem;font-weight:700;color:#FFF3D6;margin-bottom:4px'>
                Gold Safe Haven Analysis
            </div>
            <div style='font-size:0.75rem;color:#C9B27A'>9-Factor Agentic RAG · Real-time APIs</div>
        </div>
        """, unsafe_allow_html=True)

if not st.session_state.result:
    col_l, col_m, col_r = st.columns([1, 2, 1])
    with col_m:
        st.markdown("<div style='padding-top:60px;text-align:center'>", unsafe_allow_html=True)
        analyse = st.button("Run Analysis →", use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)

    if analyse:
        st.session_state.thread_id = f"session_{int(time.time())}"

        progress_bar = st.progress(0, text="Starting analysis...")
        ph_macro = st.empty()
        ph_safe_haven = st.empty()
        ph_geo = st.empty()

        def make_cards(data, pairs, label):
            html = f"<div class='sec-label'>{label}</div>"
            for lbl, key in pairs:
                val = smart_truncate(data.get(key, "Loading..."))
                html += f"<div class='semi-card'><div class='card-key'>{lbl}</div><div class='card-val'>{val}</div></div>"
            return html

        result = {}
        nodes_done = 0
        total_nodes = 4

        try:
            for chunk in app.stream(
                {},
                config={"configurable": {"thread_id": st.session_state.thread_id}},
                stream_mode="updates"
            ):
                for node_name, node_data in chunk.items():
                    for k, v in node_data.items():
                        if v:
                            result[k] = v
                    nodes_done += 1
                    pct = int((nodes_done / total_nodes) * 100)

                    if node_name == "fetch_macro":
                        progress_bar.progress(pct, text="Macro factors loaded")
                        ph_macro.markdown(make_cards(result, [
                            ("Real Yields", "real_yields"), ("USD Index", "usd_index"),
                            ("Fed Rate", "fed_rate"), ("Inflation Expectations", "inflation_expectations")
                        ], "Macro"), unsafe_allow_html=True)

                    elif node_name == "fetch_safe_haven":
                        progress_bar.progress(pct, text="Safe haven signals loaded")
                        ph_safe_haven.markdown(make_cards(result, [
                            ("2-Year Treasury", "treasury_2y"), ("VIX", "vix"), ("S&P 500 Growth", "sp500_growth")
                        ], "Safe Haven Signals"), unsafe_allow_html=True)

                    elif node_name == "fetch_geopolitical":
                        progress_bar.progress(pct, text="Geopolitical signals loaded")
                        ph_geo.markdown(make_cards(result, [
                            ("Central Bank Buying", "central_bank_buying"), ("Geopolitical Risk", "geopolitical_risk")
                        ], "Geopolitical"), unsafe_allow_html=True)

                    elif node_name == "generate_prediction":
                        progress_bar.progress(100, text="Prediction complete")

            progress_bar.empty()
            st.session_state.result = result

            pred_text = result.get("prediction", "")
            status_hist = "OFF"
            strength_hist = "0%"
            for line in pred_text.split("\n"):
                if "SAFE_HAVEN_STATUS:" in line:
                    status_hist = line.split(":")[-1].strip()
                if "STRENGTH:" in line:
                    strength_hist = line.split(":")[-1].strip()

            save_history(status_hist, strength_hist, uk_time_str(), result)
            st.session_state.history = load_history()
            st.rerun()

        except Exception as e:
            st.error(f"Analysis failed: {str(e)}")

if st.session_state.result:
    result = st.session_state.result
    prediction = result.get("prediction", "")
    scores = result.get("scores", {})

    status = "OFF"
    strength = 0
    reasoning = ""
    confidence = "Medium"
    bullish = []
    bearish = []

    for line in prediction.split("\n"):
        line = line.strip()
        if "SAFE_HAVEN_STATUS:" in line:
            status = line.split(":")[-1].strip()
        elif "STRENGTH:" in line:
            try: strength = int(float(line.split(":")[-1].strip().replace("%", "")))
            except: pass
        elif "REASONING:" in line:
            reasoning = line.replace("REASONING:", "").strip()
        elif "CONFIDENCE:" in line:
            confidence = line.replace("CONFIDENCE:", "").strip()
        elif "BULLISH_FACTORS:" in line:
            bullish = [x.strip() for x in line.replace("BULLISH_FACTORS:", "").split("|") if x.strip()]
        elif "BEARISH_FACTORS:" in line:
            bearish = [x.strip() for x in line.replace("BEARISH_FACTORS:", "").split("|") if x.strip()]

    st.markdown("<div style='padding:0 32px'>", unsafe_allow_html=True)

    st.markdown("<div class='sec-label'>Macro</div>", unsafe_allow_html=True)
    for label, key in [("Real Yields", "real_yields"), ("USD Index", "usd_index"), ("Fed Rate", "fed_rate"), ("Inflation Expectations", "inflation_expectations")]:
        st.markdown(f"<div class='semi-card'><div class='card-key'>{label}</div><div class='card-val'>{smart_truncate(result.get(key,'N/A'))}</div>{score_badge(key, scores, result)}</div>", unsafe_allow_html=True)

    st.markdown("<div class='sec-label'>Safe Haven Signals</div>", unsafe_allow_html=True)
    for label, key in [("2-Year Treasury", "treasury_2y"), ("VIX", "vix"), ("S&P 500 Growth", "sp500_growth")]:
        st.markdown(f"<div class='semi-card'><div class='card-key'>{label}</div><div class='card-val'>{smart_truncate(result.get(key,'N/A'))}</div>{score_badge(key, scores, result)}</div>", unsafe_allow_html=True)

    st.markdown("<div class='sec-label'>Geopolitical</div>", unsafe_allow_html=True)
    for label, key in [("Central Bank Buying", "central_bank_buying"), ("Geopolitical Risk", "geopolitical_risk")]:
        st.markdown(f"<div class='semi-card'><div class='card-key'>{label}</div><div class='card-val'>{smart_truncate(result.get(key,'N/A'))}</div>{score_badge(key, scores, result)}</div>", unsafe_allow_html=True)

    st.markdown("<hr style='border-color:rgba(255,190,60,0.08);margin:24px 0'>", unsafe_allow_html=True)
    st.markdown("<div style='font-family:Space Grotesk,sans-serif;font-size:1rem;font-weight:600;color:#FFF3D6;margin-bottom:14px'>Prediction</div>", unsafe_allow_html=True)

    p1, p2 = st.columns([1.2, 2.6])
    with p1:
        toggle_class = "toggle-on" if status == "ON" else "toggle-off"
        status_class = "metric-num-on" if status == "ON" else "metric-num-off"
        toggle_placeholder = st.empty()
        result_key = str(result.get("prediction", ""))[:50]
        if st.session_state.get("last_animated_result") != result_key:
            toggle_placeholder.markdown("""
            <div class='metric-card'>
                <div class='metric-lbl'>Safe Haven Status</div>
                <div class='toggle-switch toggle-flip'><div class='toggle-knob'></div></div>
                <div class='metric-lbl' style='margin-top:8px;color:#8A7A50'>Calculating...</div>
            </div>""", unsafe_allow_html=True)
            time.sleep(6)
            st.session_state.last_animated_result = result_key
        toggle_placeholder.markdown(f"""
        <div class='metric-card'>
            <div class='metric-lbl'>Safe Haven Status</div>
            <div class='toggle-switch {toggle_class}'><div class='toggle-knob'></div></div>
            <div class='{status_class}' style='margin-top:8px'>{status}</div>
            <div class='metric-lbl' style='margin-top:10px'>Strength: {strength}%</div>
            <div class='bar-track'><div class='bar-fill' style='width:{strength}%'></div></div>
        </div>""", unsafe_allow_html=True)
    with p2:
        bullish_html = "".join([f"<div style='font-size:0.8rem;color:#34D399;margin-bottom:4px'>+ {b}</div>" for b in bullish[:3]])
        bearish_html = "".join([f"<div style='font-size:0.8rem;color:#F87171;margin-bottom:4px'>- {b}</div>" for b in bearish[:3]])
        st.markdown(f"""
        <div class='metric-card' style='text-align:left'>
            <div style='display:grid;grid-template-columns:1fr 1fr;gap:16px'>
                <div><div style='font-size:0.62rem;color:#888;font-weight:700;text-transform:uppercase;margin-bottom:8px'>Bullish (Activating)</div>{bullish_html}</div>
                <div><div style='font-size:0.62rem;color:#888;font-weight:700;text-transform:uppercase;margin-bottom:8px'>Bearish (Deactivating)</div>{bearish_html}</div>
            </div>
            <div style='margin-top:12px;font-size:0.7rem;color:#888'>Confidence: <strong style='color:#FFD700'>{confidence}</strong></div>
        </div>""", unsafe_allow_html=True)

    if reasoning:
        st.markdown(f"<div class='reasoning-card'>{reasoning}</div>", unsafe_allow_html=True)

    st.markdown("<hr style='border-color:rgba(255,190,60,0.08);margin:24px 0'>", unsafe_allow_html=True)
    st.markdown("<div style='font-family:Space Grotesk,sans-serif;font-size:1rem;font-weight:600;color:#FFF3D6;margin-bottom:6px'>Ask a follow-up question</div>", unsafe_allow_html=True)
    st.markdown("<div style='font-size:0.75rem;color:#8A7A50;margin-bottom:14px'>Ask about factors, gold market behavior, or how GoldBot works</div>", unsafe_allow_html=True)

    if "followup_history" not in st.session_state:
        st.session_state.followup_history = []

    for qa in st.session_state.followup_history:
        st.markdown(f"<div style='background:rgba(40,30,10,0.5);border-radius:10px;padding:10px 14px;margin-bottom:8px;font-size:0.8rem;color:#D4C094'><strong style='color:#FFD700'>You:</strong> {qa['q']}<br><strong style='color:#FFD700'>GoldBot:</strong> {qa['a']}</div>", unsafe_allow_html=True)

    q_col1, q_col2 = st.columns([4, 1])
    with q_col1:
        followup_q = st.text_input("Question", placeholder="e.g. How does real yields affect gold? What if VIX spikes?", label_visibility="collapsed", key="followup_input")
    with q_col2:
        ask_clicked = st.button("Ask →", use_container_width=True)

    if ask_clicked and followup_q.strip():
        from graph.nodes import answer_followup_question
        with st.spinner("Thinking..."):
            answer = answer_followup_question(followup_q.strip(), result)
        st.session_state.followup_history.append({"q": followup_q.strip(), "a": answer})
        st.rerun()

    st.markdown("""
    <div style='background:rgba(80,60,10,0.3);border:1px solid rgba(200,150,20,0.25);border-radius:10px;padding:11px 15px;font-size:0.72rem;color:#D4A017;line-height:1.6;margin-top:18px'>
        Warning: This analysis is generated by an AI research tool for informational and academic purposes only.
        It does NOT constitute financial advice. Always consult a qualified financial advisor.
    </div>
    """, unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)


def one_word_signal(score):
    if score is None:
        return "N/A"
    if score > 3:
        return "Bullish"
    elif score > 0:
        return "Mild+"
    elif score < -3:
        return "Bearish"
    elif score < 0:
        return "Mild-"
    else:
        return "Neutral"


@st.cache_data(ttl=900)
def get_ticker_data(scores_snapshot, unavailable_snapshot):
    price, change, pct = get_gold_price()
    if price is None:
        return "GOLD (GC=F): N/A"

    arrow = "▲" if change and change >= 0 else "▼"
    color = "#34D399" if change and change >= 0 else "#F87171"
    price_html = f"<span style='margin-right:32px'><strong style='color:#FFD700'>GOLD</strong> <span style='color:#FFF3D6'>${price}</span> <span style='color:{color}'>{arrow} {pct}%</span></span>"

    factor_labels = [
        ("Real Yields", "real_yields"), ("USD Index", "usd_index"), ("Fed Rate", "fed_rate"),
        ("Inflation Exp.", "inflation_expectations"), ("2Y Treasury", "treasury_2y"), ("VIX", "vix"),
        ("S&P 500", "sp500_growth"), ("CB Buying", "central_bank_buying"), ("Geo Risk", "geopolitical_risk")
    ]

    def signal_color(signal):
        if signal in ("Bullish", "Mild+"):
            return "#34D399"
        elif signal in ("Bearish", "Mild-"):
            return "#F87171"
        else:
            return "#8A7A50"

    factor_html = ""
    for label, key in factor_labels:
        score_val = 0 if key in unavailable_snapshot else scores_snapshot.get(key)
        signal = one_word_signal(score_val)
        color = signal_color(signal)
        factor_html += f"<span style='margin-right:32px'><strong style='color:#C9B27A'>{label}</strong> <span style='color:{color};font-weight:600'>{signal}</span></span>"

    return price_html + factor_html


current_scores = st.session_state.result.get("scores", {}) if st.session_state.result else {}
current_unavailable = set()
if st.session_state.result:
    for k in current_scores:
        raw_v = str(st.session_state.result.get(k, ""))
        if "Data unavailable" in raw_v or "no usable content" in raw_v.lower():
            current_unavailable.add(k)
ticker_html = get_ticker_data(current_scores, frozenset(current_unavailable))

st.markdown(f"""
<style>
.ticker-wrap {{
    position: fixed; bottom: 0; left: 0; right: 0; z-index: 9999;
    background: #201B10;
    border-top: 1px solid rgba(255,190,60,0.2);
    padding: 8px 0; overflow: hidden;
}}
.ticker-move {{
    display: inline-block; white-space: nowrap;
    animation: ticker-scroll 40s linear infinite;
    font-size: 0.78rem; font-family: 'Inter', sans-serif;
}}
@keyframes ticker-scroll {{
    0% {{ transform: translateX(100vw); }}
    100% {{ transform: translateX(-100%); }}
}}
</style>
<div class='ticker-wrap'>
    <div class='ticker-move'>{ticker_html}&nbsp;&nbsp;&nbsp;&nbsp;{ticker_html}</div>
</div>
""", unsafe_allow_html=True)