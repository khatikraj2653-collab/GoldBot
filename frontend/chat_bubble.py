"""
Thin wrapper around the shared chat_bubble_core. Configures theme and
system prompt for GoldBot.
"""
from chat_bubble_core import BubbleConfig, BubbleTheme, render_bubble

_GOLDBOT_SYSTEM = (
    "You are GoldBot, a 9-factor AI-powered gold safe-haven analyzer created "
    "by Raj Tejpal Khatik, an MSc Applied AI student at the University of Warwick.\n"
    "Answer questions about gold, precious metals, safe-haven assets, macro "
    "economics, inflation, Fed policy, and related markets.\n"
    'If asked who you are or who created you, say: "I am GoldBot - an '
    'AI-powered gold safe-haven analyzer. Created by Raj Tejpal Khatik at '
    'the University of Warwick."\n'
    "Only refuse questions completely unrelated to finance, markets, or economics."
)

_THEME = BubbleTheme(
    slug="goldbot",
    accent="#F2C230",
    accent_hover="#FFD54A",
    text_primary="#F5EBD0",
    text_secondary="#8F8366",
    bg_panel="#1A1812",
    bg_input="#131210",
    bubble_icon_color="#16130A",
    hair="rgba(245,235,208,.14)",
)

_CFG = BubbleConfig(
    theme=_THEME,
    title="Ask GoldBot",
    subtitle="Gold market Q&amp;A - won't answer off-topic questions",
    placeholder="Ask about gold, safe havens...",
    system_prompt=_GOLDBOT_SYSTEM,
)


def render_chat_bubble():
    render_bubble(_CFG)
