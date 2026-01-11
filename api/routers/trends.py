"""
Trends Router
=============
Routes pour les tendances et évolutions temporelles
"""

from fastapi import APIRouter, Depends, HTTPException, Query
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


@router.get("/trends/profiles")
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


@router.get("/trends/skills")
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
