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
import folium
from folium.plugins import MarkerCluster
from streamlit_folium import st_folium

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
    /* Ajouter un padding en bas du contenu */
    .main .block-container {
        padding-bottom: 50px !important;
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

# Initialiser le compteur de reset si nécessaire
if "reset_counter" not in st.session_state:
    st.session_state.reset_counter = 0

# Initialiser la page courante dans session_state
if "current_page" not in st.session_state:
    st.session_state.current_page = 1

with st.sidebar:
    # Input pour aller à une page spécifique
    st.subheader("📄 Navigation rapide")
    page_jump = st.number_input(
        "Aller à la page",
        min_value=1,
        value=st.session_state.current_page,
        step=1,
        key=f"page_jump_{st.session_state.reset_counter}",
    )

    st.markdown("---")

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
        key=f"filter_source_{st.session_state.reset_counter}",
    )
    source_filter = [source_options[s] for s in source_filter_display]

    # Filtre par type de contrat
    contract_filter = st.multiselect(
        "Type de contrat",
        ["CDI", "CDD", "Intérim", "Stage", "Alternance"],
        default=[],
        key=f"filter_contract_{st.session_state.reset_counter}",
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
        key=f"filter_profile_{st.session_state.reset_counter}",
    )

    # Filtre télétravail
    remote_filter = st.checkbox(
        "Télétravail possible uniquement",
        key=f"filter_remote_{st.session_state.reset_counter}",
    )

    # Filtre par compétences
    skills_input = st.text_input(
        "🛠️ Compétences (séparées par des virgules)",
        placeholder="Ex: Python, SQL, Docker",
        key=f"filter_skills_{st.session_state.reset_counter}",
    )
    skills_filter = (
        [s.strip() for s in skills_input.split(",") if s.strip()]
        if skills_input
        else []
    )

    # Filtre par formation
    education_filter = st.multiselect(
        "🎓 Niveau de formation",
        [
            ("Bac+2", 2),
            ("Bac+3", 3),
            ("Bac+4", 4),
            ("Bac+5", 5),
            ("Bac+6", 6),
            ("Bac+8", 8),
        ],
        default=[],
        format_func=lambda x: x[0],
        key=f"filter_education_{st.session_state.reset_counter}",
    )
    education_levels = [e[1] for e in education_filter] if education_filter else []

    # Filtre par ville
    @st.cache_data(ttl=600)
    def load_cities_list():
        """Charge la liste des villes disponibles"""
        try:
            response = requests.get(f"{API_URL}/api/cities/list", timeout=5)
            if response.status_code == 200:
                return response.json().get("cities", [])
            return []
        except:
            return []

    cities_list = load_cities_list()
    cities_filter = st.multiselect(
        "🏙️ Ville(s)",
        cities_list,
        default=[],
        key=f"filter_cities_{st.session_state.reset_counter}",
    )

    # Filtre par code postal
    postal_code_input = st.text_input(
        "📮 Code postal",
        placeholder="Ex: 75001, 69002",
        key=f"filter_postal_{st.session_state.reset_counter}",
    )
    postal_codes_filter = (
        [p.strip() for p in postal_code_input.split(",") if p.strip()]
        if postal_code_input
        else []
    )

    # Filtre par années d'expérience
    experience_filter = st.slider(
        "💼 Années d'expérience minimum",
        min_value=0,
        max_value=15,
        value=0,
        step=1,
        key=f"filter_experience_{st.session_state.reset_counter}",
    )

    # Filtre par date de publication
    date_filter = st.date_input(
        "📅 Offres publiées depuis le",
        value=None,
        key=f"filter_date_{st.session_state.reset_counter}",
    )

    # Filtre par salaire minimum
    salary_filter = st.number_input(
        "💰 Salaire minimum (K€/an)",
        min_value=0,
        max_value=200,
        value=0,
        step=5,
        key=f"filter_salary_{st.session_state.reset_counter}",
    )

    st.markdown("---")

    # Toggle pour afficher la carte
    show_map = st.checkbox(
        "🗺️ Afficher la carte géographique",
        value=False,
        key=f"show_map_{st.session_state.reset_counter}",
    )

    st.markdown("---")

    # Bouton reset
    if st.button("🔄 Réinitialiser les filtres", use_container_width=True):
        # Incrémenter le compteur pour forcer la recréation des widgets
        st.session_state.reset_counter += 1
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
    page=1,
    limit=50,
    source=None,
    contract=None,
    profile=None,
    remote=None,
    skills=None,
    education=None,
    cities=None,
    postal_codes=None,
    experience=None,
    date_from=None,
    min_salary=None,
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
        if skills:
            params["skills"] = ",".join(skills)
        if education:
            params["education"] = ",".join([str(e) for e in education])
        if cities:
            params["cities"] = ",".join(cities)
        if postal_codes:
            params["postal_codes"] = ",".join(postal_codes)
        if experience and experience > 0:
            params["experience"] = str(experience)
        if date_from:
            params["date_from"] = date_from.isoformat()
        if min_salary and min_salary > 0:
            params["min_salary"] = str(min_salary)

        response = requests.get(f"{API_URL}/api/offers", params=params, timeout=10)
        return response.json()
    except Exception as e:
        st.error(f"Erreur lors du chargement des offres: {str(e)}")
        return {"offers": [], "count": 0, "total": 0}


