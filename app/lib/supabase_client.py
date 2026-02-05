import os
import streamlit as st
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

def _get_setting(name: str) -> str:
    # Streamlit Cloud: secrets
    if hasattr(st, "secrets") and name in st.secrets:
        return str(st.secrets[name])
    # Local: environment variables (optionally loaded via .env)
    val = os.getenv(name, "")
    if not val:
        raise RuntimeError(f"Missing required setting: {name}")
    return val

def get_supabase():
    url = _get_setting("SUPABASE_URL")
    key = _get_setting("SUPABASE_ANON_KEY")
    return create_client(url, key)

def authed_postgrest(sb, access_token: str):
    sb.postgrest.auth(access_token)
    return sb


