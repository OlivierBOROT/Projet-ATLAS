"""
ATLAS API - FastAPI Backend
============================

API REST pour l'analyse textuelle des offres d'emploi.
"""

from fastapi import FastAPI, Depends, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session
from typing import List, Dict, Optional
import os
from datetime import datetime
from dotenv import load_dotenv

# Charger les variables d'environnement
load_dotenv()

# Configuration - Utilise Supabase
DATABASE_URL = os.getenv("DATABASE_URL")

# Engine SQLAlchemy
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# FastAPI app
app = FastAPI(
    title="ATLAS API",
    description="API d'analyse textuelle et localisation des annonces spécialisées",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@app.get("/")
def root():
    return {
        "project": "ATLAS",
        "status": "running",
        "version": "1.0.0",
        "docs": "/docs",
    }


@app.get("/health")
def health_check(db: Session = Depends(get_db)):
    try:
        db.execute(text("SELECT 1"))
        return {"status": "healthy", "database": "connected"}
    except:
        return {"status": "unhealthy", "database": "disconnected"}


@app.get("/api/stats")
def get_stats(db: Session = Depends(get_db)):
    try:
        result = db.execute(text("SELECT COUNT(*) FROM fact_job_offers"))
        total_offers = result.fetchone()[0]

        result = db.execute(text("SELECT COUNT(DISTINCT region) FROM dim_locations"))
        total_regions = result.fetchone()[0]

        return {
            "total_offers": total_offers,
            "total_regions": total_regions,
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        return {"total_offers": 0, "total_regions": 13, "error": str(e)}


@app.get("/api/offers")
def get_offers(
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    source: Optional[str] = Query(None),
    contract: Optional[str] = Query(None),
    profile: Optional[str] = Query(None),
    remote: Optional[str] = Query(None),
    skills: Optional[str] = Query(None),
    education: Optional[str] = Query(None),
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

        where_sql = " AND " + " AND ".join(where_clauses) if where_clauses else ""

        query_text = f"""
            SELECT 
                f.offer_id, f.title, f.company_name, f.contract_type, f.description,
                s.source_name, f.published_date, f.collected_date,
                f.skills_extracted, f.profile_category, f.profile_score, 
                f.education_level, f.education_type, f.remote_possible, 
                f.remote_days, f.remote_percentage
            FROM fact_job_offers f
            LEFT JOIN dim_sources s ON f.source_id = s.source_id
            WHERE 1=1{where_sql}
            ORDER BY f.collected_date DESC
            LIMIT :limit OFFSET :offset
        """

        result = db.execute(text(query_text), params)

        offers = []
        for row in result:
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
                    "location": "",
                }
            )

        return {"count": len(offers), "offers": offers, "total": len(offers)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/offers/count")
def count_offers(
    source: Optional[str] = Query(None),
    contract: Optional[str] = Query(None),
    profile: Optional[str] = Query(None),
    remote: Optional[str] = Query(None),
    skills: Optional[str] = Query(None),
    education: Optional[str] = Query(None),
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

        where_sql = " AND ".join(where_clauses) if where_clauses else "1=1"

        query_text = f"""
            SELECT COUNT(*)
            FROM fact_job_offers f
            LEFT JOIN dim_sources s ON f.source_id = s.source_id
            WHERE {where_sql}
        """

        result = db.execute(text(query_text), params)
        total = result.fetchone()[0]

        return {"total": total}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/regions")
def get_regions_stats(db: Session = Depends(get_db)):
    try:
        query = text(
            """
            SELECT l.region, COUNT(*) as total
            FROM fact_job_offers f
            JOIN dim_locations l ON f.location_id = l.location_id
            WHERE l.region IS NOT NULL
            GROUP BY l.region
            ORDER BY total DESC
        """
        )

        result = db.execute(query)
        regions = [{"region": row[0], "count": row[1]} for row in result]

        return {"regions": regions}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
