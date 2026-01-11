"""
Database Saver pour les offres scrapées
========================================

Sauvegarde les offres complètes avec toutes les dimensions
dans PostgreSQL (schéma compatible avec db_inserter_v2.py)
"""

import psycopg2
import os
from datetime import datetime
from typing import Dict
import logging
import re

# Import GeoMatcher et TopicPredictor
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from collectors.geo_matcher import GeoMatcher

try:
    from api.routers.topic_predictor import get_topic_predictor
except (ModuleNotFoundError, ImportError):
    from routers.topic_predictor import get_topic_predictor

logger = logging.getLogger("database_saver")


def save_offer_to_database(
    raw_data: Dict, nlp_results: Dict, database_url: str
) -> Dict:
    """
    Sauvegarder une offre complète en base de données avec toutes les dimensions

    Args:
        raw_data: Données brutes de l'offre
        nlp_results: Résultats NLP
        database_url: URL de connexion PostgreSQL

    Returns:
        Dict avec {success: bool, duplicate: bool, message: str, offer_id: int}
    """
    if not database_url:
        logger.error("❌ DATABASE_URL non configurée")
        return {
            "success": False,
            "duplicate": False,
            "message": "DATABASE_URL non configurée",
        }

    try:
        conn = psycopg2.connect(database_url)
        cursor = conn.cursor()

        # Préparer les données
        final = nlp_results.get("final", {})
        skills = nlp_results.get("steps", {}).get("skills_extracted", {})
        info = nlp_results.get("steps", {}).get("info_extraction", {})
        category_info = nlp_results.get("steps", {}).get("category", {})

        # ===== VÉRIFICATION DE DOUBLON PAR EMBEDDING =====
        embedding_vector = final.get("embedding_vector")
        if embedding_vector:
            logger.info("🔍 Vérification des doublons par similarité d'embedding...")
            duplicate_check = _check_duplicate_by_embedding(
                cursor, embedding_vector, threshold=0.95
            )

            if duplicate_check:
                offer_id, similarity, title = duplicate_check
                logger.warning(
                    f"⚠️ Offre similaire trouvée (similarité: {similarity:.2%})"
                )
                logger.warning(f"   Offre existante #{offer_id}: {title[:80]}")
                cursor.close()
                conn.close()
                return {
                    "success": False,
                    "duplicate": True,
                    "message": f"Offre déjà présente en BDD (similarité: {similarity:.2%})",
                    "existing_offer_id": offer_id,
                    "similarity": similarity,
                    "existing_title": title,
                }

        # ===== DIMENSIONS =====

        # 1. source_id
        source_id = _get_or_create_source(
            cursor, conn, raw_data.get("source", "unknown")
        )

        # 2. date_id (basé sur published_date)
        date_id = _get_or_create_date(cursor, conn, raw_data.get("published_date"))

        # 3. commune_id (via GeoMatcher)
        commune_id = _get_commune_id(
            database_url,
            raw_data.get("location_city", "").strip(),
            raw_data.get("location_code_postal", "").strip(),
        )

        # 4. job_category_id
        job_category_id = _get_or_create_job_category(
            cursor, conn, final.get("profile_category", "Généraliste")
        )

        # 5. external_id
        external_id = (
            raw_data.get("external_id")
            or raw_data.get("url", "").split("/")[-1]
            or f"{raw_data.get('source', 'unknown')}_{datetime.now().timestamp()}"
        )

        # 6. Parser salary_min et salary_max
        salary_info = info.get("salary", {})
        if isinstance(salary_info, dict):
            salary_min = salary_info.get("min")
            salary_max = salary_info.get("max")
        else:
            salary_min, salary_max = None, None

        # 7. experience_years
        experience_years = _extract_experience_years(info.get("experience", {}))

        # 8. profile_score
        profile_score = category_info.get("profile_score", 0)

        # 9. Topic modeling (LDA)
        topic_data = _predict_topic(raw_data.get("title", ""))

        # ===== INSERTION =====

        logger.info("💾 Insertion dans fact_job_offers...")

        offer_id = _insert_or_update_offer(
            cursor,
            conn,
            source_id=source_id,
            date_id=date_id,
            commune_id=commune_id,
            job_category_id=job_category_id,
            external_id=external_id,
            title=raw_data.get("title"),
            description=raw_data.get("description"),
            description_cleaned=final.get("description_cleaned"),
            url=raw_data.get("url"),
            company_name=raw_data.get("company_name"),
            contract_type=final.get("contract_types", [None])[0],
            salary_min=salary_min,
            salary_max=salary_max,
            published_date=_parse_published_date(raw_data.get("published_date")),
            experience_years=experience_years,
            profile_category=final.get("profile_category"),
            profile_confidence=final.get("profile_confidence"),
            profile_score=profile_score,
            education_level=final.get("education_level"),
            education_type=final.get("education_type"),
            remote_possible=final.get("remote_possible"),
            remote_days=final.get("remote_days"),
            remote_percentage=final.get("remote_percentage"),
            topic_id=topic_data.get("topic_id"),
            topic_label=topic_data.get("topic_label"),
            topic_confidence=topic_data.get("topic_confidence"),
            skills_extracted=(
                skills.get("all_tech_skills", []) + skills.get("soft_skills", [])
            ),
        )

        logger.info(f"  ✅ Offre #{offer_id} insérée/mise à jour")

        # Insérer les skills et relations
        _insert_skills_and_relations(
            cursor,
            conn,
            offer_id,
            skills.get("all_tech_skills", []),
            skills.get("soft_skills", []),
        )

        # Insérer l'embedding
        _insert_embedding(
            cursor,
            conn,
            offer_id,
            final.get("embedding_vector"),
            final.get("embedding_model"),
        )

        conn.commit()
        logger.info(f"✅ Offre #{offer_id} sauvegardée en BDD avec succès")

        cursor.close()
        conn.close()

        return {
            "success": True,
            "duplicate": False,
            "message": "Offre sauvegardée avec succès",
            "offer_id": offer_id,
        }

    except Exception as e:
        logger.error(f"❌ Erreur sauvegarde BDD: {e}")
        import traceback

        traceback.print_exc()
        if "conn" in locals():
            conn.rollback()
            conn.close()
        return {"success": False, "duplicate": False, "message": f"Erreur: {str(e)}"}


