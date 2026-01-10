import streamlit as st
import requests
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import os
from datetime import datetime, timedelta

# Configuration
API_URL = os.getenv("API_URL", "http://localhost:8000")

# CSS personnalisé
st.markdown(
    """
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
""",
    unsafe_allow_html=True,
)

# Titre principal
st.title("📊 Tableau de bord")
st.markdown("**Analyse Textuelle et Localisation des Annonces Spécialisées**")
st.markdown("---")

# ============================================================================
# SIDEBAR - FILTRES
# ============================================================================

with st.sidebar:
    st.header("🔍 Filtres")

    # Filtre par source
    source_options = {
        "France Travail": "france_travail",
        "Welcome to the Jungle": "welcome_to_the_jungle",
    }
    source_filter_display = st.multiselect(
        "Source",
        list(source_options.keys()),
        default=list(source_options.keys()),
    )
    source_filter = [source_options[s] for s in source_filter_display]

    # Filtre par type de contrat
    contract_filter = st.multiselect(
        "Type de contrat",
        ["CDI", "CDD", "Intérim", "Stage", "Alternance"],
        default=["CDI", "CDD", "Stage"],
    )

    # Filtre par région
    region_filter = st.multiselect(
        "Région",
        [
            "Ile-de-France",
            "Auvergne-Rhone-Alpes",
            "Occitanie",
            "Nouvelle-Aquitaine",
            "Provence-Alpes-Cote d Azur",
        ],
        default=[],
    )

    # Filtre par date
    date_range = st.date_input(
        "Période",
        value=(datetime.now() - timedelta(days=7), datetime.now()),
        max_value=datetime.now(),
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
def load_offers(limit=100, sources=None, contracts=None):
    """Charge les offres avec leurs relations"""
    try:
        params = {"limit": limit}
        if sources:
            params["source"] = ",".join(sources)
        if contracts:
            params["contract"] = ",".join(contracts)
        response = requests.get(f"{API_URL}/api/offers", params=params)
        return response.json()
    except:
        return {"offers": [], "count": 0}


@st.cache_data(ttl=300)
def load_sources_stats():
    try:
        response = requests.get(f"{API_URL}/api/sources")
        return response.json().get("sources", [])
    except:
        return []


@st.cache_data(ttl=300)
def load_contracts_stats():
    try:
        response = requests.get(f"{API_URL}/api/contracts")
        return response.json().get("contracts", [])
    except:
        return []


@st.cache_data(ttl=300)
def load_cities_stats():
    try:
        response = requests.get(f"{API_URL}/api/cities")
        return response.json().get("cities", [])
    except:
        return []


@st.cache_data(ttl=300)
def load_regions_stats():
    try:
        response = requests.get(f"{API_URL}/api/regions")
        return response.json().get("regions", [])
    except:
        return []


@st.cache_data(ttl=300)
def load_profiles_stats():
    try:
        response = requests.get(f"{API_URL}/api/profiles")
        return response.json().get("profiles", [])
    except:
        return []


@st.cache_data(ttl=300)
def load_salaries_stats():
    try:
        response = requests.get(f"{API_URL}/api/salaries")
        return response.json()
    except:
        return {"ranges": [], "avg_by_profile": []}


@st.cache_data(ttl=300)
def load_timeline_stats():
    try:
        response = requests.get(f"{API_URL}/api/timeline")
        return response.json().get("timeline", [])
    except:
        return []


@st.cache_data(ttl=300)
def load_advanced_stats():
    try:
        response = requests.get(f"{API_URL}/api/advanced-stats")
        return response.json()
    except:
        return {"salary_fill_rate": 0, "avg_publication_delay": 0, "remote_rate": 0}


stats = load_stats()
offers_data = load_offers(
    limit=500,
    sources=source_filter if source_filter else None,
    contracts=contract_filter if contract_filter else None,
)
sources_stats = load_sources_stats()
contracts_stats = load_contracts_stats()
cities_stats = load_cities_stats()
regions_stats = load_regions_stats()
profiles_stats = load_profiles_stats()
salaries_stats = load_salaries_stats()
timeline_stats = load_timeline_stats()
advanced_stats = load_advanced_stats()

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
        delta="+12 aujourd'hui" if total_offers > 0 else None,
    )

with col2:
    total_metiers = stats.get("total_metiers", 37)
    st.metric(label="💼 Métiers identifiés", value=total_metiers)

with col3:
    total_regions = stats.get("total_regions", 5)
    st.metric(label="🗺️ Régions couvertes", value=total_regions)

with col4:
    total_locations = stats.get("total_locations", 82)
    st.metric(label="📍 Villes", value=total_locations)

