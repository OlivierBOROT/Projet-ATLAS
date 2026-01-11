"""
Offers Router
=============
Routes pour la gestion des offres d'emploi
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import create_engine, text
from typing import Optional
import os
from dotenv import load_dotenv

load_dotenv()

router = APIRouter()

# Configuration database
DATABASE_URL = os.getenv("DATABASE_URL")
engine = create_engine(DATABASE_URL)
from sqlalchemy.orm import sessionmaker

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.get("/offers")
def get_offers(
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    source: Optional[str] = Query(None),
    contract: Optional[str] = Query(None),
    profile: Optional[str] = Query(None),
    remote: Optional[str] = Query(None),
    skills: Optional[str] = Query(None),
    education: Optional[str] = Query(None),
    cities: Optional[str] = Query(None),
    postal_codes: Optional[str] = Query(None),
    experience: Optional[int] = Query(None),
    date_from: Optional[str] = Query(None),
    min_salary: Optional[int] = Query(None),
    search: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    """Récupère les offres avec pagination et filtres optionnels"""
    try:
        # Construction des filtres WHERE
        where_clauses = []
        params = {"limit": limit, "offset": offset}

        if source:
            sources = source.split(",")
            placeholders = ",".join([f":source_{i}" for i in range(len(sources))])
            where_clauses.append(f"s.source_name IN ({placeholders})")
            for i, src in enumerate(sources):
                params[f"source_{i}"] = src

        if contract:
            contracts = contract.split(",")
            placeholders = ",".join([f":contract_{i}" for i in range(len(contracts))])
            where_clauses.append(f"f.contract_type IN ({placeholders})")
            for i, ctr in enumerate(contracts):
                params[f"contract_{i}"] = ctr

        if profile:
            profiles = profile.split(",")
            placeholders = ",".join([f":profile_{i}" for i in range(len(profiles))])
            where_clauses.append(f"f.profile_category IN ({placeholders})")
            for i, prf in enumerate(profiles):
                params[f"profile_{i}"] = prf

        if remote and remote.lower() == "true":
            where_clauses.append("f.remote_possible = TRUE")

        if skills:
            skill_list = skills.split(",")
            skill_conditions = []
            for i, skill in enumerate(skill_list):
                skill_conditions.append(f":skill_{i} = ANY(f.skills_extracted)")
                params[f"skill_{i}"] = skill.strip()
            where_clauses.append(f"({' OR '.join(skill_conditions)})")

        if education:
            edu_levels = education.split(",")
            placeholders = ",".join([f":edu_{i}" for i in range(len(edu_levels))])
            where_clauses.append(f"f.education_level IN ({placeholders})")
            for i, edu in enumerate(edu_levels):
                params[f"edu_{i}"] = int(edu)

        if cities:
            city_list = cities.split(",")
            placeholders = ",".join([f":city_{i}" for i in range(len(city_list))])
            where_clauses.append(f"r.nom_commune IN ({placeholders})")
            for i, city in enumerate(city_list):
                params[f"city_{i}"] = city.strip()

        if postal_codes:
            postal_list = postal_codes.split(",")
            placeholders = ",".join([f":postal_{i}" for i in range(len(postal_list))])
            where_clauses.append(f"r.code_postal IN ({placeholders})")
            for i, postal in enumerate(postal_list):
                params[f"postal_{i}"] = postal.strip()

        if experience is not None and experience > 0:
            where_clauses.append("f.experience_years >= :experience")
            params["experience"] = experience

        if date_from:
            where_clauses.append("f.published_date >= :date_from")
            params["date_from"] = date_from

        if min_salary is not None and min_salary > 0:
            where_clauses.append("f.salary_min >= :min_salary")
            params["min_salary"] = min_salary

        if search:
            where_clauses.append(
                "(LOWER(f.title) LIKE LOWER(:search) OR LOWER(f.company_name) LIKE LOWER(:search))"
            )
            params["search"] = f"%{search}%"

        where_sql = " AND " + " AND ".join(where_clauses) if where_clauses else ""

        query_text = f"""
            SELECT 
                f.offer_id, f.title, f.company_name, f.contract_type, f.description,
                s.source_name, f.published_date, f.collected_date,
                f.skills_extracted, f.profile_category, f.profile_score, 
                f.education_level, f.education_type, f.remote_possible, 
                f.remote_days, f.remote_percentage,
                r.nom_commune, r.nom_region,
                f.salary_min, f.salary_max, f.experience_years
            FROM fact_job_offers f
            LEFT JOIN dim_sources s ON f.source_id = s.source_id
            LEFT JOIN ref_communes_france r ON f.commune_id = r.commune_id
            WHERE 1=1{where_sql}
            ORDER BY f.collected_date DESC
            LIMIT :limit OFFSET :offset
        """

        result = db.execute(text(query_text), params)

        offers = []
        for row in result:
            # Construire la localisation
            location_parts = []
            if row[16]:  # nom_commune
                location_parts.append(row[16])
            if row[17]:  # nom_region
                location_parts.append(row[17])
            location = ", ".join(location_parts) if location_parts else "Non spécifié"

            offers.append(
                {
                    "offer_id": row[0],
                    "title": row[1],
                    "company_name": row[2],
                    "contract_type": row[3],
                    "description": row[4],
                    "source": row[5],
                    "published_date": row[6].isoformat() if row[6] else None,
                    "collected_date": row[7].isoformat() if row[7] else None,
                    "skills_extracted": row[8] if row[8] else [],
                    "profile_category": row[9],
                    "profile_confidence": row[10] if row[10] else 0,
                    "education_level": row[11],
                    "education_type": row[12],
                    "remote_possible": row[13] if row[13] else False,
                    "remote_days": row[14],
                    "remote_percentage": row[15],
                    "location": location,
                    "salary_min": float(row[18]) if row[18] else None,
                    "salary_max": float(row[19]) if row[19] else None,
                    "experience_years": row[20],
                }
            )

        return {"count": len(offers), "offers": offers, "total": len(offers)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/offers/list")
def list_offers_simple(db: Session = Depends(get_db)):
    """Liste simplifiée des offres (id + titre) pour les select boxes"""
    try:
        query = text(
            """
            SELECT offer_id, title, company_name
            FROM fact_job_offers
            ORDER BY collected_date DESC
        """
        )
        result = db.execute(query)
        offers = [
            {
                "offer_id": row[0],
                "title": row[1],
                "company_name": row[2],
                "display": f"{row[0]} - {row[1]} ({row[2]})",
            }
            for row in result
        ]
        return {"offers": offers, "total": len(offers)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/offers/get/{offer_id}")
def get_offer_by_id(offer_id: int, db: Session = Depends(get_db)):
    """Récupère une offre complète avec son embedding"""
    try:
        query = text(
            """
            SELECT 
                f.offer_id, f.title, f.company_name, f.description,
                f.contract_type, f.profile_category, f.skills_extracted,
                f.education_level, f.remote_possible, 
                je.embedding, je.model_name,
                s.source_name, f.published_date, f.collected_date,
                r.nom_commune, r.nom_region
            FROM fact_job_offers f
            LEFT JOIN dim_sources s ON f.source_id = s.source_id
            LEFT JOIN ref_communes_france r ON f.commune_id = r.commune_id
            LEFT JOIN job_embeddings je ON f.offer_id = je.offer_id
            WHERE f.offer_id = :offer_id
        """
        )
        result = db.execute(query, {"offer_id": offer_id})
        row = result.fetchone()

        if not row:
            raise HTTPException(status_code=404, detail="Offre non trouvée")

        # Construire la localisation
        location_parts = []
        if row[14]:  # nom_commune
            location_parts.append(row[14])
        if row[15]:  # nom_region
            location_parts.append(row[15])
        location = ", ".join(location_parts) if location_parts else "Non spécifié"

        return {
            "offer_id": row[0],
            "title": row[1],
            "company_name": row[2],
            "description": row[3],
            "contract_type": row[4],
            "profile_category": row[5],
            "skills_extracted": row[6] if row[6] else [],
            "education_level": row[7],
            "remote_possible": row[8] if row[8] else False,
            "embedding": row[9] if row[9] else None,
            "embedding_model": row[10] if row[10] else None,
            "source": row[11],
            "published_date": row[12].isoformat() if row[12] else None,
            "collected_date": row[13].isoformat() if row[13] else None,
            "location": location,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/offers/count")
def count_offers(
    source: Optional[str] = Query(None),
    contract: Optional[str] = Query(None),
    profile: Optional[str] = Query(None),
    remote: Optional[str] = Query(None),
    skills: Optional[str] = Query(None),
    education: Optional[str] = Query(None),
    cities: Optional[str] = Query(None),
    postal_codes: Optional[str] = Query(None),
    experience: Optional[int] = Query(None),
    date_from: Optional[str] = Query(None),
    min_salary: Optional[int] = Query(None),
    search: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    """Compte le nombre total d'offres avec filtres optionnels"""
    try:
        # Construction de la requête avec filtres
        where_clauses = []
        params = {}

        if source:
            sources = source.split(",")
            where_clauses.append("s.source_name IN :sources")
            params["sources"] = tuple(sources)

        if contract:
            contracts = contract.split(",")
            where_clauses.append("f.contract_type IN :contracts")
            params["contracts"] = tuple(contracts)

        if profile:
            profiles = profile.split(",")
            where_clauses.append("f.profile_category IN :profiles")
            params["profiles"] = tuple(profiles)

        if remote and remote.lower() == "true":
            where_clauses.append("f.remote_possible = TRUE")

        if skills:
            skill_list = [s.strip() for s in skills.split(",")]
            skill_conditions = []
            for i, skill in enumerate(skill_list):
                params[f"skill_{i}"] = skill
                skill_conditions.append(f":skill_{i} = ANY(f.skills_extracted)")
            where_clauses.append(f"({' OR '.join(skill_conditions)})")

        if education:
            edu_levels = [int(e) for e in education.split(",")]
            where_clauses.append("f.education_level IN :education_levels")
            params["education_levels"] = tuple(edu_levels)

        if cities:
            city_list = [c.strip() for c in cities.split(",")]
            where_clauses.append("r.nom_commune IN :cities")
            params["cities"] = tuple(city_list)

        if postal_codes:
            postal_list = [p.strip() for p in postal_codes.split(",")]
            where_clauses.append("r.code_postal IN :postal_codes")
            params["postal_codes"] = tuple(postal_list)

        if experience is not None and experience > 0:
            where_clauses.append("f.experience_years >= :experience")
            params["experience"] = experience

        if date_from:
            where_clauses.append("f.published_date >= :date_from")
            params["date_from"] = date_from

        if min_salary is not None and min_salary > 0:
            where_clauses.append("f.salary_min >= :min_salary")
            params["min_salary"] = min_salary

        if search:
            where_clauses.append(
                "(LOWER(f.title) LIKE LOWER(:search) OR LOWER(f.company_name) LIKE LOWER(:search))"
            )
            params["search"] = f"%{search}%"

        where_sql = " AND ".join(where_clauses) if where_clauses else "1=1"

        query_text = f"""
            SELECT COUNT(*)
            FROM fact_job_offers f
            LEFT JOIN dim_sources s ON f.source_id = s.source_id
            LEFT JOIN ref_communes_france r ON f.commune_id = r.commune_id
            WHERE {where_sql}
        """

        result = db.execute(text(query_text), params)
        total = result.fetchone()[0]

        return {"total": total}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
