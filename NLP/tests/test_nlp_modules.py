"""
test_nlp_modules.py

Script de test pour valider les modules NLP sur les offres exemples.

Teste :
- Nettoyage de texte (encodage, HTML, normalisation)
- Extraction de compétences (tech + soft skills)
- Extraction d'informations (salaires, expérience, diplômes)
"""

import json
import sys
from pathlib import Path

# Ajouter le chemin des modules
sys.path.insert(0, str(Path(__file__).parent.parent / "modules"))

from text_cleaner import TextCleaner
from skill_extractor import SkillExtractor
from info_extractor import InfoExtractor


def print_section(title: str):
    """Affiche un séparateur de section"""
    print("\n" + "=" * 80)
    print(f"  {title}")
    print("=" * 80 + "\n")


def test_text_cleaning():
    """Test le nettoyage de texte"""
    print_section("TEST 1 : NETTOYAGE DE TEXTE")

    cleaner = TextCleaner()

    # Texte avec problèmes d'encodage
    test_text = "Développeur Web PHP / SQL / JS / AJAX (H/F)"

    print(f"Texte original :\n{test_text}\n")

    # Nettoyer
    cleaned = cleaner.clean_text(test_text)
    print(f"Texte nettoyé :\n{cleaned}\n")

    # Lemmatiser
    lemmas = cleaner.lemmatize(cleaned)
    print(f"Lemmes extraits :")
    print(f"  {', '.join(lemmas)}\n")


def test_skill_extraction(offer: dict):
    """Test l'extraction de compétences"""
    print_section(f"TEST 2 : EXTRACTION COMPÉTENCES - {offer['title']}")

    extractor = SkillExtractor()

    # Extraire toutes les compétences
    skills = extractor.extract_skills(offer["description"])

    print(
        f"📊 Résumé : {skills['skill_count']['tech']} compétences tech, "
        f"{skills['skill_count']['soft']} soft skills\n"
    )

    # Afficher par catégorie
    if skills["languages"]:
        print(f"💻 Langages ({len(skills['languages'])}) :")
        print(f"   {', '.join(skills['languages'])}\n")

    if skills["frameworks"]:
        print(f"🔧 Frameworks ({len(skills['frameworks'])}) :")
        print(f"   {', '.join(skills['frameworks'])}\n")

    if skills["databases"]:
        print(f"🗄️  Bases de données ({len(skills['databases'])}) :")
        print(f"   {', '.join(skills['databases'])}\n")

    if skills["cloud"]:
        print(f"☁️  Cloud & Infrastructure ({len(skills['cloud'])}) :")
        print(f"   {', '.join(skills['cloud'])}\n")

    if skills["devops"]:
        print(f"⚙️  DevOps ({len(skills['devops'])}) :")
        print(f"   {', '.join(skills['devops'])}\n")

    if skills["methods"]:
        print(f"📋 Méthodes ({len(skills['methods'])}) :")
        print(f"   {', '.join(skills['methods'])}\n")

    if skills["soft_skills"]:
        print(f"🤝 Soft Skills ({len(skills['soft_skills'])}) :")
        print(f"   {', '.join(skills['soft_skills'][:10])}")
        if len(skills["soft_skills"]) > 10:
            print(f"   ... et {len(skills['soft_skills']) - 10} autres\n")
        else:
            print()

    # Top 10 compétences
    top_skills = extractor.get_top_skills(offer["description"], n=10)
    print(f"🏆 Top 10 compétences (pondérées) :")
    for skill, score in top_skills:
        print(f"   • {skill:30} (score: {score:.1f})")

    # Catégorisation du profil
    print("\n🎯 Catégorisation de l'offre :")
    category = extractor.categorize_offer(offer["description"])
    print(f"   Profil dominant : {category['dominant_profile']}")
    print(f"   Score : {category['profile_score']}")
    if category["is_full_stack"]:
        print(f"   ⚠️  Profil Full Stack détecté !")


def test_info_extraction(offer: dict):
    """Test l'extraction d'informations structurées"""
    print_section(f"TEST 3 : EXTRACTION INFOS - {offer['title']}")

    extractor = InfoExtractor()

    # Tout extraire
    info = extractor.extract_all(offer["description"])

    # Salaire
    print("💰 Salaire :")
    if info["salary"]["min"] or info["salary"]["max"]:
        print(
            f"   Fourchette : {info['salary']['min']:,}€ - {info['salary']['max']:,}€ /an (brut)"
        )
    else:
        print(f"   Non spécifié")

    # Expérience
    print("\n📅 Expérience :")
    if info["experience"]["min"] is not None:
        if info["experience"]["min"] == info["experience"]["max"]:
            print(f"   {info['experience']['min']} ans")
        else:
            print(f"   {info['experience']['min']} à {info['experience']['max']} ans")
        print(f"   Niveau : {info['experience']['level']}")
    else:
        print(f"   Non spécifié")

    # Diplôme
    print("\n🎓 Formation :")
    if info["education"]["level"]:
        print(f"   Niveau : Bac+{info['education']['level']}")
        print(f"   Type : {info['education']['degree_type']}")
    else:
        print(f"   Non spécifié")

    # Type de contrat
    print("\n📝 Type(s) de contrat :")
    if info["contract_types"]:
        print(f"   {', '.join(info['contract_types'])}")
    else:
        print(f"   Non spécifié")

    # Télétravail
    print("\n🏠 Télétravail :")
    if info["remote"]["remote_possible"]:
        if info["remote"]["remote_days"]:
            print(
                f"   {info['remote']['remote_days']} jours/semaine ({info['remote']['remote_percentage']}%)"
            )
        elif info["remote"]["remote_percentage"]:
            print(f"   {info['remote']['remote_percentage']}%")
        else:
            print(f"   Possible (détails non précisés)")
    else:
        print(f"   Non mentionné")


