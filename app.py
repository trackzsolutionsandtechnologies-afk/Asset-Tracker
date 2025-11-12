"""
Main Streamlit Application for Asset Tracker
"""
import streamlit as st
import streamlit.components.v1 as components
import time
from datetime import datetime
from pathlib import Path
from streamlit_option_menu import option_menu
from config import get_config
from auth import login_page, forgot_password_page, check_authentication, logout, SESSION_KEYS
from register import register_page
from dashboard import dashboard_page
from forms import (
    location_form,
    supplier_form,
    category_form,
    asset_master_form,
    attachments_form,
    asset_transfer_form,
    asset_maintenance_form,
    asset_depreciation_form,
    employee_assignment_form,
    user_management_form,
)
from barcode_utils import barcode_scanner_page, barcode_print_page
from contextlib import nullcontext



# Page configuration (must be first Streamlit command)
st.set_page_config(
    page_title="Asset Tracker",
    page_icon="📦",
    layout="centered",
    
    initial_sidebar_state="expanded"
)
st.markdown(
    """
    <style>
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #e9f7ef 0%, #fefefe 100%) !important;
        padding: clamp(1.25rem, 5vw, 1.75rem) clamp(1rem, 6vw, 1.5rem) clamp(2rem, 6vw, 2.25rem) clamp(1rem, 6vw, 1.5rem) !important;
        border-right: 1px solid #d4e4d7 !important;
        box-shadow: 12px 0 24px rgba(0, 0, 0, 0.05);
        min-width: clamp(200px, 38vw, 300px) !important;
        max-width: clamp(200px, 38vw, 300px) !important;
    }
    [data-testid="stSidebar"] > div:first-child { padding-top: 1rem !important; }
    [data-testid="stSidebar"] .nav { gap: 0.5rem !important; }

    [data-testid="stSidebar"] .nav-pills .nav-link {
        display: flex !important;
        align-items: center !important;
        gap: clamp(0.45rem, 1.5vw, 0.6rem) !important;
        padding: clamp(0.55rem, 1.8vw, 0.75rem) clamp(0.8rem, 2vw, 1rem) !important;
        border-radius: 14px !important;
        font-weight: 600 !important;
        font-size: clamp(0.85rem, 2.5vw, 0.95rem) !important;
        color: #2f3e46 !important;
        background: rgba(255, 255, 255, 0.75) !important;
        border: 1px solid rgba(209, 224, 214, 0.8) !important;
        transition: all 0.2s ease-in-out !important;
        backdrop-filter: blur(6px);
    }
    [data-testid="stSidebar"] .nav-pills .nav-link svg {
        width: clamp(0.9rem, 4vw, 1.15rem) !important;
        height: clamp(0.9rem, 4vw, 1.15rem) !important;
        color: inherit !important;
    }
    [data-testid="stSidebar"] .nav-pills .nav-link:hover {
        color: #14532d !important;
        background: rgba(168, 236, 194, 0.35) !important;
        border-color: rgba(34, 197, 94, 0.45) !important;
        box-shadow: 0 12px 20px rgba(34, 197, 94, 0.18) !important;
        transform: translateY(-1px);
    }
    [data-testid="stSidebar"] .nav-pills .nav-link.active {
        background: linear-gradient(90deg, #22c55e 0%, #16a34a 100%) !important;
        color: #ffffff !important;
        border: 1px solid rgba(22, 163, 74, 0.85) !important;
        box-shadow: 0 12px 28px rgba(34, 197, 94, 0.35) !important;
        transform: translateY(-2px);
    }
    [data-testid="stSidebar"] .nav-pills .nav-link.active:hover { color: #fff !important; }

    [data-testid="stSidebar"] hr {
        border-top: 1px solid #d7e8dd !important;
        margin: 1.5rem 0 !important;
    }
    [data-testid="stSidebar"] button[kind="secondary"] {
        border-radius: 12px !important;
        border: 1px solid rgba(34, 197, 94, 0.4) !important;
        color: #14532d !important;
        background: rgba(34, 197, 94, 0.12) !important;
        font-weight: 600 !important;
    }
    [data-testid="stSidebar"] button[kind="secondary"]:hover {
        border-color: rgba(34, 197, 94, 0.75) !important;
        color: #fff !important;
        background: #22c55e !important;
    }

    button[title="Show sidebar"],
    button[title="Hide sidebar"] {
        background-color: #38a169 !important;
        color: #ffffff !important;
        border-radius: 999px !important;
        border: none !important;
        box-shadow: 0 4px 12px rgba(56, 161, 105, 0.35) !important;
        display: none !important;
    }
    button[title="Show sidebar"] svg,
    button[title="Hide sidebar"] svg { color: #ffffff !important; }
    </style>
    """,
    unsafe_allow_html=True,
)
def load_custom_css() -> None:
    css_path = Path(__file__).parent / "styles" / "main.css"
    if css_path.exists():
        with css_path.open("r", encoding="utf-8") as css_file:
            st.markdown(f"<style>{css_file.read()}</style>", unsafe_allow_html=True)
    lock_sidebar_open()
    st.markdown(
        """
        <style>
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
    button[title="Show sidebar"],
    button[title="Hide sidebar"] {
            background-color: #38a169 !important;
            color: #ffffff !important;
            border-radius: 999px !important;
            border: none !important;
            box-shadow: 0 4px 12px rgba(56, 161, 105, 0.35) !important;
            display: none !important;
        }
        button[title="Show sidebar"] svg,
        button[title="Hide sidebar"] svg {
            color: #ffffff !important;
        }

           [data-testid="stSidebar"] .nav { gap: 0.6rem !important; }

   [data-testid="stSidebar"] .nav-pills .nav-link {
       display: flex !important;
       align-items: center !important;
       gap: 0.5rem !important;
       padding: 0.65rem 1rem !important;
       border-radius: 14px !important;
       font-weight: 600 !important;
       font-family: "DIN", sans-serif !important;
       color: #1f2937 !important;
       background: rgba(255, 255, 255, 0.75) !important;
       border: 1px solid rgba(146, 163, 255, 0.35) !important;
       transition: all 0.2s ease !important;
   }

   [data-testid="stSidebar"] .nav-pills .nav-link:hover {
       color: #1e3a8a !important;
       background: rgba(99, 102, 241, 0.15) !important;
       border-color: rgba(99, 102, 241, 0.5) !important;
       box-shadow: 0 10px 18px rgba(99, 102, 241, 0.2) !important;
       transform: translateY(-1px);
   }

   [data-testid="stSidebar"] .nav-pills .nav-link.active {
       background: linear-gradient(90deg, #6366f1 0%, #8b5cf6 100%) !important;
       color: #ffffff !important;
       border: 1px solid rgba(99, 102, 241, 0.75) !important;
       font-family: "DIN", sans-serif !important;
   }

   [data-testid="stSidebar"] .nav-pills .nav-link svg {
       width: 1.05rem !important;
       height: 1.05rem !important;
       color: inherit !important;
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


def lock_sidebar_open() -> None:
    """Ensure the sidebar stays visible and remove the toggle button."""
    components.html(
        """
        <script>
        const ensureSidebar = () => {
            const doc = window.parent.document;
            const sidebar = doc.querySelector('[data-testid="stSidebar"]');
            const collapsed = doc.querySelector('[data-testid="collapsedSidebar"]');
            const toggleButtons = doc.querySelectorAll('button[title="Hide sidebar"], button[title="Show sidebar"]');
            toggleButtons.forEach(btn => btn.style.display = 'none');
            if (sidebar) {
                sidebar.style.transform = 'translateX(0%)';
                sidebar.style.marginLeft = '0';
            }
            if (collapsed) {
                collapsed.style.transform = 'translateX(0%)';
                collapsed.style.width = sidebar ? `${sidebar.offsetWidth}px` : '260px';
            }
        };
        const init = () => {
            ensureSidebar();
            const observer = new MutationObserver(ensureSidebar);
            observer.observe(window.parent.document.body, { childList: true, subtree: true });
        };
        window.requestAnimationFrame(init);
        </script>
        """,
        height=0,
    )


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
        auth_placeholder = st.empty()
        with auth_placeholder.container():
            # Show login, register, or forgot password page
            if st.session_state.get("show_forgot_password", False):
                forgot_password_page()
            elif st.session_state.get("show_register", False):
                register_page()
            else:
                login_page()
        if not check_authentication():
            return
        auth_placeholder.empty()
        st.session_state["_force_app_rerun"] = True
        return
    
    # User is authenticated - show main application
    load_custom_css()
    apply_wide_layout()
    if st.session_state.pop("_force_app_rerun", False):
        st.rerun()
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
            menu_title="",
            options=[
                "Dashboard",
                "Location",
                "Supplier",
                "Category",
                "Asset Master",
                "Asset Transfer",
                "Attachments",
                "Maintenance",
                "Depreciation",
                "Assignment",
                "Users",
                "Scan Barcode",
                "Print Barcodes",
            ],
            icons=[
                "speedometer2",
                "geo-alt",
                "truck",
                "folder",
                "box-seam",
                "arrow-repeat",
                "paperclip",
                "tools",
                "graph-down",
                "briefcase",
                "people",
                "upc-scan",
                "printer",
            ],
            menu_icon="list",
            default_index=0,
            styles={
                "container": {
                    "padding": "0 !important",
                    "background-color": "#eaf7ef",
                },
                "icon": {
                    "font-size": "1.05rem",
                    "color": "#364152",
                },
                "nav-link": {
                    "font-size": "0.92rem",
                    "font-weight": "600",
                    "padding": "0.6rem 0.95rem",
                    "border-radius": "12px",
                    "margin": "0.18rem 0",
                    "color": "#1f2937",
                    "text-transform": "none",
                },
                "nav-link-hover": {
                    "background-color": "rgba(79, 70, 229, 0.12)",
                    "color": "#312e81",
                },
                "nav-link-selected": {
                    "background": "#98EECC",
                    "color": "#ffffff",
                    
                },
            },
        )
    if "active_page" not in st.session_state:
        st.session_state["active_page"] = None

    show_spinner = False
    if st.session_state["active_page"] != selected:
        show_spinner = st.session_state["active_page"] is not None
        st.session_state["active_page"] = selected

    content_placeholder = st.empty()
    spinner_context = st.spinner("Loading...") if show_spinner else nullcontext()

    with spinner_context, content_placeholder.container():
        start_time = time.perf_counter() if show_spinner else None
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
        elif selected == "Attachments":
            attachments_form()
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

        if show_spinner and start_time is not None:
            min_duration = 0.6
            elapsed = time.perf_counter() - start_time
            if elapsed < min_duration:
                time.sleep(min_duration - elapsed)

        st.markdown(
            """
            <div style="
                margin-top: 2.5rem;
                padding: 1.5rem 0;
                border-top: 1px solid rgba(148, 163, 184, 0.35);
                display: flex;
                flex-direction: column;
                gap: 0.4rem;
                align-items: center;
                color: #475569;
                font-size: 0.85rem;
            ">
                <div>
                    Powered by
                    <span style="font-weight: 600; color: #2563eb;">Trackz</span>
                </div>
                <div style="color: #94a3b8; font-size: 0.78rem;">
                    © {year} Trackz. All rights reserved.
                </div>
            </div>
            """.format(year=datetime.now().year),
            unsafe_allow_html=True,
        )

if __name__ == "__main__":
    main()
