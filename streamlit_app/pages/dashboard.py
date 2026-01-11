import streamlit as st
import requests
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import os
from datetime import datetime, timedelta
from pathlib import Path

# Configuration
API_URL = os.getenv("API_URL", "http://localhost:8000")

# Afficher le logo dans la sidebar
try:
    # Essayer le chemin local (depuis streamlit_app/pages)
    logo_path = Path(__file__).parent.parent.parent / "images" / "Logo.png"
    if not logo_path.exists():
        # Essayer le chemin Docker (depuis /app/pages)
        logo_path = Path(__file__).parent.parent / "images" / "Logo.png"

    if logo_path.exists():
        st.sidebar.image(str(logo_path), use_container_width=True)
except:
    pass  # Si le logo n'est pas trouvé, continuer sans erreur

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


@st.cache_data(ttl=60)
def load_today_offers_count():
    """Charge le nombre d'offres collectées aujourd'hui"""
    try:
        # Calculer la date d'hier
        from datetime import datetime, timedelta

        yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
        response = requests.get(
            f"{API_URL}/api/offers/count", params={"date_from": yesterday}
        )
        return response.json().get("total", 0)
    except:
        return 0


@st.cache_data(ttl=300)
def load_available_locations(location_type):
    """Charge la liste des villes ou régions disponibles"""
    try:
        response = requests.get(
            f"{API_URL}/api/stats/available-locations",
            params={"location_type": location_type},
        )
        return response.json().get("locations", [])
    except:
        return []


@st.cache_data(ttl=300)
def load_contracts_by_location(
    location_type, location_name=None, source=None, contract=None, days=None
):
    """Charge les stats de contrats par localisation"""
    try:
        params = {"location_type": location_type}
        if location_name:
            params["location_name"] = location_name
        if source:
            params["source"] = source
        if contract:
            params["contract"] = contract
        if days:
            params["days"] = days
        response = requests.get(
            f"{API_URL}/api/stats/contracts-by-location", params=params
        )
        return response.json()
    except:
        return {}


@st.cache_data(ttl=300)
def load_profiles_by_location(
    location_type, location_name=None, limit=15, source=None, contract=None, days=None
):
    """Charge les métiers par localisation"""
    try:
        params = {"location_type": location_type, "limit": limit}
        if location_name:
            params["location_name"] = location_name
        if source:
            params["source"] = source
        if contract:
            params["contract"] = contract
        if days:
            params["days"] = days
        response = requests.get(
            f"{API_URL}/api/stats/profiles-by-location", params=params
        )
        return response.json()
    except:
        return {}


@st.cache_data(ttl=300)
def load_salaries_by_location(
    location_type, location_name=None, source=None, contract=None, days=None
):
    """Charge les stats de salaires par localisation"""
    try:
        params = {"location_type": location_type}
        if location_name:
            params["location_name"] = location_name
        if source:
            params["source"] = source
        if contract:
            params["contract"] = contract
        if days:
            params["days"] = days
        response = requests.get(
            f"{API_URL}/api/stats/salaries-by-location", params=params
        )
        return response.json()
    except:
        return {}


stats = load_stats()
offers_data = load_offers(limit=500)
sources_stats = load_sources_stats()
contracts_stats = load_contracts_stats()
cities_stats = load_cities_stats()
regions_stats = load_regions_stats()
profiles_stats = load_profiles_stats()
salaries_stats = load_salaries_stats()
timeline_stats = load_timeline_stats()
advanced_stats = load_advanced_stats()
today_count = load_today_offers_count()

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
        delta=f"+{today_count} aujourd'hui" if today_count > 0 else None,
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

st.subheader("🎯 Statistiques globales")
st.caption("Vue d'ensemble sans filtres géographiques")

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
col_f1, col_f2, col_f3, col_f4 = st.columns(4)

with col_f1:
    show_count = st.selectbox(
        "Afficher", [10, 25, 50, 100], index=1, key="offers_limit"
    )

with col_f2:
    sort_by_options = {
        "Date": "date",
        "Ville": "ville",
        "Métier": "metier",
        "Salaire": "salaire",
    }
    sort_by_display = st.selectbox(
        "Trier par", list(sort_by_options.keys()), key="offers_sort"
    )
    sort_by = sort_by_options[sort_by_display]