# ============================================================================
# FONCTIONS HELPER
# ============================================================================


def _check_duplicate_by_embedding(
    cursor, embedding_vector: list, threshold: float = 0.95
):
    """
    Vérifie si un embedding similaire existe déjà dans la BDD

    Args:
        cursor: Curseur PostgreSQL
        embedding_vector: Vecteur d'embedding (liste de floats)
        threshold: Seuil de similarité (0.95 = 95%)

    Returns:
        Tuple (offer_id, similarity, title) si doublon trouvé, None sinon
    """
    try:
        # Recherche par similarité cosinus avec pgvector
        # 1 - cosine_distance = similarité (plus proche de 1 = plus similaire)
        query = """
            SELECT 
                jo.offer_id,
                1 - (je.embedding <=> %s::vector) as similarity,
                jo.title
            FROM job_embeddings je
            JOIN fact_job_offers jo ON je.offer_id = jo.offer_id
            WHERE 1 - (je.embedding <=> %s::vector) >= %s
            ORDER BY similarity DESC
            LIMIT 1
        """

        cursor.execute(query, (embedding_vector, embedding_vector, threshold))
        result = cursor.fetchone()

        if result:
            return result  # (offer_id, similarity, title)

        return None

    except Exception as e:
        logger.warning(f"⚠️ Erreur vérification doublon: {e}")
        return None


def _get_or_create_source(cursor, conn, source_name: str) -> int:
    """Récupère ou crée une source"""
    cursor.execute(
        "SELECT source_id FROM dim_sources WHERE source_name = %s", (source_name,)
    )
    result = cursor.fetchone()
    if result:
        return result[0]

    # Créer la source
    source_type = "api" if source_name == "france_travail" else "scraping"
    is_official = source_name == "france_travail"

    cursor.execute(
        """
        INSERT INTO dim_sources (source_name, source_type, is_official, description)
        VALUES (%s, %s, %s, %s)
        RETURNING source_id
        """,
        (source_name, source_type, is_official, f"Source {source_name}"),
    )
    conn.commit()
    return cursor.fetchone()[0]


