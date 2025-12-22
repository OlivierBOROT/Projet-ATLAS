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

# Configuration
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://atlas_user:atlas_password@postgres:5432/atlas"
)

# Engine SQLAlchemy
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# FastAPI app
app = FastAPI(
    title="ATLAS API",
    description="API d'analyse textuelle et localisation des annonces spécialisées",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
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
        "docs": "/docs"
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
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        return {"total_offers": 0, "total_regions": 13, "error": str(e)}

@app.get("/api/offers")
def get_offers(
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db)
):
    try:
        query = text("""
            SELECT 
                f.offer_id, f.title, f.company_name, f.contract_type,
                l.city, l.region, s.source_name, f.collected_date
            FROM fact_job_offers f
            LEFT JOIN dim_locations l ON f.location_id = l.location_id
            LEFT JOIN dim_sources s ON f.source_id = s.source_id
            ORDER BY f.collected_date DESC
            LIMIT :limit OFFSET :offset
        """)
        
        result = db.execute(query, {"limit": limit, "offset": offset})
        
        offers = []
        for row in result:
            offers.append({
                "offer_id": row[0],
                "title": row[1],
                "company": row[2],
                "contract": row[3],
                "city": row[4],
                "region": row[5],
                "source": row[6],
                "date": row[7].isoformat() if row[7] else None
            })
        
        return {"count": len(offers), "offers": offers}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/regions")
def get_regions_stats(db: Session = Depends(get_db)):
    try:
        query = text("""
            SELECT l.region, COUNT(*) as total
            FROM fact_job_offers f
            JOIN dim_locations l ON f.location_id = l.location_id
            WHERE l.region IS NOT NULL
            GROUP BY l.region
            ORDER BY total DESC
        """)
        
        result = db.execute(query)
        regions = [{"region": row[0], "count": row[1]} for row in result]
        
        return {"regions": regions}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
