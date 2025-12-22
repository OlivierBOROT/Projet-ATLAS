"""
Test Collecteurs - 10 offres par source
========================================
Teste la collecte de 10 offres depuis chaque source pour vérifier
que tous les champs sont correctement extraits.

Usage:
    python test_collect.py
"""

import json
from datetime import datetime
from france_travail_collector import FranceTravailCollector
from wttj_collector import WTTJCollector


def print_separator(title: str):
    """Afficher un séparateur"""
    print("\n" + "=" * 70)
    print(f"{title:^70}")
    print("=" * 70)


def print_offer_details(offer: dict, index: int):
    """Afficher les détails d'une offre"""
    print(f"\n[{index}] {offer.get('title', 'N/A')}")
    print("-" * 70)
    
    fields = [
        ("External ID", "external_id"),
        ("Entreprise", "company_name"),
        ("Ville", "location_city"),
        ("Code postal", "location_postal_code"),
        ("Type de contrat", "contract_type"),
        ("Salaire", "salary_text"),
        ("Date publication", "published_date"),
        ("URL", "url"),
        ("Source", "source"),
    ]
    
    for label, key in fields:
        value = offer.get(key, "N/A")
        if value:
            print(f"  {label:20s}: {str(value)[:60]}")
        else:
            print(f"  {label:20s}: ❌ MANQUANT")
    
    # Description (aperçu)
    desc = offer.get("description", "")
    if desc:
        print(f"  {'Description':20s}: {len(desc)} caractères")
        print(f"  {'Aperçu':20s}: {desc[:100]}...")
    else:
        print(f"  {'Description':20s}: ❌ MANQUANTE")


def analyze_completeness(offers: list, source_name: str):
    """Analyser la complétude des données"""
    print_separator(f"📊 ANALYSE - {source_name}")
    
    total = len(offers)
    
    fields_stats = {
        "title": 0,
        "company_name": 0,
        "description": 0,
        "location_city": 0,
        "contract_type": 0,
        "salary_text": 0,
        "published_date": 0,
        "url": 0
    }
    
    for offer in offers:
        for field in fields_stats:
            if offer.get(field):
                fields_stats[field] += 1
    
    print(f"\nTotal d'offres: {total}")
    print("\nComplétude par champ:")
    print("-" * 40)
    
    for field, count in fields_stats.items():
        percentage = (count / total * 100) if total > 0 else 0
        status = "✅" if percentage >= 80 else "⚠️" if percentage >= 50 else "❌"
        print(f"  {status} {field:20s}: {count:2d}/{total} ({percentage:5.1f}%)")


def test_france_travail():
    """Tester France Travail"""
    print_separator("🇫🇷 TEST FRANCE TRAVAIL")
    
    print("\n🔄 Initialisation du collecteur...")
    collector = FranceTravailCollector()
    
    print("📡 Collecte de 10 offres...")
    offers = collector.collect(max_offers=10)
    
    if not offers:
        print("❌ Aucune offre collectée")
        return []
    
    print(f"\n✅ {len(offers)} offres collectées")
    
    # Afficher les détails
    print_separator("📋 DÉTAILS DES OFFRES - FRANCE TRAVAIL")
    
    for i, offer in enumerate(offers, 1):
        print_offer_details(offer, i)
    
    # Analyse
    analyze_completeness(offers, "FRANCE TRAVAIL")
    
    # Sauvegarder
    filename = f"test_france_travail_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(offers, f, ensure_ascii=False, indent=2)
    
    print(f"\n💾 Sauvegardé: {filename}")
    
    return offers


def test_wttj():
    """Tester WTTJ"""
    print_separator("🌴 TEST WELCOME TO THE JUNGLE")
    
    print("\n🔄 Initialisation du collecteur...")
    collector = WTTJCollector(headless=True)
    
    try:
        print("📡 Collecte de 10 offres...")
        offers = collector.collect(
            queries=["data analyst"],
            cities=["Paris"],
            max_pages_per_query=1,
            max_offers=10
        )
        
        if not offers:
            print("❌ Aucune offre collectée")
            return []
        
        print(f"\n✅ {len(offers)} offres collectées")
        
        # Afficher les détails
        print_separator("📋 DÉTAILS DES OFFRES - WTTJ")
        
        for i, offer in enumerate(offers, 1):
            print_offer_details(offer, i)
        
        # Analyse
        analyze_completeness(offers, "WELCOME TO THE JUNGLE")
        
        # Sauvegarder
        filename = f"test_wttj_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(offers, f, ensure_ascii=False, indent=2)
        
        print(f"\n💾 Sauvegardé: {filename}")
        
        return offers
    
    finally:
        collector.close()


