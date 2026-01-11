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
    from api.routers import (
        scraper,
        glassdoor,
        map,
        dashboard_specific_statistics,
        dashboard_collected_offers,
        dashboard_general_statistics,
        offers,
        trends,
    )
except (ModuleNotFoundError, ImportError):
    # Import pour Docker (WORKDIR /app, structure aplatie)
    from routers import (
        scraper,
        glassdoor,
        map,
        dashboard_specific_statistics,
        dashboard_collected_offers,
        dashboard_general_statistics,
        offers,
        trends,
    )

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
app.include_router(dashboard_collected_offers.router, prefix="/api", tags=["dashboard"])
app.include_router(
    dashboard_general_statistics.router, prefix="/api", tags=["dashboard"]
)
app.include_router(offers.router, prefix="/api", tags=["offers"])
app.include_router(trends.router, prefix="/api", tags=["trends"])


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


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
