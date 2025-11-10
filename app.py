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
