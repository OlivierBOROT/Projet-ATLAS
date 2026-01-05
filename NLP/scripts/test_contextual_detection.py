"""
Script de test pour la détection contextuelle des compétences
Teste avec l'offre Chef de Projets Data contenant "langages de requêtes"
"""

import sys
from pathlib import Path

# Ajouter le chemin du module NLP
sys.path.insert(0, str(Path(__file__).parent.parent))

from modules.skill_extractor import SkillExtractor

# Texte de test : Chef de Projets Data
test_description = """
CHEF DE PROJETS DATA (H/F)

Notre client, acteur majeur dans le secteur de l'assurance, recherche un Chef de Projets Data 
pour piloter des projets stratégiques autour de la donnée.

MISSIONS :
- Piloter des projets data de bout en bout (cadrage, conception, réalisation, déploiement)
- Définir et mettre en œuvre des architectures data adaptées aux besoins métiers
- Assurer la liaison entre les équipes techniques et les directions métiers
- Garantir la qualité des données et leur conformité réglementaire

PROFIL RECHERCHÉ :
- Formation supérieure en informatique ou statistiques (Bac+5)
- Expérience de 5 ans minimum en gestion de projets data
- Maîtrise des principes de modélisation de données et des langages de requêtes
- Connaissance des architectures data modernes (data lake, data warehouse)
- Compétences en data modeling et conception de schémas
- Capacité à gérer les écarts de périmètre et résoudre les conflits
- Excellent sens de la communication et du leadership
- Autonomie et esprit d'initiative

CONDITIONS :
- CDI, statut cadre
- Rémunération attractive selon profil
- Télétravail partiel possible
"""


def main():
    print("=" * 80)
    print("🧪 TEST DÉTECTION CONTEXTUELLE DES COMPÉTENCES")
    print("=" * 80)
    print()

    # Initialiser l'extracteur
    print("⏳ Initialisation du SkillExtractor...")
    extractor = SkillExtractor()
    print("✅ Extracteur initialisé\n")

    # Extraire les compétences
    print("🔬 Extraction des compétences...")
    skills = extractor.extract_skills(test_description)
    print()

    # Afficher les résultats
    print("=" * 80)
    print("📊 RÉSULTATS DE DÉTECTION")
    print("=" * 80)
    print()

    # Compétences techniques
    print("💻 COMPÉTENCES TECHNIQUES :")
    print(f"   Total : {skills['skill_count']['tech']}")
    print()

    categories = {
        "Languages": skills["languages"],
        "Frameworks": skills["frameworks"],
        "Databases": skills["databases"],
        "Cloud": skills["cloud"],
        "DevOps": skills["devops"],
        "BI": skills["bi"],
        "Methods": skills["methods"],
        "Security": skills["security"],
        "Business Software": skills["business_software"],
    }

    for category, items in categories.items():
        if items:
            print(f"   {category}:")
            for item in items:
                print(f"      - {item}")

    print()

    # Compétences soft
    print("🤝 SOFT SKILLS :")
    print(f"   Total : {skills['skill_count']['soft']}")
    print()
    if skills["soft_skills"]:
        for skill in skills["soft_skills"]:
            print(f"      - {skill}")

    print()
    print("=" * 80)
    print("✅ TEST TERMINÉ")
    print("=" * 80)


if __name__ == "__main__":
    main()
