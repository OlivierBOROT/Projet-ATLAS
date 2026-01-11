"""
Dashboard Specific Statistics Router
=====================================
Routes pour les statistiques détaillées avec filtres géographiques
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


def build_filter_clauses(
    base_clauses: list, source: str = None, contract: str = None, days: int = None
) -> tuple:
    """
    Helper function to build WHERE clauses and params for filtering

    Returns: (where_sql_string, params_dict)
    """
    where_clauses = base_clauses.copy()
    params = {}

    if source:
        where_clauses.append("s.source_name = :source")
        params["source"] = source
    if contract:
        where_clauses.append("f.contract_type = :contract")
        params["contract"] = contract
    if days:
        where_clauses.append(
            "f.published_date >= CURRENT_DATE - :days * INTERVAL '1 day'"
        )
        params["days"] = days

    where_sql = " AND ".join(where_clauses)
    return where_sql, params


@router.get("/stats/contracts-by-location")
def get_contracts_by_location(
    location_type: str = Query("city", pattern="^(city|region)$"),
    location_name: Optional[str] = Query(None),
    limit: int = Query(10, ge=1, le=50),
    source: Optional[str] = Query(None),
    contract: Optional[str] = Query(None),
    days: Optional[int] = Query(None, ge=1, le=365),
    db: Session = Depends(get_db),
):
    """
    Répartition des types de contrat par ville ou région

    Args:
        location_type: 'city' ou 'region'
        location_name: Nom de la ville ou région (optionnel, si None = top locations)
        limit: Nombre de résultats max
    """
    try:
        if location_type == "city":
            if location_name:
                # Stats pour une ville spécifique
                where_clauses = [
                    "r.nom_commune = :location_name",
                    "f.contract_type IS NOT NULL",
                ]
                params = {"location_name": location_name}

                if source:
                    where_clauses.append("s.source_name = :source")
                    params["source"] = source
                if contract:
                    where_clauses.append("f.contract_type = :contract")
                    params["contract"] = contract
                if days:
                    where_clauses.append(
                        "f.published_date >= CURRENT_DATE - :days * INTERVAL '1 day'"
                    )
                    params["days"] = days

                where_sql = " AND ".join(where_clauses)

                query = text(
                    f"""
                    SELECT 
                        f.contract_type,
                        COUNT(*) as total
                    FROM fact_job_offers f
                    JOIN ref_communes_france r ON f.commune_id = r.commune_id
                    JOIN dim_sources s ON f.source_id = s.source_id
                    WHERE {where_sql}
                    GROUP BY f.contract_type
                    ORDER BY total DESC
                """
                )
                result = db.execute(query, params)
            else:
                # Top villes avec répartition des contrats
                where_clauses_top = ["r.nom_commune IS NOT NULL"]
                where_clauses_main = [
                    "r.nom_commune IN (SELECT nom_commune FROM top_cities)",
                    "f.contract_type IS NOT NULL",
                ]
                params = {"limit": limit}

                if source:
                    where_clauses_top.append("s.source_name = :source")
                    where_clauses_main.append("s.source_name = :source")
                    params["source"] = source
                if contract:
                    where_clauses_top.append("f.contract_type = :contract")
                    where_clauses_main.append("f.contract_type = :contract")
                    params["contract"] = contract
                if days:
                    where_clauses_top.append(
                        "f.published_date >= CURRENT_DATE - :days * INTERVAL '1 day'"
                    )
                    where_clauses_main.append(
                        "f.published_date >= CURRENT_DATE - :days * INTERVAL '1 day'"
                    )
                    params["days"] = days

                where_sql_top = " AND ".join(where_clauses_top)
                where_sql_main = " AND ".join(where_clauses_main)

                query = text(
                    f"""
                    WITH top_cities AS (
                        SELECT r.nom_commune, COUNT(*) as city_total
                        FROM fact_job_offers f
                        JOIN ref_communes_france r ON f.commune_id = r.commune_id
                        JOIN dim_sources s ON f.source_id = s.source_id
                        WHERE {where_sql_top}
                        GROUP BY r.nom_commune
                        ORDER BY city_total DESC
                        LIMIT :limit
                    )
                    SELECT 
                        r.nom_commune as location,
                        f.contract_type,
                        COUNT(*) as total
                    FROM fact_job_offers f
                    JOIN ref_communes_france r ON f.commune_id = r.commune_id
                    JOIN dim_sources s ON f.source_id = s.source_id
                    WHERE {where_sql_main}
                    GROUP BY r.nom_commune, f.contract_type
                    ORDER BY COUNT(*) DESC
                """
                )
                result = db.execute(query, params)
        else:  # region
            if location_name:
                # Stats pour une région spécifique
                where_clauses = [
                    "r.nom_region = :location_name",
                    "f.contract_type IS NOT NULL",
                ]
                params = {"location_name": location_name}

                if source:
                    where_clauses.append("s.source_name = :source")
                    params["source"] = source
                if contract:
                    where_clauses.append("f.contract_type = :contract")
                    params["contract"] = contract
                if days:
                    where_clauses.append(
                        "f.published_date >= CURRENT_DATE - :days * INTERVAL '1 day'"
                    )
                    params["days"] = days

                where_sql = " AND ".join(where_clauses)

                query = text(
                    f"""
                    SELECT 
                        f.contract_type,
                        COUNT(*) as total
                    FROM fact_job_offers f
                    JOIN ref_communes_france r ON f.commune_id = r.commune_id
                    JOIN dim_sources s ON f.source_id = s.source_id
                    WHERE {where_sql}
                    GROUP BY f.contract_type
                    ORDER BY total DESC
                """
                )
                result = db.execute(query, params)
            else:
                # Toutes les régions avec répartition des contrats
                where_clauses = [
                    "r.nom_region IS NOT NULL",
                    "f.contract_type IS NOT NULL",
                ]
                params = {}

                if source:
                    where_clauses.append("s.source_name = :source")
                    params["source"] = source
                if contract:
                    where_clauses.append("f.contract_type = :contract")
                    params["contract"] = contract
                if days:
                    where_clauses.append(
                        "f.published_date >= CURRENT_DATE - :days * INTERVAL '1 day'"
                    )
                    params["days"] = days

                where_sql = " AND ".join(where_clauses)

                query = text(
                    f"""
                    SELECT 
                        r.nom_region as location,
                        f.contract_type,
                        COUNT(*) as total
                    FROM fact_job_offers f
                    JOIN ref_communes_france r ON f.commune_id = r.commune_id
                    JOIN dim_sources s ON f.source_id = s.source_id
                    WHERE {where_sql}
                    GROUP BY r.nom_region, f.contract_type
                    ORDER BY r.nom_region, total DESC
                """
                )
                result = db.execute(query, params)

        if location_name:
            # Format simple pour une localisation spécifique
            data = [{"contract": row[0], "count": row[1]} for row in result]
            return {
                "location": location_name,
                "location_type": location_type,
                "data": data,
            }
        else:
            # Format groupé par localisation
            data_by_location = {}
            for row in result:
                location = row[0]
                contract = row[1]
                count = row[2]

                if location not in data_by_location:
                    data_by_location[location] = []
                data_by_location[location].append(
                    {"contract": contract, "count": count}
                )

            return {"location_type": location_type, "data": data_by_location}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats/profiles-by-location")
def get_profiles_by_location(
    location_type: str = Query("city", pattern="^(city|region)$"),
    location_name: Optional[str] = Query(None),
    limit: int = Query(15, ge=1, le=50),
    source: Optional[str] = Query(None),
    contract: Optional[str] = Query(None),
    days: Optional[int] = Query(None, ge=1, le=365),
    db: Session = Depends(get_db),
):
    """
    Métiers les plus recherchés par ville ou région

    Args:
        location_type: 'city' ou 'region'
        location_name: Nom de la ville ou région (optionnel)
        limit: Nombre de métiers à retourner
    """
    try:
        if location_type == "city":
            if location_name:
                where_clauses = [
                    "r.nom_commune = :location_name",
                    "f.profile_category IS NOT NULL",
                ]
                params = {"location_name": location_name, "limit": limit}

                if source:
                    where_clauses.append("s.source_name = :source")
                    params["source"] = source
                if contract:
                    where_clauses.append("f.contract_type = :contract")
                    params["contract"] = contract
                if days:
                    where_clauses.append(
                        "f.published_date >= CURRENT_DATE - :days * INTERVAL '1 day'"
                    )
                    params["days"] = days

                where_sql = " AND ".join(where_clauses)

                query = text(
                    f"""
                    SELECT 
                        f.profile_category,
                        COUNT(*) as total
                    FROM fact_job_offers f
                    JOIN ref_communes_france r ON f.commune_id = r.commune_id
                    JOIN dim_sources s ON f.source_id = s.source_id
                    WHERE {where_sql}
                    GROUP BY f.profile_category
                    ORDER BY total DESC
                    LIMIT :limit
                """
                )
                result = db.execute(query, params)
            else:
                # Top métiers pour chaque ville (top 10 villes)
                where_clauses_top = ["r.nom_commune IS NOT NULL"]
                where_clauses_main = ["f.profile_category IS NOT NULL"]
                params = {}

                if source:
                    where_clauses_top.append("s.source_name = :source")
                    where_clauses_main.append("s.source_name = :source")
                    params["source"] = source
                if contract:
                    where_clauses_top.append("f.contract_type = :contract")
                    where_clauses_main.append("f.contract_type = :contract")
                    params["contract"] = contract
                if days:
                    where_clauses_top.append(
                        "f.published_date >= CURRENT_DATE - :days * INTERVAL '1 day'"
                    )
                    where_clauses_main.append(
                        "f.published_date >= CURRENT_DATE - :days * INTERVAL '1 day'"
                    )
                    params["days"] = days

                where_sql_top = " AND ".join(where_clauses_top)
                where_sql_main = " AND ".join(where_clauses_main)

                query = text(
                    f"""
                    WITH top_cities AS (
                        SELECT r.nom_commune, COUNT(*) as city_total
                        FROM fact_job_offers f
                        JOIN ref_communes_france r ON f.commune_id = r.commune_id
                        JOIN dim_sources s ON f.source_id = s.source_id
                        WHERE {where_sql_top}
                        GROUP BY r.nom_commune
                        ORDER BY city_total DESC
                        LIMIT 10
                    )
                    SELECT 
                        r.nom_commune as location,
                        f.profile_category,
                        COUNT(*) as total
                    FROM fact_job_offers f
                    JOIN ref_communes_france r ON f.commune_id = r.commune_id
                    JOIN dim_sources s ON f.source_id = s.source_id
                    JOIN top_cities tc ON r.nom_commune = tc.nom_commune
                    WHERE {where_sql_main}
                    GROUP BY r.nom_commune, f.profile_category
                    ORDER BY r.nom_commune, total DESC
                """
                )
                result = db.execute(query, params)
        else:  # region
            if location_name:
                where_clauses = [
                    "r.nom_region = :location_name",
                    "f.profile_category IS NOT NULL",
                ]
                params = {"location_name": location_name, "limit": limit}

                if source:
                    where_clauses.append("s.source_name = :source")
                    params["source"] = source
                if contract:
                    where_clauses.append("f.contract_type = :contract")
                    params["contract"] = contract
                if days:
                    where_clauses.append(
                        "f.published_date >= CURRENT_DATE - :days * INTERVAL '1 day'"
                    )
                    params["days"] = days

                where_sql = " AND ".join(where_clauses)

                query = text(
                    f"""
                    SELECT 
                        f.profile_category,
                        COUNT(*) as total
                    FROM fact_job_offers f
                    JOIN ref_communes_france r ON f.commune_id = r.commune_id
                    JOIN dim_sources s ON f.source_id = s.source_id
                    WHERE {where_sql}
                    GROUP BY f.profile_category
                    ORDER BY total DESC
                    LIMIT :limit
                """
                )
                result = db.execute(query, params)
            else:
                # Top métiers pour chaque région
                where_clauses = [
                    "r.nom_region IS NOT NULL",
                    "f.profile_category IS NOT NULL",
                ]
                params = {}

                if source:
                    where_clauses.append("s.source_name = :source")
                    params["source"] = source
                if contract:
                    where_clauses.append("f.contract_type = :contract")
                    params["contract"] = contract
                if days:
                    where_clauses.append(
                        "f.published_date >= CURRENT_DATE - :days * INTERVAL '1 day'"
                    )
                    params["days"] = days

                where_sql = " AND ".join(where_clauses)

                query = text(
                    f"""
                    SELECT 
                        r.nom_region as location,
                        f.profile_category,
                        COUNT(*) as total
                    FROM fact_job_offers f
                    JOIN ref_communes_france r ON f.commune_id = r.commune_id
                    JOIN dim_sources s ON f.source_id = s.source_id
                    WHERE {where_sql}
                    GROUP BY r.nom_region, f.profile_category
                    ORDER BY r.nom_region, total DESC
                """
                )
                result = db.execute(query, params)

        if location_name:
            # Format simple
            data = [{"profile": row[0], "count": row[1]} for row in result]
            return {
                "location": location_name,
                "location_type": location_type,
                "data": data,
            }
        else:
            # Format groupé
            data_by_location = {}
            for row in result:
                location = row[0]
                profile = row[1]
                count = row[2]

                if location not in data_by_location:
                    data_by_location[location] = []
                # Limiter à 'limit' métiers par localisation
                if len(data_by_location[location]) < limit:
                    data_by_location[location].append(
                        {"profile": profile, "count": count}
                    )

            return {"location_type": location_type, "data": data_by_location}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats/salaries-by-location")
def get_salaries_by_location(
    location_type: str = Query("city", pattern="^(city|region)$"),
    location_name: Optional[str] = Query(None),
    limit: int = Query(10, ge=1, le=50),
    source: Optional[str] = Query(None),
    contract: Optional[str] = Query(None),
    days: Optional[int] = Query(None, ge=1, le=365),
    db: Session = Depends(get_db),
):
    """
    Statistiques de salaires par ville ou région

    Args:
        location_type: 'city' ou 'region'
        location_name: Nom de la ville ou région (optionnel)
        limit: Nombre de localisations à retourner
    """
    try:
        if location_type == "city":
            if location_name:
                # Stats salaires pour une ville
                where_clauses = [
                    "r.nom_commune = :location_name",
                    "f.salary_min IS NOT NULL",
                    "f.salary_max IS NOT NULL",
                    "f.salary_min > 0",
                ]
                params = {"location_name": location_name}

                if source:
                    where_clauses.append("s.source_name = :source")
                    params["source"] = source
                if contract:
                    where_clauses.append("f.contract_type = :contract")
                    params["contract"] = contract
                if days:
                    where_clauses.append(
                        "f.published_date >= CURRENT_DATE - :days * INTERVAL '1 day'"
                    )
                    params["days"] = days

                where_sql = " AND ".join(where_clauses)

                query = text(
                    f"""
                    SELECT 
                        ROUND(AVG(f.salary_min)) as avg_min,
                        ROUND(AVG(f.salary_max)) as avg_max,
                        ROUND(AVG((f.salary_min + f.salary_max) / 2)) as avg_salary,
                        MIN(f.salary_min) as min_salary,
                        MAX(f.salary_max) as max_salary,
                        COUNT(*) as offers_with_salary
                    FROM fact_job_offers f
                    JOIN ref_communes_france r ON f.commune_id = r.commune_id
                    JOIN dim_sources s ON f.source_id = s.source_id
                    WHERE {where_sql}
                """
                )
                result = db.execute(query, params)
                row = result.fetchone()

                if row and row[5] > 0:
                    return {
                        "location": location_name,
                        "location_type": location_type,
                        "avg_min": float(row[0]) if row[0] else 0,
                        "avg_max": float(row[1]) if row[1] else 0,
                        "avg_salary": float(row[2]) if row[2] else 0,
                        "min_salary": float(row[3]) if row[3] else 0,
                        "max_salary": float(row[4]) if row[4] else 0,
                        "offers_count": row[5],
                    }
                else:
                    return {
                        "location": location_name,
                        "location_type": location_type,
                        "offers_count": 0,
                    }
            else:
                # Top villes avec salaires moyens
                where_clauses = [
                    "r.nom_commune IS NOT NULL",
                    "f.salary_min IS NOT NULL",
                    "f.salary_max IS NOT NULL",
                    "f.salary_min > 0",
                ]
                params = {"limit": limit}

                if source:
                    where_clauses.append("s.source_name = :source")
                    params["source"] = source
                if contract:
                    where_clauses.append("f.contract_type = :contract")
                    params["contract"] = contract
                if days:
                    where_clauses.append(
                        "f.published_date >= CURRENT_DATE - :days * INTERVAL '1 day'"
                    )
                    params["days"] = days

                where_sql = " AND ".join(where_clauses)

                query = text(
                    f"""
                    SELECT 
                        r.nom_commune as location,
                        ROUND(AVG((f.salary_min + f.salary_max) / 2)) as avg_salary,
                        COUNT(*) as offers_count
                    FROM fact_job_offers f
                    JOIN ref_communes_france r ON f.commune_id = r.commune_id
                    JOIN dim_sources s ON f.source_id = s.source_id
                    WHERE {where_sql}
                    GROUP BY r.nom_commune
                    HAVING COUNT(*) >= 3
                    ORDER BY avg_salary DESC
                    LIMIT :limit
                """
                )
                result = db.execute(query, params)
        else:  # region
            if location_name:
                # Stats salaires pour une région
                where_clauses = [
                    "r.nom_region = :location_name",
                    "f.salary_min IS NOT NULL",
                    "f.salary_max IS NOT NULL",
                    "f.salary_min > 0",
                ]
                params = {"location_name": location_name}

                if source:
                    where_clauses.append("s.source_name = :source")
                    params["source"] = source
                if contract:
                    where_clauses.append("f.contract_type = :contract")
                    params["contract"] = contract
                if days:
                    where_clauses.append(
                        "f.published_date >= CURRENT_DATE - :days * INTERVAL '1 day'"
                    )
                    params["days"] = days

                where_sql = " AND ".join(where_clauses)

                query = text(
                    f"""
                    SELECT 
                        ROUND(AVG(f.salary_min)) as avg_min,
                        ROUND(AVG(f.salary_max)) as avg_max,
                        ROUND(AVG((f.salary_min + f.salary_max) / 2)) as avg_salary,
                        MIN(f.salary_min) as min_salary,
                        MAX(f.salary_max) as max_salary,
                        COUNT(*) as offers_with_salary
                    FROM fact_job_offers f
                    JOIN ref_communes_france r ON f.commune_id = r.commune_id
                    JOIN dim_sources s ON f.source_id = s.source_id
                    WHERE {where_sql}
                """
                )
                result = db.execute(query, params)
                row = result.fetchone()

                if row and row[5] > 0:
                    return {
                        "location": location_name,
                        "location_type": location_type,
                        "avg_min": float(row[0]) if row[0] else 0,
                        "avg_max": float(row[1]) if row[1] else 0,
                        "avg_salary": float(row[2]) if row[2] else 0,
                        "min_salary": float(row[3]) if row[3] else 0,
                        "max_salary": float(row[4]) if row[4] else 0,
                        "offers_count": row[5],
                    }
                else:
                    return {
                        "location": location_name,
                        "location_type": location_type,
                        "offers_count": 0,
                    }
            else:
                # Toutes les régions avec salaires moyens
                where_clauses = [
                    "r.nom_region IS NOT NULL",
                    "f.salary_min IS NOT NULL",
                    "f.salary_max IS NOT NULL",
                    "f.salary_min > 0",
                ]
                params = {}

                if source:
                    where_clauses.append("s.source_name = :source")
                    params["source"] = source
                if contract:
                    where_clauses.append("f.contract_type = :contract")
                    params["contract"] = contract
                if days:
                    where_clauses.append(
                        "f.published_date >= CURRENT_DATE - :days * INTERVAL '1 day'"
                    )
                    params["days"] = days

                where_sql = " AND ".join(where_clauses)

                query = text(
                    f"""
                    SELECT 
                        r.nom_region as location,
                        ROUND(AVG((f.salary_min + f.salary_max) / 2)) as avg_salary,
                        COUNT(*) as offers_count
                    FROM fact_job_offers f
                    JOIN ref_communes_france r ON f.commune_id = r.commune_id
                    JOIN dim_sources s ON f.source_id = s.source_id
                    WHERE {where_sql}
                    GROUP BY r.nom_region
                    ORDER BY avg_salary DESC
                """
                )
                result = db.execute(query, params)

        if location_name:
            # Déjà retourné dans les if ci-dessus
            pass
        else:
            # Format liste
            data = [
                {
                    "location": row[0],
                    "avg_salary": float(row[1]) if row[1] else 0,
                    "offers_count": row[2],
                }
                for row in result
            ]
            return {"location_type": location_type, "data": data}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats/available-locations")
def get_available_locations(
    location_type: str = Query("city", pattern="^(city|region)$"),
    db: Session = Depends(get_db),
):
    """
    Liste des villes ou régions disponibles avec nombre d'offres

    Args:
        location_type: 'city' ou 'region'
    """
    try:
        if location_type == "city":
            query = text(
                """
                SELECT r.nom_commune as location, COUNT(*) as count
                FROM fact_job_offers f
                JOIN ref_communes_france r ON f.commune_id = r.commune_id
                WHERE r.nom_commune IS NOT NULL
                GROUP BY r.nom_commune
                ORDER BY count DESC, location
            """
            )
        else:  # region
            query = text(
                """
                SELECT r.nom_region as location, COUNT(*) as count
                FROM fact_job_offers f
                JOIN ref_communes_france r ON f.commune_id = r.commune_id
                WHERE r.nom_region IS NOT NULL
                GROUP BY r.nom_region
                ORDER BY count DESC, location
            """
            )

        result = db.execute(query)
        locations = [{"name": row[0], "count": row[1]} for row in result]

        return {
            "location_type": location_type,
            "locations": locations,
            "total": len(locations),
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
