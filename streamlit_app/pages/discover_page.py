"""
Page de découverte des offres d'emploi
========================================
Affiche toutes les offres avec pagination (50 offres par page)
"""

import streamlit as st
import requests
import os
from datetime import datetime
from dotenv import load_dotenv

# Charger les variables d'environnement
load_dotenv()

# Configuration
API_URL = os.getenv("API_URL", "http://localhost:8000")

# Configuration de la page
st.set_page_config(
    page_title="ATLAS - Découvrir les offres",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded",
)

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
    .offer-card {
        background: white;
        padding: 1.5rem;
        border-radius: 10px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        margin-bottom: 1.5rem;
        border-left: 4px solid #667eea;
    }
    .skill-badge {
        display: inline-block;
        padding: 0.3rem 0.8rem;
        margin: 0.2rem;
        background: #e0e7ff;
        color: #4f46e5;
        border-radius: 15px;
        font-size: 0.85rem;
    }
</style>
""",
    unsafe_allow_html=True,
)

# Titre principal
st.markdown(
    '<h1 class="main-header">🔍 Découvrir les offres</h1>', unsafe_allow_html=True
)
st.markdown("**Parcourez toutes les offres d'emploi collectées**")
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
        default=[],
    )
    source_filter = [source_options[s] for s in source_filter_display]

    # Filtre par type de contrat
    contract_filter = st.multiselect(
        "Type de contrat", ["CDI", "CDD", "Intérim", "Stage", "Alternance"], default=[]
    )

    # Filtre par profil (catégorie NLP)
    profile_filter = st.multiselect(
        "Profil technique",
        [
            "Développeur Backend",
            "Développeur Frontend",
            "Développeur Full Stack",
            "Data Scientist",
            "Data Engineer",
            "DevOps",
            "Mobile",
            "Business Intelligence",
            "Cybersécurité",
            "Cloud",
            "Généraliste",
        ],
        default=[],
    )

    # Filtre télétravail
    remote_filter = st.checkbox("Télétravail possible uniquement")

    st.markdown("---")

    # Bouton reset
    if st.button("🔄 Réinitialiser les filtres", use_container_width=True):
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
# PAGINATION
# ============================================================================

# Initialiser la page courante dans session_state
if "current_page" not in st.session_state:
    st.session_state.current_page = 1

OFFERS_PER_PAGE = 50

# ============================================================================
# CHARGEMENT DES DONNÉES
# ============================================================================


@st.cache_data(ttl=300)
def load_offers_paginated(
    page=1, limit=50, source=None, contract=None, profile=None, remote=None
):
    """Charge les offres avec pagination et filtres"""
    try:
        offset = (page - 1) * limit
        params = {"limit": limit, "offset": offset}

        # Ajouter les filtres si spécifiés
        if source:
            params["source"] = ",".join(source)
        if contract:
            params["contract"] = ",".join(contract)
        if profile:
            params["profile"] = ",".join(profile)
        if remote:
            params["remote"] = "true"

        response = requests.get(f"{API_URL}/api/offers", params=params, timeout=10)
        return response.json()
    except Exception as e:
        st.error(f"Erreur lors du chargement des offres: {str(e)}")
        return {"offers": [], "count": 0, "total": 0}


@st.cache_data(ttl=300)
def count_total_offers(source=None, contract=None, profile=None, remote=None):
    """Compte le nombre total d'offres avec filtres"""
    try:
        params = {}
        if source:
            params["source"] = ",".join(source)
        if contract:
            params["contract"] = ",".join(contract)
        if profile:
            params["profile"] = ",".join(profile)
        if remote:
            params["remote"] = "true"

        response = requests.get(f"{API_URL}/api/offers/count", params=params, timeout=5)
        return response.json().get("total", 0)
    except:
        return 0


# Préparer les filtres (source_filter contient déjà les valeurs de la BDD)
sources = source_filter if source_filter else None
contracts = contract_filter if contract_filter else None
profiles = profile_filter if profile_filter else None
remote = remote_filter if remote_filter else None

