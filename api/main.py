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

# Import des routers (compatible local et Docker)
try:
    # Import pour exécution locale (python -m uvicorn api.main:app)
    from api.routers import scraper, glassdoor, map, dashboard_specific_statistics
except (ModuleNotFoundError, ImportError):
    # Import pour Docker (WORKDIR /app, structure aplatie)
    from routers import scraper, glassdoor, map, dashboard_specific_statistics

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

# Inclure les routers
app.include_router(scraper.router, prefix="/api", tags=["scraping"])
app.include_router(glassdoor.router, prefix="/api", tags=["glassdoor"])
app.include_router(map.router, prefix="/api", tags=["map"])
app.include_router(
    dashboard_specific_statistics.router, prefix="/api", tags=["dashboard"]
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

        result = db.execute(
            text(
                "SELECT COUNT(DISTINCT nom_region) FROM ref_communes_france WHERE nom_region IS NOT NULL"
            )
        )
        total_regions = result.fetchone()[0]

        result = db.execute(
            text(
                "SELECT COUNT(DISTINCT nom_commune) FROM ref_communes_france WHERE nom_commune IS NOT NULL"
            )
        )
        total_locations = result.fetchone()[0]

        result = db.execute(
            text(
                "SELECT COUNT(DISTINCT profile_category) FROM fact_job_offers WHERE profile_category IS NOT NULL"
            )
        )
        total_metiers = result.fetchone()[0]

        return {
            "total_offers": total_offers,
            "total_regions": total_regions,
            "total_locations": total_locations,
            "total_metiers": total_metiers,
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        return {
            "total_offers": 0,
            "total_regions": 0,
            "total_locations": 0,
            "total_metiers": 0,
            "error": str(e),
        }


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
    cities: Optional[str] = Query(None),
    postal_codes: Optional[str] = Query(None),
    experience: Optional[int] = Query(None),
    date_from: Optional[str] = Query(None),
    min_salary: Optional[int] = Query(None),
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


@app.get("/api/offers/list")
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


@app.get("/api/offers/get/{offer_id}")
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


@app.get("/api/offers/count")
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


@app.get("/api/regions")
def get_regions_stats(db: Session = Depends(get_db)):
    try:
        query = text(
            """
            SELECT r.nom_region, COUNT(*) as total
            FROM fact_job_offers f
            JOIN ref_communes_france r ON f.commune_id = r.commune_id
            WHERE r.nom_region IS NOT NULL
            GROUP BY r.nom_region
            ORDER BY total DESC
        """
        )

        result = db.execute(query)
        regions = [{"region": row[0], "count": row[1]} for row in result]

        return {"regions": regions}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/sources")
def get_sources_stats(db: Session = Depends(get_db)):
    """Statistiques par source"""
    try:
        query = text(
            """
            SELECT s.source_name, COUNT(*) as total
            FROM fact_job_offers f
            JOIN dim_sources s ON f.source_id = s.source_id
            GROUP BY s.source_name
            ORDER BY total DESC
        """
        )
        result = db.execute(query)
        sources = [{"source": row[0], "count": row[1]} for row in result]
        return {"sources": sources}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/contracts")
def get_contracts_stats(db: Session = Depends(get_db)):
    """Statistiques par type de contrat"""
    try:
        query = text(
            """
            SELECT contract_type, COUNT(*) as total
            FROM fact_job_offers
            WHERE contract_type IS NOT NULL
            GROUP BY contract_type
            ORDER BY total DESC
        """
        )
        result = db.execute(query)
        contracts = [{"contract": row[0], "count": row[1]} for row in result]
        return {"contracts": contracts}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/cities")
def get_cities_stats(db: Session = Depends(get_db)):
    """Top villes avec le plus d'offres"""
    try:
        query = text(
            """
            SELECT r.nom_commune, COUNT(*) as total
            FROM fact_job_offers f
            JOIN ref_communes_france r ON f.commune_id = r.commune_id
            WHERE r.nom_commune IS NOT NULL
            GROUP BY r.nom_commune
            ORDER BY total DESC
            LIMIT 10
        """
        )
        result = db.execute(query)
        cities = [{"city": row[0], "count": row[1]} for row in result]
        return {"cities": cities}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/cities/list")
def get_cities_list(db: Session = Depends(get_db)):
    """Liste de toutes les villes avec des offres pour le filtre"""
    try:
        query = text(
            """
            SELECT DISTINCT r.nom_commune
            FROM fact_job_offers f
            JOIN ref_communes_france r ON f.commune_id = r.commune_id
            WHERE r.nom_commune IS NOT NULL
            ORDER BY r.nom_commune
        """
        )
        result = db.execute(query)
        cities = [row[0] for row in result]
        return {"cities": cities, "total": len(cities)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/profiles")
def get_profiles_stats(db: Session = Depends(get_db)):
    """Top métiers/profils les plus demandés"""
    try:
        query = text(
            """
            SELECT profile_category, COUNT(*) as total
            FROM fact_job_offers
            WHERE profile_category IS NOT NULL
            GROUP BY profile_category
            ORDER BY total DESC
            LIMIT 15
        """
        )
        result = db.execute(query)
        profiles = [{"profile": row[0], "count": row[1]} for row in result]
        return {"profiles": profiles}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/salaries")
def get_salaries_stats(db: Session = Depends(get_db)):
    """Statistiques sur les salaires"""
    try:
        # Distribution par tranche
        query_ranges = text(
            """
            SELECT 
                CASE 
                    WHEN salary_min < 30 THEN '20-30K'
                    WHEN salary_min < 40 THEN '30-40K'
                    WHEN salary_min < 50 THEN '40-50K'
                    WHEN salary_min < 60 THEN '50-60K'
                    ELSE '60K+'
                END as range,
                COUNT(*) as total
            FROM fact_job_offers
            WHERE salary_min IS NOT NULL AND salary_min > 0
            GROUP BY range
            ORDER BY range
        """
        )
        result_ranges = db.execute(query_ranges)
        ranges = [{"range": row[0], "count": row[1]} for row in result_ranges]

        # Salaire moyen par profil
        query_avg = text(
            """
            SELECT profile_category, 
                   ROUND(AVG((salary_min + salary_max) / 2)) as avg_salary
            FROM fact_job_offers
            WHERE profile_category IS NOT NULL 
              AND salary_min IS NOT NULL 
              AND salary_max IS NOT NULL
              AND salary_min > 0
            GROUP BY profile_category
            ORDER BY avg_salary DESC
            LIMIT 5
        """
        )
        result_avg = db.execute(query_avg)
        avg_by_profile = [
            {"profile": row[0], "avg_salary": row[1]} for row in result_avg
        ]

        return {"ranges": ranges, "avg_by_profile": avg_by_profile}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/timeline")
def get_timeline_stats(db: Session = Depends(get_db)):
    """Timeline des publications sur les 30 derniers jours"""
    try:
        query = text(
            """
            SELECT DATE(published_date) as date, COUNT(*) as total
            FROM fact_job_offers
            WHERE published_date >= CURRENT_DATE - INTERVAL '30 days'
              AND published_date IS NOT NULL
            GROUP BY DATE(published_date)
            ORDER BY date
        """
        )
        result = db.execute(query)
        timeline = [{"date": row[0].isoformat(), "count": row[1]} for row in result]
        return {"timeline": timeline}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/advanced-stats")
def get_advanced_stats(db: Session = Depends(get_db)):
    """Statistiques avancées"""
    try:
        # Taux de remplissage salaire
        query_salary_rate = text(
            """
            SELECT 
                ROUND(100.0 * COUNT(CASE WHEN salary_min IS NOT NULL AND salary_min > 0 THEN 1 END) / COUNT(*), 1) as rate
            FROM fact_job_offers
        """
        )
        result = db.execute(query_salary_rate)
        salary_fill_rate = result.fetchone()[0]

        # Délai moyen de publication (jours entre publication et collecte)
        query_avg_delay = text(
            """
            SELECT ROUND(AVG(EXTRACT(DAY FROM (collected_date - published_date)))) as avg_delay
            FROM fact_job_offers
            WHERE published_date IS NOT NULL AND collected_date IS NOT NULL
        """
        )
        result = db.execute(query_avg_delay)
        avg_delay = result.fetchone()[0]

        # Pourcentage d'offres avec télétravail
        query_remote_rate = text(
            """
            SELECT 
                ROUND(100.0 * COUNT(CASE WHEN remote_possible = TRUE THEN 1 END) / COUNT(*), 1) as rate
            FROM fact_job_offers
        """
        )
        result = db.execute(query_remote_rate)
        remote_rate = result.fetchone()[0]

        return {
            "salary_fill_rate": salary_fill_rate if salary_fill_rate else 0,
            "avg_publication_delay": int(avg_delay) if avg_delay else 0,
            "remote_rate": remote_rate if remote_rate else 0,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/trends/profiles")
def get_profile_trends(
    days: int = Query(30, ge=7, le=365),
    limit: int = Query(10, ge=1, le=50),
    db: Session = Depends(get_db),
):
    """Évolution des métiers les plus demandés sur N jours"""
    try:
        query = text(
            """
            WITH profile_timeline AS (
                SELECT 
                    DATE(published_date) as date,
                    profile_category,
                    COUNT(*) as count
                FROM fact_job_offers
                WHERE published_date >= CURRENT_DATE - INTERVAL ':days days'
                  AND published_date IS NOT NULL
                  AND profile_category IS NOT NULL
                GROUP BY DATE(published_date), profile_category
            ),
            top_profiles AS (
                SELECT profile_category, SUM(count) as total
                FROM profile_timeline
                GROUP BY profile_category
                ORDER BY total DESC
                LIMIT :limit
            )
            SELECT 
                pt.date,
                pt.profile_category,
                pt.count
            FROM profile_timeline pt
            JOIN top_profiles tp ON pt.profile_category = tp.profile_category
            ORDER BY pt.date, tp.total DESC
        """
        )

        result = db.execute(query, {"days": days, "limit": limit})

        trends = {}
        for row in result:
            date_str = row[0].isoformat()
            profile = row[1]
            count = row[2]

            if profile not in trends:
                trends[profile] = []
            trends[profile].append({"date": date_str, "count": count})

        return {"trends": trends, "days": days}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/trends/skills")
def get_skill_trends(
    days: int = Query(30, ge=7, le=365),
    limit: int = Query(15, ge=1, le=50),
    db: Session = Depends(get_db),
):
    """Compétences les plus demandées (séparées en tech et soft skills)"""
    try:
        # Top compétences TECH (via fact_offer_skills + dim_skills)
        query_tech = text(
            """
            SELECT 
                ds.skill_name,
                ds.skill_category,
                COUNT(*) as total
            FROM fact_job_offers f
            JOIN fact_offer_skills fos ON f.offer_id = fos.offer_id
            JOIN dim_skills ds ON fos.skill_id = ds.skill_id
            WHERE f.published_date >= CURRENT_DATE - INTERVAL ':days days'
              AND f.published_date IS NOT NULL
              AND (ds.skill_category = 'technical' OR ds.skill_category IS NULL)
            GROUP BY ds.skill_name, ds.skill_category
            ORDER BY total DESC
            LIMIT :limit
        """
        )

        result_tech = db.execute(query_tech, {"days": days, "limit": limit})
        tech_skills = [
            {"skill": row[0], "category": row[1], "count": row[2]}
            for row in result_tech
        ]

        # Top compétences SOFT (via fact_offer_skills + dim_skills)
        query_soft = text(
            """
            SELECT 
                ds.skill_name,
                ds.skill_category,
                COUNT(*) as total
            FROM fact_job_offers f
            JOIN fact_offer_skills fos ON f.offer_id = fos.offer_id
            JOIN dim_skills ds ON fos.skill_id = ds.skill_id
            WHERE f.published_date >= CURRENT_DATE - INTERVAL ':days days'
              AND f.published_date IS NOT NULL
              AND ds.skill_category = 'soft'
            GROUP BY ds.skill_name, ds.skill_category
            ORDER BY total DESC
            LIMIT :limit
        """
        )

        result_soft = db.execute(query_soft, {"days": days, "limit": limit})
        soft_skills = [
            {"skill": row[0], "category": row[1], "count": row[2]}
            for row in result_soft
        ]

        # Timeline pour les top tech skills
        tech_timeline = {}
        if tech_skills:
            top_tech_names = [s["skill"] for s in tech_skills[:10]]

            query_tech_timeline = text(
                """
                SELECT 
                    DATE(f.published_date) as date,
                    ds.skill_name,
                    COUNT(*) as count
                FROM fact_job_offers f
                JOIN fact_offer_skills fos ON f.offer_id = fos.offer_id
                JOIN dim_skills ds ON fos.skill_id = ds.skill_id
                WHERE f.published_date >= CURRENT_DATE - INTERVAL ':days days'
                  AND f.published_date IS NOT NULL
                  AND ds.skill_name = ANY(:skills)
                GROUP BY DATE(f.published_date), ds.skill_name
                ORDER BY date, ds.skill_name
            """
            )

            result_tech_timeline = db.execute(
                query_tech_timeline, {"days": days, "skills": top_tech_names}
            )

            for row in result_tech_timeline:
                date_str = row[0].isoformat()
                skill = row[1]
                count = row[2]

                if skill not in tech_timeline:
                    tech_timeline[skill] = []
                tech_timeline[skill].append({"date": date_str, "count": count})

        # Timeline pour les top soft skills
        soft_timeline = {}
        if soft_skills:
            top_soft_names = [s["skill"] for s in soft_skills[:10]]

            query_soft_timeline = text(
                """
                SELECT 
                    DATE(f.published_date) as date,
                    ds.skill_name,
                    COUNT(*) as count
                FROM fact_job_offers f
                JOIN fact_offer_skills fos ON f.offer_id = fos.offer_id
                JOIN dim_skills ds ON fos.skill_id = ds.skill_id
                WHERE f.published_date >= CURRENT_DATE - INTERVAL ':days days'
                  AND f.published_date IS NOT NULL
                  AND ds.skill_name = ANY(:skills)
                GROUP BY DATE(f.published_date), ds.skill_name
                ORDER BY date, ds.skill_name
            """
            )

            result_soft_timeline = db.execute(
                query_soft_timeline, {"days": days, "skills": top_soft_names}
            )

            for row in result_soft_timeline:
                date_str = row[0].isoformat()
                skill = row[1]
                count = row[2]

                if skill not in soft_timeline:
                    soft_timeline[skill] = []
                soft_timeline[skill].append({"date": date_str, "count": count})

        return {
            "tech_skills": tech_skills,
            "tech_timeline": tech_timeline,
            "soft_skills": soft_skills,
            "soft_timeline": soft_timeline,
            "days": days,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
