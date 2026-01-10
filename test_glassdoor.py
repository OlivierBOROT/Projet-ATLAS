"""
Test Glassdoor API
==================

Test la route Glassdoor pour récupérer le score d'une entreprise.
"""

import requests
import sys
import os
from pathlib import Path

# Ajouter le dossier parent au PYTHONPATH
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv

load_dotenv()

# Configuration
API_URL = os.getenv("API_URL", "http://localhost:8000")


def test_glassdoor_search(company_name: str):
    """Test la recherche Glassdoor"""

    print(f"\n{'='*60}")
    print(f"🔍 Test Glassdoor API - Recherche: {company_name}")
    print(f"{'='*60}\n")

    try:
        # Test avec POST
        print("📡 Requête POST /api/glassdoor/search")
        response = requests.post(
            f"{API_URL}/api/glassdoor/search",
            json={"company_name": company_name},
            timeout=30,
        )

        print(f"📊 Status: {response.status_code}")

        if response.status_code == 200:
            data = response.json()

            print(f"\n✅ SUCCÈS - Réponse reçue\n")
            print(f"{'─'*60}")
            print("📦 RÉPONSE COMPLÈTE DE L'API:")
            print(f"{'─'*60}")

            import json

            print(json.dumps(data, indent=2, ensure_ascii=False))

            print(f"{'─'*60}\n")

        else:
            print(f"\n❌ ERREUR - Status {response.status_code}")
            print(f"Message: {response.text}\n")

    except requests.exceptions.Timeout:
        print("❌ TIMEOUT - L'API n'a pas répondu dans les 30 secondes")
    except requests.exceptions.ConnectionError:
        print(f"❌ CONNEXION IMPOSSIBLE - Vérifiez que l'API est lancée sur {API_URL}")
    except Exception as e:
        print(f"❌ ERREUR: {e}")


def test_multiple_companies():
    """Test plusieurs entreprises"""

    companies = ["Google", "Airbus", "Thales", "Capgemini", "Société Générale"]

    print(f"\n{'='*60}")
    print(f"🧪 TEST MULTIPLE ENTREPRISES")
    print(f"{'='*60}")

    results = []

    for company in companies:
        try:
            response = requests.post(
                f"{API_URL}/api/glassdoor/search",
                json={"company_name": company},
                timeout=30,
            )

            if response.status_code == 200:
                data = response.json()
                results.append(
                    {
                        "company": company,
                        "found": data.get("success"),
                        "rating": data.get("rating"),
                        "reviews": data.get("reviews_count"),
                    }
                )
            else:
                results.append(
                    {
                        "company": company,
                        "found": False,
                        "rating": None,
                        "reviews": None,
                    }
                )

        except Exception as e:
            print(f"❌ Erreur pour {company}: {e}")
            results.append(
                {"company": company, "found": False, "rating": None, "reviews": None}
            )

    # Afficher le résumé
    print(f"\n📊 RÉSUMÉ DES RÉSULTATS\n")
    print(f"{'─'*60}")
    print(f"{'Entreprise':<25} {'Trouvée':<10} {'Note':<10} {'Avis':<10}")
    print(f"{'─'*60}")

    for result in results:
        found = "✅" if result["found"] else "❌"
        rating = f"{result['rating']}/5" if result["rating"] else "N/A"
        reviews = str(result["reviews"]) if result["reviews"] else "N/A"
        print(f"{result['company']:<25} {found:<10} {rating:<10} {reviews:<10}")

    print(f"{'─'*60}\n")


if __name__ == "__main__":
    # Vérifier si l'API est accessible
    try:
        health = requests.get(f"{API_URL}/health", timeout=5)
        if health.status_code != 200:
            print(f"❌ API non accessible sur {API_URL}")
            print("💡 Lancez l'API avec: uvicorn api.main:app --reload")
            sys.exit(1)
    except:
        print(f"❌ Impossible de se connecter à l'API sur {API_URL}")
        print("💡 Lancez l'API avec: uvicorn api.main:app --reload")
        sys.exit(1)

    # Test simple
    test_glassdoor_search("Airbus")

    # Test multiple (décommenter si besoin)
    # test_multiple_companies()