# Charger le nombre total d'offres avec filtres
total_offers = count_total_offers(sources, contracts, profiles, remote)
total_pages = max(1, (total_offers + OFFERS_PER_PAGE - 1) // OFFERS_PER_PAGE)

# S'assurer que la page courante est valide
if st.session_state.current_page > total_pages:
    st.session_state.current_page = total_pages
if st.session_state.current_page < 1:
    st.session_state.current_page = 1

# Charger les offres de la page courante
offers_data = load_offers_paginated(
    page=st.session_state.current_page,
    limit=OFFERS_PER_PAGE,
    source=sources,
    contract=contracts,
    profile=profiles,
    remote=remote,
)

offers = offers_data.get("offers", [])

# ============================================================================
# AFFICHAGE DES STATISTIQUES
# ============================================================================

st.subheader(f"📊 {total_offers:,} offres trouvées")

col1, col2, col3 = st.columns(3)

with col1:
    st.metric("📄 Page actuelle", f"{st.session_state.current_page} / {total_pages}")

with col2:
    start_idx = (st.session_state.current_page - 1) * OFFERS_PER_PAGE + 1
    end_idx = min(st.session_state.current_page * OFFERS_PER_PAGE, total_offers)
    st.metric("🔢 Offres affichées", f"{start_idx} - {end_idx}")

with col3:
    st.metric("📦 Total", f"{total_offers:,}")

st.markdown("---")

# ============================================================================
# AFFICHAGE DES OFFRES
# ============================================================================

if not offers:
    st.warning("😕 Aucune offre trouvée avec ces filtres")
else:
    for offer in offers:
        # Extraire les données
        offer_id = offer.get("offer_id")
        title = offer.get("title", "Sans titre")
        company = offer.get("company_name", "Entreprise non spécifiée")
        location = offer.get("location", "")
        contract_type = offer.get("contract_type", "")
        source = offer.get("source", "")
        published_date = offer.get("published_date", "")
        description = offer.get("description", "")

        # Données NLP
        profile_category = offer.get("profile_category", "")
        profile_confidence = offer.get("profile_confidence", 0)
        skills_extracted = offer.get("skills_extracted", [])
        remote_possible = offer.get("remote_possible", False)
        education_level = offer.get("education_level")

        # Créer la carte avec Streamlit natif
        st.markdown(
            f'<div class="offer-card">'
            f'<h3 style="color: #667eea; margin: 0;">📋 {title}</h3>'
            f'<p style="font-size: 1.1rem; color: #555; margin: 0.5rem 0;">🏢 {company}</p>'
            f'<p style="color: #888; font-size: 0.9rem;">'
            f'📍 <strong>{location if location else "Localisation non spécifiée"}</strong> • '
            f"📝 <strong>{contract_type}</strong> • "
            f'📅 <strong>{published_date if published_date else "Date inconnue"}</strong> • '
            f"🔗 <strong>{source}</strong>"
            f"</p>"
            f'<p style="color: #999; font-size: 0.85rem; margin-top: 0.5rem;">'
            f"🔢 ID: <strong>{offer_id}</strong>"
            f"</p>"
            f"</div>",
            unsafe_allow_html=True,
        )

        # Utiliser expander natif Streamlit pour les détails
        with st.expander("🔍 Voir les détails"):
            # Analyse NLP et Compétences côte à côte
            col_left, col_right = st.columns([1, 1])

            with col_left:
                st.markdown("**🎯 Analyse NLP**")

                if profile_category:
                    st.markdown(f"**Profil:** {profile_category}")
                    st.markdown(f"**Confiance:** {profile_confidence}%")

                if education_level:
                    st.markdown(f"**Formation:** Bac+{education_level}")

                if remote_possible:
                    st.markdown("**Télétravail:** ✅ Possible")
                else:
                    st.markdown("**Télétravail:** ❌ Non mentionné")

            with col_right:
                st.markdown("**🛠️ Compétences détectées**")
                if skills_extracted and len(skills_extracted) > 0:
                    skills_html = "".join(
                        [
                            f'<span class="skill-badge">{skill}</span>'
                            for skill in skills_extracted
                        ]
                    )
                    st.markdown(skills_html, unsafe_allow_html=True)
                else:
                    st.markdown("_Aucune compétence détectée_")

            st.markdown("---")

            # Description complète en dernier
            st.markdown("**📄 Description complète**")
            st.markdown(description)

# ============================================================================
# PAGINATION
# ============================================================================

st.markdown("---")

col_prev, col_info, col_next = st.columns([1, 2, 1])

with col_prev:
    if st.button(
        "⬅️ Précédent",
        use_container_width=True,
        disabled=(st.session_state.current_page <= 1),
    ):
        st.session_state.current_page -= 1
        st.rerun()

with col_info:
    st.markdown(
        f"<div style='text-align: center; padding: 0.5rem;'>Page {st.session_state.current_page} sur {total_pages}</div>",
        unsafe_allow_html=True,
    )

with col_next:
    if st.button(
        "Suivant ➡️",
        use_container_width=True,
        disabled=(st.session_state.current_page >= total_pages),
    ):
        st.session_state.current_page += 1
        st.rerun()

# Navigation rapide
st.markdown("---")
st.markdown("**📍 Navigation rapide**")
col_nav1, col_nav2, col_nav3 = st.columns(3)

with col_nav1:
    if st.button("⏮️ Première page", use_container_width=True):
        st.session_state.current_page = 1
        st.rerun()

with col_nav2:
    page_input = st.number_input(
        "Aller à la page:",
        min_value=1,
        max_value=total_pages,
        value=st.session_state.current_page,
        key="page_jump",
    )
    if st.button("Aller", use_container_width=True):
        st.session_state.current_page = page_input
        st.rerun()

with col_nav3:
    if st.button("Dernière page ⏭️", use_container_width=True):
        st.session_state.current_page = total_pages
        st.rerun()

# ============================================================================
# FOOTER
# ============================================================================

st.markdown("---")
st.caption(f"🔄 Dernière mise à jour: {datetime.now().strftime('%d/%m/%Y %H:%M')}")
