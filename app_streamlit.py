import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import hashlib
from datetime import datetime
import pandas as pd

# Page configuration for mobile responsiveness
st.set_page_config(
    page_title="Asset Tracker",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Google Sheets configuration
SCOPE = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

SPREADSHEET_ID = "1q9jfezVWpFYAmvjo81Lk788kf9DNwqvSx7yxHWRGkec"

# Custom CSS for mobile responsiveness
st.markdown("""
    <style>
        /* Mobile responsive styles */
        @media screen and (max-width: 768px) {
            .main > div {
                padding-left: 1rem;
                padding-right: 1rem;
            }
            .stButton > button {
                width: 100%;
                min-width: 100%;
            }
            input[type="text"], input[type="password"], input[type="email"] {
                width: 100% !important;
            }
        }
        
        /* General responsive improvements */
        .stApp {
            max-width: 100%;
            padding: 0.5rem;
        }
        
        /* Form styling */
        .login-container {
            max-width: 400px;
            margin: 0 auto;
            padding: 2rem;
        }
        
        @media screen and (max-width: 768px) {
            .login-container {
                max-width: 100%;
                padding: 1rem;
            }
        }
        
        /* Hide Streamlit branding for cleaner look */
        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}
        header {visibility: hidden;}
        
        /* Green login button styling */
        div[data-testid="column"]:nth-of-type(1) button[kind="formSubmit"] {
            background-color: #28a745 !important;
            color: white !important;
            border-color: #28a745 !important;
        }
        
        div[data-testid="column"]:nth-of-type(1) button[kind="formSubmit"]:hover {
            background-color: #218838 !important;
            border-color: #218838 !important;
        }
        
        /* Purple signup button styling */
        div[data-testid="column"]:nth-of-type(2) button[kind="formSubmit"] {
            background-color: #CDC1FF !important;
            color: white !important;
            border-color: #6f42c1 !important;
        }
        
        div[data-testid="column"]:nth-of-type(2) button[kind="formSubmit"]:hover {
            background-color: #5a32a3 !important;
            border-color: #5a32a3 !important;
        }
        
        /* Alternative selector for form buttons */
        form div[data-testid="column"]:first-child button {
            background-color: #28a745 !important;
            color: white !important;
        }
        
        form div[data-testid="column"]:last-child button {
            background-color: #6f42c1 !important;
            color: white !important;
        }
    </style>
    
    <script>
        // Function to style buttons based on their text content
        function styleButtons() {
            const buttons = document.querySelectorAll('button[kind="formSubmit"]');
            buttons.forEach(button => {
                const buttonText = button.textContent.trim();
                if (buttonText === 'Login') {
                    button.style.backgroundColor = '#28a745';
                    button.style.color = 'white';
                    button.style.borderColor = '#28a745';
                } else if (buttonText === 'Signup') {
                    button.style.backgroundColor = '#6f42c1';
                    button.style.color = 'white';
                    button.style.borderColor = '#6f42c1';
                }
            });
        }
        
        // Run on page load
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', styleButtons);
        } else {
            styleButtons();
        }
        
        // Also run after Streamlit updates
        setTimeout(styleButtons, 100);
        setInterval(styleButtons, 500);
    </script>
""", unsafe_allow_html=True)

def get_google_sheets_client():
    """Initialize and return Google Sheets client"""
    try:
        # Try to get credentials from session state or secrets
        if 'gc' not in st.session_state:
            creds = None
            
            # Method 1: Try to get from Streamlit secrets
            try:
                if hasattr(st, 'secrets') and 'google_credentials' in st.secrets:
                    creds_dict = st.secrets['google_credentials']
                    creds = Credentials.from_service_account_info(creds_dict, scopes=SCOPE)
            except Exception:
                pass
            
            # Method 2: Try to load from file
            if creds is None:
                try:
                    import os
                    if os.path.exists('credentials.json'):
                        creds = Credentials.from_service_account_file(
                            'credentials.json', scopes=SCOPE
                        )
                except Exception:
                    pass
            
            # Method 3: Try default application credentials (if running on Google Cloud)
            if creds is None:
                try:
                    from google.auth import default
                    creds, project = default(scopes=SCOPE)
                except Exception:
                    pass
            
            if creds is None:
                st.error("Could not find Google credentials. Please configure credentials using one of the methods in the README.")
                return None
            
            st.session_state['gc'] = gspread.authorize(creds)
        return st.session_state['gc']
    except Exception as e:
        st.error(f"Error connecting to Google Sheets: {str(e)}")
        st.info("Please ensure your Google Cloud credentials are properly configured.")
        return None

def hash_password(password):
    """Hash password using SHA256"""
    return hashlib.sha256(password.encode()).hexdigest()

def get_users_sheet():
    """Get or create users sheet"""
    try:
        gc = get_google_sheets_client()
        if gc is None:
            return None
        
        spreadsheet = gc.open_by_key(SPREADSHEET_ID)
        
        # Try to get the users sheet, create if it doesn't exist
        try:
            worksheet = spreadsheet.worksheet("Users")
        except gspread.exceptions.WorksheetNotFound:
            # Create users sheet if it doesn't exist
            worksheet = spreadsheet.add_worksheet(title="Users", rows=1000, cols=10)
            # Add headers
            worksheet.append_row(["username", "email", "password_hash", "created_at", "last_login"])
        
        return worksheet
    except Exception as e:
        st.error(f"Error accessing users sheet: {str(e)}")
        return None

def register_user(username, email, password):
    """Register a new user"""
    worksheet = get_users_sheet()
    if worksheet is None:
        raise Exception("Cannot connect to Google Sheets. Please check your credentials.")
    
    try:
        # Check if username or email already exists
        records = worksheet.get_all_records()
        for record in records:
            if record.get('username', '').lower() == username.lower():
                raise Exception("Username already exists")
            if record.get('email', '').lower() == email.lower():
                raise Exception("Email already exists")
        
        # Hash password
        password_hash = hash_password(password)
        
        # Add new user
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        worksheet.append_row([username, email, password_hash, current_time, ""])
        
        return True, "Signup successful!"
    except Exception as e:
        # Re-raise if it's already an Exception with a message
        error_msg = str(e)
        if "Cannot connect" in error_msg or "Username already" in error_msg or "Email already" in error_msg:
            raise Exception(error_msg)
        else:
            raise Exception(f"Signup failed: {error_msg}")

def authenticate_user(username, password):
    """Authenticate a user"""
    worksheet = get_users_sheet()
    if worksheet is None:
        raise Exception("Cannot connect to Google Sheets. Please check your credentials.")
    
    try:
        records = worksheet.get_all_records()
        password_hash = hash_password(password)
        
        for record in records:
            if (record.get('username', '').lower() == username.lower() or 
                record.get('email', '').lower() == username.lower()):
                if record.get('password_hash') == password_hash:
                    # Update last login
                    row_index = records.index(record) + 2  # +2 because header is row 1 and list is 0-indexed
                    try:
                        worksheet.update_cell(row_index, 5, datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
                    except:
                        pass  # Don't fail if update fails
                    
                    user_info = {
                        'username': record.get('username'),
                        'email': record.get('email')
                    }
                    return True, user_info
        
        return False, None
    except Exception as e:
        raise Exception(f"Authentication error: {str(e)}")

def login_page():
    """Display login page"""
    st.markdown('<div class="login-container">', unsafe_allow_html=True)
    
    st.title("🔐 Asset Tracker Login")
    st.markdown("---")
    
    # Display error messages if any
    if 'login_error' in st.session_state and st.session_state['login_error']:
        st.error(st.session_state['login_error'])
        # Clear after displaying so it doesn't persist
        del st.session_state['login_error']
    
    with st.form("login_form"):
        username = st.text_input("Username or Email", placeholder="Enter your username or email")
        password = st.text_input("Password", type="password", placeholder="Enter your password")
        
        col1, col2 = st.columns(2)
        with col1:
            login_button = st.form_submit_button("Login", use_container_width=True)
        with col2:
            register_link = st.form_submit_button("Signup", use_container_width=True)
    
    if login_button:
        if username and password:
            try:
                success, user_info = authenticate_user(username, password)
                if success:
                    st.session_state['authenticated'] = True
                    st.session_state['user'] = user_info
                    st.session_state['login_error'] = None  # Clear any previous errors
                    st.rerun()
                else:
                    st.session_state['login_error'] = "Invalid username or password"
                    st.rerun()
            except Exception as e:
                st.session_state['login_error'] = f"Login error: {str(e)}"
                st.rerun()
        else:
            st.session_state['login_error'] = "Please fill in all fields"
            st.rerun()
    
    if register_link:
        st.session_state['page'] = 'register'
        st.rerun()
    
    st.markdown('</div>', unsafe_allow_html=True)

def register_page():
    """Display register page"""
    st.markdown('<div class="login-container">', unsafe_allow_html=True)
    
    st.title("📝 Signup")
    st.markdown("---")
    
    # Display error/success messages if any
    if 'signup_error' in st.session_state and st.session_state['signup_error']:
        st.error(st.session_state['signup_error'])
        del st.session_state['signup_error']
    
    if 'signup_success' in st.session_state and st.session_state['signup_success']:
        st.success(st.session_state['signup_success'])
        st.info("You can now login with your credentials")
        if st.button("Go to Login", use_container_width=True):
            del st.session_state['signup_success']
            st.session_state['page'] = 'login'
            st.rerun()
        return  # Return early to prevent form from showing
    
    with st.form("register_form"):
        username = st.text_input("Username", placeholder="Choose a username")
        email = st.text_input("Email", placeholder="Enter your email address")
        password = st.text_input("Password", type="password", placeholder="Choose a password")
        confirm_password = st.text_input("Confirm Password", type="password", placeholder="Confirm your password")
        
        col1, col2 = st.columns(2)
        with col1:
            register_button = st.form_submit_button("Signup", use_container_width=True)
        with col2:
            login_link = st.form_submit_button("Back to Login", use_container_width=True)
    
    if register_button:
        if username and email and password and confirm_password:
            if password != confirm_password:
                st.session_state['signup_error'] = "Passwords do not match!"
                st.rerun()
            elif len(password) < 6:
                st.session_state['signup_error'] = "Password must be at least 6 characters long"
                st.rerun()
            else:
                try:
                    success, message = register_user(username, email, password)
                    if success:
                        st.session_state['signup_success'] = message
                        st.rerun()
                except Exception as e:
                    st.session_state['signup_error'] = str(e)
                    st.rerun()
        else:
            st.session_state['signup_error'] = "Please fill in all fields"
            st.rerun()
    
    if login_link:
        st.session_state['page'] = 'login'
        st.rerun()
    
    st.markdown('</div>', unsafe_allow_html=True)

def main():
    """Main application"""
    # Initialize session state
    if 'authenticated' not in st.session_state:
        st.session_state['authenticated'] = False
    if 'page' not in st.session_state:
        st.session_state['page'] = 'login'
    if 'user' not in st.session_state:
        st.session_state['user'] = None
    
    # Check authentication status
    if not st.session_state['authenticated']:
        if st.session_state['page'] == 'register':
            register_page()
        else:
            login_page()
    else:
        # User is authenticated - show main app (placeholder for now)
        st.title("🏠 Asset Tracker Dashboard")
        st.success(f"Welcome, {st.session_state['user']['username']}!")
        
        if st.button("Logout"):
            st.session_state['authenticated'] = False
            st.session_state['user'] = None
            st.rerun()

if __name__ == "__main__":
    main()
 

