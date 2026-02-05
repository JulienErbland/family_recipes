import streamlit as st
from pathlib import Path

def load_css():
    css_path = Path("app/static/style.css")
    if css_path.exists():
        st.markdown(f"<style>{css_path.read_text()}</style>", unsafe_allow_html=True)
