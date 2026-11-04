"""
3D dancing GoldBot for the analysis-page hero: a three.js scene rendered in a
transparent components iframe (see static/robot3d.html).
"""
import os

import streamlit.components.v1 as components

_TEMPLATE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static", "robot3d.html")


def render_robot_3d(height=420):
    """Render the dancing robot; the page is static, so no data is injected."""
    with open(_TEMPLATE_PATH, "r", encoding="utf-8") as f:
        html = f.read()
    components.html(html, height=height, scrolling=False)
