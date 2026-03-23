import streamlit as st
import streamlit.components.v1 as components
import os

st.set_page_config(
    page_title="AI Market Analysis",
    page_icon="📈",
    layout="wide"
)

# Hide Streamlit default header/footer for clean look
st.markdown("""
    <style>
        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}
        header {visibility: hidden;}
        .block-container {padding: 0 !important;}
    </style>
""", unsafe_allow_html=True)

html_file = os.path.join(os.path.dirname(__file__), "index.html")

if os.path.exists(html_file):
    with open(html_file, "r", encoding="utf-8") as f:
        html = f.read()
    components.html(html, height=4000, scrolling=True)
else:
    st.warning("Report not generated yet. Run the bot to generate it.")
