"""
Authentication module for Asset Tracker
"""
import streamlit as st
import bcrypt
import hashlib
import secrets
from datetime import datetime, timedelta
from typing import Optional
from google_sheets import read_data, append_data, update_data, find_row
from config import SHEETS, SESSION_KEYS


def hash_password(password: str) -> str:
    """Hash a password using bcrypt"""
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')


def verify_password(password: str, hashed: str) -> bool:
    """Verify a password against a hash"""
    try:
        return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))
    except:
        return False


def generate_reset_token() -> str:
    """Generate a secure reset token"""
    return secrets.token_urlsafe(32)


def authenticate_user(username: str, password: str) -> bool:
    """Authenticate a user"""
    try:
        df = read_data(SHEETS["users"])
        if df.empty:
            return False
        
        username_clean = username.strip().lower()
        
        user = None
        if "Username" in df.columns:
            user = df[df["Username"].str.strip().str.lower() == username_clean]
            if user.empty:
                user = df[df["Username"].astype(str).str.strip().str.lower() == username_clean]
        
        if user.empty:
            return False
        
        hashed_password = None
        if "Password" in user.columns:
            hashed_password = user.iloc[0]["Password"]
        elif "password" in user.columns:
            hashed_password = user.iloc[0]["password"]
        elif len(user.columns) >= 2:
            hashed_password = user.iloc[0].iloc[1]
        
        if not hashed_password:
            return False
        
        return verify_password(password, str(hashed_password))
    except Exception as e:
        if "auth_debug" in st.session_state and st.session_state["auth_debug"]:
            st.error(f"Authentication error: {str(e)}")
            import traceback
            st.code(traceback.format_exc())
        return False


def get_user_role(username: str) -> str:
    """Get user role"""
    try:
        df = read_data(SHEETS["users"])
        if df.empty:
            return "user"
        
        user = df[df["Username"] == username]
        if user.empty:
            return "user"
        
        return user.iloc[0].get("Role", "user")
    except:
        return "user"


def create_user(username: str, password: str, email: str, role: str = "user") -> bool:
    """Create a new user"""
    try:
        df = read_data(SHEETS["users"])
        if not df.empty and username in df["Username"].values:
            return False
        
        hashed_password = hash_password(password)
        return append_data(SHEETS["users"], [username, hashed_password, email, role])
    except Exception as e:
        st.error(f"Error creating user: {str(e)}")
        return False


def request_password_reset(username: str) -> Optional[str]:
    """Request a password reset and return token"""
    try:
        df = read_data(SHEETS["users"])
        if df.empty:
            return None
        
        user = df[df["Username"] == username]
        if user.empty:
            return None
        
        token = generate_reset_token()
        expiry = (datetime.now() + timedelta(hours=24)).isoformat()
        
        append_data(SHEETS["password_resets"], [username, token, expiry])
        return token
    except Exception as e:
        st.error(f"Error requesting password reset: {str(e)}")
        return None


def reset_password(username: str, token: str, new_password: str) -> bool:
    """Reset password using token"""
    try:
        df = read_data(SHEETS["password_resets"])
        if df.empty:
            return False
        
        reset_requests = df[
            (df["Username"] == username) & 
            (df["Reset Token"] == token)
        ]
        
        if reset_requests.empty:
            return False
        
        expiry_str = reset_requests.iloc[0]["Expiry"]
        expiry = datetime.fromisoformat(expiry_str)
        if datetime.now() > expiry:
            return False
        
        users_df = read_data(SHEETS["users"])
        user_row = users_df[users_df["Username"] == username]
        if user_row.empty:
            return False
        
        row_index = user_row.index[0]
        hashed_password = hash_password(new_password)
        user_data = user_row.iloc[0].tolist()
        user_data[1] = hashed_password
        
        return update_data(SHEETS["users"], row_index, user_data)
    except Exception as e:
        st.error(f"Error resetting password: {str(e)}")
        return False


