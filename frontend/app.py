import streamlit as st
import os
import sys

# Windows' default console encoding (cp1252) can't print many Unicode
# characters (emoji, symbols) that show up in fetched news text or API
# errors. Force UTF-8 with a safe fallback so print() never crashes.
for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8", errors="replace")

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from log_client import log_event
from chat_bubble import render_chat_bubble

st.set_page_config(
    page_title="GoldBot - AI Gold Safe-Haven Analyser",
    page_icon="::",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# SEO tags injected into the real top-level document (st.markdown runs in
# Streamlit's own DOM, unlike st.components.v1.html which sandboxes into an
# iframe Google's crawler won't associate with this page's <head>).
st.markdown("""
<script>
(function() {
  document.title = "GoldBot — AI Gold Safe-Haven Analyser";
  function setMeta(attr, key, content) {
    let el = document.querySelector(`meta[${attr}="${key}"]`);
    if (!el) { el = document.createElement('meta'); el.setAttribute(attr, key); document.head.appendChild(el); }
    el.setAttribute('content', content);
  }
  const desc = "9-factor AI agent testing gold's safe-haven status with real-time macro and geopolitical signals, built by Raj Tejpal Khatik.";
  setMeta('name', 'description', desc);
  setMeta('property', 'og:title', "GoldBot — AI Gold Safe-Haven Analyser");
  setMeta('property', 'og:description', desc);
  setMeta('property', 'og:type', 'website');
  setMeta('property', 'og:url', 'https://goldbot-raj.streamlit.app/');
  setMeta('name', 'twitter:card', 'summary_large_image');
  setMeta('name', 'twitter:title', "GoldBot — AI Gold Safe-Haven Analyser");
  setMeta('name', 'twitter:description', desc);

  let canonical = document.querySelector('link[rel="canonical"]');
  if (!canonical) { canonical = document.createElement('link'); canonical.setAttribute('rel', 'canonical'); document.head.appendChild(canonical); }
  canonical.setAttribute('href', 'https://goldbot-raj.streamlit.app/');

  if (!document.getElementById('goldbot-jsonld')) {
    const s = document.createElement('script');
    s.type = 'application/ld+json';
    s.id = 'goldbot-jsonld';
    s.textContent = JSON.stringify({
      "@context": "https://schema.org",
      "@type": "SoftwareApplication",
      "name": "GoldBot",
      "applicationCategory": "FinanceApplication",
      "operatingSystem": "Web",
      "url": "https://goldbot-raj.streamlit.app/",
      "description": desc,
      "author": {
        "@type": "Person",
        "name": "Raj Tejpal Khatik",
        "sameAs": [
          "https://www.linkedin.com/in/raj-khatik-6ab086395",
          "https://github.com/khatikraj2653-collab",
          "https://portfolio-raj.pages.dev/"
        ]
      }
    });
    document.head.appendChild(s);
  }
})();
</script>
""", unsafe_allow_html=True)

st.markdown("""
<style>
#MainMenu, footer, header { visibility: hidden; }
[data-testid="stToolbar"] { display: none; }
[data-testid="stDecoration"] { display: none; }
[data-testid="stSidebar"] { display: none !important; }
[data-testid="collapsedControl"] { display: none !important; }
[data-testid="stSidebarNav"] { display: none !important; }
.block-container { padding: 0 !important; max-width: 100% !important; }
[data-testid="stAppViewContainer"], [data-testid="stMain"] {
    background: #1A1712 !important;
}

[data-testid="stPageLink"] {
    position: fixed !important;
    top: 14px !important;
    right: 48px !important;
    z-index: 99999 !important;
    width: auto !important;
}
[data-testid="stPageLink"] a {
    background: linear-gradient(135deg, #B8860B, #FFD700) !important;
    color: #1A1712 !important;
    border: none !important;
    border-radius: 9px !important;
    padding: 9px 22px !important;
    font-size: 13px !important;
    font-weight: 600 !important;
    font-family: 'Inter', sans-serif !important;
    box-shadow: 0 0 18px rgba(255,190,60,0.4) !important;
    text-decoration: none !important;
    display: inline-block !important;
}
[data-testid="stPageLink"] a:hover {
    box-shadow: 0 0 30px rgba(255,215,0,0.6) !important;
    transform: translateY(-1px) !important;
}
[data-testid="stPageLink"] svg { display: none !important; }

iframe[title="streamlit_component"] {
    background: transparent !important;
}
</style>
""", unsafe_allow_html=True)

if "visit_logged" not in st.session_state:
    log_event("visit", detail="landing page")
    st.session_state.visit_logged = True

st.page_link("pages/analysis.py", label="Get Started ->")

landing_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'landing.html')
with open(landing_path, 'r', encoding='utf-8') as f:
    html_content = f.read()

iframe_fixes = """
<style>
#welcomeModal { display: none !important; }
body { background: #1A1712 !important; }
#hero { min-height: 650px !important; padding-top: 40px !important; }
.nav-cta { display: none !important; }
.nav { justify-content: center !important; gap: 60px !important; }
.nav-logo { position: absolute !important; left: 48px !important; }
</style>
"""
html_content = html_content.replace('<head>', '<head>' + iframe_fixes)

st.components.v1.html(html_content, height=2850, scrolling=True)

render_chat_bubble()
