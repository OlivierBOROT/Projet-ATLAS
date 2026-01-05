#!/usr/bin/env python3
"""
Vérification des skills pour une offre
"""
import os
import sys
from pathlib import Path
from dotenv import load_dotenv
import psycopg2

# Chargement .env
env_path = Path(__file__).parent.parent.parent / ".env"
load_dotenv(env_path)

# Connexion DB
conn = psycopg2.connect(os.getenv("DATABASE_URL"))
cursor = conn.cursor()

offer_id = 2662  # Dernière offre testée

print(f"\n{'='*80}")
print(f"🔍 VÉRIFICATION OFFRE #{offer_id}")
print(f"{'='*80}\n")

# 1. Skills extracted
cursor.execute(
    "SELECT skills_extracted FROM fact_job_offers WHERE offer_id = %s", (offer_id,)
)
row = cursor.fetchone()
print(f"📋 skills_extracted: {row[0]}")

# 2. Nombre de relations
cursor.execute(
    "SELECT COUNT(*) FROM fact_offer_skills WHERE offer_id = %s", (offer_id,)
)
print(f"🔗 Relations dans fact_offer_skills: {cursor.fetchone()[0]}")

# 3. Liste des skills liées
cursor.execute(
    """
    SELECT s.skill_name, s.skill_category 
    FROM fact_offer_skills fos
    JOIN dim_skills s ON fos.skill_id = s.skill_id
    WHERE fos.offer_id = %s
    ORDER BY s.skill_category, s.skill_name
    """,
    (offer_id,),
)
skills = cursor.fetchall()
if skills:
    print(f"\n💡 Skills liées ({len(skills)}):")
    for skill_name, skill_cat in skills:
        print(f"   - {skill_name} ({skill_cat})")
else:
    print("\n❌ Aucune skill liée")

cursor.close()
conn.close()

print(f"\n{'='*80}\n")
