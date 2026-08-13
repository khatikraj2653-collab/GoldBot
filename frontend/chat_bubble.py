"""
Floating 'Ask GoldBot' chat bubble — reuses the existing
answer_followup_question() logic (same grounding, identity, live gold
price, refusal rules), just presented as a persistent floating widget
instead of an inline box. Usable from both the landing and analysis pages.
"""
import streamlit as st
from log_client import log_event

BUBBLE_CSS = """
<style>
.st-key-goldbot_bubble_toggle {
    position: fixed !important;
    bottom: 24px !important;
    right: 24px !important;
    z-index: 999999 !important;
    width: 58px !important;
}
.st-key-goldbot_bubble_toggle button {
    width: 58px !important;
    height: 58px !important;
    border-radius: 50% !important;
    background: linear-gradient(135deg, #B8860B, #FFD700) !important;
    color: #1A1712 !important;
    font-size: 26px !important;
    line-height: 1 !important;
    box-shadow: 0 4px 22px rgba(255,190,60,0.5) !important;
    border: none !important;
    padding: 0 !important;
}
.st-key-goldbot_bubble_toggle button:hover {
    box-shadow: 0 6px 30px rgba(255,215,0,0.65) !important;
    transform: translateY(-2px);
}
.st-key-goldbot_bubble_panel {
    position: fixed !important;
    bottom: 94px !important;
    right: 24px !important;
    width: 380px !important;
    max-width: calc(100vw - 32px) !important;
    max-height: calc(100vh - 140px) !important;
    background: #14100A !important;
    border: 1px solid rgba(255,190,60,0.25) !important;
    border-radius: 16px !important;
    padding: 0 !important;
    z-index: 999998 !important;
    box-shadow: 0 16px 48px rgba(0,0,0,0.55) !important;
    display: flex !important;
    flex-direction: column !important;
    overflow: hidden !important;
}
.st-key-goldbot_bubble_header {
    padding: 14px 18px 10px !important;
    border-bottom: 1px solid rgba(255,190,60,0.15) !important;
    flex-shrink: 0 !important;
}
.goldbot-bubble-title {
    font-family: 'Space Grotesk', sans-serif; font-size: 0.95rem; font-weight: 700;
    color: #FFF3D6; margin-bottom: 2px;
}
.goldbot-bubble-sub {
    font-size: 0.68rem; color: #8A7A50;
}
.st-key-goldbot_bubble_messages {
    flex: 1 1 auto !important;
    overflow-y: auto !important;
    padding: 12px 16px !important;
    min-height: 120px !important;
    max-height: 360px !important;
}
.goldbot-bubble-messages-inner {
    display: flex;
    flex-direction: column;
    gap: 8px;
}
.goldbot-bubble-user {
    background: linear-gradient(135deg,rgba(180,130,10,0.35),rgba(255,210,0,0.18));
    border: 1px solid rgba(255,190,60,0.3);
    border-radius: 14px 14px 4px 14px;
    padding: 9px 12px;
    font-size: 0.8rem; color: #FFF3D6; line-height: 1.55;
    max-width: 84%; align-self: flex-end;
}
.goldbot-bubble-bot {
    background: rgba(40,30,10,0.75);
    border: 1px solid rgba(200,150,20,0.2);
    border-radius: 14px 14px 14px 4px;
    padding: 10px 12px;
    font-size: 0.8rem; color: #F0E6C8; line-height: 1.55;
    max-width: 88%; align-self: flex-start;
}
.goldbot-bubble-typing {
    font-size: 0.75rem; color: #8A7A50; align-self: flex-start;
    padding: 2px 4px;
}
.st-key-goldbot_bubble_inputrow {
    padding: 10px 14px 14px !important;
    border-top: 1px solid rgba(255,190,60,0.15) !important;
    flex-shrink: 0 !important;
}
.st-key-goldbot_bubble_panel [data-baseweb="base-input"],
.st-key-goldbot_bubble_panel [data-baseweb="input"] {
    background: #1F1A10 !important;
    border: 1px solid rgba(255,190,60,0.3) !important;
    border-radius: 8px !important;
}
.st-key-goldbot_bubble_panel .stTextInput input {
    background: #1F1A10 !important;
    color: #FFF3D6 !important;
    font-size: 0.82rem !important;
    -webkit-text-fill-color: #FFF3D6 !important;
}
.st-key-goldbot_bubble_panel .stTextInput input::placeholder {
    color: #8A7A50 !important;
    opacity: 1 !important;
}
</style>
"""


def render_chat_bubble():
    if "bubble_open" not in st.session_state:
        st.session_state.bubble_open = False
    if "bubble_history" not in st.session_state:
        st.session_state.bubble_history = []
    if "bubble_input_counter" not in st.session_state:
        st.session_state.bubble_input_counter = 0
    if "bubble_thinking" not in st.session_state:
        st.session_state.bubble_thinking = False

    st.markdown(BUBBLE_CSS, unsafe_allow_html=True)

    with st.container(key="goldbot_bubble_toggle"):
        icon = "×" if st.session_state.bubble_open else "💬"
        if st.button(icon, key="goldbot_bubble_toggle_btn"):
            st.session_state.bubble_open = not st.session_state.bubble_open
            st.rerun()

    if not st.session_state.bubble_open:
        return

    with st.container(key="goldbot_bubble_panel"):
        with st.container(key="goldbot_bubble_header"):
            st.markdown(
                "<div class='goldbot-bubble-title'>Ask GoldBot</div>"
                "<div class='goldbot-bubble-sub'>Gold market Q&amp;A - won't answer off-topic questions</div>",
                unsafe_allow_html=True,
            )

        with st.container(key="goldbot_bubble_messages"):
            parts = ["<div class='goldbot-bubble-messages-inner'>"]
            for msg in st.session_state.bubble_history:
                css_class = "goldbot-bubble-user" if msg["role"] == "user" else "goldbot-bubble-bot"
                parts.append(f"<div class='{css_class}'>{msg['content']}</div>")
            if st.session_state.bubble_thinking:
                parts.append("<div class='goldbot-bubble-typing'>Thinking...</div>")
            parts.append("</div>")
            st.markdown("".join(parts), unsafe_allow_html=True)

        with st.container(key="goldbot_bubble_inputrow"):
            q_col, btn_col = st.columns([5, 1])
            with q_col:
                question = st.text_input(
                    "", placeholder="Ask about gold, safe havens...",
                    label_visibility="collapsed",
                    key=f"bubble_input_{st.session_state.bubble_input_counter}",
                    disabled=st.session_state.bubble_thinking,
                )
            with btn_col:
                ask = st.button(
                    "Ask", use_container_width=True, key="goldbot_bubble_ask_btn",
                    disabled=st.session_state.bubble_thinking,
                )

            if ask and question and not st.session_state.bubble_thinking:
                st.session_state.bubble_history.append({"role": "user", "content": question})
                st.session_state.bubble_thinking = True
                st.session_state.bubble_input_counter += 1
                st.rerun()

    if st.session_state.bubble_thinking:
        last_question = st.session_state.bubble_history[-1]["content"]
        from graph.nodes import answer_followup_question

        try:
            reply = answer_followup_question(last_question, st.session_state.get("result") or {})
        except Exception:
            reply = "Sorry, I couldn't process that right now. Please try again shortly."

        st.session_state.bubble_history.append({"role": "assistant", "content": reply})
        log_event("chat", question=last_question, reply=reply)
        st.session_state.bubble_thinking = False
        st.rerun()
