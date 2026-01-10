"""
Page de comparaison d'offres d'emploi
======================================
Compare deux offres avec analyse NLP complète
"""

import streamlit as st
import sys
from pathlib import Path
import json

# Ajouter le chemin des modules NLP
nlp_modules_path = Path(__file__).parent.parent.parent / "NLP" / "modules"
sys.path.insert(0, str(nlp_modules_path))

try:
    from text_cleaner import TextCleaner
    from skill_extractor import SkillExtractor
    from info_extractor import InfoExtractor
    from embedding_generator import EmbeddingGenerator

    NLP_AVAILABLE = True
except ImportError as e:
    st.error(f"❌ Modules NLP non disponibles: {e}")
    NLP_AVAILABLE = False

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
    .comparison-box {
        background: #f8f9fa;
        padding: 1rem;
        border-radius: 8px;
        border-left: 4px solid #667eea;
        margin-bottom: 1rem;
    }
    .similarity-score {
        font-size: 2.5rem;
        font-weight: bold;
        text-align: center;
        padding: 2rem;
        border-radius: 10px;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
    }
</style>
""",
    unsafe_allow_html=True,
)

st.markdown(
    '<h1 class="main-header">⚖️ Comparaisons d\'offres</h1>', unsafe_allow_html=True
)

# ============================================================================
# SECTION 1: COMPARAISON BDD (à venir)
# ============================================================================

st.header("🗄️ Comparaison depuis la base de données")


# Charger la liste des offres
@st.cache_data(ttl=300)
def load_offers_list():
    """Charge la liste des offres depuis l'API"""
    import requests

    try:
        response = requests.get("http://localhost:8000/api/offers/list")
        if response.status_code == 200:
            return response.json()["offers"]
        return []
    except:
        return []


def load_offer_by_id(offer_id):
    """Charge une offre complète avec son embedding"""
    import requests

    try:
        response = requests.get(f"http://localhost:8000/api/offers/get/{offer_id}")
        if response.status_code == 200:
            return response.json()
        return None
    except:
        return None


offers_list = load_offers_list()

if not offers_list:
    st.warning("⚠️ Impossible de charger les offres. Vérifiez que l'API est lancée.")
