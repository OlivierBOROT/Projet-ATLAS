"""
Pipeline de Collecte et Insertion - France Travail + WTTJ
=========================================================
Collecte depuis France Travail et WTTJ, puis insère dans PostgreSQL.

⚡ PERFORMANCES:
  - France Travail: API REST (rapide) + option Selenium pour company_name
  - WTTJ: Selenium (lent, optionnel)

Usage:
    # 🚀 COLLECTE RAPIDE (recommandé - France Travail uniquement)
    python pipeline_collect.py --france-travail 200 --skip-wttj
    
    # 🎯 COLLECTE COMPLÈTE (avec WTTJ)
    python pipeline_collect.py --france-travail 150 --wttj 50
    
    # 🧪 TEST RAPIDE
    python pipeline_collect.py --dry-run --france-travail 20
"""

import argparse
import json
from datetime import datetime
from pathlib import Path

from france_travail_collector import FranceTravailCollector
from wttj_collector import WTTJCollector
from db_inserter import DBInserter


def print_separator(title: str):
    """Afficher un séparateur stylisé"""
    print("\n" + "=" * 70)
    print(f"{title:^70}")
    print("=" * 70)


def collect_france_travail(max_offers: int, use_selenium: bool = False) -> list:
    """
    Collecter depuis France Travail
    
    Args:
        max_offers: Nombre maximum d'offres à collecter
        use_selenium: Utiliser Selenium pour extraire company_name manquant
    
    Returns:
        Liste d'offres normalisées
    """
    print_separator("🇫🇷 COLLECTE FRANCE TRAVAIL (API)")
    
    try:
        collector = FranceTravailCollector(use_selenium=use_selenium)
        offers = collector.collect(max_offers=max_offers)
        
        print(f"\n✅ France Travail: {len(offers)} offres collectées")
        return offers
    
    except Exception as e:
        print(f"\n❌ Erreur France Travail: {e}")
        import traceback
        traceback.print_exc()
        return []


def collect_wttj(max_offers: int) -> list:
    """
    Collecter depuis WTTJ
    
    Args:
        max_offers: Nombre maximum d'offres à collecter
    
    Returns:
        Liste d'offres normalisées
    """
    print_separator("🌴 COLLECTE WELCOME TO THE JUNGLE (Selenium)")
    
    collector = WTTJCollector(headless=True)
    
    try:
        # Configuration par défaut
        queries = ["data analyst", "data scientist", "data engineer"]
        cities = ["Paris", "Lyon"]
        max_pages = 2
        
        print(f"\n📋 Configuration:")
        print(f"  Requêtes: {', '.join(queries)}")
        print(f"  Villes: {', '.join(cities)}")
        print(f"  Pages/requête: {max_pages}")
        print(f"  Max offres: {max_offers}")
        
        offers = collector.collect(
            queries=queries,
            cities=cities,
            max_pages_per_query=max_pages,
            max_offers=max_offers
        )
        
        print(f"\n✅ WTTJ: {len(offers)} offres collectées")
        return offers
    
    except Exception as e:
        print(f"\n❌ Erreur WTTJ: {e}")
        import traceback
        traceback.print_exc()
        return []
    
    finally:
        collector.close()


def save_backup(offers: list, source: str):
    """
    Sauvegarder un backup JSON
    
    Args:
        offers: Liste d'offres
        source: Nom de la source
    """
    if not offers:
        return
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f"backup_{source}_{timestamp}.json"
    
    Path("backups").mkdir(exist_ok=True)
    filepath = Path("backups") / filename
    
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(offers, f, ensure_ascii=False, indent=2)
    
    print(f"  💾 Backup: {filepath}")


