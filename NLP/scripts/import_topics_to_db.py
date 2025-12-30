"""
import_topics_to_db.py (CORRIGÉ)

Importe les topics du CSV généré vers la base de données PostgreSQL
"""

import os
import pandas as pd
import psycopg2
from psycopg2.extras import execute_values
from dotenv import load_dotenv
from datetime import datetime

print("="*80)
print("📥 IMPORT TOPICS VERS BASE DE DONNÉES")
print("="*80)
print()

# ============================================================================
# CONFIGURATION
# ============================================================================

load_dotenv()
DATABASE_URL = os.getenv('DATABASE_URL')

# Fichier CSV généré par topic modeling
CSV_FILE = "topic_modeling_results_20251230_134751.csv"

# ============================================================================
# CHARGEMENT DONNÉES
# ============================================================================

print("📊 Chargement du CSV...")

try:
    df = pd.read_csv(CSV_FILE, encoding='utf-8')
    print(f"   ✅ {len(df):,} lignes chargées")
    print(f"\n   Colonnes : {list(df.columns)}")
    
except FileNotFoundError:
    print(f"   ❌ ERREUR : Fichier {CSV_FILE} introuvable")
    print("\n   💡 Fichiers CSV disponibles :")
    import glob
    for f in glob.glob("topic_modeling_results_*.csv"):
        print(f"      - {f}")
    exit(1)

# Vérifier structure - ADAPTER AUX NOMS DES COLONNES
if 'dominant_topic' in df.columns:
    # Renommer pour compatibilité
    df['topic_id'] = df['dominant_topic']
    print("   ✅ Colonne 'dominant_topic' renommée en 'topic_id'")
elif 'topic_id' not in df.columns:
    print(f"\n   ❌ ERREUR : Ni 'topic_id' ni 'dominant_topic' trouvé")
    print(f"   Colonnes disponibles : {list(df.columns)}")
    exit(1)

# Vérifier autres colonnes requises
required_cols = ['offer_id', 'topic_id', 'topic_label', 'topic_confidence']
missing = [col for col in required_cols if col not in df.columns]

if missing:
    print(f"\n   ❌ ERREUR : Colonnes manquantes : {missing}")
    exit(1)

print(f"\n   ✅ Structure validée")

# Afficher aperçu
print(f"\n   Aperçu des données :")
print(df[['offer_id', 'topic_id', 'topic_label', 'topic_confidence']].head(3))

# ============================================================================
# CONNEXION BDD
# ============================================================================

print("\n🔌 Connexion à la base de données...")

try:
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()
    print("   ✅ Connecté")
    
except Exception as e:
    print(f"   ❌ ERREUR : {e}")
    exit(1)

# ============================================================================
# VÉRIFIER SI COLONNES EXISTENT
# ============================================================================

print("\n🔍 Vérification structure BDD...")

cur.execute("""
    SELECT column_name 
    FROM information_schema.columns 
    WHERE table_name = 'fact_job_offers' 
    AND column_name IN ('topic_id', 'topic_label', 'topic_confidence')
""")

existing_cols = [row[0] for row in cur.fetchall()]

if len(existing_cols) < 3:
    print(f"   ⚠️  Colonnes manquantes : {set(['topic_id', 'topic_label', 'topic_confidence']) - set(existing_cols)}")
    print(f"   💡 Exécuter d'abord : add_topics_to_db.sql")
    
    response = input("\n   Voulez-vous que je les crée maintenant ? (y/n) : ")
    if response.lower() == 'y':
        print("\n   🔧 Création des colonnes...")
        try:
            cur.execute("""
                ALTER TABLE fact_job_offers
                ADD COLUMN IF NOT EXISTS topic_id INTEGER,
                ADD COLUMN IF NOT EXISTS topic_label VARCHAR(100),
                ADD COLUMN IF NOT EXISTS topic_confidence DECIMAL(3,2)
            """)
            conn.commit()
            print("   ✅ Colonnes créées")
        except Exception as e:
            print(f"   ❌ ERREUR : {e}")
            exit(1)
    else:
        exit(0)
else:
    print(f"   ✅ Colonnes existantes : {existing_cols}")

# ============================================================================
# IMPORT TOPICS
# ============================================================================

print("\n📥 Import des topics dans fact_job_offers...")

