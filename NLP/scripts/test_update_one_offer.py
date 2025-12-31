"""
Test UPDATE d'une offre
========================
Script pour tester l'update d'une seule offre en BDD
"""

import os
import sys
import psycopg2
from dotenv import load_dotenv

# Ajouter le chemin des modules NLP
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "modules"))

from text_cleaner import TextCleaner
from skill_extractor import SkillExtractor
from info_extractor import InfoExtractor

# Forcer l'encodage UTF-8 pour stdout/stderr sur Windows
if sys.platform == "win32":
    import io

    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8")

# Charger les variables d'environnement
load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")

print("=" * 80)
print("🧪 TEST UPDATE D'UNE OFFRE")
print("=" * 80)

# Connexion BDD
print("\n📡 Connexion à PostgreSQL...")
conn = psycopg2.connect(DATABASE_URL)
cursor = conn.cursor()

# Récupérer UNE offre aléatoire
print("📊 Récupération d'une offre aléatoire...")
cursor.execute(
    """
    SELECT offer_id, title, description
    FROM fact_job_offers
    WHERE description IS NOT NULL 
      AND LENGTH(description) > 200
    ORDER BY RANDOM()
    LIMIT 1
"""
)

offer = cursor.fetchone()
if not offer:
    print("❌ Aucune offre trouvée")
    exit(1)

offer_id, title, description = offer
print(f"✅ Offre #{offer_id} : {title}\n")

# Initialiser les modules NLP
print("⏳ Initialisation des modules NLP...")
cleaner = TextCleaner()
skill_extractor = SkillExtractor()
info_extractor = InfoExtractor()
print("✅ Modules initialisés\n")

# Traiter l'offre
print("🔬 Traitement NLP...")
print(f"📄 Description (extrait) : {description[:150]}...\n")

# 1. NETTOYAGE ET LEMMATISATION
cleaned = cleaner.clean_text(description)
lemmas = cleaner.lemmatize(cleaned)
description_cleaned = " ".join(lemmas)

print(f"🧹 Description cleaned (extrait) : {description_cleaned[:200]}...\n")

# 2. EXTRACTION SKILLS
skills = skill_extractor.extract_skills(description)
category = skill_extractor.categorize_offer(description)

# Calcul du profile_confidence (en pourcentage)
max_score = 10
profile_confidence = min(100, int((category["profile_score"] / max_score) * 100))

print(f"🎯 PROFIL IDENTIFIÉ :")
print(f"   Catégorie : {category['dominant_profile']}")
print(f"   Score : {category['profile_score']} compétences matchées")
print(f"   Confiance : {profile_confidence}%\n")

print(f"💻 COMPÉTENCES TECHNIQUES ({len(skills['all_tech_skills'])}) :")
if skills["all_tech_skills"]:
    print(f"   {', '.join(skills['all_tech_skills'][:10])}")
else:
    print("   Aucune")

print(f"\n🤝 SOFT SKILLS ({len(skills['soft_skills'])}) :")
if skills["soft_skills"]:
    print(f"   {', '.join(skills['soft_skills'][:10])}")
else:
    print("   Aucune")

# 3. EXTRACTION INFOS
info = info_extractor.extract_all(description)

print(f"\n📋 INFORMATIONS EXTRAITES :")
if info["education"]["level"]:
    print(
        f"   🎓 Formation : Bac+{info['education']['level']} ({info['education']['degree_type']})"
    )
else:
    print("   🎓 Formation : Non spécifiée")

if info["remote"]["remote_possible"]:
    if info["remote"]["remote_days"]:
        print(
            f"   🏠 Télétravail : {info['remote']['remote_days']} jours/semaine ({info['remote']['remote_percentage']}%)"
        )
    elif info["remote"]["remote_percentage"]:
        print(f"   🏠 Télétravail : {info['remote']['remote_percentage']}%")
    else:
        print("   🏠 Télétravail : Possible")
else:
    print("   🏠 Télétravail : Non mentionné")

# UPDATE EN BDD
print("\n" + "=" * 80)
print("💾 UPDATE EN BASE DE DONNÉES")
print("=" * 80)

