"""
Script d'enrichissement massif des offres existantes avec NLP
================================================================

Ce script traite TOUTES les offres de la base de données avec les modules NLP :
- TextCleaner : nettoyage et lemmatisation
- SkillExtractor : extraction des compétences techniques et soft skills
- InfoExtractor : extraction des informations structurées

Mode d'exécution :
------------------
1. DRY-RUN (par défaut) : teste sur 10 offres sans écrire en BDD
2. BATCH : traite toutes les offres par batch de 100

Usage :
-------
# Test sur 10 offres
python enrich_existing_offers.py --dry-run

# Traitement complet
python enrich_existing_offers.py --batch-size 100

# Reprendre après une interruption
python enrich_existing_offers.py --resume

Date: 2025-12-31
"""

import os
import sys
import argparse
import psycopg2
from psycopg2.extras import execute_values
from dotenv import load_dotenv
from datetime import datetime
from tqdm import tqdm
import logging

# Ajouter le chemin des modules NLP
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "modules"))

from text_cleaner import TextCleaner
from skill_extractor import SkillExtractor
from info_extractor import InfoExtractor

# Forcer l'encodage UTF-8 pour stdout/stderr sur Windows AVANT la configuration du logging
if sys.platform == "win32":
    import io

    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8")

# Configuration du logging avec encodage UTF-8
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(
            f'enrichment_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log',
            encoding="utf-8",
        ),
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger(__name__)

# Charger les variables d'environnement
load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")


