"""
Main Streamlit Application for Asset Tracker
"""
import streamlit as st
from pathlib import Path
from streamlit_option_menu import option_menu
from config import get_config
from auth import login_page, forgot_password_page, check_authentication, logout, SESSION_KEYS
from dashboard import dashboard_page
from forms import (
    location_form,
    supplier_form,
    category_form,
    asset_master_form,
    asset_transfer_form,
    asset_maintenance_form,
    asset_depreciation_form,
    employee_assignment_form,
    user_management_form,
)
from barcode_utils import barcode_scanner_page, barcode_print_page



# Page configuration (must be first Streamlit command)
st.set_page_config(
    page_title="Asset Tracker",
    page_icon="📦",
    layout="centered",
    
    initial_sidebar_state="expanded"
)

def load_custom_css() -> None:
    css_path = Path(__file__).parent / "styles" / "main.css"
    if css_path.exists():
        with css_path.open("r", encoding="utf-8") as css_file:
            st.markdown(f"<style>{css_file.read()}</style>", unsafe_allow_html=True)
    st.markdown(
        """
        <style>
        [data-testid="stSidebar"] {
            background: linear-gradient(180deg, #eef2ff 0%, #ffffff 100%) !important;
            padding: 1.5rem 1.25rem 2rem 1.25rem !important;
            border-right: 1px solid #e2e8f0 !important;
        }
        [data-testid="stSidebar"] > div:first-child {
            padding-top: 1rem !important;
        }
        [data-testid="stSidebar"] .nav {
            gap: 0.35rem !important;
        }
        [data-testid="stSidebar"] .nav-pills .nav-link {
            display: flex !important;
            align-items: center !important;
            gap: 0.5rem !important;
            border-radius: 12px !important;
            padding: 0.55rem 0.85rem !important;
            font-weight: 600 !important;
            color: #2d3748 !important;
            background: transparent !important;
            border: 1px solid transparent !important;
            transition: all 0.2s ease-in-out !important;
        }
        [data-testid="stSidebar"] .nav-pills .nav-link svg {
            width: 1rem !important;
            height: 1rem !important;
            color: inherit !important;
        }
        [data-testid="stSidebar"] .nav-pills .nav-link:hover {
            color: #1a365d !important;
            background: rgba(82, 109, 255, 0.08) !important;
            border-color: rgba(82, 109, 255, 0.2) !important;
        }
        [data-testid="stSidebar"] .nav-pills .nav-link.active {
            background: linear-gradient(90deg, #3641f8 0%, #5a67ff 100%) !important;
            color: #ffffff !important;
            box-shadow: 0 8px 18px rgba(54, 65, 248, 0.25) !important;
        }
        [data-testid="stSidebar"] .nav-pills .nav-link.active:hover {
            color: #fff !important;
        }
        [data-testid="stSidebar"] hr {
            border-top: 1px solid #d7dceb !important;
            margin: 1.25rem 0 !important;
        }
        [data-testid="stSidebar"] button[kind="secondary"] {
            border-radius: 12px !important;
            border: 1px solid #d7dceb !important;
            color: #2d3748 !important;
            background: #f8fafc !important;
            font-weight: 600 !important;
        }
        [data-testid="stSidebar"] button[kind="secondary"]:hover {
            border-color: #5a67ff !important;
            color: #1a365d !important;
            background: #edf2ff !important;
        }
        header[data-testid="stHeader"], header {
            display: none !important;
        }
        div[data-testid="stToolbar"],
        button[kind="header"],
        div[data-testid="stDecoration"],
        div[data-testid="stStatusWidget"],
        button[data-testid="stActionButton"],
        button[data-testid="stFeedbackButton"],
        div[class*="viewerBadge"],
        a[class*="viewerBadge"],
        div[class*="stStatusWidget"],
        div[data-testid="stDeployStatus"] {
            display: none !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def load_auth_css() -> None:
    css_path = Path(__file__).parent / "styles" / "auth.css"
    if css_path.exists():
        with css_path.open("r", encoding="utf-8") as css_file:
            st.markdown(f"<style>{css_file.read()}</style>", unsafe_allow_html=True)


def apply_wide_layout() -> None:
    st.markdown(
        """
        <style>
        div[data-testid="block-container"] {
            max-width: 95% !important;
            padding-left: 2rem !important;
            padding-right: 2rem !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


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
        load_auth_css()
        # Show login or forgot password page
        if st.session_state.get("show_forgot_password", False):
            forgot_password_page()
        else:
            login_page()
        return
    
    # User is authenticated - show main application
    load_custom_css()
    apply_wide_layout()
    username = st.session_state.get(SESSION_KEYS["username"], "User")
    if isinstance(username, str):
        display_name = username.strip() or "User"
        display_name = display_name.title()
    else:
        display_name = "User"
    
    # Sidebar
    with st.sidebar:
        st.markdown(f"### 👋 Welcome {display_name}")
        
        if st.button("🔓 Logout", use_container_width=True):
            logout()
        
        st.divider()
        
        # Navigation menu
        selected = option_menu(
            menu_title="Navigation",
            options=[
                "Dashboard",
                "Location",
                "Supplier",
                "Category",
                "Asset Master",
                "Asset Transfer",
                "Maintenance",
                "Depreciation",
                "Assignment",
                "Users",
                "Scan Barcode",
                "Print Barcodes"
            ],
            icons=[
                "speedometer2",
                "geo-alt",
                "truck",
                "folder",
                "box-seam",
                "arrow-repeat",
                "tools",
                "graph-down",
                "person-badge",
                "people",
                "search",
                "printer"
            ],
            menu_icon="list",
            default_index=0,
        )
    # Main content area
    if selected == "Dashboard":
        dashboard_page()
    elif selected == "Location":
        location_form()
    elif selected == "Supplier":
        supplier_form()
    elif selected == "Category":
        category_form()
    elif selected == "Asset Master":
        asset_master_form()
    elif selected == "Asset Transfer":
        asset_transfer_form()
    elif selected == "Maintenance":
        asset_maintenance_form()
    elif selected == "Depreciation":
        asset_depreciation_form()
    elif selected == "Assignment":
        employee_assignment_form()
    elif selected == "Users":
        user_management_form()
    elif selected == "Scan Barcode":
        barcode_scanner_page()
    elif selected == "Print Barcodes":
        barcode_print_page()

if __name__ == "__main__":
    main()
