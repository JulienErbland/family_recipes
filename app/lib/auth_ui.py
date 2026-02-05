import streamlit as st
from app.lib.session import init_session, logout
from app.lib.supabase_client import get_supabase
from supabase_auth.errors import AuthApiError

def auth_sidebar():
    init_session()
    sb = get_supabase()

    st.sidebar.header("Account")

    if st.session_state.session:
        email = st.session_state.user.email if st.session_state.user else "Unknown"
        st.sidebar.success(f"Logged in as: {email}")
        if st.sidebar.button("Log out", key="logout_btn"):
            logout()
            st.rerun()
        return

    tab_login, tab_signup = st.sidebar.tabs(["Login", "Sign up"])

    with tab_login:
        email = st.text_input("Email", key="login_email")
        password = st.text_input("Password", type="password", key="login_pw")

        if st.button("Login", key="login_btn"):
            try:
                res = sb.auth.sign_in_with_password({"email": email.strip(), "password": password})
                st.session_state.session = res.session
                st.session_state.user = res.user
                st.rerun()
            except AuthApiError as e:
                msg = str(e)
                if "Email not confirmed" in msg:
                    st.error(
                        "Email not confirmed. Confirm it in Supabase Auth settings or disable email confirmation for dev."
                    )
                else:
                    st.error(f"Login failed: {msg}")

    with tab_signup:
        first_name = st.text_input("First name", key="signup_first_name")
        last_name = st.text_input("Last name", key="signup_last_name")
        signup_email = st.text_input("Email", key="signup_email")
        signup_pw = st.text_input("Password", type="password", key="signup_pw")
        signup_pw2 = st.text_input("Confirm password", type="password", key="signup_pw2")

        if st.button("Create account", key="signup_btn"):
            fn = (first_name or "").strip()
            ln = (last_name or "").strip()
            em = (signup_email or "").strip()

            if not fn or not ln:
                st.error("Please enter your first name and last name.")
                st.stop()

            if not em:
                st.error("Please enter your email.")
                st.stop()

            if not signup_pw:
                st.error("Please enter a password.")
                st.stop()

            if signup_pw != signup_pw2:
                st.error("Passwords do not match.")
                st.stop()

            try:
                # Store first/last name in auth user metadata so your DB trigger can copy it into public.profiles
                sb.auth.sign_up({
                    "email": em,
                    "password": signup_pw,
                    "options": {
                        "data": {
                            "first_name": fn,
                            "last_name": ln,
                        }
                    }
                })
                st.success("Account created. Check your email to confirm (if confirmation is enabled).")
            except AuthApiError as e:
                st.error(f"Sign up failed: {str(e)}")
