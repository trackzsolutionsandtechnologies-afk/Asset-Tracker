"""
Main Streamlit Application for Asset Tracker
"""
import streamlit as st
from streamlit_option_menu import option_menu
from config import get_config
from auth import login_page, forgot_password_page, check_authentication, logout, SESSION_KEYS
from dashboard import dashboard_page
from forms import location_form, supplier_form, category_form, asset_master_form, asset_transfer_form
from barcode_utils import barcode_scanner_page, barcode_print_page

# Page configuration (must be first Streamlit command)
st.set_page_config(
    page_title="Asset Tracker",
    page_icon="📦",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
    <style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1f77b4;
        text-align: center;
        padding: 1rem;
    }
    .stButton>button {
        width: 100%;
    }
    /* Hide loading indicators and status widgets */
    [data-testid="stStatusWidget"] {
        display: none !important;
    }
    /* Hide spinner containers but keep functionality */
    div[data-testid="stSpinner"] {
        display: none !important;
    }
    /* Hide "Running" text in status */
    .stStatusWidget {
        display: none !important;
    }
    </style>
""", unsafe_allow_html=True)

def main():
    """Main application function"""
    
    # Initialize configuration from secrets (after Streamlit is initialized)
    try:
        get_config()
    except:
        pass
    
    # Clear cached credentials warning if credentials are found
    # This helps if the warning was shown before credentials were set up
    try:
        import os
        if os.path.exists("credentials.json"):
            if "credentials_warning_shown" in st.session_state:
                del st.session_state["credentials_warning_shown"]
            if "connection_error_shown" in st.session_state:
                del st.session_state["connection_error_shown"]
    except:
        pass
    
    # Check if user is authenticated
    if not check_authentication():
        # Show login or forgot password page
        if st.session_state.get("show_forgot_password", False):
            forgot_password_page()
        else:
            login_page()
            # Add user management options
            try:
                from google_sheets import read_data
                from config import SHEETS
                import bcrypt
                
                st.divider()
                with st.expander("🔧 User Management & Diagnostics"):
                    # Check if users exist
                    try:
                        df = read_data(SHEETS["users"])
                        if df.empty or len(df) == 0:
                            st.info("⚠️ No users found. Create an admin user to get started.")
                        else:
                            st.success(f"✅ Found {len(df)} user(s) in the system")
                            if st.checkbox("Show users (for debugging)"):
                                st.dataframe(df[["Username", "Email", "Role"]], use_container_width=True)
                    except Exception as e:
                        st.warning(f"Could not read users: {str(e)}")
                    
                    # Create admin user option
                    st.subheader("Create Admin User")
                    if st.button("Create Default Admin User"):
                        try:
                            hashed_password = bcrypt.hashpw("admin123".encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
                            from google_sheets import append_data
                            if append_data(SHEETS["users"], ["admin", hashed_password, "admin@example.com", "admin"]):
                                st.success("✅ Admin user created! Username: `admin`, Password: `admin123`")
                                st.info("⚠️ Please change the password after first login!")
                                st.rerun()
                            else:
                                st.error("Failed to create user. Check Google Sheets connection.")
                        except Exception as e:
                            st.error(f"Error creating user: {str(e)}")
                    
                    # Debug mode
                    if st.checkbox("Enable debug mode (shows detailed errors)"):
                        st.session_state["auth_debug"] = True
                    else:
                        st.session_state["auth_debug"] = False
            except Exception as e:
                if "auth_debug" in st.session_state and st.session_state.get("auth_debug"):
                    st.error(f"Error in user management: {str(e)}")
                pass  # Silently fail if we can't check users
        return
    
    # User is authenticated - show main application
    username = st.session_state.get(SESSION_KEYS["username"], "User")
    
    # Sidebar
    with st.sidebar:
        st.title(f"👤 {username}")
        
        if st.button("🚪 Logout", use_container_width=True):
            logout()
        
        st.divider()
        
        # Navigation menu
        selected = option_menu(
            menu_title="Navigation",
            options=[
                "Dashboard",
                "Location Form",
                "Supplier Form",
                "Category Form",
                "Asset Master",
                "Asset Transfer",
                "Barcode Scanner",
                "Print Barcodes"
            ],
            icons=[
                "speedometer2",
                "geo-alt",
                "building",
                "folder",
                "box-seam",
                "arrow-left-right",
                "search",
                "printer"
            ],
            menu_icon="list",
            default_index=0,
            styles={
                "container": {"padding": "5!important", "background-color": "#fafafa"},
                "icon": {"color": "#1f77b4", "font-size": "18px"},
                "nav-link": {
                    "font-size": "16px",
                    "text-align": "left",
                    "margin": "0px",
                    "--hover-color": "#eee",
                },
                "nav-link-selected": {"background-color": "#1f77b4"},
            }
        )
    
    # Main content area
    if selected == "Dashboard":
        dashboard_page()
    elif selected == "Location Form":
        location_form()
    elif selected == "Supplier Form":
        supplier_form()
    elif selected == "Category Form":
        category_form()
    elif selected == "Asset Master":
        asset_master_form()
    elif selected == "Asset Transfer":
        asset_transfer_form()
    elif selected == "Barcode Scanner":
        barcode_scanner_page()
    elif selected == "Print Barcodes":
        barcode_print_page()

if __name__ == "__main__":
    main()