def test_complete_pipeline(offer: dict):
    """Test le pipeline complet sur une offre"""
    print_section(f"PIPELINE COMPLET - {offer['title']}")

    cleaner = TextCleaner()
    skill_extractor = SkillExtractor()
    info_extractor = InfoExtractor()

    # Étape 1 : Nettoyage
    print("⏳ Étape 1/3 : Nettoyage...")
    cleaned = cleaner.clean_text(offer["description"])
    lemmas = cleaner.lemmatize(cleaned)
    print(f"   ✅ Texte nettoyé ({len(cleaned)} caractères)")
    print(f"   ✅ {len(lemmas)} lemmes extraits")

    # Étape 2 : Extraction compétences
    print("\n⏳ Étape 2/3 : Extraction compétences...")
    skills = skill_extractor.extract_skills(offer["description"])
    category = skill_extractor.categorize_offer(offer["description"])
    print(f"   ✅ {skills['skill_count']['tech']} compétences techniques")
    print(f"   ✅ {skills['skill_count']['soft']} soft skills")
    print(f"   ✅ Profil : {category['dominant_profile']}")

    # Étape 3 : Extraction infos
    print("\n⏳ Étape 3/3 : Extraction informations...")
    info = info_extractor.extract_all(offer["description"])

    extracted_count = 0
    if info["salary"]["min"]:
        print(
            f"   ✅ Salaire : {info['salary']['min']:,}€ - {info['salary']['max']:,}€"
        )
        extracted_count += 1
    if info["experience"]["min"] is not None:
        print(
            f"   ✅ Expérience : {info['experience']['min']}-{info['experience']['max']} ans ({info['experience']['level']})"
        )
        extracted_count += 1
    if info["education"]["level"]:
        print(f"   ✅ Formation : Bac+{info['education']['level']}")
        extracted_count += 1
    if info["contract_types"]:
        print(f"   ✅ Contrat : {', '.join(info['contract_types'])}")
        extracted_count += 1
    if info["remote"]["remote_possible"]:
        print(f"   ✅ Télétravail : Oui")
        extracted_count += 1

    print(f"\n📊 Résumé : {extracted_count}/5 informations extraites")

    # Résultat structuré
    result = {
        "offer_id": offer["id"],
        "title": offer["title"],
        "company": offer["company"],
        "cleaned_text": cleaned,
        "lemmas_count": len(lemmas),
        "skills": {
            "tech": skills["all_tech_skills"],
            "soft": skills["soft_skills"],
            "count": skills["skill_count"],
        },
        "category": category,
        "info": info,
    }

    return result


def main():
    """Fonction principale"""
    print("\n" + "🎯" * 40)
    print("  TEST DES MODULES NLP - PROJET ATLAS")
    print("🎯" * 40)

    # Charger les exemples
    json_path = Path(__file__).parent / "example_offers.json"

    try:
        with open(json_path, "r", encoding="utf-8") as f:
            offers = json.load(f)

        print(f"\n✅ {len(offers)} offres chargées depuis {json_path.name}\n")

    except FileNotFoundError:
        print(f"\n❌ Fichier {json_path} introuvable !")
        return

    # Test 1 : Nettoyage de texte
    test_text_cleaning()

    input("\nAppuyez sur Entrée pour continuer...")

    # Test 2 & 3 : Pour chaque offre
    for i, offer in enumerate(offers, 1):
        print(f"\n{'#' * 80}")
        print(f"  OFFRE {i}/{len(offers)}")
        print(f"{'#' * 80}")

        # Extraction compétences
        test_skill_extraction(offer)

        input("\nAppuyez sur Entrée pour continuer...")

        # Extraction infos
        test_info_extraction(offer)

        input("\nAppuyez sur Entrée pour continuer...")

    # Pipeline complet sur la première offre
    print("\n\n" + "🚀" * 40)
    print("  DÉMONSTRATION PIPELINE COMPLET")
    print("🚀" * 40)

    result = test_complete_pipeline(offers[0])

    # Sauvegarder le résultat
    output_path = Path(__file__).parent / "test_result.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print(f"\n✅ Résultat sauvegardé dans : {output_path.name}")

    print("\n" + "✅" * 40)
    print("  TESTS TERMINÉS AVEC SUCCÈS")
    print("✅" * 40 + "\n")


if __name__ == "__main__":
    main()
