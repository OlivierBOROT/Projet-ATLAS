"""
Script pour exécuter la migration SQL NLP
==========================================
Exécute le fichier migration_nlp_enrichment.sql
"""

import psycopg2
import os
from dotenv import load_dotenv

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")

print("📡 Connexion à Supabase...")
conn = psycopg2.connect(DATABASE_URL)
conn.autocommit = True
cursor = conn.cursor()

print("🏗️  Exécution de la migration NLP...")
with open("migration_nlp_enrichment.sql", "r", encoding="utf-8") as f:
    migration_sql = f.read()

try:
    cursor.execute(migration_sql)
    print("✅ Migration exécutée avec succès !")
except Exception as e:
    print(f"❌ Erreur lors de la migration: {e}")

cursor.close()
conn.close()

print("\n✅ Terminé !")
