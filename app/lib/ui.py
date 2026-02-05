from pathlib import Path
import streamlit as st

def load_css():
    css_path = Path(__file__).parents[2] / "assets" / "style.css"
    if css_path.exists():
        st.markdown(
            f"<style>{css_path.read_text()}</style>",
            unsafe_allow_html=True,
        )