def _get_or_create_date(cursor, conn, published_date_str: str) -> int:
    """Récupère ou crée une date"""
    if not published_date_str:
        return None

    try:
        pub_date = datetime.fromisoformat(
            published_date_str.replace("Z", "+00:00")
        ).date()
    except:
        return None

    cursor.execute("SELECT date_id FROM dim_dates WHERE full_date = %s", (pub_date,))
    result = cursor.fetchone()
    if result:
        return result[0]

    # Créer la date
    month_names = [
        "",
        "Janvier",
        "Février",
        "Mars",
        "Avril",
        "Mai",
        "Juin",
        "Juillet",
        "Août",
        "Septembre",
        "Octobre",
        "Novembre",
        "Décembre",
    ]
    day_names = [
        "Lundi",
        "Mardi",
        "Mercredi",
        "Jeudi",
        "Vendredi",
        "Samedi",
        "Dimanche",
    ]

    cursor.execute(
        """
        INSERT INTO dim_dates
        (full_date, year, quarter, month, month_name, week, day_of_week, day_name, is_weekend)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        RETURNING date_id
        """,
        (
            pub_date,
            pub_date.year,
            (pub_date.month - 1) // 3 + 1,
            pub_date.month,
            month_names[pub_date.month],
            pub_date.isocalendar()[1],
            pub_date.weekday() + 1,
            day_names[pub_date.weekday()],
            pub_date.weekday() >= 5,
        ),
    )
    conn.commit()
    return cursor.fetchone()[0]


def _get_commune_id(database_url: str, city: str, postal_code: str) -> int:
    """Récupère le commune_id via GeoMatcher"""
    if not city:
        return None

    geo_matcher = GeoMatcher(database_url)
    commune_id = geo_matcher.find_commune_id(city, postal_code)
    geo_matcher.close()

    if not commune_id:
        logger.warning(f"  ⚠️ Commune non trouvée: {city} ({postal_code})")

    return commune_id


def _get_or_create_job_category(cursor, conn, profile_category: str) -> int:
    """Récupère ou crée une catégorie d'emploi"""
    if not profile_category or profile_category == "Généraliste":
        return None

    cursor.execute(
        "SELECT job_category_id FROM dim_job_categories WHERE category_name = %s",
        (profile_category,),
    )
    result = cursor.fetchone()
    if result:
        return result[0]

    # Créer la catégorie
    cursor.execute(
        """
        INSERT INTO dim_job_categories (category_name, category_code, level)
        VALUES (%s, %s, 1)
        RETURNING job_category_id
        """,
        (profile_category, profile_category.upper().replace(" ", "_")),
    )
    conn.commit()
    return cursor.fetchone()[0]


def _parse_salary(salary_text: str) -> tuple:
    """Parse le salaire depuis le texte"""
    if not salary_text:
        return None, None

    # Détecter format "K" (milliers)
    has_k = bool(re.search(r"\d+\s*K", salary_text, re.IGNORECASE))
    numbers = re.findall(r"(\d+(?:\.\d+)?)", salary_text)

    if has_k:
        numbers = [float(n) * 1000 if float(n) < 1000 else float(n) for n in numbers]
    else:
        numbers = [float(n) for n in numbers if float(n) >= 100]

    salary_min, salary_max = None, None
    if len(numbers) >= 2:
        salary_min, salary_max = numbers[0], numbers[1]
    elif len(numbers) == 1:
        salary_min = numbers[0]

    return salary_min, salary_max


def _extract_experience_years(experience_data: Dict) -> int:
    """Extrait les années d'expérience"""
    if not experience_data:
        return None

    exp_min = experience_data.get("min")
    exp_max = experience_data.get("max")

    if exp_min is not None and exp_max is not None:
        return (exp_min + exp_max) // 2
    elif exp_min is not None:
        return exp_min

    return None


def _parse_published_date(published_date_str: str):
    """Parse la date de publication"""
    if not published_date_str:
        return None

    try:
        return datetime.fromisoformat(published_date_str.replace("Z", "+00:00")).date()
    except:
        return None


def _predict_topic(title: str) -> Dict:
    """Prédit le topic avec le modèle LDA"""
    try:
        predictor = get_topic_predictor()
        return predictor.predict_topic(title)
    except Exception as e:
        logger.warning(f"  ⚠️ Erreur prédiction topic: {e}")
        return {"topic_id": None, "topic_label": None, "topic_confidence": None}


