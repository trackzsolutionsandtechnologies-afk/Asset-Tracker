import streamlit as st

def load_auth_css():
    """Inject custom CSS for login & forgot password pages"""
    st.markdown("""
    <style>
    /* Page background */
    body {
        background: linear-gradient(135deg, #1a2240, #3c4f91);
        color: #ffffff;
    }

    /* Center wrapper */
    .auth-form-wrapper {
        display: flex;
        justify-content: center;
        align-items: center;
        height: 90vh;
    }

    /* Streamlit form styling */
    form[data-testid="stForm"] {
        background: rgba(255, 255, 255, 0.95);
        border-radius: 18px;
        padding: 40px 36px;
        box-shadow: 0 8px 24px rgba(0,0,0,0.25);
        max-width: 420px;
        width: 100%;
        margin: 0 auto;
    }

    /* Input boxes */
    form[data-testid="stForm"] input {
        border-radius: 8px !important;
        border: 1px solid #ccc !important;
        padding: 10px !important;
        width: 100%;
    }

    /* Buttons */
    form[data-testid="stForm"] button[kind="primary"] {
        background-color: #3c4f91 !important;
        color: white !important;
        font-weight: bold !important;
        border-radius: 8px !important;
        padding: 10px !important;
        width: 100% !important;
        transition: background 0.2s ease-in-out;
    }

    form[data-testid="stForm"] button[kind="primary"]:hover {
        background-color: #2a3670 !important;
    }

    form[data-testid="stForm"] button[kind="secondary"] {
        background-color: #f2f2f2 !important;
        color: #333 !important;
        border-radius: 8px !important;
        padding: 10px !important;
    }

    /* Title */
    h1 {
        text-align: center;
        margin-bottom: 24px;
        font-size: 28px;
        color: #ffffff;
    }
    </style>
    """, unsafe_allow_html=True)