def compare_sources(ft_offers: list, wttj_offers: list):
    """Comparer les deux sources"""
    print_separator("🔍 COMPARAISON DES SOURCES")
    
    print("\n📊 Statistiques comparatives:")
    print("-" * 70)
    print(f"{'':30s} {'France Travail':^18s} {'WTTJ':^18s}")
    print("-" * 70)
    
    stats = [
        ("Nombre d'offres", len(ft_offers), len(wttj_offers)),
        ("Avec titre", 
         sum(1 for o in ft_offers if o.get('title')),
         sum(1 for o in wttj_offers if o.get('title'))),
        ("Avec entreprise",
         sum(1 for o in ft_offers if o.get('company_name')),
         sum(1 for o in wttj_offers if o.get('company_name'))),
        ("Avec description",
         sum(1 for o in ft_offers if o.get('description')),
         sum(1 for o in wttj_offers if o.get('description'))),
        ("Avec localisation",
         sum(1 for o in ft_offers if o.get('location_city')),
         sum(1 for o in wttj_offers if o.get('location_city'))),
        ("Avec contrat",
         sum(1 for o in ft_offers if o.get('contract_type')),
         sum(1 for o in wttj_offers if o.get('contract_type'))),
        ("Avec salaire",
         sum(1 for o in ft_offers if o.get('salary_text')),
         sum(1 for o in wttj_offers if o.get('salary_text'))),
    ]
    
    for label, ft_val, wttj_val in stats:
        print(f"{label:30s} {ft_val:^18d} {wttj_val:^18d}")
    
    print("-" * 70)
    
    # Recommandations
    print("\n💡 RECOMMANDATIONS:")
    
    if len(ft_offers) < 5:
        print("  ⚠️ France Travail: Peu d'offres collectées, vérifier les credentials API")
    
    if len(wttj_offers) < 5:
        print("  ⚠️ WTTJ: Peu d'offres collectées, vérifier le scraping Selenium")
    
    ft_desc_rate = sum(1 for o in ft_offers if o.get('description')) / len(ft_offers) * 100 if ft_offers else 0
    wttj_desc_rate = sum(1 for o in wttj_offers if o.get('description')) / len(wttj_offers) * 100 if wttj_offers else 0
    
    if ft_desc_rate < 80:
        print(f"  ⚠️ France Travail: Taux de descriptions faible ({ft_desc_rate:.0f}%)")
    
    if wttj_desc_rate < 80:
        print(f"  ⚠️ WTTJ: Taux de descriptions faible ({wttj_desc_rate:.0f}%)")
    
    if ft_offers and wttj_offers and ft_desc_rate >= 80 and wttj_desc_rate >= 80:
        print("  ✅ Les deux sources sont opérationnelles et complètes!")


def main():
    """Fonction principale"""
    print("\n")
    print("╔" + "=" * 68 + "╗")
    print("║" + " " * 15 + "TEST COLLECTEURS - 10 OFFRES/SOURCE" + " " * 18 + "║")
    print("╚" + "=" * 68 + "╝")
    
    print("\nCe test va:")
    print("  1️⃣  Collecter 10 offres depuis France Travail")
    print("  2️⃣  Collecter 10 offres depuis WTTJ")
    print("  3️⃣  Afficher tous les champs extraits")
    print("  4️⃣  Analyser la complétude des données")
    print("  5️⃣  Comparer les deux sources")
    
    input("\n▶️  Appuyez sur ENTRÉE pour démarrer...")
    
    # Test France Travail
    ft_offers = test_france_travail()
    
    # Test WTTJ
    wttj_offers = test_wttj()
    
    # Comparaison
    if ft_offers or wttj_offers:
        compare_sources(ft_offers, wttj_offers)
    
    # Résumé final
    print_separator("✅ TEST TERMINÉ")
    
    print("\n📁 Fichiers générés:")
    print("  - test_france_travail_*.json")
    print("  - test_wttj_*.json")
    
    print("\n🚀 Prochaines étapes:")
    print("  1. Vérifier la qualité des données dans les fichiers JSON")
    print("  2. Si tout est OK, lancer: python pipeline_collect.py")
    print("  3. Les offres seront collectées et insérées dans la BDD")
    
    print("\n" + "=" * 70)


if __name__ == "__main__":
    main()