@st.cache_data(ttl=300)
def count_total_offers(
    source=None,
    contract=None,
    profile=None,
    remote=None,
    skills=None,
    education=None,
    cities=None,
    postal_codes=None,
    experience=None,
    date_from=None,
    min_salary=None,
):
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
        if skills:
            params["skills"] = ",".join(skills)
        if education:
            params["education"] = ",".join([str(e) for e in education])
        if cities:
            params["cities"] = ",".join(cities)
        if postal_codes:
            params["postal_codes"] = ",".join(postal_codes)
        if experience and experience > 0:
            params["experience"] = str(experience)
        if date_from:
            params["date_from"] = date_from.isoformat()
        if min_salary and min_salary > 0:
            params["min_salary"] = str(min_salary)

        response = requests.get(f"{API_URL}/api/offers/count", params=params, timeout=5)
        return response.json().get("total", 0)
    except:
        return 0


@st.cache_data(ttl=300)
def load_map_data(
    source=None,
    contract=None,
    profile=None,
    remote=None,
    skills=None,
    education=None,
    cities=None,
    postal_codes=None,
    experience=None,
    date_from=None,
    min_salary=None,
):
    """Charge les données géographiques pour la carte"""
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
        if skills:
            params["skills"] = ",".join(skills)
        if education:
            params["education"] = ",".join([str(e) for e in education])
        if cities:
            params["cities"] = ",".join(cities)
        if postal_codes:
            params["postal_codes"] = ",".join(postal_codes)
        if experience and experience > 0:
            params["experience"] = str(experience)
        if date_from:
            params["date_from"] = date_from.isoformat()
        if min_salary and min_salary > 0:
            params["min_salary"] = str(min_salary)

        response = requests.get(f"{API_URL}/api/map-data", params=params, timeout=10)
        return response.json()
    except Exception as e:
        st.error(f"Erreur lors du chargement de la carte: {str(e)}")
        return {"cities": [], "total": 0}


@st.cache_data(ttl=600)
def get_glassdoor_score(company_name: str):
    """Récupère le score Glassdoor d'une entreprise"""
    try:
        response = requests.post(
            f"{API_URL}/api/glassdoor/search",
            json={"company_name": company_name},
            timeout=30,
        )
        if response.status_code == 200:
            return response.json()
        return None
    except Exception as e:
        return {"success": False, "error": str(e)}