with col_f3:
    search_query = st.text_input(
        "🔎 Rechercher", placeholder="Mot-clé...", key="offers_search"
    )

with col_f4:
    # Réutiliser les mêmes filtres que les statistiques détaillées
    date_filter_offers_options = {
        "Tout": None,
        "7 derniers jours": 7,
        "30 derniers jours": 30,
        "90 derniers jours": 90,
    }
    date_filter_offers_display = st.selectbox(
        "Période", list(date_filter_offers_options.keys()), index=2, key="date_offers"
    )
    date_filter_offers = date_filter_offers_options[date_filter_offers_display]


# Charger les offres avec filtres depuis le nouvel endpoint
@st.cache_data(ttl=300)
def load_collected_offers(
    limit, sort_by, search=None, source=None, contract=None, days=None
):
    """Charge les offres collectées avec filtres avancés"""
    try:
        params = {
            "limit": limit,
            "offset": 0,
            "sort_by": sort_by,
        }
        if search:
            params["search"] = search
        if source:
            params["source"] = source
        if contract:
            params["contract"] = contract
        if days:
            params["days"] = days

        response = requests.get(f"{API_URL}/api/offers/collected", params=params)
        return response.json()
    except:
        return {"offers": [], "total": 0}


# Charger les offres avec les filtres appliqués
# On réutilise source_filter et contract_filter des statistiques détaillées s'ils existent
collected_offers_data = load_collected_offers(
    show_count,
    sort_by,
    search_query if search_query else None,
    source_filter if "source_filter" in locals() else None,
    contract_filter if "contract_filter" in locals() else None,
    date_filter_offers,
)

# Affichage des offres
if collected_offers_data.get("total", 0) > 0:
    offers = collected_offers_data["offers"]

    # Afficher le nombre total
    st.caption(
        f"**{collected_offers_data['total']} offres** trouvées (affichage de {len(offers)})"
    )

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
# SECTION 8 : STATISTIQUES DÉTAILLÉES PAR LOCALISATION
# ============================================================================

st.markdown("---")

st.subheader("📍 Statistiques détaillées par localisation")
st.caption("Analyse approfondie avec filtres géographiques et temporels")

# Filtres pour les statistiques détaillées
col_filter1, col_filter2, col_filter3 = st.columns(3)

with col_filter1:
    # Filtre par source
    source_options = {
        "Toutes": None,
        "France Travail": "france_travail",
        "Welcome to the Jungle": "welcome_to_the_jungle",
    }
    source_filter_display = st.selectbox(
        "Source", list(source_options.keys()), key="source_detailed"
    )
    source_filter = source_options[source_filter_display]

    # Filtre par type de contrat
    contract_options = {
        "Tous": None,
        "CDI": "CDI",
        "CDD": "CDD",
        "Stage": "Stage",
        "Alternance": "Alternance",
        "Intérim": "Intérim",
    }
    contract_filter_display = st.selectbox(
        "Type de contrat", list(contract_options.keys()), key="contract_detailed"
    )
    contract_filter = contract_options[contract_filter_display]

with col_filter2:
    location_type_filter = st.selectbox(
        "Type de localisation", ["Ville", "Région"], key="location_type_detailed"
    )
    location_type_api = "city" if location_type_filter == "Ville" else "region"

    # Charger les localisations disponibles
    available_locations = load_available_locations(location_type_api)

    if available_locations:
        location_options = ["Toutes"] + [
            f"{loc['name']} ({loc['count']} offres)" for loc in available_locations
        ]
        selected_location_display = st.selectbox(
            f"Sélectionner une {location_type_filter.lower()}",
            location_options,
            key="selected_location_detailed",
        )

        # Extraire le nom de la localisation
        if selected_location_display == "Toutes":
            selected_location = None
        else:
            selected_location = selected_location_display.split(" (")[0]
    else:
        st.info("Aucune localisation disponible")
        selected_location = None

with col_filter3:
    # Filtre par date
    date_filter_options = {
        "Tout": None,
        "7 derniers jours": 7,
        "30 derniers jours": 30,
        "90 derniers jours": 90,
    }
    date_filter_display = st.selectbox(
        "Période", list(date_filter_options.keys()), index=2, key="date_detailed"
    )
    date_filter = date_filter_options[date_filter_display]

    top_n = st.slider(
        "Top N", min_value=5, max_value=20, value=10, step=5, key="top_n_detailed"
    )