else:
    st.info(f"📊 {len(offers_list)} offres disponibles dans la base de données")

    # Deux colonnes pour les selects
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("📄 Offre 1")
        offer1_option = st.selectbox(
            "Sélectionnez la première offre",
            options=offers_list,
            format_func=lambda x: x["display"],
            key="db_offer1",
        )

    with col2:
        st.subheader("📄 Offre 2")
        offer2_option = st.selectbox(
            "Sélectionnez la deuxième offre",
            options=offers_list,
            format_func=lambda x: x["display"],
            key="db_offer2",
        )

    # Bouton de comparaison
    st.markdown("<br>", unsafe_allow_html=True)
    col_btn1, col_btn2, col_btn3 = st.columns([1, 1, 1])
    with col_btn2:
        compare_db_button = st.button(
            "🔍 Comparer les offres (BDD)", type="primary", use_container_width=True
        )

    if compare_db_button:
        if offer1_option["offer_id"] == offer2_option["offer_id"]:
            st.error("❌ Veuillez sélectionner deux offres différentes")
        else:
            with st.spinner("Chargement des offres..."):
                offer1_data = load_offer_by_id(offer1_option["offer_id"])
                offer2_data = load_offer_by_id(offer2_option["offer_id"])

            if not offer1_data or not offer2_data:
                st.error("❌ Erreur lors du chargement des offres")
            elif not offer1_data.get("embedding") or not offer2_data.get("embedding"):
                st.error("❌ Les embeddings ne sont pas disponibles pour ces offres")
            else:
                st.markdown("---")
                st.header("📊 Résultats de la comparaison (BDD)")

                # Récupérer le module embedding
                embedding_gen = st.session_state.nlp_modules[
                    "embedding_gen"
                ]  # Convertir les embeddings (pgvector string format → numpy array)
                import numpy as np
                import json

                def parse_pgvector_embedding(embedding):
                    if isinstance(embedding, str):
                        if embedding.startswith("[") and embedding.endswith("]"):
                            return np.array(json.loads(embedding))
                        return np.array(
                            [float(x) for x in embedding.strip("[]").split(",")]
                        )
                    elif isinstance(embedding, list):
                        return np.array(embedding)
                    else:
                        return embedding

                emb1 = parse_pgvector_embedding(offer1_data["embedding"])
                emb2 = parse_pgvector_embedding(offer2_data["embedding"])

                # Calculer les métriques
                similarity = embedding_gen.cosine_similarity(emb1, emb2)
                euclidean_dist = embedding_gen.euclidean_distance(emb1, emb2)

                # Affichage des offres
                col1, col2 = st.columns(2)

                with col1:
                    st.markdown("**📄 Offre 1**")
                    st.markdown(f"**Titre:** {offer1_data['title']}")
                    st.markdown(f"**Entreprise:** {offer1_data['company_name']}")
                    st.markdown(
                        f"**Profil:** {offer1_data['profile_category'] or 'N/A'}"
                    )
                    st.markdown(f"**Contrat:** {offer1_data['contract_type'] or 'N/A'}")
                    st.markdown(f"**Localisation:** {offer1_data['location']}")
                    if offer1_data["skills_extracted"]:
                        st.markdown(
                            f"**Compétences:** {', '.join(offer1_data['skills_extracted'][:10])}"
                        )
                        if len(offer1_data["skills_extracted"]) > 10:
                            st.caption(
                                f"... et {len(offer1_data['skills_extracted']) - 10} autres"
                            )

                with col2:
                    st.markdown("**📄 Offre 2**")
                    st.markdown(f"**Titre:** {offer2_data['title']}")
                    st.markdown(f"**Entreprise:** {offer2_data['company_name']}")
                    st.markdown(
                        f"**Profil:** {offer2_data['profile_category'] or 'N/A'}"
                    )
                    st.markdown(f"**Contrat:** {offer2_data['contract_type'] or 'N/A'}")
                    st.markdown(f"**Localisation:** {offer2_data['location']}")
                    if offer2_data["skills_extracted"]:
                        st.markdown(
                            f"**Compétences:** {', '.join(offer2_data['skills_extracted'][:10])}"
                        )
                        if len(offer2_data["skills_extracted"]) > 10:
                            st.caption(
                                f"... et {len(offer2_data['skills_extracted']) - 10} autres"
                            )

                # Métriques de similarité
                st.markdown("---")
                st.subheader("🎯 Métriques de similarité")

                col1, col2 = st.columns(2)

                with col1:
                    st.markdown(
                        f'<div class="similarity-score">{similarity:.1%}<br><small>Similarité cosinus</small></div>',
                        unsafe_allow_html=True,
                    )

                with col2:
                    st.markdown(
                        f'<div class="similarity-score">{euclidean_dist:.2f}<br><small>Distance euclidienne</small></div>',
                        unsafe_allow_html=True,
                    )

                # Interprétation
                st.markdown("---")
                st.markdown("**📌 Interprétation:**")

                col1, col2 = st.columns(2)

                with col1:
                    st.markdown("**Similarité cosinus:**")
                    st.caption(
                        "Mesure l'orientation des offres (0% = opposées, 100% = identiques). Compare le contenu global sans tenir compte du volume de texte."
                    )
                    if similarity >= 0.9:
                        st.success(
                            "🟢 **Très similaire** - Les offres sont presque identiques"
                        )
                    elif similarity >= 0.75:
                        st.info("🔵 **Similaire** - Beaucoup de points communs")
                    elif similarity >= 0.5:
                        st.warning(
                            "🟡 **Moyennement similaire** - Quelques différences notables"
                        )
                    else:
                        st.error("🔴 **Peu similaire** - Offres assez différentes")

                with col2:
                    st.markdown("**Distance euclidienne:**")
                    st.caption(
                        "Mesure la distance directe entre les offres. Plus la distance est faible, plus les offres sont proches en termes de densité d'informations."
                    )
                    if euclidean_dist <= 2.0:
                        st.success(
                            "🟢 **Très proche** - Distance très faible entre les vecteurs"
                        )
                    elif euclidean_dist <= 5.0:
                        st.info("🔵 **Proche** - Distance modérée")
                    elif euclidean_dist <= 10.0:
                        st.warning("🟡 **Éloignée** - Distance significative")
                    else:
                        st.error(
                            "🔴 **Très éloignée** - Grande distance entre les vecteurs"
                        )

                # Compétences en commun
                if offer1_data["skills_extracted"] and offer2_data["skills_extracted"]:
                    st.markdown("---")
                    st.subheader("🔗 Compétences en commun")

                    skills_common = set(offer1_data["skills_extracted"]) & set(
                        offer2_data["skills_extracted"]
                    )

                    if skills_common:
                        st.markdown(f"**{len(skills_common)} compétences communes:**")
                        st.markdown(f"*{', '.join(sorted(skills_common))}*")
                    else:
                        st.info("Aucune compétence en commun détectée")

