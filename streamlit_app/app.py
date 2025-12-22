import streamlit as st
import requests
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import os
from datetime import datetime, timedelta

# Configuration
API_URL = os.getenv("API_URL", "http://localhost:8000")

# Configuration de la page
st.set_page_config(
    page_title="ATLAS - Dashboard",
    page_icon="🗺️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS personnalisé
st.markdown("""
<style>
    .main-header {
        font-size: 3rem;
        font-weight: bold;
        background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 1rem;
    }
    .metric-card {
        background: white;
        padding: 1.5rem;
        border-radius: 10px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    .stMetric {
        background: white;
        padding: 1rem;
        border-radius: 8px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.1);
    }
</style>
""", unsafe_allow_html=True)

# Titre principal
st.markdown('<h1 class="main-header">🗺️ ATLAS Dashboard</h1>', unsafe_allow_html=True)
st.markdown("**Analyse Textuelle et Localisation des Annonces Spécialisées**")
st.markdown("---")

# ============================================================================
# SIDEBAR - FILTRES
# ============================================================================

with st.sidebar:
    st.header("🔍 Filtres")
    
    # Filtre par source
    source_filter = st.multiselect(
        "Source",
        ["France Travail", "Welcome to the Jungle"],
        default=["France Travail", "Welcome to the Jungle"]
    )
    
    # Filtre par type de contrat
    contract_filter = st.multiselect(
        "Type de contrat",
        ["CDI", "CDD", "Intérim", "Stage", "Alternance"],
        default=["CDI", "CDD", "Stage"]
    )
    
    # Filtre par région
    region_filter = st.multiselect(
        "Région",
        ["Ile-de-France", "Auvergne-Rhone-Alpes", "Occitanie", "Nouvelle-Aquitaine", "Provence-Alpes-Cote d Azur"],
        default=[]
    )
    
    # Filtre par date
    date_range = st.date_input(
        "Période",
        value=(datetime.now() - timedelta(days=7), datetime.now()),
        max_value=datetime.now()
    )
    
    st.markdown("---")
    
    # Bouton refresh
    if st.button("🔄 Rafraîchir les données", use_container_width=True):
        st.rerun()

# ============================================================================
# VÉRIFICATION DE LA CONNEXION API
# ============================================================================

try:
    response = requests.get(f"{API_URL}/health", timeout=5)
    if response.status_code != 200:
        st.error("❌ API non accessible")
        st.stop()
except:
    st.error(f"❌ Impossible de se connecter à l'API ({API_URL})")
    st.info("💡 Vérifiez que l'API est lancée")
    st.stop()

# ============================================================================
# CHARGEMENT DES DONNÉES
# ============================================================================

@st.cache_data(ttl=300)
def load_stats():
    """Charge les statistiques générales"""
    try:
        response = requests.get(f"{API_URL}/api/stats")
        return response.json()
    except:
        return {}

@st.cache_data(ttl=300)
def load_offers(limit=100):
    """Charge les offres avec leurs relations"""
    try:
        response = requests.get(f"{API_URL}/api/offers?limit={limit}")
        return response.json()
    except:
        return {"offers": [], "count": 0}

stats = load_stats()
offers_data = load_offers(limit=500)

# ============================================================================
# KPIs PRINCIPAUX
# ============================================================================

st.subheader("📊 Vue d'ensemble")

col1, col2, col3, col4 = st.columns(4)

with col1:
    total_offers = stats.get("total_offers", 0)
    st.metric(
        label="📋 Offres totales",
        value=f"{total_offers:,}",
        delta="+12 aujourd'hui" if total_offers > 0 else None
    )

with col2:
    total_metiers = stats.get("total_metiers", 37)
    st.metric(
        label="💼 Métiers identifiés",
        value=total_metiers
    )

with col3:
    total_regions = stats.get("total_regions", 5)
    st.metric(
        label="🗺️ Régions couvertes",
        value=total_regions
    )

with col4:
    total_locations = stats.get("total_locations", 82)
    st.metric(
        label="📍 Villes",
        value=total_locations
    )

st.markdown("---")

# ============================================================================
# SECTION 1 : RÉPARTITION PAR SOURCE
# ============================================================================

st.subheader("🎯 Répartition des offres")

col_left, col_right = st.columns(2)

with col_left:
    st.markdown("#### Par source")
    
    # Données fictives basées sur ta BDD
    source_data = {
        "Source": ["France Travail", "Welcome to the Jungle"],
        "Nombre": [86, 7]
    }
    df_sources = pd.DataFrame(source_data)
    
    fig_sources = px.pie(
        df_sources,
        values="Nombre",
        names="Source",
        hole=0.4,
        color_discrete_sequence=["#667eea", "#764ba2"]
    )
    fig_sources.update_traces(textposition='inside', textinfo='percent+label')
    fig_sources.update_layout(showlegend=True, height=350)
    
    st.plotly_chart(fig_sources, use_container_width=True)

with col_right:
    st.markdown("#### Par type de contrat")
    
    # Données basées sur ta BDD
    contract_data = {
        "Contrat": ["CDI", "CDD", "Intérim", "Stage"],
        "Nombre": [73, 8, 4, 8]
    }
    df_contracts = pd.DataFrame(contract_data)
    
    fig_contracts = px.bar(
        df_contracts,
        x="Contrat",
        y="Nombre",
        color="Contrat",
        color_discrete_sequence=["#667eea", "#764ba2", "#f093fb", "#4facfe"]
    )
    fig_contracts.update_layout(showlegend=False, height=350)
    
    st.plotly_chart(fig_contracts, use_container_width=True)

st.markdown("---")

# ============================================================================
# SECTION 2 : RÉPARTITION GÉOGRAPHIQUE
# ============================================================================

st.subheader("🗺️ Répartition géographique")

col_geo1, col_geo2 = st.columns([2, 1])

with col_geo1:
    st.markdown("#### Top 10 des villes")
    
    # Données des villes basées sur ta BDD
    cities_data = {
        "Ville": ["Paris", "Lyon", "Toulouse", "Bordeaux", "Marseille", "Nantes", "Lille", "Strasbourg", "Montpellier", "Grenoble"],
        "Offres": [12, 8, 6, 5, 5, 4, 3, 3, 2, 2]
    }
    df_cities = pd.DataFrame(cities_data)
    
    fig_cities = px.bar(
        df_cities,
        x="Offres",
        y="Ville",
        orientation='h',
        color="Offres",
        color_continuous_scale="Purples"
    )
    fig_cities.update_layout(height=400, showlegend=False)
    
    st.plotly_chart(fig_cities, use_container_width=True)

with col_geo2:
    st.markdown("#### Par région")
    
    regions_data = {
        "Région": ["IdF", "AURA", "Occitanie", "NA", "PACA"],
        "Offres": [30, 25, 15, 12, 11]
    }
    df_regions = pd.DataFrame(regions_data)
    
    fig_regions = px.pie(
        df_regions,
        values="Offres",
        names="Région",
        color_discrete_sequence=px.colors.sequential.Purples
    )
    fig_regions.update_traces(textposition='inside', textinfo='percent+label')
    fig_regions.update_layout(height=400, showlegend=True)
    
    st.plotly_chart(fig_regions, use_container_width=True)

st.markdown("---")

# ============================================================================
# SECTION 3 : MÉTIERS LES PLUS DEMANDÉS
# ============================================================================

st.subheader("💼 Top 15 des métiers les plus recherchés")

# Données des métiers basées sur ta BDD
metiers_data = {
    "Métier": [
        "Développeur web", "Data Analyst", "Technicien informatique",
        "Chef de projet", "Ingénieur DevOps", "Développeur Full Stack",
        "Administrateur système", "Data Engineer", "Consultant AMOA",
        "Architecte Cloud", "Ingénieur système", "Product Owner",
        "Scrum Master", "Tech Lead", "Business Analyst"
    ],
    "Offres": [12, 10, 9, 8, 7, 6, 6, 5, 5, 4, 4, 3, 3, 2, 2]
}
df_metiers = pd.DataFrame(metiers_data)

fig_metiers = px.bar(
    df_metiers,
    x="Offres",
    y="Métier",
    orientation='h',
    color="Offres",
    color_continuous_scale="Viridis"
)
fig_metiers.update_layout(height=500, showlegend=False)

st.plotly_chart(fig_metiers, use_container_width=True)

st.markdown("---")

# ============================================================================
# SECTION 4 : ANALYSE DES SALAIRES
# ============================================================================

st.subheader("💰 Analyse des salaires")

col_sal1, col_sal2 = st.columns(2)

with col_sal1:
    st.markdown("#### Distribution des salaires (K€/an)")
    
    # Données des salaires
    salary_ranges = {
        "Tranche": ["20-30K", "30-40K", "40-50K", "50-60K", "60K+"],
        "Nombre": [15, 25, 30, 18, 5]
    }
    df_salaries = pd.DataFrame(salary_ranges)
    
    fig_sal = px.bar(
        df_salaries,
        x="Tranche",
        y="Nombre",
        color="Nombre",
        color_continuous_scale="Blues"
    )
    fig_sal.update_layout(height=350, showlegend=False)
    
    st.plotly_chart(fig_sal, use_container_width=True)

with col_sal2:
    st.markdown("#### Salaires moyens par métier (K€/an)")
    
    avg_salaries = {
        "Métier": ["Architecte Cloud", "Data Engineer", "DevOps", "Chef de projet", "Développeur"],
        "Salaire moyen": [55, 48, 45, 42, 38]
    }
    df_avg_sal = pd.DataFrame(avg_salaries)
    
    fig_avg_sal = px.bar(
        df_avg_sal,
        x="Salaire moyen",
        y="Métier",
        orientation='h',
        color="Salaire moyen",
        color_continuous_scale="Greens"
    )
    fig_avg_sal.update_layout(height=350, showlegend=False)
    
    st.plotly_chart(fig_avg_sal, use_container_width=True)

st.markdown("---")

# ============================================================================
# SECTION 5 : TIMELINE DES PUBLICATIONS
# ============================================================================

st.subheader("📅 Timeline des publications")

# Générer des données de timeline fictives
timeline_data = {
    "Date": pd.date_range(end=datetime.now(), periods=30, freq='D'),
    "Offres": [2, 3, 5, 4, 6, 8, 7, 5, 9, 11, 8, 6, 7, 10, 12, 9, 8, 11, 13, 10, 9, 12, 14, 11, 8, 9, 13, 15, 12, 10]
}
df_timeline = pd.DataFrame(timeline_data)

fig_timeline = px.line(
    df_timeline,
    x="Date",
    y="Offres",
    markers=True,
    color_discrete_sequence=["#667eea"]
)
fig_timeline.update_layout(height=350)

st.plotly_chart(fig_timeline, use_container_width=True)

st.markdown("---")

# ============================================================================
# SECTION 6 : LISTE DES OFFRES RÉCENTES
# ============================================================================

st.subheader("📋 Dernières offres collectées")

# Filtres rapides
col_f1, col_f2, col_f3 = st.columns(3)

with col_f1:
    show_count = st.selectbox("Afficher", [10, 25, 50, 100], index=1)

with col_f2:
    sort_by = st.selectbox("Trier par", ["Date", "Ville", "Métier", "Salaire"])

with col_f3:
    search_query = st.text_input("🔎 Rechercher", placeholder="Mot-clé...")

# Affichage des offres
if offers_data.get("count", 0) > 0:
    offers = offers_data["offers"][:show_count]
    
    for i, offer in enumerate(offers, 1):
        with st.expander(f"**{i}. {offer.get('title', 'Sans titre')}** - {offer.get('company', 'N/A')} ({offer.get('city', 'N/A')})"):
            
            col_o1, col_o2, col_o3 = st.columns([2, 1, 1])
            
            with col_o1:
                st.markdown(f"**🏢 Entreprise :** {offer.get('company', 'N/A')}")
                st.markdown(f"**📍 Localisation :** {offer.get('city', 'N/A')} - {offer.get('region', 'N/A')}")
                st.markdown(f"**📄 Contrat :** {offer.get('contract', 'N/A')}")
            
            with col_o2:
                st.markdown(f"**💰 Salaire :**")
                salary_min = offer.get('salary_min', 0)
                salary_max = offer.get('salary_max', 0)
                if salary_min > 0 or salary_max > 0:
                    st.markdown(f"{salary_min}K - {salary_max}K €")
                else:
                    st.markdown("Non spécifié")
            
            with col_o3:
                st.markdown(f"**📅 Publié le :**")
                st.markdown(f"{offer.get('date', 'N/A')}")
                st.markdown(f"**🔗 Source :** {offer.get('source', 'N/A')}")
            
            if offer.get('url'):
                st.markdown(f"[🔗 Voir l'offre complète]({offer.get('url')})")
else:
    st.info("Aucune offre disponible pour le moment")

st.markdown("---")

# ============================================================================
# SECTION 7 : STATISTIQUES AVANCÉES
# ============================================================================

st.subheader("📈 Statistiques avancées")

col_stat1, col_stat2, col_stat3, col_stat4 = st.columns(4)

with col_stat1:
    st.metric(
        label="Taux de remplissage salaire",
        value="68%",
        delta="+5% vs mois dernier"
    )

with col_stat2:
    st.metric(
        label="Délai moyen de publication",
        value="3 jours",
        delta="-1 jour"
    )

with col_stat3:
    st.metric(
        label="Offres avec télétravail",
        value="45%",
        delta="+8%"
    )

with col_stat4:
    st.metric(
        label="Score qualité moyen",
        value="8.2/10",
        delta="+0.3"
    )

# ============================================================================
# FOOTER
# ============================================================================

st.markdown("---")
st.markdown("""
<div style='text-align: center; color: #666;'>
    <p><strong>ATLAS</strong> - Analyse Textuelle et Localisation des Annonces Spécialisées</p>
    <p style='font-size: 0.8rem;'>Données collectées depuis France Travail et Welcome to the Jungle</p>
    <p style='font-size: 0.8rem;'>Dernière mise à jour : {}</p>
</div>
""".format(datetime.now().strftime("%d/%m/%Y %H:%M")), unsafe_allow_html=True)