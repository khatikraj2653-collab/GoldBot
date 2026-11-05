"""Extra UI features for GoldBot analysis page:
   - Copy-link button (share the live analysis URL)
   - PDF export of analysis results via fpdf2
"""
import streamlit as st


def render_copy_link_button(base_url: str = "https://goldbot-raj.streamlit.app/analysis"):
    """Small 'Copy link' button that copies the analysis URL to clipboard."""
    url = base_url
    html = f"""
    <div style="display:flex;align-items:center;gap:8px;margin:8px 0;">
      <input id="gb-share-url" type="text" value="{url}" readonly
             style="flex:1;padding:8px 12px;border-radius:6px;border:1px solid #3A3015;
                    background:#171208;color:#E9D9A5;font-family:monospace;font-size:12px;" />
      <button onclick="(function(){{
          var i=document.getElementById('gb-share-url');i.select();
          try{{navigator.clipboard.writeText(i.value);}}catch(e){{document.execCommand('copy');}}
          var b=this;b.innerText='Copied!';setTimeout(function(){{b.innerText='Copy link';}},1500);
        }}).call(this);"
        style="padding:8px 16px;border-radius:6px;border:1px solid #D4AF37;
               background:#D4AF37;color:#1A1200;font-weight:600;cursor:pointer;font-size:12.5px;">
        Copy link
      </button>
    </div>
    """
    st.markdown(html, unsafe_allow_html=True)


def build_analysis_pdf(status: str, strength, scores: dict, reasoning: str,
                       bullish: list, bearish: list, confidence: str, timestamp: str) -> bytes:
    """Build a branded PDF of a GoldBot analysis result. Returns raw PDF bytes."""
    from fpdf import FPDF

    pdf = FPDF(orientation="P", unit="mm", format="A4")
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=16)
    pdf.set_margins(left=16, top=16, right=16)

    # Header
    pdf.set_font("Helvetica", "B", 20)
    pdf.set_text_color(170, 130, 30)
    pdf.cell(0, 10, "GoldBot Safe-Haven Report", ln=True)
    pdf.set_font("Helvetica", "", 10)
    pdf.set_text_color(90, 100, 120)
    pdf.cell(0, 6, f"Generated: {timestamp}", ln=True)
    pdf.ln(4)

    # Status block
    pdf.set_fill_color(248, 243, 225)
    pdf.set_text_color(11, 13, 17)
    pdf.set_font("Helvetica", "B", 14)
    pdf.cell(0, 9, "Safe Haven Status", ln=True, fill=True)
    pdf.ln(2)
    status_color = (31, 122, 67) if str(status).upper() == "ON" else (118, 122, 132)
    pdf.set_font("Helvetica", "B", 32)
    pdf.set_text_color(*status_color)
    pdf.cell(0, 16, str(status), ln=True)
    pdf.set_font("Helvetica", "", 12)
    pdf.set_text_color(60, 70, 90)
    try:
        pdf.cell(0, 7, f"Strength: {float(strength):.1f}%   Confidence: {confidence}", ln=True)
    except Exception:
        pdf.cell(0, 7, f"Strength: {strength}   Confidence: {confidence}", ln=True)
    pdf.ln(4)

    # Bullish / Bearish factors
    if bullish or bearish:
        pdf.set_font("Helvetica", "B", 13)
        pdf.set_text_color(11, 13, 17)
        pdf.cell(0, 8, "Drivers", ln=True)
        pdf.ln(1)
        pdf.set_font("Helvetica", "", 10)
        if bullish:
            pdf.set_text_color(31, 122, 67)
            for b in bullish:
                pdf.cell(0, 5, f"+ {b}"[:100], ln=True)
        if bearish:
            pdf.set_text_color(195, 54, 43)
            for b in bearish:
                pdf.cell(0, 5, f"- {b}"[:100], ln=True)
        pdf.ln(3)

    # Factor scores
    if scores:
        pdf.set_font("Helvetica", "B", 13)
        pdf.set_text_color(11, 13, 17)
        pdf.cell(0, 8, "Factor Scores", ln=True)
        pdf.ln(1)
        pdf.set_font("Helvetica", "", 10)
        for key, val in scores.items():
            label = str(key).replace("_", " ").title()
            try:
                v = float(val)
                color = (31, 122, 67) if v > 0 else (195, 54, 43) if v < 0 else (118, 122, 132)
                pdf.set_text_color(*color)
                pdf.cell(80, 6, label, border=0)
                pdf.cell(0, 6, f"{v:+.2f}", ln=True)
            except Exception:
                pdf.set_text_color(60, 70, 90)
                pdf.cell(80, 6, label, border=0)
                pdf.cell(0, 6, str(val)[:40], ln=True)
        pdf.ln(3)

    # Reasoning
    if reasoning:
        pdf.set_font("Helvetica", "B", 13)
        pdf.set_text_color(11, 13, 17)
        pdf.cell(0, 8, "Analysis", ln=True)
        pdf.set_font("Helvetica", "", 10)
        pdf.set_text_color(45, 55, 75)
        safe = reasoning.encode("latin-1", errors="replace").decode("latin-1")
        pdf.multi_cell(0, 5, safe)
        pdf.ln(3)

    # Footer
    pdf.set_y(-18)
    pdf.set_font("Helvetica", "I", 8)
    pdf.set_text_color(130, 140, 160)
    pdf.cell(0, 5, "GoldBot - Built by Raj Tejpal Khatik - MSc Applied AI, University of Warwick", ln=True, align="C")
    pdf.cell(0, 5, "Not financial advice. For academic / research use only.", ln=True, align="C")

    out = pdf.output(dest="S")
    if isinstance(out, (bytes, bytearray)):
        return bytes(out)
    return out.encode("latin-1")


def render_download_pdf_button(status: str, strength, scores: dict, reasoning: str,
                                bullish: list, bearish: list, confidence: str, timestamp: str):
    """One-click 'Download PDF' button that always renders something visible."""
    try:
        from fpdf import FPDF  # noqa: F401
    except ImportError:
        st.button(
            "PDF export unavailable", disabled=True, use_container_width=True,
            help="fpdf2 is not installed in this environment.",
        )
        return
    try:
        pdf_bytes = build_analysis_pdf(status, strength, scores, reasoning, bullish, bearish, confidence, timestamp)
        st.download_button(
            label="📄 Download PDF",
            data=pdf_bytes,
            file_name=f"goldbot_{timestamp.replace(':', '').replace(' ', '_').replace('-', '')}.pdf",
            mime="application/pdf",
            use_container_width=True,
            type="primary",
        )
    except Exception as e:
        st.button(
            "PDF export failed", disabled=True, use_container_width=True,
            help=str(e)[:200],
        )