st.markdown("---")

# ============================================================================
# SECTION 2: COMPARAISON MANUELLE
# ============================================================================

st.header("✍️ Comparaison manuelle")

if not NLP_AVAILABLE:
    st.error(
        "Les modules NLP ne sont pas disponibles. Vérifiez l'installation des dépendances."
    )
    st.stop()

# Initialiser les modules NLP
if "nlp_modules" not in st.session_state:
    with st.spinner("Chargement des modules NLP..."):
        try:
            st.session_state.nlp_modules = {
                "cleaner": TextCleaner(),
                "skill_extractor": SkillExtractor(),
                "info_extractor": InfoExtractor(),
                "embedding_gen": EmbeddingGenerator(),
            }
            st.success("✅ Modules NLP chargés")
        except Exception as e:
            st.error(f"Erreur lors du chargement: {e}")
            st.stop()

# Colonnes pour les deux offres
col1, col2 = st.columns(2)

with col1:
    st.subheader("📄 Offre 1")
    offer1 = st.text_area(
        "Description de l'offre 1",
        height=300,
        placeholder="Collez ici la description complète de la première offre d'emploi...",
        key="offer1",
    )

with col2:
    st.subheader("📄 Offre 2")
    offer2 = st.text_area(
        "Description de l'offre 2",
        height=300,
        placeholder="Collez ici la description complète de la deuxième offre d'emploi...",
        key="offer2",
    )

# Bouton de comparaison centré
st.markdown("<br>", unsafe_allow_html=True)
col_btn1, col_btn2, col_btn3 = st.columns([1, 1, 1])
with col_btn2:
    compare_button = st.button(
        "🔍 Comparer les offres", type="primary", use_container_width=True
    )

# ============================================================================
# TRAITEMENT ET COMPARAISON
# ============================================================================