st.markdown("---")

# ============================================================================
# SECTION 1 : RÉPARTITION PAR SOURCE
# ============================================================================

st.subheader("🎯 Répartition des offres")

col_left, col_right = st.columns(2)

with col_left:
    st.markdown("#### Par source")

    if sources_stats:
        df_sources = pd.DataFrame(sources_stats)
        df_sources.columns = ["Source", "Nombre"]

        fig_sources = px.pie(
            df_sources,
            values="Nombre",
            names="Source",
            hole=0.4,
            color_discrete_sequence=["#667eea", "#764ba2"],
        )
        fig_sources.update_traces(textposition="inside", textinfo="percent+label")
        fig_sources.update_layout(showlegend=True, height=350)

        st.plotly_chart(fig_sources, use_container_width=True)
    else:
        st.info("Aucune donnée disponible")

with col_right:
    st.markdown("#### Par type de contrat")

    if contracts_stats:
        df_contracts = pd.DataFrame(contracts_stats)
        df_contracts.columns = ["Contrat", "Nombre"]

        fig_contracts = px.bar(
            df_contracts,
            x="Contrat",
            y="Nombre",
            color="Contrat",
            color_discrete_sequence=["#667eea", "#764ba2", "#f093fb", "#4facfe"],
        )
        fig_contracts.update_layout(showlegend=False, height=350)

        st.plotly_chart(fig_contracts, use_container_width=True)
    else:
        st.info("Aucune donnée disponible")

st.markdown("---")

# ============================================================================
# SECTION 2 : RÉPARTITION GÉOGRAPHIQUE
# ============================================================================

st.subheader("🗺️ Répartition géographique")

col_geo1, col_geo2 = st.columns([2, 1])

with col_geo1:
    st.markdown("#### Top 10 des villes")

    if cities_stats:
        df_cities = pd.DataFrame(cities_stats)
        df_cities.columns = ["Ville", "Offres"]

        fig_cities = px.bar(
            df_cities,
            x="Offres",
            y="Ville",
            orientation="h",
            color="Offres",
            color_continuous_scale="Purples",
        )
        fig_cities.update_layout(height=400, showlegend=False)

        st.plotly_chart(fig_cities, use_container_width=True)
    else:
        st.info("Aucune donnée disponible")

with col_geo2:
    st.markdown("#### Par région")

    if regions_stats:
        df_regions = pd.DataFrame(regions_stats)
        df_regions.columns = ["Région", "Offres"]

        fig_regions = px.pie(
            df_regions,
            values="Offres",
            names="Région",
            color_discrete_sequence=px.colors.sequential.Purples,
        )
        fig_regions.update_traces(textposition="inside", textinfo="percent+label")
        fig_regions.update_layout(height=400, showlegend=True)

        st.plotly_chart(fig_regions, use_container_width=True)
    else:
        st.info("Aucune donnée disponible")

st.markdown("---")

# ============================================================================
# SECTION 3 : MÉTIERS LES PLUS DEMANDÉS
# ============================================================================

st.subheader("💼 Top 15 des métiers les plus recherchés")

if profiles_stats:
    df_metiers = pd.DataFrame(profiles_stats)
    df_metiers.columns = ["Métier", "Offres"]

    fig_metiers = px.bar(
        df_metiers,
        x="Offres",
        y="Métier",
        orientation="h",
        color="Offres",
        color_continuous_scale="Viridis",
    )
    fig_metiers.update_layout(height=500, showlegend=False)

    st.plotly_chart(fig_metiers, use_container_width=True)
else:
    st.info("Aucune donnée disponible")

st.markdown("---")

# ============================================================================
# SECTION 4 : ANALYSE DES SALAIRES
# ============================================================================

st.subheader("💰 Analyse des salaires")

col_sal1, col_sal2 = st.columns(2)

with col_sal1:
    st.markdown("#### Distribution des salaires (K€/an)")

    if salaries_stats.get("ranges"):
        df_salaries = pd.DataFrame(salaries_stats["ranges"])
        df_salaries.columns = ["Tranche", "Nombre"]

        fig_sal = px.bar(
            df_salaries,
            x="Tranche",
            y="Nombre",
            color="Nombre",
            color_continuous_scale="Blues",
        )
        fig_sal.update_layout(height=350, showlegend=False)

        st.plotly_chart(fig_sal, use_container_width=True)
    else:
        st.info("Aucune donnée disponible")