# Préparer les filtres (source_filter contient déjà les valeurs de la BDD)
sources = source_filter if source_filter else None
contracts = contract_filter if contract_filter else None
profiles = profile_filter if profile_filter else None
remote = remote_filter if remote_filter else None
skills = skills_filter if skills_filter else None
education = education_levels if education_levels else None
cities = cities_filter if cities_filter else None
postal_codes = postal_codes_filter if postal_codes_filter else None
experience = experience_filter if experience_filter > 0 else None
date_from = date_filter if date_filter else None
min_salary = salary_filter if salary_filter > 0 else None

# Charger le nombre total d'offres avec filtres
total_offers = count_total_offers(
    sources,
    contracts,
    profiles,
    remote,
    skills,
    education,
    cities,
    postal_codes,
    experience,
    date_from,
    min_salary,
)
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
    skills=skills,
    education=education,
    cities=cities,
    postal_codes=postal_codes,
    experience=experience,
    date_from=date_from,
    min_salary=min_salary,
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
# CARTE GÉOGRAPHIQUE (si activée)
# ============================================================================

if show_map:
    st.subheader("🗺️ Carte géographique des offres")

    with st.spinner("Chargement de la carte..."):
        # Charger les données géographiques avec les mêmes filtres
        map_data = load_map_data(
            sources,
            contracts,
            profiles,
            remote,
            skills,
            education,
            cities,
            postal_codes,
            experience,
            date_from,
            min_salary,
        )
        cities_map = map_data.get("cities", [])

        if cities_map:
            # Créer la carte centrée sur la France
            m = folium.Map(
                location=[46.603354, 1.888334],  # Centre de la France
                zoom_start=6,
                tiles="OpenStreetMap",
            )

            # Créer le cluster de marqueurs
            marker_cluster = MarkerCluster(
                name="Offres d'emploi",
                overlay=True,
                control=True,
                icon_create_function="""
                    function(cluster) {
                        var childCount = cluster.getChildCount();
                        var c = ' marker-cluster-';
                        if (childCount < 10) {
                            c += 'small';
                        } else if (childCount < 50) {
                            c += 'medium';
                        } else {
                            c += 'large';
                        }
                        return new L.DivIcon({ 
                            html: '<div><span>' + childCount + '</span></div>', 
                            className: 'marker-cluster' + c, 
                            iconSize: new L.Point(40, 40) 
                        });
                    }
                """,
            )

            # Ajouter les marqueurs pour chaque ville
            for city_data in cities_map:
                # Créer le popup avec les informations
                popup_html = f"""
                    <div style="font-family: Arial; min-width: 200px;">
                        <h4 style="margin: 0 0 10px 0; color: #667eea;">{city_data['city']}</h4>
                        <p style="margin: 5px 0;"><strong>Région:</strong> {city_data['region']}</p>
                        <p style="margin: 5px 0;"><strong>Offres:</strong> {city_data['count']}</p>
                        <p style="margin: 5px 0;"><strong>Profils:</strong><br>{", ".join(city_data['profiles'][:5]) if city_data['profiles'] else "N/A"}</p>
                        <p style="margin: 5px 0;"><strong>Contrats:</strong><br>{", ".join(city_data['contracts']) if city_data['contracts'] else "N/A"}</p>
                    </div>
                """

                # Couleur du marqueur en fonction du nombre d'offres
                if city_data["count"] < 5:
                    color = "lightblue"
                elif city_data["count"] < 20:
                    color = "blue"
                else:
                    color = "darkblue"

                folium.CircleMarker(
                    location=[city_data["lat"], city_data["lon"]],
                    radius=8,
                    popup=folium.Popup(popup_html, max_width=300),
                    tooltip=f"{city_data['city']}: {city_data['count']} offres",
                    color=color,
                    fill=True,
                    fillColor=color,
                    fillOpacity=0.7,
                ).add_to(marker_cluster)

            # Ajouter le cluster à la carte
            marker_cluster.add_to(m)

            # Afficher la carte
            st_folium(m, width=None, height=500)

            st.caption(f"📍 {len(cities_map)} villes avec des offres d'emploi")
        else:
            st.info("Aucune donnée géographique disponible pour ces filtres")

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
        remote_days = offer.get("remote_days")
        remote_percentage = offer.get("remote_percentage")
        education_level = offer.get("education_level")
        education_type = offer.get("education_type")
        experience_years = offer.get("experience_years")
        salary_min = offer.get("salary_min")
        salary_max = offer.get("salary_max")

        # Construire les badges d'informations
        info_badges = []

        # Salaire
        if salary_min and salary_max:
            info_badges.append(f"💰 {int(salary_min)}-{int(salary_max)}K€")
        elif salary_min:
            info_badges.append(f"💰 À partir de {int(salary_min)}K€")

        # Expérience
        if experience_years:
            exp_text = (
                f"{experience_years} an"
                if experience_years == 1
                else f"{experience_years} ans"
            )
            info_badges.append(f"💼 {exp_text} d'exp.")

        # Formation
        if education_level:
            info_badges.append(f"🎓 Bac+{education_level}")

        # Télétravail
        if remote_possible:
            if remote_percentage:
                info_badges.append(f"🏠 Télétravail {remote_percentage}%")
            elif remote_days:
                info_badges.append(f"🏠 Télétravail {remote_days}j/sem")
            else:
                info_badges.append("🏠 Télétravail possible")

        # Créer la carte avec Streamlit natif
        info_line = " • ".join(info_badges) if info_badges else ""

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
            + (
                f'<p style="color: #4a5568; font-size: 0.95rem; margin-top: 0.5rem; font-weight: 500;">{info_line}</p>'
                if info_line
                else ""
            )
            + f'<p style="color: #999; font-size: 0.85rem; margin-top: 0.5rem;">'
            f"🔢 ID: <strong>{offer_id}</strong>"
            f"</p>"
            f"</div>",
            unsafe_allow_html=True,
        )

        # Utiliser expander natif Streamlit pour les détails
        with st.expander("🔍 Voir les détails"):
            # Informations détaillées en haut
            st.markdown("### 📊 Informations détaillées")

            detail_cols = st.columns(3)

            with detail_cols[0]:
                st.markdown("**💰 Rémunération**")
                if salary_min and salary_max:
                    st.markdown(
                        f"• **Fourchette:** {int(salary_min)}-{int(salary_max)}K€/an"
                    )
                elif salary_min:
                    st.markdown(f"• **Minimum:** {int(salary_min)}K€/an")
                elif salary_max:
                    st.markdown(f"• **Maximum:** {int(salary_max)}K€/an")
                else:
                    st.markdown("• _Non renseigné_")

            with detail_cols[1]:
                st.markdown("**💼 Expérience & Formation**")
                if experience_years:
                    exp_text = (
                        f"{experience_years} an"
                        if experience_years == 1
                        else f"{experience_years} ans"
                    )
                    st.markdown(f"• **Expérience:** {exp_text}")
                else:
                    st.markdown("• **Expérience:** _Non renseigné_")

                if education_level:
                    edu_text = f"Bac+{education_level}"
                    if education_type:
                        edu_text += f" ({education_type})"
                    st.markdown(f"• **Formation:** {edu_text}")
                else:
                    st.markdown("• **Formation:** _Non renseigné_")

            with detail_cols[2]:
                st.markdown("**🏠 Télétravail**")
                if remote_possible:
                    if remote_percentage:
                        st.markdown(f"• **Taux:** {remote_percentage}%")
                    if remote_days:
                        st.markdown(f"• **Jours/sem:** {remote_days}")
                    if not remote_percentage and not remote_days:
                        st.markdown("• ✅ **Possible**")
                else:
                    st.markdown("• ❌ **Non mentionné**")

            st.markdown("---")

            # Analyse NLP et Compétences côte à côte
            col_left, col_right = st.columns([1, 1])

            with col_left:
                st.markdown("**🎯 Analyse NLP**")

                if profile_category:
                    st.markdown(f"• **Profil:** {profile_category}")
                    st.markdown(f"• **Confiance:** {profile_confidence}%")
                else:
                    st.markdown("_Aucun profil détecté_")

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

            st.markdown("---")

            # Bouton Glassdoor
            col_glassdoor, col_empty = st.columns([1, 3])

            with col_glassdoor:
                if st.button(
                    f"⭐ Score Glassdoor",
                    key=f"glassdoor_{offer_id}",
                    use_container_width=True,
                ):
                    with st.spinner("Recherche sur Glassdoor..."):
                        glassdoor_data = get_glassdoor_score(company)

                        if glassdoor_data and glassdoor_data.get("success"):
                            rating = glassdoor_data.get("rating")
                            reviews_count = glassdoor_data.get("reviews_count")
                            company_url = glassdoor_data.get("company_url")

                            st.success(f"✅ **{glassdoor_data.get('company_name')}**")

                            # Afficher le rating avec des étoiles
                            if rating:
                                stars = "⭐" * int(rating)
                                st.markdown(f"### {stars} **{rating}/5**")
                            else:
                                st.markdown("**Note:** Non disponible")

                            if reviews_count:
                                st.markdown(f"📝 **{reviews_count:,}** avis")

                            if company_url:
                                st.markdown(f"🔗 [Voir sur Glassdoor]({company_url})")
                        else:
                            error_msg = (
                                glassdoor_data.get("error")
                                if glassdoor_data
                                else "Entreprise non trouvée"
                            )
                            st.warning(f"⚠️ {error_msg}")

