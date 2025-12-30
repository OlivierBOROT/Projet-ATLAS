"""
assign_topics_remaining.py

Utilise le modèle LDA sauvegardé (.pkl) pour attribuer topics 
aux offres qui n'en ont pas encore (celles filtrées/dédupliquées)

Temps estimé : 5-10 minutes
"""

import os
import sys
import psycopg2
from psycopg2.extras import execute_values
import pandas as pd
import numpy as np
from dotenv import load_dotenv
import pickle
import spacy
import re
from datetime import datetime

print("="*80)
print("🎯 ATTRIBUTION TOPICS AUX OFFRES RESTANTES")
print("="*80)
print()

# ============================================================================
# CONFIGURATION
# ============================================================================

load_dotenv()
DATABASE_URL = os.getenv('DATABASE_URL')

# Fichier modèle LDA
MODEL_FILE = "lda_model_20251230_134751.pkl"

# Labels des 8 topics
TOPIC_LABELS = [
    "Ingénierie Cloud & Cybersécurité",
    "Consulting & Architecture IT",
    "Data Analysis & Transformation Digitale",
    "Direction Commerciale & Administration IT",
    "Gestion Commerciale & Qualité",
    "Gestion de Projet & Développement",
    "Ingénierie R&D & Data Science",
    "Product Management & Développement Java",
]

# Stopwords pour lemmatisation
TITLE_STOPWORDS = set([
    'le', 'la', 'les', 'un', 'une', 'des', 'de', 'du', 'au', 'aux',
    'et', 'ou', 'pour', 'avec', 'sans', 'sur', 'sous', 'dans',
    'junior', 'senior', 'confirmé', 'confirme', 'expérimenté', 'experimente',
    'indépendant', 'independant', 'adjoint', 'multi', 'sites',
    'alternance', 'stage', 'cdi', 'cdd',
])

# ============================================================================
# CHARGEMENT MODÈLE LDA
# ============================================================================

print("📦 Chargement du modèle LDA...")

try:
    with open(MODEL_FILE, 'rb') as f:
        saved = pickle.load(f)
        lda = saved['lda']
        vectorizer = saved['vectorizer']
        feature_names = saved['feature_names']
    
    print(f"   ✅ Modèle chargé : {MODEL_FILE}")
    print(f"   📊 {lda.n_components} topics")
    
except FileNotFoundError:
    print(f"   ❌ ERREUR : Fichier {MODEL_FILE} introuvable")
    print("\n   💡 Fichiers .pkl disponibles :")
    import glob
    for f in glob.glob("lda_model_*.pkl"):
        print(f"      - {f}")
    exit(1)

# ============================================================================
# CHARGEMENT SPACY
# ============================================================================

print("\n🔤 Chargement spaCy...")

try:
    nlp = spacy.load("fr_core_news_md")
    print("   ✅ spaCy FR chargé")
except:
    print("   ❌ ERREUR : Installer avec 'python -m spacy download fr_core_news_md'")
    exit(1)

# ============================================================================
# FONCTIONS PREPROCESSING
# ============================================================================

def clean_title(title):
    """Nettoie un titre"""
    if not title:
        return ""
    title = title.lower()
    title = re.sub(r'\(h/f\)|\(f/h\)|\bh/f\b|\bf/h\b', '', title)
    title = re.sub(r'\(cdi\)|\(cdd\)|\bstage\b|\balternance\b', '', title, flags=re.IGNORECASE)
    title = re.sub(r'[^\w\s\-]', ' ', title)
    title = re.sub(r'\s+', ' ', title).strip()
    return title

def lemmatize_title(title, nlp_model):
    """Lemmatise un titre"""
    if not title:
        return ""
    doc = nlp_model(title)
    lemmas = [
        token.lemma_.lower()
        for token in doc 
        if (token.pos_ in ['NOUN', 'ADJ', 'PROPN']
            and not token.is_stop
            and token.lemma_.lower() not in TITLE_STOPWORDS
            and len(token.lemma_) > 2
            and token.is_alpha)
    ]
    return ' '.join(lemmas)

def predict_topic(title, lda_model, vectorizer):
    """Prédit le topic d'un titre"""
    # Preprocessing
    title_clean = clean_title(title)
    title_lemmatized = lemmatize_title(title_clean, nlp)
    
    # Vectoriser
    title_vec = vectorizer.transform([title_lemmatized])
    
    # Prédire
    topic_dist = lda_model.transform(title_vec)
    topic_id = topic_dist.argmax()
    confidence = topic_dist.max()
    
    return int(topic_id), float(confidence)

