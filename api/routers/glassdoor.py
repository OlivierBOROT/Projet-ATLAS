"""
Glassdoor API Integration
==========================

Récupère les informations et scores des entreprises depuis Glassdoor
via RapidAPI.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict, List
import http.client
import json
import os
from dotenv import load_dotenv
import logging

load_dotenv()
logger = logging.getLogger("glassdoor")

router = APIRouter()

# Configuration
RAPIDAPI_KEY = os.getenv("RAPIDAPI_KEY")
RAPIDAPI_HOST = "glassdoor-real-time.p.rapidapi.com"


# ============================================================================
# MODELS
# ============================================================================


class GlassdoorRequest(BaseModel):
    """Requête Glassdoor"""

    company_name: str


class GlassdoorResponse(BaseModel):
    """Réponse Glassdoor"""

    success: bool
    company_name: str
    rating: Optional[float] = None
    reviews_count: Optional[int] = None
    company_id: Optional[int] = None  # ID est un entier dans l'API Glassdoor
    company_url: Optional[str] = None
    company_info: Optional[Dict] = None
    error: Optional[str] = None


# ============================================================================
# FONCTIONS HELPER
# ============================================================================


def search_company_glassdoor(company_name: str) -> Dict:
    """
    Recherche une entreprise sur Glassdoor via RapidAPI

    Args:
        company_name: Nom de l'entreprise à rechercher

    Returns:
        Dict avec les informations de l'entreprise
    """
    if not RAPIDAPI_KEY:
        raise ValueError("RAPIDAPI_KEY non configurée dans .env")

    try:
        # Connexion à l'API
        conn = http.client.HTTPSConnection(RAPIDAPI_HOST)

        headers = {"x-rapidapi-key": RAPIDAPI_KEY, "x-rapidapi-host": RAPIDAPI_HOST}

        # Encoder le nom de l'entreprise pour l'URL
        from urllib.parse import quote

        encoded_name = quote(company_name)

        # Requête
        conn.request("GET", f"/companies/search?query={encoded_name}", headers=headers)

        res = conn.getresponse()
        data = res.read()

        # Parser la réponse JSON
        response_data = json.loads(data.decode("utf-8"))

        conn.close()

        return response_data

    except Exception as e:
        logger.error(f"❌ Erreur recherche Glassdoor: {e}")
        raise


def extract_company_info(glassdoor_data: Dict, company_name: str) -> Dict:
    """
    Extrait les informations pertinentes depuis la réponse Glassdoor

    Args:
        glassdoor_data: Données brutes de l'API
        company_name: Nom recherché

    Returns:
        Dict avec rating, reviews_count, etc.
    """
    try:
        # Structure réelle de Glassdoor API
        if "data" in glassdoor_data and glassdoor_data["data"]:
            employer_results = glassdoor_data["data"].get("employerResults", [])

            if not employer_results:
                return None

            # Prendre le premier résultat
            first_result = employer_results[0]
            employer = first_result.get("employer", {})
            ratings = first_result.get("employerRatings", {})
            counts = employer.get("counts", {})

            return {
                "company_name": employer.get("shortName", company_name),
                "rating": ratings.get("overallRating"),
                "reviews_count": counts.get("reviewCount"),
                "salary_count": counts.get("salaryCount"),
                "job_count": counts.get("globalJobCount", {}).get("jobCount"),
                "company_id": employer.get("id"),
                "company_url": (
                    f"https://www.glassdoor.com/Overview/Working-at-{employer.get('shortName', '').replace(' ', '-')}-EI_IE{employer.get('id')}.htm"
                    if employer.get("id")
                    else None
                ),
                "logo_url": employer.get("squareLogoUrl"),
            }

        return None

    except Exception as e:
        logger.error(f"❌ Erreur extraction données: {e}")
        return None


# ============================================================================
# ENDPOINTS
# ============================================================================


@router.post("/glassdoor/search", response_model=GlassdoorResponse)
async def get_glassdoor_score(request: GlassdoorRequest):
    """
    Recherche une entreprise sur Glassdoor et retourne son score

    Args:
        request: Nom de l'entreprise

    Returns:
        Score Glassdoor et informations de l'entreprise
    """
    logger.info(f"🔍 Recherche Glassdoor: {request.company_name}")

    try:
        # Recherche sur Glassdoor
        glassdoor_data = search_company_glassdoor(request.company_name)

        # Extraire les infos
        company_info = extract_company_info(glassdoor_data, request.company_name)

        if company_info:
            logger.info(
                f"✅ Entreprise trouvée: {company_info.get('company_name')} - Note: {company_info.get('rating')}"
            )

            return GlassdoorResponse(
                success=True,
                company_name=company_info.get("company_name"),
                rating=company_info.get("rating"),
                reviews_count=company_info.get("reviews_count"),
                company_id=company_info.get("company_id"),
                company_url=company_info.get("company_url"),
                company_info=company_info,
            )
        else:
            logger.warning(f"⚠️ Entreprise non trouvée: {request.company_name}")
            return GlassdoorResponse(
                success=False,
                company_name=request.company_name,
                error="Entreprise non trouvée sur Glassdoor",
            )

    except ValueError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        logger.error(f"❌ Erreur Glassdoor: {e}")
        raise HTTPException(status_code=500, detail=f"Erreur Glassdoor: {str(e)}")


@router.get("/glassdoor/search/{company_name}")
async def get_glassdoor_score_get(company_name: str):
    """
    Version GET pour rechercher une entreprise sur Glassdoor

    Args:
        company_name: Nom de l'entreprise

    Returns:
        Score Glassdoor et informations
    """
    request = GlassdoorRequest(company_name=company_name)
    return await get_glassdoor_score(request)