if compare_button:
    if not offer1 or not offer2:
        st.error("❌ Veuillez remplir les deux descriptions d'offres")
    else:
        st.markdown("---")
        st.header("📊 Résultats de la comparaison")

        # Récupérer les modules
        cleaner = st.session_state.nlp_modules["cleaner"]
        skill_extractor = st.session_state.nlp_modules["skill_extractor"]
        info_extractor = st.session_state.nlp_modules["info_extractor"]
        embedding_gen = st.session_state.nlp_modules["embedding_gen"]

        # ========================================================================
        # ÉTAPE 1: NETTOYAGE ET LEMMATISATION
        # ========================================================================

        st.subheader("1️⃣ Nettoyage et lemmatisation")

        with st.spinner("Nettoyage des textes..."):
            # Offre 1
            cleaned1 = cleaner.clean_text(offer1)
            lemmas1 = cleaner.lemmatize(cleaned1)
            text_lemmatized1 = " ".join(lemmas1)

            # Offre 2
            cleaned2 = cleaner.clean_text(offer2)
            lemmas2 = cleaner.lemmatize(cleaned2)
            text_lemmatized2 = " ".join(lemmas2)

        col1, col2 = st.columns(2)

        with col1:
            st.markdown("**Offre 1 - Texte nettoyé (lemmes)**")
            st.text_area(
                "Lemmes offre 1",
                value=text_lemmatized1,
                height=150,
                disabled=True,
                label_visibility="collapsed",
            )
            st.caption(f"✅ {len(lemmas1)} lemmes extraits")

        with col2:
            st.markdown("**Offre 2 - Texte nettoyé (lemmes)**")
            st.text_area(
                "Lemmes offre 2",
                value=text_lemmatized2,
                height=150,
                disabled=True,
                label_visibility="collapsed",
            )
            st.caption(f"✅ {len(lemmas2)} lemmes extraits")

        # ========================================================================
        # ÉTAPE 2: EXTRACTION D'INFORMATIONS
        # ========================================================================

        st.subheader("2️⃣ Extraction d'informations")

        with st.spinner("Extraction des informations structurées..."):
            info1 = info_extractor.extract_all(offer1)
            info2 = info_extractor.extract_all(offer2)

        col1, col2 = st.columns(2)

        with col1:
            st.markdown("**Offre 1 - Informations extraites**")
            with st.container():
                st.markdown(
                    f"**💰 Salaire:** {info1['salary']['min'] or 'N/A'}€ - {info1['salary']['max'] or 'N/A'}€"
                )
                st.markdown(
                    f"**📅 Expérience:** {info1['experience']['min'] or 'N/A'}-{info1['experience']['max'] or 'N/A'} ans ({info1['experience']['level'] or 'N/A'})"
                )
                st.markdown(
                    f"**🎓 Formation:** Bac+{info1['education']['level'] or 'N/A'} ({info1['education']['degree_type'] or 'N/A'})"
                )
                st.markdown(
                    f"**📝 Contrats:** {', '.join(info1['contract_types']) if info1['contract_types'] else 'N/A'}"
                )
                st.markdown(
                    f"**🏠 Télétravail:** {'✅ Oui' if info1['remote']['remote_possible'] else '❌ Non'}"
                )

        with col2:
            st.markdown("**Offre 2 - Informations extraites**")
            with st.container():
                st.markdown(
                    f"**💰 Salaire:** {info2['salary']['min'] or 'N/A'}€ - {info2['salary']['max'] or 'N/A'}€"
                )
                st.markdown(
                    f"**📅 Expérience:** {info2['experience']['min'] or 'N/A'}-{info2['experience']['max'] or 'N/A'} ans ({info2['experience']['level'] or 'N/A'})"
                )
                st.markdown(
                    f"**🎓 Formation:** Bac+{info2['education']['level'] or 'N/A'} ({info2['education']['degree_type'] or 'N/A'})"
                )
                st.markdown(
                    f"**📝 Contrats:** {', '.join(info2['contract_types']) if info2['contract_types'] else 'N/A'}"
                )
                st.markdown(
                    f"**🏠 Télétravail:** {'✅ Oui' if info2['remote']['remote_possible'] else '❌ Non'}"
                )

        # ========================================================================
        # ÉTAPE 3: EXTRACTION DE COMPÉTENCES
        # ========================================================================

        st.subheader("3️⃣ Extraction de compétences")

        with st.spinner("Extraction des compétences..."):
            skills1 = skill_extractor.extract_skills(offer1)
            skills2 = skill_extractor.extract_skills(offer2)

        col1, col2 = st.columns(2)

        with col1:
            st.markdown("**Offre 1 - Compétences détectées**")
            with st.container():
                st.markdown(
                    f"**💻 Tech:** {skills1['skill_count']['tech']} compétences"
                )
                if skills1["all_tech_skills"]:
                    st.markdown(f"*{', '.join(skills1['all_tech_skills'][:15])}*")
                    if len(skills1["all_tech_skills"]) > 15:
                        st.caption(
                            f"... et {len(skills1['all_tech_skills']) - 15} autres"
                        )

                st.markdown(
                    f"**🤝 Soft skills:** {skills1['skill_count']['soft']} compétences"
                )
                if skills1["soft_skills"]:
                    st.markdown(f"*{', '.join(skills1['soft_skills'][:10])}*")
                    if len(skills1["soft_skills"]) > 10:
                        st.caption(f"... et {len(skills1['soft_skills']) - 10} autres")

        with col2:
            st.markdown("**Offre 2 - Compétences détectées**")
            with st.container():
                st.markdown(
                    f"**💻 Tech:** {skills2['skill_count']['tech']} compétences"
                )
                if skills2["all_tech_skills"]:
                    st.markdown(f"*{', '.join(skills2['all_tech_skills'][:15])}*")
                    if len(skills2["all_tech_skills"]) > 15:
                        st.caption(
                            f"... et {len(skills2['all_tech_skills']) - 15} autres"
                        )

                st.markdown(
                    f"**🤝 Soft skills:** {skills2['skill_count']['soft']} compétences"
                )
                if skills2["soft_skills"]:
                    st.markdown(f"*{', '.join(skills2['soft_skills'][:10])}*")
                    if len(skills2["soft_skills"]) > 10:
                        st.caption(f"... et {len(skills2['soft_skills']) - 10} autres")

        # ========================================================================
        # ÉTAPE 4: COMPARAISON DES EMBEDDINGS
        # ========================================================================

        st.subheader("4️⃣ Similarité sémantique (Embeddings)")

        with st.spinner("Calcul de la similarité..."):
            embedding1 = embedding_gen.generate(text_lemmatized1)
            embedding2 = embedding_gen.generate(text_lemmatized2)
            similarity = embedding_gen.cosine_similarity(embedding1, embedding2)
            euclidean_dist = embedding_gen.euclidean_distance(embedding1, embedding2)

        # Affichage du score de similarité et distance euclidienne
        col1, col2 = st.columns(2)

        with col1:
            st.markdown(
                f'<div class="similarity-score">{similarity:.1%}<br><small>Similarité cosinus</small></div>',
                unsafe_allow_html=True,
            )

        with col2:
            st.markdown(
                f'<div class="similarity-score">{euclidean_dist:.2f}<br><small>Distance euclidienne</small></div>',
                unsafe_allow_html=True,
            )

        # Interprétation
        st.markdown("---")
        st.markdown("**📌 Interprétation:**")

        col1, col2 = st.columns(2)

        with col1:
            st.markdown("**Similarité cosinus:**")
            st.caption(
                "Mesure l'orientation des offres (0% = opposées, 100% = identiques). Compare le contenu global sans tenir compte du volume de texte."
            )
            if similarity >= 0.9:
                st.success("🟢 **Très similaire** - Les offres sont presque identiques")
            elif similarity >= 0.75:
                st.info("🔵 **Similaire** - Beaucoup de points communs")
            elif similarity >= 0.5:
                st.warning(
                    "🟡 **Moyennement similaire** - Quelques différences notables"
                )
            else:
                st.error("🔴 **Peu similaire** - Offres assez différentes")

        with col2:
            st.markdown("**Distance euclidienne:**")
            st.caption(
                "Mesure la distance directe entre les offres. Plus la distance est faible, plus les offres sont proches en termes de densité d'informations."
            )
            if euclidean_dist <= 2.0:
                st.success(
                    "🟢 **Très proche** - Distance très faible entre les vecteurs"
                )
            elif euclidean_dist <= 5.0:
                st.info("🔵 **Proche** - Distance modérée")
            elif euclidean_dist <= 10.0:
                st.warning("🟡 **Éloignée** - Distance significative")
            else:
                st.error("🔴 **Très éloignée** - Grande distance entre les vecteurs")

        # Compétences en commun
        st.markdown("---")
        st.subheader("🔗 Compétences en commun")

        tech_common = set(skills1["all_tech_skills"]) & set(skills2["all_tech_skills"])
        soft_common = set(skills1["soft_skills"]) & set(skills2["soft_skills"])

        col1, col2 = st.columns(2)

        with col1:
            st.markdown(f"**💻 Compétences techniques communes ({len(tech_common)})**")
            if tech_common:
                st.markdown(f"*{', '.join(sorted(tech_common))}*")
            else:
                st.caption("Aucune compétence technique en commun")

        with col2:
            st.markdown(f"**🤝 Soft skills communes ({len(soft_common)})**")
            if soft_common:
                st.markdown(f"*{', '.join(sorted(soft_common))}*")
            else:
                st.caption("Aucune soft skill en commun")

# ============================================================================
# FOOTER
# ============================================================================

st.markdown("---")
st.caption(
    "💡 Utilisez cette page pour comparer deux offres d'emploi et analyser leurs similarités"
)