st.markdown("---")

# Graphique 1 : Répartition des types de contrat
st.markdown(f"#### 📄 Types de contrat par {location_type_filter.lower()}")

contracts_data = load_contracts_by_location(
    location_type_api, selected_location, source_filter, contract_filter, date_filter
)

if contracts_data:
    if selected_location:
        # Une localisation spécifique
        if contracts_data.get("data"):
            df_contracts_loc = pd.DataFrame(contracts_data["data"])

            fig_contracts_loc = px.pie(
                df_contracts_loc,
                values="count",
                names="contract",
                title=f"Répartition des contrats - {selected_location}",
                color_discrete_sequence=px.colors.qualitative.Set2,
                hole=0.4,
            )
            fig_contracts_loc.update_traces(
                textposition="inside", textinfo="percent+label"
            )
            st.plotly_chart(fig_contracts_loc, use_container_width=True)
        else:
            st.info(f"Aucune donnée disponible pour {selected_location}")
    else:
        # Toutes les localisations (groupées)
        if contracts_data.get("data"):
            # Prendre les top N localisations
            location_totals = {
                loc: sum(item["count"] for item in items)
                for loc, items in contracts_data["data"].items()
            }
            top_locations = sorted(
                location_totals.items(), key=lambda x: x[1], reverse=True
            )[:top_n]
            top_location_names = [loc[0] for loc in top_locations]

            # Préparer les données pour un graphique empilé
            all_contracts = set()
            for loc_name in top_location_names:
                for item in contracts_data["data"][loc_name]:
                    all_contracts.add(item["contract"])

            # Créer un DataFrame
            data_for_chart = []
            for loc_name in top_location_names:
                loc_data = {
                    item["contract"]: item["count"]
                    for item in contracts_data["data"][loc_name]
                }
                for contract in all_contracts:
                    data_for_chart.append(
                        {
                            "location": loc_name,
                            "contract": contract,
                            "count": loc_data.get(contract, 0),
                        }
                    )

            df_contracts_all = pd.DataFrame(data_for_chart)

            fig_contracts_all = px.bar(
                df_contracts_all,
                x="location",
                y="count",
                color="contract",
                title=f"Top {top_n} {location_type_filter.lower()}s - Types de contrat",
                barmode="stack",
                color_discrete_sequence=px.colors.qualitative.Bold,
            )
            fig_contracts_all.update_layout(
                xaxis_title="", yaxis_title="Nombre d'offres", height=450
            )
            st.plotly_chart(fig_contracts_all, use_container_width=True)
        else:
            st.info("Aucune donnée disponible")
else:
    st.info("Aucune donnée disponible")

st.markdown("---")

# Graphique 2 : Métiers les plus recherchés
st.markdown(f"#### 💼 Métiers les plus recherchés par {location_type_filter.lower()}")

profiles_data = load_profiles_by_location(
    location_type_api,
    selected_location,
    top_n,
    source_filter,
    contract_filter,
    date_filter,
)

if profiles_data:
    if selected_location:
        # Une localisation spécifique
        if profiles_data.get("data"):
            df_profiles_loc = pd.DataFrame(profiles_data["data"])

            fig_profiles_loc = px.bar(
                df_profiles_loc,
                x="count",
                y="profile",
                orientation="h",
                title=f"Top métiers - {selected_location}",
                color="count",
                color_continuous_scale="Viridis",
            )
            fig_profiles_loc.update_layout(
                xaxis_title="Nombre d'offres",
                yaxis_title="",
                height=max(400, len(df_profiles_loc) * 30),
                showlegend=False,
            )
            st.plotly_chart(fig_profiles_loc, use_container_width=True)
        else:
            st.info(f"Aucune donnée disponible pour {selected_location}")
    else:
        # Toutes les localisations (top métiers par localisation)
        if profiles_data.get("data"):
            # Prendre top N localisations par nombre d'offres
            location_totals = {
                loc: sum(item["count"] for item in items)
                for loc, items in profiles_data["data"].items()
            }
            top_locations = sorted(
                location_totals.items(), key=lambda x: x[1], reverse=True
            )[:top_n]

            # Afficher en grille
            num_cols = 2
            locations_per_col = (len(top_locations) + num_cols - 1) // num_cols

            for i in range(0, len(top_locations), num_cols):
                cols = st.columns(num_cols)
                for j, col in enumerate(cols):
                    if i + j < len(top_locations):
                        loc_name = top_locations[i + j][0]
                        loc_data = profiles_data["data"][loc_name][:5]  # Top 5 métiers

                        with col:
                            st.markdown(f"**{loc_name}**")
                            df_loc = pd.DataFrame(loc_data)

                            fig_loc = px.bar(
                                df_loc,
                                x="count",
                                y="profile",
                                orientation="h",
                                color_discrete_sequence=["#667eea"],
                            )
                            fig_loc.update_layout(
                                height=250,
                                showlegend=False,
                                margin=dict(l=0, r=0, t=0, b=0),
                                xaxis_title="",
                                yaxis_title="",
                            )
                            st.plotly_chart(
                                fig_loc,
                                use_container_width=True,
                                key=f"profile_chart_{loc_name}_{i}_{j}",
                            )
        else:
            st.info("Aucune donnée disponible")
