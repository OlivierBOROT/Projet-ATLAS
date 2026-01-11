"""
Router pour la gestion de la carte géographique
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


@router.get("/map-data")
def get_map_data(
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
    """Données géographiques pour la carte (offres groupées par ville avec GPS)"""
    try:
        # Construction des filtres WHERE
        where_clauses = []
        params = {}

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
                r.nom_commune,
                r.nom_region,
                r.latitude,
                r.longitude,
                COUNT(*) as total_offers,
                ARRAY_AGG(DISTINCT f.profile_category) FILTER (WHERE f.profile_category IS NOT NULL) as profiles,
                ARRAY_AGG(DISTINCT f.contract_type) FILTER (WHERE f.contract_type IS NOT NULL) as contracts
            FROM fact_job_offers f
            LEFT JOIN dim_sources s ON f.source_id = s.source_id
            JOIN ref_communes_france r ON f.commune_id = r.commune_id
            WHERE r.latitude IS NOT NULL 
              AND r.longitude IS NOT NULL{where_sql}
            GROUP BY r.nom_commune, r.nom_region, r.latitude, r.longitude
            ORDER BY total_offers DESC
        """

        result = db.execute(text(query_text), params)

        cities = []
        for row in result:
            cities.append(
                {
                    "city": row[0],
                    "region": row[1],
                    "lat": float(row[2]),
                    "lon": float(row[3]),
                    "count": row[4],
                    "profiles": row[5] if row[5] else [],
                    "contracts": row[6] if row[6] else [],
                }
            )

        return {"cities": cities, "total": len(cities)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
