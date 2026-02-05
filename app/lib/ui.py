import streamlit as st
from pathlib import Path
import base64

def load_css():
    base_app_dir = Path(__file__).resolve().parents[1]  # .../app
    css_path = base_app_dir / "static" / "style.css"

    if not css_path.exists():
        st.sidebar.error("CSS not found")
        st.sidebar.write("Expected:")
        st.sidebar.code(str(css_path))

        st.sidebar.write("Contents of app/static/:")
        static_dir = base_app_dir / "static"
        if static_dir.exists():
            st.sidebar.code("\n".join([p.name for p in static_dir.iterdir()]))
        else:
            st.sidebar.warning(f"'static' folder not found at: {static_dir}")

        return

    st.markdown(f"<style>{css_path.read_text()}</style>", unsafe_allow_html=True)

def set_page_background(image_path: str, css_class: str):
    img = Path(image_path)
    if not img.exists():
        st.warning(f"Background not found: {image_path}")
        return

    b64 = base64.b64encode(img.read_bytes()).decode()

    st.markdown(
        f"""
        <style>
        body {{
          background: none !important;
        }}

        .{css_class} {{
          position: relative;
          min-height: 100vh;
          background:
            linear-gradient(rgba(255,255,255,.80), rgba(255,255,255,.80)),
            url("data:image/jpeg;base64,{b64}") center / cover no-repeat;
        }}
        </style>
        """,
        unsafe_allow_html=True
    )

def set_full_page_background(image_path: str, overlay: float = 0.5):
    """
    Full-page background for Streamlit with a light overlay.
    - image_path: e.g. "app/static/bg_home.png"
    - overlay: 0.0 (no overlay) -> 1.0 (fully white)
    """
    img = Path(image_path)

    if not img.exists():
        st.sidebar.error("Background image not found")
        st.sidebar.code(str(img.resolve()))
        return

    ext = img.suffix.lower()
    if ext in [".jpg", ".jpeg"]:
        mime = "image/jpeg"
    elif ext == ".png":
        mime = "image/png"
    else:
        st.sidebar.error(f"Unsupported image type: {ext}")
        return

    b64 = base64.b64encode(img.read_bytes()).decode("utf-8")
    a = max(0.0, min(1.0, overlay))

    st.markdown(
        f"""
        <style>
        /* Apply background to the main Streamlit containers (most reliable) */
        .stApp,
        [data-testid="stAppViewContainer"],
        [data-testid="stApp"] {{
          background:
            linear-gradient(rgba(255, 244, 232,{a}), rgba(255, 244, 232,{a})),
            url("data:{mime};base64,{b64}") center / cover no-repeat fixed !important;
        }}

        /* Make inner layers transparent so the background shows through */
        [data-testid="stHeader"] {{
          background: transparent !important;
        }}

        .block-container {{
          background: transparent !important;
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )