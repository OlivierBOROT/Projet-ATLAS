import streamlit as st
import requests
import json

st.set_page_config(page_title="Administration - ATLAS", page_icon="⚙️", layout="wide")

st.title("⚙️ Administration - Scraping à la demande")

st.markdown("---")

# ============================================================================
# CONFIGURATION
# ============================================================================

API_BASE_URL = "http://localhost:8000"


# ============================================================================
# FONCTIONS
# ============================================================================


def scrape_offer(source: str, identifier: str, save_to_db: bool = False) -> dict:
    """
    Appeler l'API de scraping

    Args:
        source: "wttj" ou "france_travail"
        identifier: URL pour WTTJ, ID pour France Travail
        save_to_db: Sauvegarder en BDD après scraping

    Returns:
        Réponse JSON de l'API
    """
    try:
        response = requests.post(
            f"{API_BASE_URL}/api/scrape",
            json={"source": source, "identifier": identifier, "save_to_db": save_to_db},
            timeout=300,
        )
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        st.error(f"❌ Erreur lors de l'appel API: {str(e)}")
        return None
    except Exception as e:
        st.error(f"❌ Erreur: {str(e)}")
        return None


def display_raw_data(raw_data: dict):
    """Afficher les données brutes scrapées"""
    st.subheader("📦 Données brutes")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("**Titre**")
        st.write(raw_data.get("title", "N/A"))

        st.markdown("**Entreprise**")
        st.write(raw_data.get("company_name", "N/A"))

        st.markdown("**Type de contrat**")
        st.write(raw_data.get("contract_type", "N/A"))

        st.markdown("**Localisation**")
        location = raw_data.get("location_city", "N/A")
        if raw_data.get("location_code_postal"):
            location += f" ({raw_data.get('location_code_postal')})"
        st.write(location)

    with col2:
        st.markdown("**Date de publication**")
        st.write(raw_data.get("published_date", "N/A"))

        st.markdown("**Source**")
        st.write(raw_data.get("source", "N/A"))

        st.markdown("**URL**")
        st.write(raw_data.get("url", "N/A"))

        if raw_data.get("salary_text"):
            st.markdown("**Salaire**")
            st.write(raw_data.get("salary_text"))

    # Description complète
    st.markdown("**Description**")
    description = raw_data.get("description", "N/A")
    if description and description != "N/A":
        with st.expander(
            f"Voir la description ({len(description)} caractères)", expanded=False
        ):
            st.text_area(
                "Description complète",
                description,
                height=300,
                disabled=True,
                label_visibility="collapsed",
            )
    else:
        st.write("Pas de description disponible")


def display_nlp_results(nlp_results: dict):
    """Afficher les résultats du traitement NLP"""
    st.subheader("🧠 Résultats du traitement NLP")

    if "error" in nlp_results:
        st.error(f"❌ Erreur NLP: {nlp_results['error']}")
        return

    # Résumé final
    if "final" in nlp_results:
        st.markdown("### 📊 Résumé")

        col1, col2, col3 = st.columns(3)

        with col1:
            st.metric(
                "Profil détecté", nlp_results["final"].get("profile_category", "N/A")
            )
            confidence = nlp_results["final"].get("profile_confidence", 0)
            st.caption(
                f"Confiance: {confidence:.1%}" if confidence else "Confiance: N/A"
            )

        with col2:
            st.metric(
                "Compétences extraites", nlp_results["final"].get("skills_count", 0)
            )

        with col3:
            st.metric(
                "Dimensions embedding",
                nlp_results["final"].get("embedding_dimensions", 0),
            )

        # Détails supplémentaires
        st.markdown("---")

        col1, col2, col3 = st.columns(3)

        with col1:
            st.markdown("**Type de contrat**")
            contract_types = nlp_results["final"].get("contract_types", [])
            st.write(", ".join(contract_types) if contract_types else "N/A")

            st.markdown("**Niveau d'études**")
            edu_level = nlp_results["final"].get("education_level")
            st.write(f"Niveau {edu_level}" if edu_level else "N/A")

        with col2:
            st.markdown("**Type de formation**")
            st.write(nlp_results["final"].get("education_type", "N/A"))

        with col3:
            st.markdown("**Télétravail**")
            remote = nlp_results["final"].get("remote_possible", False)
            if remote:
                days = nlp_results["final"].get("remote_days")
                percentage = nlp_results["final"].get("remote_percentage")
                remote_text = "Oui"
                if days:
                    remote_text += f" ({days} jours/semaine)"
                elif percentage:
                    remote_text += f" ({percentage}%)"
                st.write(remote_text)
            else:
                st.write("Non")

    # Top compétences
    if "final" in nlp_results and nlp_results["final"].get("top_skills"):
        st.markdown("### 🎯 Top 10 des compétences")
        skills = nlp_results["final"]["top_skills"]

        # Afficher en colonnes
        cols = st.columns(5)
        for i, skill in enumerate(skills):
            with cols[i % 5]:
                st.markdown(f"• {skill}")

    # Détails des étapes NLP
    if "steps" in nlp_results:
        st.markdown("---")
        st.markdown("### 🔬 Détails du traitement")

        # 1. Texte nettoyé
        if "cleaned_text" in nlp_results["steps"]:
            with st.expander("1️⃣ Texte nettoyé et lemmatisé", expanded=False):
                cleaned = nlp_results["steps"]["cleaned_text"]
                st.text_area(
                    "Texte après nettoyage",
                    cleaned,
                    height=200,
                    disabled=True,
                    label_visibility="collapsed",
                )
                st.caption(f"Longueur: {len(cleaned)} caractères")

        # 2. Extraction d'informations
        if "info_extraction" in nlp_results["steps"]:
            with st.expander("2️⃣ Informations extraites", expanded=False):
                info = nlp_results["steps"]["info_extraction"]
                st.json(info)

        # 3. Compétences complètes
        if "skills_extracted" in nlp_results["steps"]:
            with st.expander("3️⃣ Toutes les compétences extraites", expanded=False):
                skills_dict = nlp_results["steps"]["skills_extracted"]

                # Vérifier si c'est un dictionnaire avec catégories
                if isinstance(skills_dict, dict):
                    # Compter le total
                    total_skills = sum(
                        len(v) for v in skills_dict.values() if isinstance(v, list)
                    )
                    st.write(f"**{total_skills} compétences détectées:**")

                    # Afficher par catégorie
                    for category, skill_list in skills_dict.items():
                        if isinstance(skill_list, list) and skill_list:
                            st.markdown(
                                f"**{category.capitalize()}** ({len(skill_list)}):"
                            )
                            cols = st.columns(4)
                            for i, skill in enumerate(skill_list):
                                with cols[i % 4]:
                                    st.markdown(f"• {skill}")
                            st.markdown("")  # Espace entre catégories
                else:
                    # Format liste simple (fallback)
                    st.write(f"**{len(skills_dict)} compétences détectées:**")
                    if skills_dict:
                        cols = st.columns(4)
                        for i, skill in enumerate(skills_dict):
                            with cols[i % 4]:
                                st.markdown(f"• {skill}")
                    else:
                        st.write("Aucune compétence détectée")

        # 4. Embedding
        if "embedding" in nlp_results["steps"]:
            with st.expander("4️⃣ Embedding vectoriel", expanded=False):
                emb_info = nlp_results["steps"]["embedding"]

                st.markdown(f"**Modèle:** {emb_info.get('model', 'N/A')}")
                st.markdown(f"**Dimensions:** {emb_info.get('shape', 'N/A')}")

                if "vector" in emb_info:
                    st.markdown("**Vecteur (premiers 20 éléments):**")
                    vector = emb_info["vector"]
                    st.code(str(vector[:20]))

                    st.caption(f"Vecteur complet: {len(vector)} dimensions")


# ============================================================================
# INTERFACE
# ============================================================================

st.markdown(
    """
Cette page permet de scraper et analyser une offre d'emploi à la demande.

**Sources disponibles:**
- **Welcome to the Jungle (WTTJ):** Entrez l'URL complète de l'offre
- **France Travail:** Entrez l'ID de l'offre (visible dans l'URL)
"""
)

st.markdown("---")

# Sélection de la source
col1, col2 = st.columns([1, 2])

with col1:
    source = st.selectbox(
        "📌 Source",
        options=["wttj", "france_travail"],
        format_func=lambda x: (
            "Welcome to the Jungle" if x == "wttj" else "France Travail"
        ),
        help="Sélectionnez la source de l'offre à scraper",
    )

with col2:
    if source == "wttj":
        identifier = st.text_input(
            "🔗 URL de l'offre WTTJ",
            placeholder="https://www.welcometothejungle.com/fr/companies/...",
            help="Copiez-collez l'URL complète de l'offre Welcome to the Jungle",
        )
    else:  # france_travail
        identifier = st.text_input(
            "🔢 ID de l'offre France Travail",
            placeholder="Ex: 180MVNK",
            help="Entrez l'ID de l'offre (visible dans l'URL candidat.francetravail.fr/offres/recherche/detail/ID)",
        )

# Option de sauvegarde en BDD
save_to_db = st.checkbox(
    "💾 Sauvegarder l'offre en base de données après traitement",
    value=False,
    help="L'offre sera insérée/mise à jour dans PostgreSQL avec tous les résultats NLP",
)

# Bouton de scraping
if st.button("🚀 Scraper et analyser", type="primary", use_container_width=True):
    if not identifier:
        st.warning("⚠️ Veuillez entrer un identifiant d'offre")
    else:
        with st.spinner("🔄 Scraping et traitement NLP en cours..."):
            result = scrape_offer(source, identifier, save_to_db)

        if result and result.get("success"):
            st.success("✅ Scraping et analyse terminés avec succès!")

            # Confirmation sauvegarde BDD
            if result.get("saved_to_db"):
                st.success("💾 Offre sauvegardée en base de données!")
            elif save_to_db:
                st.warning("⚠️ Sauvegarde en BDD échouée (voir logs API)")

            st.markdown("---")

            # Affichage des données brutes
            if "raw_data" in result:
                display_raw_data(result["raw_data"])

            st.markdown("---")

            # Affichage des résultats NLP
            if "nlp_results" in result:
                display_nlp_results(result["nlp_results"])
        else:
            st.error("❌ Échec du scraping. Vérifiez l'identifiant et réessayez.")