def insert_to_database(offers: list, dry_run: bool = False):
    """
    Insérer les offres dans PostgreSQL
    
    Args:
        offers: Liste d'offres normalisées
        dry_run: Si True, simulation sans insertion
    """
    if not offers:
        print("\n⚠️ Aucune offre à insérer")
        return {"total": 0, "inserted": 0, "duplicates": 0, "errors": 0}
    
    print_separator("💾 INSERTION DANS POSTGRESQL")
    
    if dry_run:
        print("\n⚠️ MODE DRY-RUN: Simulation sans insertion réelle\n")
        return {"total": len(offers), "inserted": len(offers), "duplicates": 0, "errors": 0}
    
    try:
        inserter = DBInserter()
        stats = inserter.insert_batch(offers)
        inserter.close()
        
        return stats
    
    except Exception as e:
        print(f"\n❌ Erreur insertion: {e}")
        import traceback
        traceback.print_exc()
        return {"total": len(offers), "inserted": 0, "duplicates": 0, "errors": len(offers)}


def main():
    """Fonction principale"""
    parser = argparse.ArgumentParser(
        description="Pipeline de collecte et insertion d'offres d'emploi (France Travail + WTTJ)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemples d'utilisation:

  🚀 COLLECTE RAPIDE (recommandé - France Travail uniquement):
  python pipeline_collect.py --france-travail 200 --skip-wttj
  
  🎯 COLLECTE COMPLÈTE (France Travail + WTTJ):
  python pipeline_collect.py --france-travail 150 --wttj 50
  
  🧪 TEST RAPIDE:
  python pipeline_collect.py --dry-run --france-travail 20
  
  💡 TIPS:
  - France Travail utilise l'API (rapide)
  - WTTJ utilise Selenium (lent) - utilisez --skip-wttj pour plus de rapidité
  - --use-selenium active Selenium pour France Travail (extraction company_name)
        """
    )
    
    # Sources
    parser.add_argument(
        "--france-travail",
        type=int,
        default=0,
        help="Nombre d'offres France Travail (défaut: 0)"
    )
    
    parser.add_argument(
        "--wttj",
        type=int,
        default=0,
        help="Nombre d'offres WTTJ (défaut: 0)"
    )
    
    # Options de skip
    parser.add_argument(
        "--skip-france-travail",
        action="store_true",
        help="Ne pas collecter France Travail"
    )
    
    parser.add_argument(
        "--skip-wttj",
        action="store_true",
        help="Ne pas collecter WTTJ (recommandé pour rapidité)"
    )
    
    # Options Selenium
    parser.add_argument(
        "--use-selenium",
        action="store_true",
        help="Activer Selenium pour France Travail (extraction company_name manquant - plus lent)"
    )
    
    # Options générales
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Mode simulation (pas d'insertion en BDD)"
    )
    
    parser.add_argument(
        "--no-insert",
        action="store_true",
        help="Collecter seulement (pas d'insertion)"
    )
    
    args = parser.parse_args()
    
    # Validation : au moins une source activée
    if (args.skip_france_travail or args.france_travail == 0) and \
       (args.skip_wttj or args.wttj == 0):
        parser.error("❌ Au moins une source doit être activée (--france-travail ou --wttj)")
    
    # ========================================================================
    # BANNER & CONFIG
    # ========================================================================
    print("\n")
    print("╔" + "=" * 68 + "╗")
    print("║" + " " * 15 + "PIPELINE COLLECTE & INSERTION ATLAS" + " " * 18 + "║")
    print("╚" + "=" * 68 + "╝")
    
    start_time = datetime.now()
    
    print(f"\n⏰ Démarrage: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"\n📋 Configuration de collecte:")
    
    # Affichage de la config
    if not args.skip_france_travail and args.france_travail > 0:
        selenium_status = "ON ⚠️" if args.use_selenium else "OFF ✅"
        print(f"  🇫🇷 France Travail: {args.france_travail} offres (API + Selenium: {selenium_status})")
    
    if not args.skip_wttj and args.wttj > 0:
        print(f"  🌴 WTTJ: {args.wttj} offres (Selenium - lent 🐌)")
    
    print(f"\n📊 Options:")
    print(f"  💾 Insertion BDD: {'NON (dry-run)' if args.dry_run else 'NON' if args.no_insert else 'OUI'}")
    print(f"  💾 Backups JSON: OUI")
    
    # ========================================================================
    # ÉTAPE 1: COLLECTE
    # ========================================================================
    all_offers = []
    
    # France Travail (API + optionnel Selenium)
    if not args.skip_france_travail and args.france_travail > 0:
        ft_offers = collect_france_travail(args.france_travail, use_selenium=args.use_selenium)
        all_offers.extend(ft_offers)
        save_backup(ft_offers, "france_travail")
    
    # WTTJ (Selenium - lent)
    if not args.skip_wttj and args.wttj > 0:
        wttj_offers = collect_wttj(args.wttj)
        all_offers.extend(wttj_offers)
        save_backup(wttj_offers, "wttj")
    
    # ========================================================================
    # ÉTAPE 2: INSERTION
    # ========================================================================
    stats = {"total": 0, "inserted": 0, "duplicates": 0, "errors": 0}
    
    if all_offers and not args.no_insert:
        stats = insert_to_database(all_offers, dry_run=args.dry_run)
    
    # ========================================================================
    # RÉSUMÉ FINAL
    # ========================================================================
    print_separator("📊 RÉSUMÉ FINAL")
    
    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()
    
    print(f"\n⏱️  Durée totale: {duration:.0f}s ({duration/60:.1f} minutes)")
    
    print("\n📦 Collecte:")
    print(f"  Total offres collectées: {len(all_offers)}")
    
    if not args.skip_france_travail and args.france_travail > 0:
        ft_count = sum(1 for o in all_offers if o.get('source') == 'france_travail')
        print(f"  - France Travail: {ft_count}")
    
    if not args.skip_wttj and args.wttj > 0:
        wttj_count = sum(1 for o in all_offers if o.get('source') == 'welcome_to_the_jungle')
        print(f"  - WTTJ: {wttj_count}")
    
    if not args.no_insert:
        print("\n💾 Insertion:")
        print(f"  Offres insérées: {stats['inserted']}")
        print(f"  Doublons ignorés: {stats['duplicates']}")
        print(f"  Erreurs: {stats['errors']}")
        
        if stats['total'] > 0:
            success_rate = stats['inserted'] / stats['total'] * 100
            print(f"  Taux de succès: {success_rate:.1f}%")
    
    print("\n📁 Backups sauvegardés dans: ./backups/")
    
    # ========================================================================
    # MESSAGES FINAUX & TIPS
    # ========================================================================
    print("\n" + "=" * 70)
    
    if args.dry_run:
        print("⚠️  MODE DRY-RUN: Aucune donnée insérée en base")
        print("   Relancez sans --dry-run pour insertion réelle")
    elif args.no_insert:
        print("📦 COLLECTE TERMINÉE (pas d'insertion)")
        print("   Utilisez les backups JSON pour insertion ultérieure")
    elif stats['inserted'] > 0:
        print("✅ PIPELINE TERMINÉ AVEC SUCCÈS!")
        print(f"   {stats['inserted']} nouvelles offres dans la base ATLAS")
    else:
        print("⚠️  PIPELINE TERMINÉ AVEC AVERTISSEMENTS")
        print("   Vérifier les logs ci-dessus pour détails")
    
    # Tips d'optimisation
    print("\n💡 TIPS D'OPTIMISATION:")
    
    if args.use_selenium:
        print("   - Désactivez --use-selenium pour France Travail (plus rapide)")
    
    if not args.skip_wttj and args.wttj > 0:
        print("   - WTTJ utilise Selenium (lent). Utilisez --skip-wttj pour plus de rapidité")
    
    print("\n🚀 COMMANDE OPTIMALE (la plus rapide):")
    print("   python pipeline_collect.py --france-travail 200 --skip-wttj")
    
    print("=" * 70 + "\n")


if __name__ == "__main__":
    main()