def _insert_or_update_offer(cursor, conn, **kwargs) -> int:
    """Insère ou met à jour une offre"""
    query = """
        INSERT INTO fact_job_offers (
            source_id, date_id, commune_id, job_category_id,
            external_id, title, description, description_cleaned,
            url, company_name, contract_type,
            salary_min, salary_max,
            published_date, collected_date,
            experience_years,
            profile_category, profile_confidence, profile_score,
            education_level, education_type,
            remote_possible, remote_days, remote_percentage,
            topic_id, topic_label, topic_confidence,
            skills_extracted, processed, processing_date
        ) VALUES (
            %s, %s, %s, %s,
            %s, %s, %s, %s,
            %s, %s, %s,
            %s, %s,
            %s, NOW(),
            %s,
            %s, %s, %s,
            %s, %s,
            %s, %s, %s,
            %s, %s, %s,
            %s, TRUE, NOW()
        )
        ON CONFLICT (external_id) 
        DO UPDATE SET
            description_cleaned = EXCLUDED.description_cleaned,
            salary_min = EXCLUDED.salary_min,
            salary_max = EXCLUDED.salary_max,
            profile_category = EXCLUDED.profile_category,
            profile_confidence = EXCLUDED.profile_confidence,
            profile_score = EXCLUDED.profile_score,
            education_level = EXCLUDED.education_level,
            education_type = EXCLUDED.education_type,
            remote_possible = EXCLUDED.remote_possible,
            remote_days = EXCLUDED.remote_days,
            remote_percentage = EXCLUDED.remote_percentage,
            experience_years = EXCLUDED.experience_years,
            topic_id = EXCLUDED.topic_id,
            topic_label = EXCLUDED.topic_label,
            topic_confidence = EXCLUDED.topic_confidence,
            skills_extracted = EXCLUDED.skills_extracted,
            processed = TRUE,
            processing_date = NOW()
        RETURNING offer_id
    """

    cursor.execute(
        query,
        (
            kwargs["source_id"],
            kwargs["date_id"],
            kwargs["commune_id"],
            kwargs["job_category_id"],
            kwargs["external_id"],
            kwargs["title"],
            kwargs["description"],
            kwargs["description_cleaned"],
            kwargs["url"],
            kwargs["company_name"],
            kwargs["contract_type"],
            kwargs["salary_min"],
            kwargs["salary_max"],
            kwargs["published_date"],
            kwargs["experience_years"],
            kwargs["profile_category"],
            kwargs["profile_confidence"],
            kwargs["profile_score"],
            kwargs["education_level"],
            kwargs["education_type"],
            kwargs["remote_possible"],
            kwargs["remote_days"],
            kwargs["remote_percentage"],
            kwargs["topic_id"],
            kwargs["topic_label"],
            kwargs["topic_confidence"],
            kwargs["skills_extracted"],
        ),
    )

    return cursor.fetchone()[0]


def _insert_skills_and_relations(
    cursor, conn, offer_id: int, tech_skills: list, soft_skills: list
):
    """Insère les skills dans dim_skills et crée les relations"""
    all_skills = tech_skills + soft_skills

    if not all_skills:
        return

    logger.info(f"💾 Insertion de {len(all_skills)} compétences...")

    # Insérer tech skills
    for skill in tech_skills:
        cursor.execute(
            """
            INSERT INTO dim_skills (skill_name, skill_category)
            VALUES (%s, 'technical')
            ON CONFLICT (skill_name) DO NOTHING
            """,
            (skill,),
        )

    # Insérer soft skills
    for skill in soft_skills:
        cursor.execute(
            """
            INSERT INTO dim_skills (skill_name, skill_category)
            VALUES (%s, 'soft')
            ON CONFLICT (skill_name) DO NOTHING
            """,
            (skill,),
        )

    # Créer les relations
    logger.info("💾 Création des relations offer-skills...")
    for skill in all_skills:
        cursor.execute(
            """
            INSERT INTO fact_offer_skills (offer_id, skill_id)
            SELECT %s, skill_id 
            FROM dim_skills 
            WHERE skill_name = %s
            ON CONFLICT (offer_id, skill_id) DO NOTHING
            """,
            (offer_id, skill),
        )


def _insert_embedding(cursor, conn, offer_id: int, embedding_vector, model_name: str):
    """Insère l'embedding dans job_embeddings"""
    if not embedding_vector:
        return

    logger.info("💾 Insertion de l'embedding...")
    cursor.execute(
        """
        INSERT INTO job_embeddings (offer_id, embedding, model_name, created_at)
        VALUES (%s, %s, %s, NOW())
        ON CONFLICT (offer_id) 
        DO UPDATE SET 
            embedding = EXCLUDED.embedding,
            model_name = EXCLUDED.model_name,
            created_at = NOW()
        """,
        (offer_id, embedding_vector, model_name),
    )
