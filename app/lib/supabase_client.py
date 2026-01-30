import os
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

def get_supabase():
    # Uses anon key; RLS will protect the DB.
    url = os.environ["SUPABASE_URL"]
    key = os.environ["SUPABASE_ANON_KEY"]
    return create_client(url, key)

def authed_postgrest(sb, access_token: str):
    """
    Important: attach the user's JWT to PostgREST.
    All SELECT/INSERT/UPDATE/DELETE will be checked by RLS using auth.uid().
    """
    sb.postgrest.auth(access_token)
    return sb

