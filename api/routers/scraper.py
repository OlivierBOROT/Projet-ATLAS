"""
Router de scraping à la demande
================================

Permet de scraper une offre d'emploi depuis:
- Welcome to the Jungle (URL)
- France Travail (ID)

Et traiter l'offre avec les modules NLP.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict, Optional, List
from datetime import datetime
import logging
import sys
import requests
from pathlib import Path
import psycopg2
from psycopg2.extras import execute_values
import os
from dotenv import load_dotenv

# Ajouter le dossier parent au PYTHONPATH pour importer collectors
project_root = Path(__file__).parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# Import des collecteurs existants
from collectors.wttj_collector import WTTJCollector
from collectors.france_travail_collector import FranceTravailCollector

# Import des modules de traitement
try:
    from api.routers.database_saver import save_offer_to_database
    from api.routers.topic_predictor import predict_topic_for_offer
except (ModuleNotFoundError, ImportError):
    from routers.database_saver import save_offer_to_database
    from routers.topic_predictor import predict_topic_for_offer

logger = logging.getLogger("scraper")

router = APIRouter()

# Configuration BDD
load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")


# ============================================================================
# MODELS
# ============================================================================


class ScrapeRequest(BaseModel):
    """Requête de scraping"""

    source: str  # "wttj" ou "france_travail"
    identifier: str  # URL pour WTTJ, ID pour France Travail
    save_to_db: bool = False  # Sauvegarder en BDD après scraping


class ScrapeResponse(BaseModel):
    """Réponse du scraping"""

    success: bool
    source: str
    raw_data: Dict
    nlp_results: Optional[Dict] = None
    saved_to_db: bool = False
    error: Optional[str] = None


# ============================================================================
# WELCOME TO THE JUNGLE
# ============================================================================


def scrape_wttj_offer(url: str) -> Dict:
    """
    Scraper une offre Welcome to the Jungle

    Args:
        url: URL complète de l'offre WTTJ

    Returns:
        Dictionnaire avec les données extraites
    """
    logger.info(f"🔍 Scraping WTTJ: {url}")

    collector = None
    try:
        # Initialiser le collecteur
        collector = WTTJCollector(headless=True)

        # Extraire les détails de l'offre
        job_data = collector.extract_job_details(url)

        if not job_data:
            raise HTTPException(
                status_code=500, detail="Impossible d'extraire les données de l'offre"
            )

        logger.info(f"✅ Scraping WTTJ réussi: {job_data.get('title', 'Sans titre')}")
        return job_data

    except Exception as e:
        logger.error(f"❌ Erreur scraping WTTJ: {e}")
        raise HTTPException(status_code=500, detail=f"Erreur scraping WTTJ: {str(e)}")

    finally:
        if collector:
            collector.close()


# ============================================================================
# FRANCE TRAVAIL
# ============================================================================


def scrape_france_travail_offer(offer_id: str) -> Dict:
    """
    Récupérer une offre France Travail via API

    Args:
        offer_id: ID de l'offre France Travail

    Returns:
        Dictionnaire avec les données extraites
    """
    logger.info(f"🔍 Récupération France Travail: {offer_id}")

    try:
        # Initialiser le collecteur
        collector = FranceTravailCollector(use_selenium=False)

        # Authentification
        token = collector.authenticate()

        # Récupération de l'offre via API
        offer_response = requests.get(
            f"https://api.francetravail.io/partenaire/offresdemploi/v2/offres/{offer_id}",
            headers={"Authorization": f"Bearer {token}"},
            timeout=30,
        )
        offer_response.raise_for_status()
        raw_offer = offer_response.json()

        # Normaliser l'offre
        job_data = collector.normalize_offer(raw_offer)

        logger.info(
            f"✅ Récupération France Travail réussie: {job_data.get('title', 'Sans titre')}"
        )
        return job_data

    except requests.exceptions.RequestException as e:
        logger.error(f"❌ Erreur API France Travail: {e}")
        raise HTTPException(
            status_code=500, detail=f"Erreur API France Travail: {str(e)}"
        )
    except Exception as e:
        logger.error(f"❌ Erreur traitement: {e}")
        raise HTTPException(status_code=500, detail=f"Erreur traitement: {str(e)}")


# ============================================================================
# NLP PROCESSING
# ============================================================================


def process_nlp(job_data: Dict) -> Dict:
    """
    Traiter l'offre avec les modules NLP

    Args:
        job_data: Données brutes de l'offre

    Returns:
        Résultats NLP structurés
    """
    logger.info("🧠 Traitement NLP...")

    try:
        # Import des modules NLP
        from NLP.modules.text_cleaner import TextCleaner
        from NLP.modules.skill_extractor import SkillExtractor
        from NLP.modules.info_extractor import InfoExtractor
        from NLP.modules.embedding_generator import EmbeddingGenerator

        description = job_data.get("description", "")

        if not description:
            return {"error": "Pas de description disponible", "steps_completed": []}

        nlp_results = {"steps": {}, "final": {}}

        # 1. Nettoyage du texte
        cleaner = TextCleaner()
        clean_result = cleaner.clean_and_lemmatize(description)

        cleaned_text = clean_result.get("cleaned_text", "")
        lemmas_str = clean_result.get("lemmas_str", "")

        nlp_results["steps"][
            "cleaned_text"
        ] = lemmas_str  # Texte lemmatisé pour affichage
        nlp_results["steps"]["lemmas"] = clean_result.get("lemmas", [])
        logger.info("  ✅ Texte nettoyé")

        # 2. Extraction d'informations
        info_extractor = InfoExtractor()
        info = info_extractor.extract_all(description)
        nlp_results["steps"]["info_extraction"] = info
        logger.info("  ✅ Informations extraites")

        # 3. Extraction de compétences et catégorisation
        skill_extractor = SkillExtractor()
        skills = skill_extractor.extract_skills(description)
        category = skill_extractor.categorize_offer(description)
        nlp_results["steps"]["skills_extracted"] = skills
        nlp_results["steps"]["category"] = category

        # Vérifier que category est bien un dict
        if not isinstance(category, dict):
            logger.error(f"⚠️ category n'est pas un dict: {type(category)} = {category}")
            category = {"dominant_profile": "Inconnu", "profile_score": 0}

        # Compter le total de compétences (toutes catégories confondues)
        total_skills = sum(len(v) for v in skills.values() if isinstance(v, list))

        # Calculer profile_confidence
        total_tech_skills = len(skills.get("all_tech_skills", []))
        matched_skills = category.get("profile_score", 0)

        if total_tech_skills == 0 or matched_skills == 0:
            profile_confidence = 0
        else:
            ratio = matched_skills / total_tech_skills
            if matched_skills == 1:
                confidence_factor = 0.5
            elif matched_skills == 2:
                confidence_factor = 0.7
            else:
                confidence_factor = 1.0
            profile_confidence = min(100, int(ratio * confidence_factor * 100))

        logger.info(f"  ✅ {total_skills} compétences extraites")
        logger.info(
            f"  🎯 Profil: {category.get('dominant_profile')} ({profile_confidence}%)"
        )

        # 4. Génération d'embedding
        # Utiliser lemmas_str (mots lemmatisés) pour l'embedding si disponible, sinon cleaned_text
        text_for_embedding = (
            lemmas_str if lemmas_str and len(lemmas_str.strip()) >= 10 else cleaned_text
        )

        # Validation du texte pour l'embedding
        if (
            not text_for_embedding
            or not isinstance(text_for_embedding, str)
            or len(text_for_embedding.strip()) < 10
        ):
            logger.warning(
                f"⚠️ Texte pour embedding invalide ou trop court (longueur: {len(text_for_embedding) if text_for_embedding else 0})"
            )
            # Utiliser la description originale comme fallback
            text_for_embedding = (
                description
                if description and len(description) > 10
                else "Pas de texte disponible"
            )

        logger.info(f"  📝 Texte pour embedding: {len(text_for_embedding)} caractères")

        embedding_gen = EmbeddingGenerator()
        embedding = embedding_gen.generate(text_for_embedding)

        # Vérifier que l'embedding est valide
        if embedding is None or (hasattr(embedding, "size") and embedding.size == 0):
            raise ValueError("Embedding vide généré")

        nlp_results["steps"]["embedding"] = {
            "shape": list(embedding.shape),  # Convertir tuple en liste pour JSON
            "model": embedding_gen.model_name,
            "vector": embedding.tolist(),  # Convertir numpy array en liste
        }
        logger.info(f"  ✅ Embedding généré ({embedding.shape[0]} dimensions)")

        # 5. Topic Modeling (LDA) - Optionnel
        logger.info("  🎯 Prédiction du topic...")
        try:
            topic_result = predict_topic_for_offer(job_data.get("title", ""))
            nlp_results["steps"]["topic"] = topic_result
            if topic_result.get("topic_id") is not None:
                logger.info(
                    f"  ✅ Topic {topic_result['topic_id']}: {topic_result['topic_label']} "
                    f"({topic_result['topic_confidence']:.0%})"
                )
        except Exception as e:
            logger.warning(f"  ⚠️ Topic modeling non disponible: {str(e)[:100]}")
            topic_result = {
                "topic_id": None,
                "topic_label": None,
                "topic_confidence": None,
            }
            nlp_results["steps"]["topic"] = topic_result

        # Résumé final
        # Récupérer le top 10 des compétences (toutes catégories confondues, sans doublons)
        all_skills_set = set()
        if isinstance(skills, dict):
            for skill_category, skill_list in skills.items():
                # Ignorer les catégories de métadonnées
                if isinstance(skill_list, list) and skill_category not in [
                    "all_tech_skills",
                    "skill_count",
                ]:
                    all_skills_set.update(skill_list)

        all_skills_list = list(all_skills_set)

        nlp_results["final"] = {
            "profile_category": category.get("dominant_profile"),
            "profile_confidence": profile_confidence,
            "contract_types": info.get("contract_types", []),
            "salary_min": info.get("salary", {}).get("min"),
            "salary_max": info.get("salary", {}).get("max"),
            "education_level": info.get("education", {}).get("level"),
            "education_type": info.get("education", {}).get("degree_type"),
            "remote_possible": info.get("remote", {}).get("remote_possible", False),
            "remote_days": info.get("remote", {}).get("remote_days"),
            "remote_percentage": info.get("remote", {}).get("remote_percentage"),
            "skills_count": len(all_skills_list),
            "top_skills": all_skills_list[:10] if all_skills_list else [],
            "skills_by_category": skills,
            "embedding_dimensions": int(embedding.shape[0]),
            "description_cleaned": lemmas_str,  # Pour la BDD
            "embedding_vector": embedding.tolist(),  # Pour la BDD
            "embedding_model": embedding_gen.model_name,  # Pour la BDD
            "topic_id": topic_result.get("topic_id"),  # Pour la BDD
            "topic_label": topic_result.get("topic_label"),  # Pour la BDD
            "topic_confidence": topic_result.get("topic_confidence"),  # Pour la BDD
        }

        logger.info("✅ Traitement NLP terminé")
        return nlp_results

    except Exception as e:
        import traceback

        error_details = traceback.format_exc()
        logger.error(f"❌ Erreur NLP: {e}")
        logger.error(f"Détails: {error_details}")
        return {"error": str(e), "error_details": error_details, "steps_completed": []}


# ============================================================================
# DATABASE SAVE (wrapper simplifié)
# ============================================================================


def save_to_database(raw_data: Dict, nlp_results: Dict) -> Dict:
    """
    Wrapper pour sauvegarder l'offre en BDD
    La logique complète est dans database_saver.py

    Args:
        raw_data: Données brutes de l'offre
        nlp_results: Résultats NLP

    Returns:
        Dict avec {success: bool, duplicate: bool, message: str, ...}
    """
    return save_offer_to_database(raw_data, nlp_results, DATABASE_URL)


# ============================================================================
# ENDPOINTS
# ============================================================================


@router.post("/scrape", response_model=ScrapeResponse)
async def scrape_offer(request: ScrapeRequest):
    """
    Scraper une offre d'emploi à la demande

    Args:
        request: Source (wttj/france_travail) et identifiant (URL/ID)

    Returns:
        Données brutes + résultats NLP
    """
    logger.info(f"📥 Requête scraping: {request.source} - {request.identifier[:50]}")

    try:
        # 1. Scraping selon la source
        if request.source.lower() == "wttj":
            raw_data = scrape_wttj_offer(request.identifier)
        elif request.source.lower() == "france_travail":
            raw_data = scrape_france_travail_offer(request.identifier)
        else:
            raise HTTPException(
                status_code=400,
                detail=f"Source invalide: {request.source}. Utilisez 'wttj' ou 'france_travail'",
            )

        # 2. Traitement NLP
        nlp_results = process_nlp(raw_data)

        # 3. Sauvegarde en BDD (optionnelle)
        saved_to_db = False
        db_result = None
        if request.save_to_db:
            logger.info("💾 Sauvegarde en BDD demandée...")
            db_result = save_to_database(raw_data, nlp_results)

            if db_result.get("duplicate"):
                # Doublon détecté
                logger.warning(f"⚠️ {db_result['message']}")
                logger.warning(
                    f"   Offre existante: {db_result.get('existing_title', 'N/A')}"
                )
                return ScrapeResponse(
                    success=False,
                    source=request.source,
                    raw_data=raw_data,
                    nlp_results=nlp_results,
                    saved_to_db=False,
                    error=f"Doublon détecté: {db_result['message']} (Offre #{db_result.get('existing_offer_id')})",
                )

            saved_to_db = db_result.get("success", False)
            if saved_to_db:
                logger.info("✅ Sauvegarde en BDD réussie")
            else:
                logger.warning(
                    f"⚠️ Sauvegarde en BDD échouée: {db_result.get('message')}"
                )

        # 4. Réponse
        return ScrapeResponse(
            success=True,
            source=request.source,
            raw_data=raw_data,
            nlp_results=nlp_results,
            saved_to_db=saved_to_db,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Erreur scraping: {e}")
        raise HTTPException(status_code=500, detail=f"Erreur: {str(e)}")
