"""
script_topic_modeling_full.py

Script pour appliquer Topic Modeling LDA sur TOUTES les offres (5000)
Résultats sauvegardés en CSV + statistiques
"""

import os
import psycopg2
import pandas as pd
import numpy as np
from dotenv import load_dotenv
import spacy
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.decomposition import LatentDirichletAllocation
import re
import pickle
from datetime import datetime

print("="*80)
print("🎯 TOPIC MODELING LDA - CORPUS COMPLET")
print("="*80)
print()

# ============================================================================
# CONFIGURATION
# ============================================================================

load_dotenv()
DATABASE_URL = os.getenv('DATABASE_URL')

# Paramètres
N_TOPICS = 8
MAX_OFFRES_PAR_TITRE = 3

# Topics labels (d'après analyse)
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

# ============================================================================
# CHARGEMENT DONNÉES
# ============================================================================

print("📊 Chargement des données...")
conn = psycopg2.connect(DATABASE_URL)

query = """
SELECT 
    offer_id,
    title,
    description,
    company_name
FROM fact_job_offers
WHERE title IS NOT NULL AND description IS NOT NULL
ORDER BY offer_id
"""

df = pd.read_sql(query, conn)
conn.close()

print(f"   {len(df):,} offres chargées\n")

# ============================================================================
# FILTRAGE TECH
# ============================================================================

print("🔍 Filtrage offres Tech/Data/IA...")

TECH_KEYWORDS = [
    'data', 'données', 'machine learning', 'ml', 'ia', 'ai',
    'développeur', 'developpeur', 'java', 'python', 'javascript',
    'devops', 'cloud', 'aws', 'azure', 'docker', 'kubernetes',
    'ingénieur', 'ingenieur', 'architecte', 'consultant',
    'administrateur', 'système', 'systeme', 'réseau', 'reseau',
    'informatique', 'it', 'sql', 'chef de projet',
]

def is_tech_offer(title):
    return any(kw in str(title).lower() for kw in TECH_KEYWORDS)

df = df[df['title'].apply(is_tech_offer)].copy()
print(f"   {len(df):,} offres tech retenues\n")

# ============================================================================
# DÉDUPLICATION
# ============================================================================

print("🔄 Déduplication...")
df = df.groupby('title', as_index=False).head(MAX_OFFRES_PAR_TITRE)
print(f"   {len(df):,} offres après dédup\n")

# ============================================================================
# NETTOYAGE & LEMMATISATION
# ============================================================================

print("🧹 Nettoyage et lemmatisation (peut prendre 10-20 min)...")

# Charger spaCy
nlp = spacy.load("fr_core_news_md")

TITLE_STOPWORDS = set([
    'le', 'la', 'les', 'un', 'une', 'des', 'de', 'du', 'au', 'aux',
    'et', 'ou', 'pour', 'avec', 'sans', 'sur', 'sous', 'dans',
    'junior', 'senior', 'confirmé', 'confirme', 'expérimenté',
    'indépendant', 'independant', 'adjoint', 'alternance', 'stage',
])

def clean_title(title):
    if not title:
        return ""
    title = title.lower()
    title = re.sub(r'\(h/f\)|\(f/h\)|\bh/f\b|\bf/h\b', '', title)
    title = re.sub(r'\(cdi\)|\(cdd\)|\bstage\b|\balternance\b', '', title, flags=re.IGNORECASE)
    title = re.sub(r'[^\w\s\-]', ' ', title)
    title = re.sub(r'\s+', ' ', title).strip()
    return title

def lemmatize_title(title, nlp_model):
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

# Appliquer
df['title_cleaned'] = df['title'].apply(clean_title)
df['title_lemmatized'] = df['title_cleaned'].apply(lambda x: lemmatize_title(x, nlp))

print(f"   ✅ {len(df):,} titres lemmatisés\n")

# ============================================================================
# VECTORISATION & LDA
# ============================================================================

print("🔄 Vectorisation et entraînement LDA...")

documents = df['title_lemmatized'].tolist()

vectorizer = CountVectorizer(
    max_df=0.6,
    min_df=5,  # Plus strict pour 5000 offres
    max_features=800,
    token_pattern=r'\b[a-zàâäéèêëïîôùûüÿçæœ]{3,}\b'
)

tf = vectorizer.fit_transform(documents)
feature_names = vectorizer.get_feature_names_out()

print(f"   Matrice TF : {tf.shape}")

lda = LatentDirichletAllocation(
    n_components=N_TOPICS,
    random_state=42,
    max_iter=30,
    learning_method='online',
    n_jobs=-1
)

lda.fit(tf)

print(f"   ✅ LDA entraîné (8 topics)\n")

# ============================================================================
# ATTRIBUTION TOPICS
# ============================================================================

print("📊 Attribution des topics...")

doc_topic_dist = lda.transform(tf)
df['dominant_topic'] = doc_topic_dist.argmax(axis=1)
df['topic_confidence'] = doc_topic_dist.max(axis=1)
df['topic_label'] = df['dominant_topic'].map(lambda x: TOPIC_LABELS[x])

print("   ✅ Topics attribués\n")

# ============================================================================
# STATISTIQUES
# ============================================================================

print("="*80)
print("📈 RÉSULTATS - CORPUS COMPLET")
print("="*80)
print()

for i in range(N_TOPICS):
    count = (df['dominant_topic'] == i).sum()
    pct = count / len(df) * 100
    print(f"   {TOPIC_LABELS[i]:50} : {count:5} ({pct:5.1f}%)")

print(f"\n   TOTAL : {len(df):,} offres")

# ============================================================================
# EXPORT
# ============================================================================

timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
output_file = f"topic_modeling_results_{timestamp}.csv"

df_export = df[['offer_id', 'title', 'company_name', 'dominant_topic', 
                'topic_confidence', 'topic_label']].copy()

df_export.to_csv(output_file, index=False, encoding='utf-8')

print(f"\n✅ Résultats exportés : {output_file}")
print(f"   {len(df_export):,} offres avec topics")

# Sauvegarder modèle
model_file = f"lda_model_{timestamp}.pkl"
with open(model_file, 'wb') as f:
    pickle.dump({'lda': lda, 'vectorizer': vectorizer, 'feature_names': feature_names}, f)

print(f"✅ Modèle sauvegardé : {model_file}")

print("\n" + "="*80)
print("✨ TOPIC MODELING TERMINÉ !")
print("="*80)