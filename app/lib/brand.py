import streamlit as st
from pathlib import Path
import base64

def sidebar_brand():
    logo_path = Path("app/static/logo.png")
    logo_html = ""
    if logo_path.exists():
        b64 = base64.b64encode(logo_path.read_bytes()).decode("utf-8")
        logo_html = f"<img src='data:image/png;base64,{b64}' />"

    st.sidebar.markdown(
        f"""
        <div class="sidebar-brand">
          {logo_html}
        </div>
        """,
        unsafe_allow_html=True
    )
