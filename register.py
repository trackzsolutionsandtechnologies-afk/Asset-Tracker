"""
User registration page for Asset Tracker
"""
from __future__ import annotations

import re
import streamlit as st
from typing import Tuple

from auth import create_user
from google_sheets import read_data
from config import SHEETS


def _username_or_email_exists(username: str, email: str) -> Tuple[bool, str]:
    """Return True if username or email already exists along with the field name."""
    try:
        df = read_data(SHEETS["users"])
    except Exception as exc:  # pragma: no cover - defensive
        st.error(f"Unable to validate existing users: {exc}")
        return True, "error"

    if df.empty:
        return False, ""

    username_clean = username.strip().lower()
    email_clean = email.strip().lower()

    if "Username" in df.columns:
        username_series = df["Username"].astype(str).str.strip().str.lower()
        if username_series.eq(username_clean).any():
            return True, "username"

    if "Email" in df.columns:
        email_series = df["Email"].astype(str).str.strip().str.lower()
        if email_series.eq(email_clean).any():
            return True, "email"

    return False, ""


def _is_valid_email(email: str) -> bool:
    """Basic email validation."""
    return bool(re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email.strip()))


def _validate_password(password: str) -> Tuple[bool, str]:
    """Validate password complexity and return (is_valid, message)."""
    if len(password) < 8:
        return False, "Password must be at least 8 characters long."
    if password.strip() != password:
        return False, "Password cannot start or end with spaces."
    if not re.search(r"[A-Z]", password):
        return False, "Include at least one uppercase letter."
    if not re.search(r"[a-z]", password):
        return False, "Include at least one lowercase letter."
    if not re.search(r"[0-9]", password):
        return False, "Include at least one number."
    return True, ""


def register_page() -> None:
    """Render the user registration page."""
    from app import load_auth_css  # local import to avoid circular dependency

    load_auth_css()

    st.title("📝 Create an Account")
    st.write(
        "Provide your details below to request access to the Asset Tracker application."
    )

    st.markdown('<div class="auth-form-wrapper">', unsafe_allow_html=True)
    with st.form("register_form"):
        col1, col2 = st.columns(2)
        with col1:
            username = st.text_input("Username").strip()
        with col2:
            email = st.text_input("Email address").strip()

        password = st.text_input("Password", type="password")
        confirm_password = st.text_input("Confirm password", type="password")
        role = st.selectbox(
            "Role",
            options=["user", "admin"],
            index=0,
            help="Most accounts should use the default 'user' role.",
        )

        submitted = st.form_submit_button("Register", type="primary", use_container_width=True)

    st.markdown("</div>", unsafe_allow_html=True)

    if submitted:
        if not username:
            st.error("Username is required.")
            return
        if not email:
            st.error("Email address is required.")
            return
        if not _is_valid_email(email):
            st.error("Please enter a valid email address.")
            return
        if password != confirm_password:
            st.error("Passwords do not match.")
            return

        password_valid, message = _validate_password(password)
        if not password_valid:
            st.error(message)
            return

        exists, field = _username_or_email_exists(username, email)
        if exists:
            if field == "username":
                st.error("That username is already in use. Please choose another.")
            elif field == "email":
                st.error("An account with that email already exists.")
            else:
                st.error("Unable to verify existing users. Please try again later.")
            return

        created = create_user(username, password, email, role)
        if created:
            st.success("Account created successfully! You can now sign in.")
            if st.button("Return to login", type="secondary"):
                st.session_state["show_register"] = False
                st.experimental_rerun()
        else:
            st.error("Could not create the account. Please try again.")

    if st.button("Back to login", type="secondary"):
        st.session_state["show_register"] = False
        st.experimental_rerun()

