import streamlit as st

# Set page configuration
st.set_page_config(page_title="Grading System", layout="wide")

# High-quality dark abstract image URL for the background
bg_url = "https://images.unsplash.com/photo-1618005182384-a83a8bd57fbe?q=80&w=1920&auto=format&fit=crop"

# Inject Custom CSS
st.markdown(
    f"""
    <style>
    /* 1. Full-screen Blurred Background with Dark Tint Overlay */
    .stApp {{
        background: 
            linear-gradient(rgba(12, 14, 22, 0.65), rgba(12, 14, 22, 0.65)),
            url("{bg_url}") no-repeat center center fixed;
        background-size: cover;
    }}

    /* 2. Glassmorphism Header (Replaces old text) */
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

    /* Inactive Tabs */
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

    /* Hover Tab State */
    .stTabs [data-baseweb="tab"]:hover {{
        color: rgba(255, 255, 255, 0.95) !important;
        background-color: rgba(255, 255, 255, 0.08) !important;
    }}

    /* Active Tab Highlight (Sleek Translucent Glass Pill) */
    .stTabs [aria-selected="true"] {{
        background: rgba(255, 255, 255, 0.18) !important;
        color: #FFFFFF !important;
        font-weight: 600;
        border: 1px solid rgba(255, 255, 255, 0.25) !important;
        box-shadow: 0 4px 16px rgba(0, 0, 0, 0.25) !important;
        backdrop-filter: blur(10px);
    }}

    /* Hide standard red/blue indicator underline */
    .stTabs [data-baseweb="tab-highlight-title"] {{
        display: none !important;
    }}
    </style>

    <!-- Display the header card -->
    <div class="header-card">
        <h1 class="title-text">Grading system</h1>
    </div>
""",
    unsafe_allow_html=True,
)

# ----------------------------------------------------
# Main Navigation Tabs
# ----------------------------------------------------
tab1, tab2, tab3, tab4 = st.tabs(
    [
        "1 Sheet Generator",
        "2 Auto Grader",
        "3 Master Consolidator",
        "4 الحضور (Attendance)",
    ]
)

with tab1:
    st.write("### Sheet Generator Content")

with tab2:
    st.write("### Upload Answer Keys & Batch Grade Mixed Papers")
    col1, col2 = st.columns(2)
    with col1:
        st.file_uploader("Upload Reference Answer Sheet Photo for Form A")
    with col2:
        st.file_uploader("Upload Reference Answer Sheet Photo for Form B")

with tab3:
    st.write("### Master Consolidator Content")

with tab4:
    st.write("### Attendance Tracker Content")
