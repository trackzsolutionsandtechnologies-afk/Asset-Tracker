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
        
        # Clean username (remove whitespace, case-insensitive matching)
        username_clean = username.strip().lower()
        
        # Try to find user - check both exact match and case-insensitive
        user = None
        if "Username" in df.columns:
            # Try exact match first
            user = df[df["Username"].str.strip().str.lower() == username_clean]
            if user.empty:
                # Try case-insensitive
                user = df[df["Username"].astype(str).str.strip().str.lower() == username_clean]
        
        if user.empty:
            return False
        
        # Get password - handle different column name variations
        hashed_password = None
        if "Password" in user.columns:
            hashed_password = user.iloc[0]["Password"]
        elif "password" in user.columns:
            hashed_password = user.iloc[0]["password"]
        else:
            # Try to get second column (assuming: Username, Password, Email, Role)
            if len(user.columns) >= 2:
                hashed_password = user.iloc[0].iloc[1]  # Second column
        
        if not hashed_password:
            return False
        
        # Verify password
        return verify_password(password, str(hashed_password))
    except Exception as e:
        # Show more detailed error for debugging
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
            return False  # User already exists
        
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
            return None  # Don't reveal if user exists or not
        
        token = generate_reset_token()
        expiry = (datetime.now() + timedelta(hours=24)).isoformat()
        
        # Store reset token
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
        
        # Find valid token
        reset_requests = df[
            (df["Username"] == username) & 
            (df["Reset Token"] == token)
        ]
        
        if reset_requests.empty:
            return False
        
        # Check if token is expired
        expiry_str = reset_requests.iloc[0]["Expiry"]
        expiry = datetime.fromisoformat(expiry_str)
        if datetime.now() > expiry:
            return False
        
        # Update password
        users_df = read_data(SHEETS["users"])
        user_row = users_df[users_df["Username"] == username]
        if user_row.empty:
            return False
        
        row_index = user_row.index[0]
        hashed_password = hash_password(new_password)
        user_data = user_row.iloc[0].tolist()
        user_data[1] = hashed_password  # Update password
        
        return update_data(SHEETS["users"], row_index, user_data)
    except Exception as e:
        st.error(f"Error resetting password: {str(e)}")
        return False

def login_page():
    """Display login page"""
    # --- Custom CSS for styling ---
    st.markdown(
        """
        <style>
        .login-screen {
            min-height: calc(100vh - 6rem);
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 3rem 1.5rem;
            background: linear-gradient(145deg, #f5f7fb 0%, #ffffff 40%, #eef1f8 100%);
        }
        [data-testid="stForm"][aria-label="login_form"] {
            width: 100%;
            max-width: 380px;
            padding: 2.5rem 2.75rem 2rem;
            border-radius: 22px;
            background: rgba(255, 255, 255, 0.98);
            box-shadow: 0 22px 48px rgba(31, 45, 61, 0.12);
            border: 1px solid rgba(226, 232, 240, 0.65);
            backdrop-filter: blur(6px);
        }
        [data-testid="stForm"][aria-label="login_form"] .stTextInput>label {
            display: none;
        }
        [data-testid="stForm"][aria-label="login_form"] .stTextInput>div>div>input {
            height: 48px;
            border-radius: 14px;
            border: 1px solid #e0e7f1;
            background: #f6f8fc;
            padding: 0 18px;
            font-size: 15px;
            color: #1f2937;
            box-shadow: none;
        }
        [data-testid="stForm"][aria-label="login_form"] .stTextInput>div>div>input:focus {
            border-color: #4c6ef5;
            box-shadow: 0 0 0 3px rgba(76, 110, 245, 0.12);
            background: #ffffff;
        }
        [data-testid="stForm"][aria-label="login_form"] .login-title {
            font-size: 26px;
            font-weight: 600;
            color: #1f2937;
            text-align: center;
            margin-bottom: 0.3rem;
        }
        [data-testid="stForm"][aria-label="login_form"] .login-subtitle {
            font-size: 14px;
            color: #6b7280;
            text-align: center;
            margin-bottom: 2rem;
        }
        [data-testid="stForm"][aria-label="login_form"] button[kind="primary"] {
            height: 48px;
            border-radius: 14px;
            font-size: 15px;
            font-weight: 600;
            background: linear-gradient(135deg, #3d8bfd, #5b6dfb);
            border: none;
            box-shadow: 0 12px 24px rgba(61, 139, 253, 0.30);
        }
        [data-testid="stForm"][aria-label="login_form"] button[kind="primary"]:hover {
            background: linear-gradient(135deg, #366efc, #4356fb);
        }
        [data-testid="stForm"][aria-label="login_form"] button[kind="secondary"] {
            border: none;
            background: transparent;
            box-shadow: none;
            color: #5b6b92;
            font-size: 13px;
            font-weight: 500;
            padding: 0;
        }
        [data-testid="stForm"][aria-label="login_form"] .aux-links {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-top: 1.25rem;
            font-size: 13.5px;
            color: #5b6b92;
        }
        [data-testid="stForm"][aria-label="login_form"] .aux-links span {
            color: #3d8bfd;
            font-weight: 600;
            cursor: pointer;
        }
        </style>
        <div class="login-screen">
        """,
        unsafe_allow_html=True,
    )

    st.title("🔐 Asset Tracker - Sign In")
    
    with st.form("login_form"):
        st.markdown(
            """
            <div class="login-title">Welcome Back</div>
            <div class="login-subtitle">Please sign in to your account</div>
            """,
            unsafe_allow_html=True,
        )

        username = st.text_input(
            "Username",
            key="login_username",
            placeholder="Username or email",
            label_visibility="collapsed",
        )
        password = st.text_input(
            "Password",
            type="password",
            key="login_password",
            placeholder="Password",
            label_visibility="collapsed",
        )

        col1, col2 = st.columns([3, 1])
        
        with col1:
            submit_button = st.form_submit_button("Sign In", use_container_width=True)
        
        with col2:
            forgot_password = st.form_submit_button("Forgot Password", use_container_width=True)
        
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