# Préparer données
updates = []
for _, row in df.iterrows():
    updates.append((
        int(row['topic_id']),
        str(row['topic_label']),
        float(row['topic_confidence']),
        int(row['offer_id'])
    ))

print(f"   ⏳ Mise à jour de {len(updates):,} offres...")

# Update par batch (plus rapide)
update_query = """
    UPDATE fact_job_offers
    SET 
        topic_id = data.topic_id,
        topic_label = data.topic_label,
        topic_confidence = data.topic_confidence
    FROM (VALUES %s) AS data(topic_id, topic_label, topic_confidence, offer_id)
    WHERE fact_job_offers.offer_id = data.offer_id
"""

try:
    execute_values(
        cur,
        update_query,
        updates,
        template="(%s, %s, %s, %s)"
    )
    
    conn.commit()
    
    # Vérifier résultat
    cur.execute("SELECT COUNT(*) FROM fact_job_offers WHERE topic_id IS NOT NULL")
    count = cur.fetchone()[0]
    
    print(f"   ✅ {count:,} offres mises à jour avec succès")
    
except Exception as e:
    conn.rollback()
    print(f"   ❌ ERREUR lors de l'import : {e}")
    cur.close()
    conn.close()
    exit(1)

# ============================================================================
# STATISTIQUES
# ============================================================================

print("\n📊 Statistiques post-import...")

# Distribution des topics
cur.execute("""
    SELECT 
        topic_id,
        topic_label,
        COUNT(*) as nb_offres,
        ROUND(AVG(topic_confidence)::numeric, 2) as confiance_moy
    FROM fact_job_offers
    WHERE topic_id IS NOT NULL
    GROUP BY topic_id, topic_label
    ORDER BY topic_id
""")

print("\n   Distribution des topics :")
total = 0
for row in cur.fetchall():
    topic_id, label, count, conf = row
    pct = (count / len(df)) * 100
    print(f"   Topic {topic_id} : {label:50} → {count:5} offres ({pct:5.1f}%) | conf={conf}")
    total += count

print(f"\n   TOTAL : {total:,} offres avec topics")

# Topics par région (Top 5)
cur.execute("""
    SELECT 
        r.nom_region,
        COUNT(*) as nb_offres
    FROM fact_job_offers f
    JOIN ref_communes_france r ON f.commune_id = r.commune_id
    WHERE f.topic_id IS NOT NULL
    GROUP BY r.nom_region
    ORDER BY nb_offres DESC
    LIMIT 5
""")

print("\n   Top 5 régions avec topics :")
for row in cur.fetchall():
    region, count = row
    print(f"   {region:30} : {count:4} offres")

# Confiance moyenne par topic
cur.execute("""
    SELECT 
        topic_label,
        COUNT(*) as nb_offres,
        ROUND(AVG(topic_confidence)::numeric, 3) as conf_moy,
        ROUND(MIN(topic_confidence)::numeric, 3) as conf_min,
        ROUND(MAX(topic_confidence)::numeric, 3) as conf_max
    FROM fact_job_offers
    WHERE topic_id IS NOT NULL
    GROUP BY topic_label
    ORDER BY nb_offres DESC
""")

print("\n   Qualité des prédictions (confiance) :")
for row in cur.fetchall():
    label, count, avg_conf, min_conf, max_conf = row
    print(f"   {label[:40]:40} | avg={avg_conf} min={min_conf} max={max_conf}")

# ============================================================================
# FINALISATION
# ============================================================================

cur.close()
conn.close()

print("\n" + "="*80)
print("✅ IMPORT TERMINÉ AVEC SUCCÈS")
print("="*80)
print(f"""
📊 Résumé :
   - {len(df):,} topics importés depuis CSV
   - Base de données mise à jour
   - Colonnes ajoutées : topic_id, topic_label, topic_confidence
   
🎯 Prochaines étapes :
   1. Créer table dim_topics (optionnel) : add_topics_to_db.sql
   2. Enrichissement NLP complet : nlp_enrichment_full.py
   3. Visualisations Streamlit
   
💡 Test rapide :
   SELECT topic_label, COUNT(*) 
   FROM fact_job_offers 
   WHERE topic_id IS NOT NULL 
   GROUP BY topic_label;
""")