try:
    # 1. Mise à jour de fact_job_offers
    update_query = """
        UPDATE fact_job_offers
        SET 
            description_cleaned = %s,
            profile_category = %s,
            profile_confidence = %s,
            education_level = %s,
            education_type = %s,
            remote_possible = %s,
            remote_days = %s,
            remote_percentage = %s,
            processed = TRUE,
            processing_date = NOW()
        WHERE offer_id = %s
    """

    cursor.execute(
        update_query,
        (
            description_cleaned,
            category["dominant_profile"],
            profile_confidence,
            info["education"]["level"],
            info["education"]["degree_type"],
            info["remote"]["remote_possible"],
            info["remote"]["remote_days"],
            info["remote"]["remote_percentage"],
            offer_id,
        ),
    )

    # 2. Mise à jour de skills_extracted dans fact_job_offers
    all_skills = skills["all_tech_skills"] + skills["soft_skills"]
    cursor.execute(
        """
        UPDATE fact_job_offers
        SET skills_extracted = %s
        WHERE offer_id = %s
        """,
        (all_skills, offer_id),
    )
    print(f"\n📝 Mise à jour skills_extracted: {len(all_skills)} skills")

    # 3. Insertion des skills techniques dans dim_skills (si nouvelles)
    if skills["all_tech_skills"]:
        print(
            f"📝 Insertion des {len(skills['all_tech_skills'])} compétences techniques dans dim_skills..."
        )
        for skill in skills["all_tech_skills"]:
            cursor.execute(
                """
                INSERT INTO dim_skills (skill_name, skill_category)
                VALUES (%s, 'technical')
                ON CONFLICT (skill_name) DO NOTHING
            """,
                (skill,),
            )

    # 4. Insertion des soft skills dans dim_skills (si nouvelles)
    if skills["soft_skills"]:
        print(
            f"📝 Insertion des {len(skills['soft_skills'])} soft skills dans dim_skills..."
        )
        for skill in skills["soft_skills"]:
            cursor.execute(
                """
                INSERT INTO dim_skills (skill_name, skill_category)
                VALUES (%s, 'soft')
                ON CONFLICT (skill_name) DO NOTHING
            """,
                (skill,),
            )

    # 5. Création des relations dans fact_offer_skills
    if all_skills:
        print(f"📝 Création des relations dans fact_offer_skills...")
        for skill in all_skills:
            cursor.execute(
                """
                INSERT INTO fact_offer_skills (offer_id, skill_id)
                SELECT %s, skill_id 
                FROM dim_skills 
                WHERE skill_name = %s
                ON CONFLICT (offer_id, skill_id) DO NOTHING
                """,
                (offer_id, skill),
            )

    conn.commit()
    print("\n✅ UPDATE réussi !")

    # Vérification
    print("\n" + "=" * 80)
    print("🔍 VÉRIFICATION")
    print("=" * 80)

    cursor.execute(
        """
        SELECT 
            profile_category,
            profile_confidence,
            education_level,
            education_type,
            remote_possible,
            remote_days,
            remote_percentage,
            processed,
            processing_date,
            LEFT(description_cleaned, 150) as cleaned_preview
        FROM fact_job_offers
        WHERE offer_id = %s
    """,
        (offer_id,),
    )

    result = cursor.fetchone()
    if result:
        print(f"\n📋 Offre #{offer_id} :")
        print(f"   Profil : {result[0]} ({result[1]}%)")
        print(
            f"   Formation : Bac+{result[2] if result[2] else 'N/A'} ({result[3] if result[3] else 'N/A'})"
        )
        print(
            f"   Télétravail : {result[4]} ({result[5] if result[5] else 'N/A'} jours, {result[6] if result[6] else 'N/A'}%)"
        )
        print(f"   Processed : {result[7]}")
        print(f"   Processing date : {result[8]}")
        print(f"\n   Description cleaned (extrait) :\n   {result[9]}...")
        print("\n✅ Données correctement enregistrées en BDD !")

except Exception as e:
    print(f"\n❌ Erreur lors de l'UPDATE : {str(e)}")
    conn.rollback()
finally:
    cursor.close()
    conn.close()

print("\n" + "=" * 80)
print("✅ TEST TERMINÉ")
print("=" * 80)
