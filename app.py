import base64
import streamlit as st


# Helper function to encode image to base64
def get_base64_of_bin_file(bin_file):
    with open(bin_file, "rb") as f:
        data = f.read()
    return base64.b64encode(data).decode()


# Encode background image
bg_base64 = get_base64_of_bin_file("image_9ebd99.jpg")

st.markdown(
    f"""
    <style>
    /* 1. Full-screen Blurred Background with Dark Overlay */
    .stApp {{
        background: 
            linear-gradient(rgba(12, 14, 22, 0.65), rgba(12, 14, 22, 0.65)),
            url("data:image/jpeg;base64,{bg_base64}") no-repeat center center fixed;
        background-size: cover;
    }}

    /* 2. Sleek Glass Header Container (Replaces old hero text) */
    .header-card {{
        background: rgba(255, 255, 255, 0.05);
        backdrop-filter: blur(25px);
        -webkit-backdrop-filter: blur(25px);
        border: 1px solid rgba(255, 255, 255, 0.12);
        border-radius: 18px;
        padding: 24px 32px;
        margin-bottom: 28px;
        box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.35);
    }}

    .title-text {{
        font-family: -apple-system, BlinkMacSystemFont, "SF Pro Display", "SF Pro Text", "Helvetica Neue", Arial, sans-serif;
        font-size: 2.8rem;
        font-weight: 700;
        letter-spacing: -0.025em;
        background: linear-gradient(135deg, #00D2FF 0%, #3A7BD5 50%, #FF7E5F 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin: 0;
        line-height: 1.1;
    }}

    /* 3. Sleek Translucent Tabs Bar (Replaces Bright Blue Highlight) */
    .stTabs [data-baseweb="tab-list"] {{
        gap: 8px;
        background-color: rgba(255, 255, 255, 0.05) !important;
        padding: 6px;
        border-radius: 14px;
        border: 1px solid rgba(255, 255, 255, 0.1) !important;
        backdrop-filter: blur(20px);
        -webkit-backdrop-filter: blur(20px);
    }}

    /* Inactive Tab Styling */
    .stTabs [data-baseweb="tab"] {{
        height: 40px;
        border-radius: 10px;
        font-weight: 500;
        font-size: 14px;
        color: rgba(255, 255, 255, 0.65) !important;
        border: 1px solid transparent !important;
        padding: 0 18px;
        background-color: transparent !important;
        transition: all 0.25s ease;
    }}

    /* Hover State for Tabs */
    .stTabs [data-baseweb="tab"]:hover {{
        color: rgba(255, 255, 255, 0.95) !important;
        background-color: rgba(255, 255, 255, 0.08) !important;
    }}

    /* Active Tab Highlight (Translucent Glass Pill) */
    .stTabs [aria-selected="true"] {{
        background: rgba(255, 255, 255, 0.18) !important;
        color: #FFFFFF !important;
        font-weight: 600;
        border: 1px solid rgba(255, 255, 255, 0.25) !important;
        box-shadow: 0 4px 16px rgba(0, 0, 0, 0.25) !important;
        backdrop-filter: blur(10px);
    }}

    /* Remove Default Streamlit Tab Indicator Line */
    .stTabs [data-baseweb="tab-highlight-title"] {{
        display: none !important;
    }}
    </style>

    <div class="header-card">
        <h1 class="title-text">Grading system</h1>
    </div>
""",
    unsafe_allow_html=True,
)
