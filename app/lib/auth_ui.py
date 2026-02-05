import streamlit as st
from app.lib.session import init_session, logout
from app.lib.supabase_client import get_supabase
from supabase_auth.errors import AuthApiError, AuthWeakPasswordError

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
        last_name  = st.text_input("Last name",  key="signup_last_name")
        signup_email = st.text_input("Email", key="signup_email")
        signup_pw  = st.text_input("Password", type="password", key="signup_pw")
        signup_pw2 = st.text_input("Confirm password", type="password", key="signup_pw2")

        if st.button("Create account", key="signup_btn"):
            if signup_pw != signup_pw2:
                st.error("Passwords do not match.")
                st.stop()

            if len(signup_pw) < 8:
                st.error("Password must be at least 8 characters.")
                st.stop()

            try:
                res = sb.auth.sign_up({
                    "email": signup_email,
                    "password": signup_pw,
                    # keep your options/data here if you added names
                })

                st.success("Account created ✅ You may need to confirm your email, depending on settings.")
                # If email confirmation is OFF, you can auto-login here (optional)
                # (If you already implemented auto-login, keep it.)

            except AuthWeakPasswordError:
                st.error(
                    "Password too weak. Use at least 8 characters, and add a mix of letters/numbers/symbols if required."
                )
            except AuthApiError as e:
                st.error(f"Sign up failed: {str(e)}")
            except Exception as e:
                st.error("Unexpected error during signup.")
                st.exception(e)