def login_page():
    """Display login page"""
    st.markdown(
        """
        <style>
        [data-testid="stAppViewContainer"] {
            background-color: #5C3E94!important;
            color: #321313 !important;  /*this is login header color*/
        }
        [data-testid="stSidebar"] {
            background-color: transparent !important;
        }
        .login-form-container label,
        .login-form-container span,
        .login-form-container p,
        .login-form-container h1 {
            color: #5C3E94 !important;
        }
        .login-form-container .stTextInput > div > div > input {
            background-color: ##5C3E94 !important;
            color:#5C3E94 !important;
            border: 1px solid #444444 !important;
            height: 48px !important;
            padding: 0 16px !important;
            width: 50% !important;
        }
        .login-form-container button[kind="primary"] {
            background-color: #5C3E94 !important;
            color: #5C3E94 !important;
            border: 1px solid #ffffff !important;
        }
        .login-form-container button[kind="primary"]:hover {
            background-color: #5C3E94 !important;
            color: #5C3E94 !important;
        }
        .login-form-container button[kind="secondary"] {
            background-color: #5C3E94 !important;
            color: #5C3E94 !important;
            border: 1px solid #ffffff !important;
        }
        .login-form-container button[kind="secondary"]:hover {
            background-color: #5C3E94 !important;
            color: #5C3E94 !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    st.markdown('<div class="login-form-container">', unsafe_allow_html=True)
    st.title("🔐 Asset Tracker - Sign In")

    with st.form("login_form"):
        username = st.text_input("Username", key="login_username")
        password = st.text_input("Password", type="password", key="login_password")
        col1, col2 = st.columns([3, 1])
        
        with col1:
            submit_button = st.form_submit_button("Sign In", use_container_width=True)
        with col2:
            forgot_password = st.form_submit_button(
                "Forgot Password", use_container_width=True, type="secondary"
            )
        
        if submit_button:
            if authenticate_user(username, password):
                st.session_state[SESSION_KEYS["authenticated"]] = True
                st.session_state[SESSION_KEYS["username"]] = username
                st.session_state[SESSION_KEYS["user_role"]] = get_user_role(username)
                st.success("Login successful!")
                st.rerun()
            else:
                st.error("Invalid username or password")
        
        if forgot_password:
            st.session_state["show_forgot_password"] = True
            st.rerun()

    st.markdown("</div>", unsafe_allow_html=True)


def forgot_password_page():
    """Display forgot password page"""
    st.title("🔑 Forgot Password")

    if "reset_step" not in st.session_state:
        st.session_state["reset_step"] = "request"

    if st.session_state["reset_step"] == "request":
        with st.form("forgot_password_form"):
            username = st.text_input("Enter your username")
            submit = st.form_submit_button("Request Reset Token")

            if submit:
                token = request_password_reset(username)
                if token:
                    st.session_state["reset_token"] = token
                    st.session_state["reset_username"] = username
                    st.session_state["reset_step"] = "reset"
                    st.success(f"Reset token generated: {token}")
                    st.info("Please save this token. You'll need it to reset your password.")
                    st.rerun()
                else:
                    st.error("Could not generate reset token. Please check your username.")
        
        if st.button("Back to Login"):
            st.session_state["show_forgot_password"] = False
            st.session_state["reset_step"] = "request"
            st.rerun()

    elif st.session_state["reset_step"] == "reset":
        with st.form("reset_password_form"):
            st.text_input("Username", value=st.session_state.get("reset_username", ""), disabled=True)
            token = st.text_input("Reset Token", value=st.session_state.get("reset_token", ""))
            new_password = st.text_input("New Password", type="password")
            confirm_password = st.text_input("Confirm Password", type="password")
            submit = st.form_submit_button("Reset Password")

            if submit:
                if new_password != confirm_password:
                    st.error("Passwords do not match")
                elif len(new_password) < 6:
                    st.error("Password must be at least 6 characters")
                else:
                    username = st.session_state.get("reset_username", "")
                    if reset_password(username, token, new_password):
                        st.success("Password reset successful! Please login with your new password.")
                        st.session_state["show_forgot_password"] = False
                        st.session_state["reset_step"] = "request"
                        if st.button("Go to Login"):
                            st.rerun()
                    else:
                        st.error("Invalid token or token expired")

        if st.button("Back"):
            st.session_state["reset_step"] = "request"
            st.rerun()


def check_authentication():
    """Check if user is authenticated"""
    if SESSION_KEYS["authenticated"] not in st.session_state:
        st.session_state[SESSION_KEYS["authenticated"]] = False
    return st.session_state[SESSION_KEYS["authenticated"]]


def logout():
    """Logout user"""
    for key in SESSION_KEYS.values():
        if key in st.session_state:
            del st.session_state[key]
    st.rerun()