else:
    st.info("Aucune donnée disponible")

st.markdown("---")

# Graphique 3 : Salaires par localisation
st.markdown(f"#### 💰 Salaires moyens par {location_type_filter.lower()}")

salaries_data = load_salaries_by_location(
    location_type_api, selected_location, source_filter, contract_filter, date_filter
)

if salaries_data:
    if selected_location:
        # Une localisation spécifique
        if salaries_data.get("offers_count", 0) > 0:
            col_sal1, col_sal2, col_sal3 = st.columns(3)

            with col_sal1:
                st.metric(
                    label="Salaire moyen",
                    value=f"{salaries_data.get('avg_salary', 0):.0f}K €",
                )

            with col_sal2:
                st.metric(
                    label="Fourchette",
                    value=f"{salaries_data.get('avg_min', 0):.0f}K - {salaries_data.get('avg_max', 0):.0f}K €",
                )

            with col_sal3:
                st.metric(
                    label="Offres avec salaire",
                    value=salaries_data.get("offers_count", 0),
                )

            # Mini graphique de la fourchette
            fig_range = go.Figure()

            fig_range.add_trace(
                go.Bar(
                    x=[salaries_data.get("avg_min", 0)],
                    y=["Minimum"],
                    orientation="h",
                    name="Min",
                    marker_color="lightblue",
                )
            )

            fig_range.add_trace(
                go.Bar(
                    x=[
                        salaries_data.get("avg_max", 0)
                        - salaries_data.get("avg_min", 0)
                    ],
                    y=["Minimum"],
                    orientation="h",
                    name="Max",
                    marker_color="darkblue",
                    base=[salaries_data.get("avg_min", 0)],
                )
            )

            fig_range.update_layout(
                barmode="stack",
                height=150,
                showlegend=False,
                xaxis_title="Salaire (K€)",
                yaxis_title="",
                margin=dict(l=0, r=0, t=20, b=0),
            )

            st.plotly_chart(fig_range, use_container_width=True)
        else:
            st.info(f"Aucune donnée de salaire pour {selected_location}")
    else:
        # Toutes les localisations
        if salaries_data.get("data"):
            df_salaries_all = pd.DataFrame(salaries_data["data"][:top_n])

            fig_salaries_all = px.bar(
                df_salaries_all,
                x="avg_salary",
                y="location",
                orientation="h",
                title=f"Top {top_n} {location_type_filter.lower()}s - Salaires moyens (K€/an)",
                color="avg_salary",
                color_continuous_scale="Greens",
                hover_data={"offers_count": True},
            )
            fig_salaries_all.update_layout(
                xaxis_title="Salaire moyen (K€)",
                yaxis_title="",
                height=max(400, len(df_salaries_all) * 40),
            )
            st.plotly_chart(fig_salaries_all, use_container_width=True)

            # Tableau récapitulatif
            with st.expander("📊 Voir le tableau détaillé"):
                st.dataframe(
                    df_salaries_all.rename(
                        columns={
                            "location": "Localisation",
                            "avg_salary": "Salaire moyen (K€)",
                            "offers_count": "Nombre d'offres",
                        }
                    ),
                    use_container_width=True,
                    hide_index=True,
                )
        else:
            st.info("Aucune donnée disponible")
else:
    st.info("Aucune donnée disponible")

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