with col_sal2:
    st.markdown("#### Salaires moyens par métier (K€/an)")

    if salaries_stats.get("avg_by_profile"):
        df_avg_sal = pd.DataFrame(salaries_stats["avg_by_profile"])
        df_avg_sal.columns = ["Métier", "Salaire moyen"]

        fig_avg_sal = px.bar(
            df_avg_sal,
            x="Salaire moyen",
            y="Métier",
            orientation="h",
            color="Salaire moyen",
            color_continuous_scale="Greens",
        )
        fig_avg_sal.update_layout(height=350, showlegend=False)

        st.plotly_chart(fig_avg_sal, use_container_width=True)
    else:
        st.info("Aucune donnée disponible")

st.markdown("---")

# ============================================================================
# SECTION 5 : TIMELINE DES PUBLICATIONS
# ============================================================================

st.subheader("📅 Timeline des publications")

if timeline_stats:
    df_timeline = pd.DataFrame(timeline_stats)
    df_timeline.columns = ["Date", "Offres"]
    df_timeline["Date"] = pd.to_datetime(df_timeline["Date"])

    fig_timeline = px.line(
        df_timeline,
        x="Date",
        y="Offres",
        markers=True,
        color_discrete_sequence=["#667eea"],
    )
    fig_timeline.update_layout(height=350)

    st.plotly_chart(fig_timeline, use_container_width=True)
else:
    st.info("Aucune donnée disponible")

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

    # Mapping des sources
    source_names = {
        "france_travail": "France Travail",
        "welcome_to_the_jungle": "Welcome to the Jungle",
    }

    for i, offer in enumerate(offers, 1):
        # Extraire les infos de localisation
        location = offer.get("location", "N/A")
        company_name = offer.get("company_name", "N/A")

        with st.expander(
            f"**{i}. {offer.get('title', 'Sans titre')}** - {company_name} ({location})"
        ):

            col_o1, col_o2, col_o3 = st.columns([2, 1, 1])

            with col_o1:
                st.markdown(f"**🏢 Entreprise :** {company_name}")
                st.markdown(f"**📍 Localisation :** {location}")
                st.markdown(f"**📄 Contrat :** {offer.get('contract_type', 'N/A')}")

            with col_o2:
                st.markdown(f"**💰 Salaire :**")
                salary_min = offer.get("salary_min")
                salary_max = offer.get("salary_max")
                if salary_min and salary_max:
                    st.markdown(f"{int(salary_min)}K - {int(salary_max)}K €")
                elif salary_min:
                    st.markdown(f"À partir de {int(salary_min)}K €")
                else:
                    st.markdown("Non spécifié")

            with col_o3:
                st.markdown(f"**📅 Publié le :**")
                published_date = offer.get("published_date")
                if published_date:
                    # Extraire seulement la date (format: YYYY-MM-DD)
                    date_only = (
                        published_date.split("T")[0]
                        if "T" in published_date
                        else published_date
                    )
                    st.markdown(f"{date_only}")
                else:
                    st.markdown("N/A")

                source = offer.get("source", "N/A")
                source_display = source_names.get(source, source)
                st.markdown(f"**🔗 Source :** {source_display}")

            if offer.get("url"):
                st.markdown(f"[🔗 Voir l'offre complète]({offer.get('url')})")
else:
    st.info("Aucune offre disponible pour le moment")

st.markdown("---")

# ============================================================================
# SECTION 7 : STATISTIQUES AVANCÉES
# ============================================================================

st.subheader("📈 Statistiques avancées")

col_stat1, col_stat2, col_stat3 = st.columns(3)

with col_stat1:
    salary_rate = advanced_stats.get("salary_fill_rate", 0)
    st.metric(
        label="Taux de remplissage salaire",
        value=f"{salary_rate}%",
    )

with col_stat2:
    avg_delay = advanced_stats.get("avg_publication_delay", 0)
    st.metric(label="Délai moyen de publication", value=f"{avg_delay} jours")

with col_stat3:
    remote_rate = advanced_stats.get("remote_rate", 0)
    st.metric(label="Offres avec télétravail", value=f"{remote_rate}%")

# ============================================================================
# FOOTER
# ============================================================================

st.markdown("---")
st.markdown(
    """
<div style='text-align: center; color: #666;'>
    <p><strong>ATLAS</strong> - Analyse Textuelle et Localisation des Annonces Spécialisées</p>
    <p style='font-size: 0.8rem;'>Données collectées depuis France Travail et Welcome to the Jungle</p>
    <p style='font-size: 0.8rem;'>Dernière mise à jour : {}</p>
</div>
""".format(
        datetime.now().strftime("%d/%m/%Y %H:%M")
    ),
    unsafe_allow_html=True,
)