class OfferEnricher:
    """Classe pour enrichir les offres avec NLP"""

    def __init__(self):
        """Initialise les modules NLP"""
        logger.info("⏳ Initialisation des modules NLP...")
        self.cleaner = TextCleaner()
        self.skill_extractor = SkillExtractor()
        self.info_extractor = InfoExtractor()
        logger.info("✅ Modules NLP initialisés")
        logger.info(
            f"   - {len(self.skill_extractor.all_tech_skills)} compétences tech"
        )
        logger.info(f"   - {len(self.skill_extractor.soft_skills)} soft skills")

    def process_offer(self, offer_id, description):
        """
        Traite une offre avec les 3 modules NLP

        Args:
            offer_id: ID de l'offre
            description: Texte de l'offre

        Returns:
            dict avec les résultats NLP
        """
        try:
            # 1. NETTOYAGE ET LEMMATISATION
            cleaned = self.cleaner.clean_text(description)
            lemmas = self.cleaner.lemmatize(cleaned)
            # description_cleaned = version lemmatisée sans stopwords
            description_cleaned = " ".join(lemmas)

            # 2. EXTRACTION SKILLS
            skills = self.skill_extractor.extract_skills(description)
            category = self.skill_extractor.categorize_offer(description)

            # Calcul du profile_confidence (en pourcentage)
            max_score = 10  # On considère 10+ skills comme 100%
            profile_confidence = min(
                100, int((category["profile_score"] / max_score) * 100)
            )

            # 3. EXTRACTION INFOS
            info = self.info_extractor.extract_all(description)

            return {
                "offer_id": offer_id,
                "description_cleaned": description_cleaned,
                "skills_tech": skills["all_tech_skills"],
                "skills_soft": skills["soft_skills"],
                "profile_category": category["dominant_profile"],
                "profile_confidence": profile_confidence,
                "education_level": info["education"]["level"],
                "education_type": info["education"]["degree_type"],
                "remote_possible": info["remote"]["remote_possible"],
                "remote_days": info["remote"]["remote_days"],
                "remote_percentage": info["remote"]["remote_percentage"],
                "success": True,
                "error": None,
            }
        except Exception as e:
            logger.error(f"❌ Erreur traitement offre {offer_id}: {str(e)}")
            return {"offer_id": offer_id, "success": False, "error": str(e)}

    def update_offer_in_db(self, conn, result):
        """
        Met à jour une offre dans la BDD avec les résultats NLP

        Args:
            conn: Connexion psycopg2
            result: Résultats du traitement NLP
        """
        if not result["success"]:
            return False

        try:
            cursor = conn.cursor()

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
                    result["description_cleaned"],
                    result["profile_category"],
                    result["profile_confidence"],
                    result["education_level"],
                    result["education_type"],
                    result["remote_possible"],
                    result["remote_days"],
                    result["remote_percentage"],
                    result["offer_id"],
                ),
            )

            # 2. Mise à jour du tableau skills_extracted dans fact_job_offers
            all_skills = result["skills_tech"] + result["skills_soft"]
            cursor.execute(
                """
                UPDATE fact_job_offers
                SET skills_extracted = %s
                WHERE offer_id = %s
            """,
                (all_skills, result["offer_id"]),
            )

            # 3. Insertion des skills techniques dans dim_skills (si nouvelles)
            if result["skills_tech"]:
                for skill in result["skills_tech"]:
                    cursor.execute(
                        """
                        INSERT INTO dim_skills (skill_name, skill_category)
                        VALUES (%s, 'technical')
                        ON CONFLICT (skill_name) DO NOTHING
                    """,
                        (skill,),
                    )

            # 4. Insertion des soft skills dans dim_skills (si nouvelles)
            if result["skills_soft"]:
                for skill in result["skills_soft"]:
                    cursor.execute(
                        """
                        INSERT INTO dim_skills (skill_name, skill_category)
                        VALUES (%s, 'soft')
                        ON CONFLICT (skill_name) DO NOTHING
                    """,
                        (skill,),
                    )

            # 5. Création des relations offer-skill dans fact_offer_skills
            for skill in all_skills:
                cursor.execute(
                    """
                    INSERT INTO fact_offer_skills (offer_id, skill_id)
                    SELECT %s, skill_id 
                    FROM dim_skills 
                    WHERE skill_name = %s
                    ON CONFLICT (offer_id, skill_id) DO NOTHING
                """,
                    (result["offer_id"], skill),
                )

            conn.commit()
            cursor.close()
            return True

        except Exception as e:
            logger.error(
                f"❌ Erreur mise à jour BDD offre {result['offer_id']}: {str(e)}"
            )
            conn.rollback()
            return False

    def enrich_offers(self, dry_run=True, batch_size=100, resume=False):
        """
        Enrichit toutes les offres de la BDD

        Args:
            dry_run: Si True, teste sur 10 offres sans écrire en BDD
            batch_size: Taille des batchs de traitement
            resume: Si True, reprend les offres non traitées uniquement
        """
        logger.info("=" * 80)
        logger.info("🚀 DÉBUT DE L'ENRICHISSEMENT NLP")
        logger.info("=" * 80)

        if dry_run:
            logger.info("⚠️  MODE DRY-RUN : Test sur 10 offres (sans modification BDD)")
        else:
            logger.info(f"✅ MODE BATCH : Traitement complet par batch de {batch_size}")

        # Connexion BDD
        conn = psycopg2.connect(DATABASE_URL)
        cursor = conn.cursor()

        # Récupérer les offres à traiter
        if resume:
            where_clause = "processed = FALSE AND"
            logger.info(
                "🔄 Mode RESUME : traitement des offres non traitées uniquement"
            )
        else:
            where_clause = ""
            logger.info("🆕 Mode COMPLET : traitement de toutes les offres")

        if dry_run:
            limit_clause = "LIMIT 10"
        else:
            limit_clause = ""

        query = f"""
            SELECT offer_id, description
            FROM fact_job_offers
            WHERE {where_clause}
                description IS NOT NULL
                AND LENGTH(description) > 100
            ORDER BY offer_id
            {limit_clause}
        """

        cursor.execute(query)
        offers = cursor.fetchall()
        total_offers = len(offers)

        logger.info(f"\n📊 {total_offers} offres à traiter")

        # Statistiques
        stats = {"total": total_offers, "success": 0, "errors": 0, "skipped": 0}

        # Traitement avec barre de progression
        for offer_id, description in tqdm(offers, desc="Enrichissement"):
            # Traiter l'offre
            result = self.process_offer(offer_id, description)

            if result["success"]:
                # Mise à jour en BDD (sauf en dry-run)
                if not dry_run:
                    if self.update_offer_in_db(conn, result):
                        stats["success"] += 1
                    else:
                        stats["errors"] += 1
                else:
                    # En dry-run, on log TOUS les détails de l'offre
                    logger.info("\n" + "=" * 80)
                    logger.info(f"📋 OFFRE #{offer_id}")
                    logger.info("=" * 80)

                    # Description originale (extrait)
                    desc_preview = (
                        description[:200] + "..."
                        if len(description) > 200
                        else description
                    )
                    logger.info(
                        f"\n📄 Description originale (extrait) :\n{desc_preview}\n"
                    )

                    # Description nettoyée (lemmatisée sans stopwords) - extrait
                    cleaned_preview = (
                        result["description_cleaned"][:300] + "..."
                        if len(result["description_cleaned"]) > 300
                        else result["description_cleaned"]
                    )
                    logger.info(
                        f"🧹 Description cleaned (lemmatisée, extrait) :\n{cleaned_preview}\n"
                    )

                    # Résultats NLP
                    logger.info(f"🎯 PROFIL IDENTIFIÉ :")
                    logger.info(f"   Catégorie : {result['profile_category']}")
                    logger.info(f"   Confiance : {result['profile_confidence']}%")

                    logger.info(
                        f"\n💻 COMPÉTENCES TECHNIQUES ({len(result['skills_tech'])}) :"
                    )
                    if result["skills_tech"]:
                        logger.info(f"   {', '.join(result['skills_tech'][:10])}")
                        if len(result["skills_tech"]) > 10:
                            logger.info(
                                f"   ... et {len(result['skills_tech']) - 10} autres"
                            )
                    else:
                        logger.info("   Aucune compétence technique détectée")

                    logger.info(f"\n🤝 SOFT SKILLS ({len(result['skills_soft'])}) :")
                    if result["skills_soft"]:
                        logger.info(f"   {', '.join(result['skills_soft'][:10])}")
                        if len(result["skills_soft"]) > 10:
                            logger.info(
                                f"   ... et {len(result['skills_soft']) - 10} autres"
                            )
                    else:
                        logger.info("   Aucune soft skill détectée")

                    logger.info(f"\n📋 INFORMATIONS EXTRAITES :")
                    if result["education_level"]:
                        logger.info(
                            f"   🎓 Formation : Bac+{result['education_level']} ({result['education_type']})"
                        )
                    else:
                        logger.info("   🎓 Formation : Non spécifiée")

                    if result["remote_possible"]:
                        if result["remote_days"]:
                            logger.info(
                                f"   🏠 Télétravail : {result['remote_days']} jours/semaine ({result['remote_percentage']}%)"
                            )
                        elif result["remote_percentage"]:
                            logger.info(
                                f"   🏠 Télétravail : {result['remote_percentage']}%"
                            )
                        else:
                            logger.info("   🏠 Télétravail : Possible")
                    else:
                        logger.info("   🏠 Télétravail : Non mentionné")

                    stats["success"] += 1
            else:
                stats["errors"] += 1

        # Fermeture connexion
        cursor.close()
        conn.close()

        # Résumé
        logger.info("\n" + "=" * 80)
        logger.info("📊 RÉSUMÉ DE L'ENRICHISSEMENT")
        logger.info("=" * 80)
        logger.info(
            f"   Total traité : {stats['success'] + stats['errors']}/{stats['total']}"
        )
        logger.info(f"   ✅ Succès : {stats['success']}")
        logger.info(f"   ❌ Erreurs : {stats['errors']}")

        success_rate = (
            (stats["success"] / stats["total"] * 100) if stats["total"] > 0 else 0
        )
        logger.info(f"   📈 Taux de succès : {success_rate:.1f}%")

        if dry_run:
            logger.info("\n⚠️  MODE DRY-RUN : Aucune modification effectuée en BDD")
            logger.info(
                "   Pour lancer le traitement complet : python enrich_existing_offers.py"
            )
        else:
            logger.info("\n✅ Enrichissement terminé !")


def main():
    """Point d'entrée principal"""
    parser = argparse.ArgumentParser(
        description="Enrichissement NLP des offres d'emploi"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        default=True,
        help="Mode test sur 10 offres (défaut: True)",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=100,
        help="Taille des batchs de traitement (défaut: 100)",
    )
    parser.add_argument(
        "--resume",
        action="store_true",
        help="Reprendre les offres non traitées uniquement",
    )
    parser.add_argument(
        "--full",
        action="store_true",
        help="Désactive le mode dry-run (traitement complet)",
    )

    args = parser.parse_args()

    # Si --full est spécifié, désactiver dry-run
    if args.full:
        args.dry_run = False

    # Créer l'enrichisseur et lancer le traitement
    enricher = OfferEnricher()
    enricher.enrich_offers(
        dry_run=args.dry_run, batch_size=args.batch_size, resume=args.resume
    )


if __name__ == "__main__":
    main()