# ============================================================================
# NAVIGATION FLOTTANTE
# ============================================================================

# Navigation flottante en bas de page
with st.container():
    # Vérifier si l'utilisateur a changé la page via l'input de la sidebar
    if page_jump != st.session_state.current_page:
        st.session_state.current_page = min(max(1, page_jump), total_pages)
        st.rerun()

    col1, col2, col3, col4, col5 = st.columns([0.8, 0.8, 2, 0.8, 0.8])

    with col1:
        if st.button(
            "⏪",
            key="first",
            disabled=(st.session_state.current_page <= 1),
            help="Première page",
        ):
            st.session_state.current_page = 1
            st.rerun()

    with col2:
        if st.button(
            "➖",
            key="prev",
            disabled=(st.session_state.current_page <= 1),
            help="Page précédente",
        ):
            st.session_state.current_page = max(1, st.session_state.current_page - 1)
            st.rerun()

    with col3:
        page_input = st.number_input(
            "Page",
            min_value=1,
            max_value=total_pages,
            value=st.session_state.current_page,
            label_visibility="collapsed",
        )
        if page_input != st.session_state.current_page:
            st.session_state.current_page = page_input
            st.rerun()

    with col4:
        if st.button(
            "➕",
            key="next",
            disabled=(st.session_state.current_page >= total_pages),
            help="Page suivante",
        ):
            st.session_state.current_page = min(
                total_pages, st.session_state.current_page + 1
            )
            st.rerun()

    with col5:
        if st.button(
            "⏩",
            key="last",
            disabled=(st.session_state.current_page >= total_pages),
            help="Dernière page",
        ):
            st.session_state.current_page = total_pages
            st.rerun()

    st.markdown(
        f"<div style='text-align: center; padding: 0.5rem; color: #888;'>Page {st.session_state.current_page} / {total_pages}</div>",
        unsafe_allow_html=True,
    )

# ============================================================================
# FOOTER
# ============================================================================

st.markdown("---")
st.caption(f"🔄 Dernière mise à jour: {datetime.now().strftime('%d/%m/%Y %H:%M')}")
