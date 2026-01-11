"""
Dashboard General Statistics Router
====================================
Routes pour les statistiques générales du dashboard
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import create_engine, text
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


@router.get("/sources")
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


@router.get("/contracts")
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


@router.get("/cities")
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


@router.get("/cities/list")
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


@router.get("/regions")
def get_regions_stats(db: Session = Depends(get_db)):
    """Statistiques par région"""
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


@router.get("/profiles")
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


@router.get("/salaries")
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


@router.get("/timeline")
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


@router.get("/advanced-stats")
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
