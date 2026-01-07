#!/usr/bin/env python3
"""
Vérification de l'embedding pour une offre
"""
import os
import sys
from pathlib import Path
from dotenv import load_dotenv
import psycopg2
from pgvector.psycopg2 import register_vector
import numpy as np

# Chargement .env
env_path = Path(__file__).parent.parent.parent / ".env"
load_dotenv(env_path)

# Connexion DB
conn = psycopg2.connect(os.getenv("DATABASE_URL"))
register_vector(conn)
cursor = conn.cursor()

offer_id = 1579  # Dernière offre testée

print(f"\n{'='*80}")
print(f"🔍 VÉRIFICATION EMBEDDING OFFRE #{offer_id}")
print(f"{'='*80}\n")

# 1. Vérifier si l'embedding existe
cursor.execute(
    """
    SELECT embedding_id, model_name, created_at 
    FROM job_embeddings 
    WHERE offer_id = %s
    """,
    (offer_id,),
)
result = cursor.fetchone()

if result:
    embedding_id, model_name, created_at = result
    print(f"✅ Embedding trouvé !")
    print(f"   - Embedding ID: {embedding_id}")
    print(f"   - Modèle: {model_name}")
    print(f"   - Créé le: {created_at}")

    # 2. Récupérer et analyser l'embedding
    cursor.execute(
        "SELECT embedding FROM job_embeddings WHERE offer_id = %s", (offer_id,)
    )
    embedding_raw = cursor.fetchone()[0]

    if embedding_raw is not None:
        # requête retourne un pgvector donc on le convertit en np.array
        embedding = np.array(embedding_raw)

        print(f"\n📊 Analyse de l'embedding:")
        print(f"   - Dimensions: {len(embedding)}")
        print(f"   - Type: {type(embedding_raw)}")
        print(f"   - Min: {embedding.min():.4f}")
        print(f"   - Max: {embedding.max():.4f}")
        print(f"   - Moyenne: {embedding.mean():.4f}")
        print(f"   - Écart-type: {embedding.std():.4f}")
        print(f"   - Norme L2: {np.linalg.norm(embedding):.4f}")

        # Extrait du vecteur
        print(f"\n   Extrait du vecteur (10 premières valeurs):")
        print(f"   {embedding[:10]}")
    else:
        print("\n❌ Embedding NULL")
else:
    print(f"❌ Aucun embedding trouvé pour l'offre #{offer_id}")

    # Vérifier si l'offre existe
    cursor.execute(
        "SELECT offer_id, title FROM fact_job_offers WHERE offer_id = %s", (offer_id,)
    )
    offer = cursor.fetchone()
    if offer:
        print(f"   L'offre existe: {offer[1]}")
    else:
        print(f"   L'offre n'existe pas dans fact_job_offers")

# 3. Statistiques globales
cursor.execute("SELECT COUNT(*) FROM job_embeddings")
total_embeddings = cursor.fetchone()[0]

cursor.execute("SELECT COUNT(*) FROM fact_job_offers")
total_offers = cursor.fetchone()[0]

print(f"\n📈 Statistiques globales:")
print(f"   - Total embeddings: {total_embeddings}")
print(f"   - Total offres: {total_offers}")
if total_offers > 0:
    coverage = (total_embeddings / total_offers) * 100
    print(f"   - Couverture: {coverage:.1f}%")

cursor.close()
conn.close()

print(f"\n{'='*80}\n")
