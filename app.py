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

import streamlit as st

st.markdown("""
    <style>
    /* Import DIN font */
    @import url('https://fonts.cdnfonts.com/css/din-regular');

    html, body, [class*="css"] {
        font-family: 'DIN', sans-serif !important;
        background-color: #ffffff !important;
        color: #262730 !important;
    }

    /* Sidebar also white */
    [data-testid="stSidebar"] {
        background-color: #ffffff !important;
    }

    /* Make buttons white with blue border */
    div.stButton > button {
        background-color: #ffffff !important;
        color: #1f77b4 !important;
        border: 2px solid #1f77b4 !important;
        border-radius: 8px !important;
        font-weight: 600 !important;
    }

    /* Button hover effect */
    div.stButton > button:hover {
        background-color: #1f77b4 !important;
        color: #ffffff !important;
    }
    </style>
""", unsafe_allow_html=True)




# Page configuration (must be first Streamlit command)
st.set_page_config(
    page_title="Asset Tracker",
    page_icon="📦",
    layout="centered",
    initial_sidebar_state="expanded"
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
        # Show login or forgot password page
        if st.session_state.get("show_forgot_password", False):
            forgot_password_page()
        else:
            login_page()
        return
    
    # User is authenticated - show main application
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
                "search",
                "printer"
            ],
            menu_icon="list",
            default_index=0,
            styles={
                "container": {
                    "padding": "5px",
                 "background": "linear-gradient(180deg, #2b1542, #3a2060)",  # same as sidebar
                    "border-radius": "0px",
                   
                },
                "icon": {
                    "color": "#c3aed6",  # light lavender icons
                    "font-size": "20px",
                    
                },
                "nav-link": {
                    "font-size": "16px",
                    "text-align": "left",
                    "margin": "5px 0",
                    "padding": "10px 18px",
                    "color": "#e4d9f5",  # light text
                    "border-radius": "8px",
                    "background-color": "transparent",
        "transition": "all 0.3s ease",
         "font-family": "'D-DIN', sans-serif",
                    
                },
  "nav-link-hover": {
            "background-color": "#4c2a85",  # mid purple highlight on hover
            "color": "#007bff",
        },




                "nav-link-selected": {
                   "background-color": "#6f42c1",  # bright purple active item
            "color": "white",
            "font-weight": "600",
            "box-shadow": "0 0 8px rgba(111, 66, 193, 0.5)",
                },
                "menu-title": {
                    "color": "#b897ff",
                    "font-size": "18px",
                    "font-weight": "600",
                    "margin-bottom": "10px",
                     "font-family": "'D-DIN', sans-serif",
                    
                },
            }
        )
    st.markdown(
    """
    <style>
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #2b1542, #3a2060);
        color: #e4d9f5;
    }
    [data-testid="stSidebar"] * {
        color: #e4d9f5 !important;
    }
    </style>
    """,
    unsafe_allow_html=True
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
    elif selected == "Scan Barcode":
        barcode_scanner_page()
    elif selected == "Print Barcodes":
        barcode_print_page()

if __name__ == "__main__":
    main()
