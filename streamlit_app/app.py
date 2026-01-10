import streamlit as st
from pathlib import Path
from datetime import datetime, timedelta

# Configuration de la page (doit être la première commande Streamlit)
st.set_page_config(
    page_title="ATLAS",
    page_icon="🗺️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Pages path definition
PAGES_PATH = Path(__file__).parent / "pages"

# Menu Definition
pages = {
    "Principal": [
        st.Page(PAGES_PATH / "dashboard.py", title="📊 Tableau de bord"),
        st.Page(PAGES_PATH / "discover_page.py", title="🔍 Explorer les offres"),
    ],
    "Analyses": [
        st.Page(PAGES_PATH / "tendances_page.py", title="📈 Tendances"),
        st.Page(PAGES_PATH / "comparaisons_page.py", title="⚖️ Comparaisons"),
    ],
    "Administration": [
        st.Page(PAGES_PATH / "administration_page.py", title="⚙️ Administration"),
    ],
}

# Navigation
pg = st.navigation(pages)
pg.run()