# ============================================================================
# CHARGEMENT OFFRES SANS TOPIC
# ============================================================================

print("\n📊 Chargement des offres sans topic...")

try:
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()
    
    # Offres sans topic attribué
    query = """
        SELECT offer_id, title
        FROM fact_job_offers
        WHERE topic_id IS NULL
        AND title IS NOT NULL
        ORDER BY offer_id
    """
    
    cur.execute(query)
    offers = cur.fetchall()
    
    print(f"   ✅ {len(offers):,} offres à classifier")
    
    if len(offers) == 0:
        print("\n   ℹ️  Toutes les offres ont déjà un topic !")
        print("   ✅ Rien à faire")
        exit(0)
    
except Exception as e:
    print(f"   ❌ ERREUR : {e}")
    exit(1)

# ============================================================================
# CLASSIFICATION PAR BATCH
# ============================================================================

print(f"\n🔄 Classification en cours...")

BATCH_SIZE = 100
total_batches = (len(offers) // BATCH_SIZE) + 1

updates = []
processed = 0

for i in range(0, len(offers), BATCH_SIZE):
    batch = offers[i:i+BATCH_SIZE]
    batch_num = i // BATCH_SIZE + 1
    
    print(f"   Batch {batch_num}/{total_batches} ({len(batch)} offres)... ", end='', flush=True)
    
    for offer_id, title in batch:
        try:
            topic_id, confidence = predict_topic(title, lda, vectorizer)
            topic_label = TOPIC_LABELS[topic_id]
            
            updates.append((
                topic_id,
                topic_label,
                confidence,
                offer_id
            ))
            
            processed += 1
            
        except Exception as e:
            print(f"\n   ⚠️  Erreur offre {offer_id} : {e}")
            continue
    
    print("✅")

# ============================================================================
# UPDATE BDD
# ============================================================================

print(f"\n💾 Mise à jour de la base de données...")

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
    print(f"   ⏳ Mise à jour {len(updates):,} offres...")
    
    execute_values(
        cur,
        update_query,
        updates,
        template="(%s, %s, %s, %s)"
    )
    
    conn.commit()
    
    # Vérifier
    cur.execute("SELECT COUNT(*) FROM fact_job_offers WHERE topic_id IS NOT NULL")
    total_with_topics = cur.fetchone()[0]
    
    print(f"   ✅ Base de données mise à jour")
    print(f"   📊 {total_with_topics:,} offres ont maintenant un topic")
    
except Exception as e:
    conn.rollback()
    print(f"   ❌ ERREUR : {e}")
    exit(1)

# ============================================================================
# STATISTIQUES FINALES
# ============================================================================

print("\n" + "="*80)
print("📊 STATISTIQUES FINALES")
print("="*80)

# Distribution globale
cur.execute("""
    SELECT 
        topic_id,
        topic_label,
        COUNT(*) as nb_offres,
        ROUND(100.0 * COUNT(*) / (SELECT COUNT(*) FROM fact_job_offers WHERE topic_id IS NOT NULL), 1) as pct,
        ROUND(AVG(topic_confidence)::numeric, 2) as conf_moy
    FROM fact_job_offers
    WHERE topic_id IS NOT NULL
    GROUP BY topic_id, topic_label
    ORDER BY topic_id
""")

print("\n   Distribution des topics (CORPUS COMPLET) :")
for row in cur.fetchall():
    topic_id, label, count, pct, conf = row
    print(f"   Topic {topic_id} : {label:50} → {count:5} ({pct:5.1f}%) | conf={conf}")

# Total
cur.execute("SELECT COUNT(*) FROM fact_job_offers")
total_offers = cur.fetchone()[0]

cur.execute("SELECT COUNT(*) FROM fact_job_offers WHERE topic_id IS NOT NULL")
with_topics = cur.fetchone()[0]

print(f"\n   TOTAL : {with_topics:,} / {total_offers:,} offres avec topics ({100*with_topics/total_offers:.1f}%)")

# ============================================================================
# FINALISATION
# ============================================================================

cur.close()
conn.close()

print("\n" + "="*80)
print("✅ ATTRIBUTION TERMINÉE")
print("="*80)
print(f"""
📊 Résumé :
   - {processed:,} offres classifiées
   - Modèle LDA réutilisé avec succès
   - {with_topics:,} / {total_offers:,} offres ont un topic

""")
