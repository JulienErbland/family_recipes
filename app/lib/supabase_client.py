import os
import streamlit as st
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

def _get_setting(name: str) -> str:
    # 1) Try Streamlit secrets (but it can raise if no secrets.toml exists)
    try:
        val = st.secrets.get(name, None)
        if val:
            return str(val)
    except Exception:
        pass

    # 2) Fallback to environment variables (loaded via .env locally)
    val = os.getenv(name, "")
    if not val:
        raise RuntimeError(
            f"Missing required setting: {name}. "
            f"Set it in .env (local) or in Streamlit Cloud Secrets."
        )
    return val


@st.cache_resource
def get_supabase():
    url = _get_setting("SUPABASE_URL")
    key = _get_setting("SUPABASE_ANON_KEY")
    return create_client(url, key)

def authed_postgrest(sb, access_token: str):
    sb.postgrest.auth(access_token)
    return sb
