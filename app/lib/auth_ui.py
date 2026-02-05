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
        fn = st.text_input("First name", key="signup_fn")
        ln = st.text_input("Last name", key="signup_ln")

        signup_email = st.text_input("Email", key="signup_email")
        signup_pw = st.text_input("Password", type="password", key="signup_pw")
        signup_pw2 = st.text_input("Confirm password", type="password", key="signup_pw2")

        if st.button("Create account", key="signup_btn"):
            if signup_pw != signup_pw2:
                st.error("Passwords do not match.")
                st.stop()

            if len(signup_pw) < 8:
                st.error("Password must be at least 8 characters.")
                st.stop()

            em = (signup_email or "").strip()
            first = (fn or "").strip()
            last = (ln or "").strip()

            if not em:
                st.error("Please enter an email.")
                st.stop()
            if not first or not last:
                st.error("Please enter first name and last name.")
                st.stop()

            try:
                # 1) Create account (store names in metadata so your trigger copies them)
                res = sb.auth.sign_up({
                    "email": em,
                    "password": signup_pw,
                    "options": {
                        "data": {"first_name": first, "last_name": last}
                    }
                })

                # 2) If Supabase returns a session, log them in directly
                if getattr(res, "session", None):
                    st.session_state.session = res.session
                    st.session_state.user = res.user
                    st.success("Account created ✅ Logged in.")
                    st.rerun()

                # 3) Otherwise, try to sign in immediately (works when email confirmation is OFF)
                try:
                    login = sb.auth.sign_in_with_password({"email": em, "password": signup_pw})
                    st.session_state.session = login.session
                    st.session_state.user = login.user
                    st.success("Account created ✅ Logged in.")
                    st.rerun()
                except Exception:
                    # Most common case: email confirmation required
                    st.success("Account created ✅ Please check your email to confirm your account, then log in.")

            except AuthWeakPasswordError:
                st.error("Password too weak. Use at least 8 characters (and meet any policy requirements).")
            except AuthApiError as e:
                st.error(f"Sign up failed: {str(e)}")
