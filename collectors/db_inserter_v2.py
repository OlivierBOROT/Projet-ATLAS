"""
Inserteur d'offres dans PostgreSQL - VERSION 2
===============================================
Utilise le référentiel ref_communes_france au lieu de dim_locations

Changements vs v1:
- ✅ Utilise commune_id (ref_communes_france) au lieu de location_id (dim_locations)
- ✅ Pas de création dynamique de localisations
- ✅ Matching intelligent avec GeoMatcher
- ✅ Logging des communes non trouvées

Usage:
    from db_inserter_v2 import DBInserterV2
    inserter = DBInserterV2()
    inserter.insert_batch(offers)
"""

import os
import logging
from typing import Dict, List
from datetime import datetime
from pathlib import Path

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import IntegrityError
from dotenv import load_dotenv

from geo_matcher import GeoMatcher

# Charger .env
env_path = Path(__file__).parent.parent / '.env'
if env_path.exists():
    load_dotenv(dotenv_path=env_path)
else:
    load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("DBInserterV2")


class DBInserterV2:
    """Inserteur d'offres dans PostgreSQL avec référentiel géographique"""
    
    def __init__(self):
        """Initialiser la connexion PostgreSQL et le GeoMatcher"""
        database_url = os.getenv("DATABASE_URL")
        if not database_url:
            raise ValueError("❌ DATABASE_URL requis dans .env")
        
        self.engine = create_engine(database_url)
        Session = sessionmaker(bind=self.engine)
        self.session = Session()
        
        # Initialiser le GeoMatcher
        self.geo_matcher = GeoMatcher(database_url)
        
        # Compteurs pour stats
        self.communes_not_found = []
        
        logger.info("✅ Connexion PostgreSQL établie")
        logger.info("✅ GeoMatcher initialisé")
    
    def get_or_create_source(self, source_name: str) -> int:
        """Récupère ou crée une source"""
        q = text("SELECT source_id FROM dim_sources WHERE source_name=:name")
        r = self.session.execute(q, {"name": source_name}).fetchone()
        
        if r:
            return r[0]
        
        # Créer la source
        source_type = "api" if source_name == "france_travail" else "scraping"
        is_official = source_name == "france_travail"
        
        q = text("""
            INSERT INTO dim_sources (source_name, source_type, is_official, description)
            VALUES (:name, :type, :official, :desc)
            RETURNING source_id
        """)
        
        r = self.session.execute(q, {
            "name": source_name,
            "type": source_type,
            "official": is_official,
            "desc": f"Source {source_name}"
        })
        self.session.commit()
        
        return r.fetchone()[0]
    
    def get_or_create_date(self, iso_date: str) -> int:
        """Récupère ou crée une date"""
        if not iso_date:
            return None
        
        try:
            d = datetime.fromisoformat(iso_date.replace("Z", "+00:00")).date()
        except:
            return None
        
        # Chercher date existante
        q = text("SELECT date_id FROM dim_dates WHERE full_date=:d")
        r = self.session.execute(q, {"d": d}).fetchone()
        
        if r:
            return r[0]
        
        # Créer nouvelle date
        month_names = ['', 'Janvier', 'Février', 'Mars', 'Avril', 'Mai', 'Juin',
                       'Juillet', 'Août', 'Septembre', 'Octobre', 'Novembre', 'Décembre']
        day_names = ['Lundi', 'Mardi', 'Mercredi', 'Jeudi', 'Vendredi', 'Samedi', 'Dimanche']
        
        q = text("""
            INSERT INTO dim_dates
            (full_date, year, quarter, month, month_name, week, day_of_week, day_name, is_weekend)
            VALUES (:d, :y, :q, :m, :mn, :w, :dw, :dn, :we)
            RETURNING date_id
        """)
        
        r = self.session.execute(q, {
            "d": d,
            "y": d.year,
            "q": (d.month - 1) // 3 + 1,
            "m": d.month,
            "mn": month_names[d.month],
            "w": d.isocalendar()[1],
            "dw": d.weekday() + 1,
            "dn": day_names[d.weekday()],
            "we": d.weekday() >= 5
        })
        self.session.commit()
        
        return r.fetchone()[0]
    
    def get_commune_id(self, offer: Dict) -> int:
        """
        Récupère le commune_id depuis ref_communes_france
        
        Args:
            offer: Offre normalisée
        
        Returns:
            commune_id ou None si non trouvé
        """
        city = offer.get("location_city", "").strip()
        postal_code = offer.get("location_postal_code", "")
        
        if not city:
            return None
        
        # Utiliser le GeoMatcher
        commune_id = self.geo_matcher.find_commune_id(city, postal_code)
        
        # Logger si non trouvé
        if not commune_id:
            location_str = f"{city} ({postal_code})" if postal_code else city
            self.communes_not_found.append(location_str)
            logger.warning(f"⚠️ Commune non trouvée: {location_str}")
        
        return commune_id
    
    def get_job_category_from_title(self, title: str) -> tuple:
        """
        Déterminer la catégorie depuis le titre (pour sources sans ROME)
        
        Returns:
            (category_name, category_code)
        """
        title_lower = title.lower()
        
        # Mapping titre → catégorie
        if any(kw in title_lower for kw in ['data analyst', 'analyste de données', 'analyste data', 'business analyst data']):
            return ('Data Analyst', 'WTTJ_DA')
        
        elif any(kw in title_lower for kw in ['data scientist', 'scientist']):
            return ('Data Scientist', 'WTTJ_DS')
        
        elif any(kw in title_lower for kw in ['data engineer', 'ingénieur data', 'ingénieur données']):
            return ('Data Engineer', 'WTTJ_DE')
        
        elif any(kw in title_lower for kw in ['machine learning', 'ml engineer', 'ai engineer']):
            return ('ML Engineer', 'WTTJ_ML')
        
        elif any(kw in title_lower for kw in ['développeur', 'developer', 'dev ']):
            return ('Développeur', 'DEV')
        
        else:
            return ('Autre', 'OTHER')
    
    def get_or_create_job_category(self, offer: Dict) -> int:
        """Récupère ou crée une catégorie d'emploi"""
        # Priorité: ROME code > détection depuis titre
        rome_code = offer.get("job_rome_code", "").strip()
        rome_label = offer.get("job_rome_label", "").strip()
        
        if rome_code and rome_label:
            category_name = rome_label
            category_code = rome_code
        else:
            # Détection depuis titre
            category_name, category_code = self.get_job_category_from_title(offer["title"])
        
        # Chercher catégorie existante
        q = text("SELECT job_category_id FROM dim_job_categories WHERE category_code=:code")
        r = self.session.execute(q, {"code": category_code}).fetchone()
        
        if r:
            return r[0]
        
        # Créer nouvelle catégorie
        q = text("""
            INSERT INTO dim_job_categories (category_name, category_code, level)
            VALUES (:name, :code, 1)
            RETURNING job_category_id
        """)
        
        r = self.session.execute(q, {
            "name": category_name,
            "code": category_code
        })
        self.session.commit()
        
        return r.fetchone()[0]
    
    def clean_description(self, description: str) -> str:
        """Nettoyer la description HTML"""
        if not description:
            return ""
        
        import re
        from html import unescape
        
        # Enlever les balises HTML
        description = re.sub(r'<[^>]+>', ' ', description)
        
        # Décoder les entités HTML
        description = unescape(description)
        
        # Normaliser les espaces
        description = re.sub(r'\s+', ' ', description)
        
        return description.strip()
    
    def extract_salary_from_description(self, description: str) -> str:
        """Extraire le salaire depuis la description"""
        import re
        
        if not description:
            return ""
        
        # Pattern 1: "XXK - YYK"
        match = re.search(r'(\d+K?\s*-\s*\d+K?)', description)
        if match:
            return match.group(1)
        
        # Pattern 2: "XXK à YYK"
        match = re.search(r'(\d+K?\s*à\s*\d+K?)', description)
        if match:
            return match.group(1)
        
        # Pattern 3: "Entre XXK et YYK"
        match = re.search(r'[Ee]ntre\s*(\d+K?\s*et\s*\d+K?)', description)
        if match:
            return match.group(1)
        
        return ""
    
    def parse_salary(self, salary_text: str):
        """Parser le salaire depuis le texte"""
        if not salary_text:
            return None, None
        
        import re
        
        # Détecter format "K" (milliers)
        has_k = bool(re.search(r'\d+\s*K', salary_text, re.IGNORECASE))
        
        # Capturer nombres
        numbers = re.findall(r'(\d+(?:\.\d+)?)', salary_text)
        
        # Filtrage intelligent
        if has_k:
            numbers = [float(n) for n in numbers]
            numbers = [n * 1000 if n < 1000 else n for n in numbers]
        else:
            numbers = [float(n) for n in numbers if float(n) >= 100]
        
        salary_min = None
        salary_max = None
        
        if len(numbers) >= 2:
            salary_min = numbers[0]
            salary_max = numbers[1]
        elif len(numbers) == 1:
            salary_min = numbers[0]
        
        return salary_min, salary_max
    
    def insert_offer(self, offer: Dict) -> bool:
        """
        Insérer une offre dans la base de données
        
        Args:
            offer: Offre normalisée
        
        Returns:
            True si insertion réussie, False sinon
        """
        try:
            # Vérifier doublon
            q = text("SELECT offer_id FROM fact_job_offers WHERE external_id=:eid")
            if self.session.execute(q, {"eid": offer["external_id"]}).fetchone():
                logger.debug(f"  ⏭️ Doublon: {offer['external_id']}")
                return False
            
            # Résoudre les dimensions
            source_id = self.get_or_create_source(offer["source"])
            date_id = self.get_or_create_date(offer.get("published_date"))
            commune_id = self.get_commune_id(offer)  # ← CHANGEMENT ICI
            category_id = self.get_or_create_job_category(offer)
            
            # Si commune non trouvée, skip l'offre
            if not commune_id:
                logger.warning(f"  ⏭️ Skip (commune non trouvée): {offer['title'][:50]}")
                return False
            
            # Parser le salaire
            salary_text_to_parse = offer.get("salary_text", "")
            
            if not salary_text_to_parse:
                salary_text_to_parse = self.extract_salary_from_description(offer.get("description", ""))
            
            salary_min, salary_max = self.parse_salary(salary_text_to_parse)
            
            # Date de publication
            pub_date = None
            if offer.get("published_date"):
                try:
                    pub_date = datetime.fromisoformat(
                        offer["published_date"].replace("Z", "+00:00")
                    ).date()
                except:
                    pass
            
            # Insertion
            q = text("""
                INSERT INTO fact_job_offers (
                    source_id, date_id, commune_id, job_category_id,
                    external_id, title, description, url, company_name,
                    contract_type, salary_min, salary_max,
                    published_date, collected_date
                ) VALUES (
                    :source, :date, :commune, :cat,
                    :eid, :title, :desc, :url, :company,
                    :contract, :sal_min, :sal_max,
                    :pub, NOW()
                )
            """)
            
            self.session.execute(q, {
                "source": source_id,
                "date": date_id,
                "commune": commune_id,  # ← commune_id au lieu de location_id
                "cat": category_id,
                "eid": offer["external_id"],
                "title": offer["title"],
                "desc": self.clean_description(offer["description"]),
                "url": offer.get("url"),
                "company": offer.get("company_name"),
                "contract": offer.get("contract_type"),
                "sal_min": salary_min,
                "sal_max": salary_max,
                "pub": pub_date
            })
            
            self.session.commit()
            logger.info(f"  ✅ {offer['title'][:50]}...")
            return True
        
        except IntegrityError:
            self.session.rollback()
            return False
        
        except Exception as e:
            self.session.rollback()
            logger.error(f"  ❌ Erreur: {e}")
            return False
    
    def insert_batch(self, offers: List[Dict]) -> Dict:
        """
        Insérer un batch d'offres
        
        Args:
            offers: Liste d'offres normalisées
        
        Returns:
            Statistiques d'insertion
        """
        logger.info("=" * 70)
        logger.info(f"💾 INSERTION DE {len(offers)} OFFRES (avec référentiel géographique)")
        logger.info("=" * 70)
        
        # Réinitialiser les stats
        self.communes_not_found = []
        
        inserted = 0
        duplicates = 0
        skipped = 0
        errors = 0
        
        for i, offer in enumerate(offers, 1):
            if i % 10 == 0:
                logger.info(f"\n⏳ Progression: {i}/{len(offers)}")
            
            result = self.insert_offer(offer)
            
            if result:
                inserted += 1
            elif offer.get("external_id") in [o.get("external_id") for o in offers[:i-1]]:
                duplicates += 1
            else:
                skipped += 1
        
        stats = {
            "total": len(offers),
            "inserted": inserted,
            "duplicates": duplicates,
            "skipped": skipped,
            "errors": errors,
            "communes_not_found": len(set(self.communes_not_found))
        }
        
        logger.info("\n" + "=" * 70)
        logger.info("📊 RÉSUMÉ")
        logger.info("=" * 70)
        logger.info(f"Total:              {stats['total']}")
        logger.info(f"Insérées:           {stats['inserted']}")
        logger.info(f"Doublons:           {stats['duplicates']}")
        logger.info(f"Skipped (no loc):   {stats['skipped']}")
        logger.info(f"Erreurs:            {stats['errors']}")
        logger.info(f"Succès:             {stats['inserted']/stats['total']*100:.1f}%")
        
        # Afficher les communes non trouvées
        if self.communes_not_found:
            unique_not_found = list(set(self.communes_not_found))
            logger.warning(f"\n⚠️ Communes non trouvées ({len(unique_not_found)}):")
            for loc in unique_not_found[:10]:
                logger.warning(f"   - {loc}")
            if len(unique_not_found) > 10:
                logger.warning(f"   ... et {len(unique_not_found) - 10} autres")
        
        # Stats GeoMatcher
        geo_stats = self.geo_matcher.get_stats()
        logger.info(f"\n📍 GeoMatcher:")
        logger.info(f"   Cache: {geo_stats.get('cache_size', 0)} entrées")
        
        logger.info("=" * 70)
        
        return stats
    
    def close(self):
        """Fermer la connexion"""
        self.session.close()
        self.geo_matcher.close()
        logger.info("🔚 Connexion fermée")


# ============================================================================
# TEST STANDALONE
# ============================================================================
if __name__ == "__main__":
    from datetime import datetime
    
    print("\n🧪 TEST DB INSERTER V2\n")
    
    # Créer des offres de test
    test_offers = [
        {
            "external_id": "test_v2_001",
            "title": "Data Analyst",
            "description": "Test description",
            "company_name": "Test Company",
            "contract_type": "CDI",
            "salary_text": "40K - 50K €",
            "location_city": "Paris",
            "location_postal_code": "75001",
            "published_date": datetime.now().isoformat(),
            "source": "test"
        },
        {
            "external_id": "test_v2_002",
            "title": "Data Scientist",
            "description": "Test description Lyon",
            "company_name": "Test Company 2",
            "contract_type": "CDI",
            "salary_text": "50K - 60K €",
            "location_city": "Lyon",
            "location_postal_code": "69001",
            "published_date": datetime.now().isoformat(),
            "source": "test"
        }
    ]
    
    inserter = DBInserterV2()
    
    try:
        stats = inserter.insert_batch(test_offers)
        print(f"\n✅ Test terminé: {stats['inserted']} insertion(s)")
    
    finally:
        inserter.close()
