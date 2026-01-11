"""
Dashboard Collected Offers Router
==================================
Routes pour les offres collectées avec filtres avancés
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


@router.get("/offers/collected")
def get_collected_offers(
    limit: int = Query(25, ge=1, le=100),
    offset: int = Query(0, ge=0),
    source: Optional[str] = Query(None),
    contract: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    sort_by: Optional[str] = Query("date", pattern="^(date|ville|metier|salaire)$"),
    days: Optional[int] = Query(None, ge=1, le=365),
    db: Session = Depends(get_db),
):
    """
    Récupère les dernières offres collectées avec filtres avancés

    Args:
        limit: Nombre d'offres à retourner
        offset: Décalage pour la pagination
        source: Filtrer par source (france_travail ou welcome_to_the_jungle)
        contract: Filtrer par type de contrat
        search: Recherche par mot-clé dans le titre ou l'entreprise
        sort_by: Trier par date, ville, metier ou salaire
        days: Limiter aux N derniers jours
    """
    try:
        # Construire les clauses WHERE
        where_clauses = ["1=1"]
        params = {"limit": limit, "offset": offset}

        if source:
            where_clauses.append("s.source_name = :source")
            params["source"] = source

        if contract:
            where_clauses.append("f.contract_type = :contract")
            params["contract"] = contract

        if search:
            where_clauses.append(
                "(LOWER(f.title) LIKE LOWER(:search) OR LOWER(f.company_name) LIKE LOWER(:search))"
            )
            params["search"] = f"%{search}%"

        if days:
            where_clauses.append(
                "f.collected_date >= CURRENT_DATE - :days * INTERVAL '1 day'"
            )
            params["days"] = days

        where_sql = " AND ".join(where_clauses)

        # Construire l'ORDER BY
        order_mapping = {
            "date": "f.collected_date DESC",
            "ville": "r.nom_commune ASC",
            "metier": "f.profile_category ASC",
            "salaire": "f.salary_min DESC NULLS LAST",
        }
        order_sql = order_mapping.get(sort_by, "f.collected_date DESC")

        # Requête principale
        query = text(
            f"""
            SELECT 
                f.offer_id,
                f.title,
                f.company_name,
                f.contract_type,
                f.description,
                s.source_name,
                f.published_date,
                f.collected_date,
                f.skills_extracted,
                f.profile_category,
                f.profile_confidence,
                f.education_level,
                f.education_type,
                f.remote_possible,
                f.remote_days,
                f.remote_percentage,
                r.nom_commune,
                r.nom_region,
                f.salary_min,
                f.salary_max,
                f.experience_years,
                f.url
            FROM fact_job_offers f
            LEFT JOIN dim_sources s ON f.source_id = s.source_id
            LEFT JOIN ref_communes_france r ON f.commune_id = r.commune_id
            WHERE {where_sql}
            ORDER BY {order_sql}
            LIMIT :limit OFFSET :offset
        """
        )

        result = db.execute(query, params)

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
                    "url": row[21],
                }
            )

        # Compter le total pour la pagination
        count_query = text(
            f"""
            SELECT COUNT(*)
            FROM fact_job_offers f
            LEFT JOIN dim_sources s ON f.source_id = s.source_id
            LEFT JOIN ref_communes_france r ON f.commune_id = r.commune_id
            WHERE {where_sql}
        """
        )

        count_result = db.execute(
            count_query,
            {k: v for k, v in params.items() if k not in ["limit", "offset"]},
        )
        total = count_result.fetchone()[0]

        return {
            "offers": offers,
            "total": total,
            "limit": limit,
            "offset": offset,
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
