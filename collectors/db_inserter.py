"""
Inserteur d'offres dans PostgreSQL
===================================
Insère les offres collectées dans la base de données ATLAS.

Requirements:
    - DATABASE_URL dans .env
    - pip install sqlalchemy psycopg2-binary

Usage:
    from db_inserter import DBInserter
    inserter = DBInserter()
    inserter.insert_batch(offers)
"""

import os
import logging
from typing import Dict, List
from datetime import datetime
from dotenv import load_dotenv

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import IntegrityError

# Configuration
load_dotenv()
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("DBInserter")


class DBInserter:
    """Inserteur d'offres dans PostgreSQL"""
    
    # Mapping département → région
    DEPT_TO_REGION = {
        "01": "Auvergne-Rhône-Alpes", "03": "Auvergne-Rhône-Alpes", 
        "07": "Auvergne-Rhône-Alpes", "15": "Auvergne-Rhône-Alpes",
        "26": "Auvergne-Rhône-Alpes", "38": "Auvergne-Rhône-Alpes",
        "42": "Auvergne-Rhône-Alpes", "43": "Auvergne-Rhône-Alpes",
        "63": "Auvergne-Rhône-Alpes", "69": "Auvergne-Rhône-Alpes",
        "73": "Auvergne-Rhône-Alpes", "74": "Auvergne-Rhône-Alpes",
        "75": "Île-de-France", "77": "Île-de-France", "78": "Île-de-France",
        "91": "Île-de-France", "92": "Île-de-France", "93": "Île-de-France",
        "94": "Île-de-France", "95": "Île-de-France",
        "13": "Provence-Alpes-Côte d'Azur", "83": "Provence-Alpes-Côte d'Azur",
        "84": "Provence-Alpes-Côte d'Azur", "04": "Provence-Alpes-Côte d'Azur",
        "05": "Provence-Alpes-Côte d'Azur", "06": "Provence-Alpes-Côte d'Azur",
        "31": "Occitanie", "09": "Occitanie", "11": "Occitanie",
        "12": "Occitanie", "30": "Occitanie", "32": "Occitanie",
        "34": "Occitanie", "46": "Occitanie", "48": "Occitanie",
        "65": "Occitanie", "66": "Occitanie", "81": "Occitanie", "82": "Occitanie",
        "33": "Nouvelle-Aquitaine", "16": "Nouvelle-Aquitaine",
        "17": "Nouvelle-Aquitaine", "19": "Nouvelle-Aquitaine",
        "23": "Nouvelle-Aquitaine", "24": "Nouvelle-Aquitaine",
        "40": "Nouvelle-Aquitaine", "47": "Nouvelle-Aquitaine",
        "64": "Nouvelle-Aquitaine", "79": "Nouvelle-Aquitaine",
        "86": "Nouvelle-Aquitaine", "87": "Nouvelle-Aquitaine",
    }
    
    DEPT_NAMES = {
        "01": "Ain", "03": "Allier", "07": "Ardèche", "15": "Cantal",
        "26": "Drôme", "38": "Isère", "42": "Loire", "43": "Haute-Loire",
        "63": "Puy-de-Dôme", "69": "Rhône", "73": "Savoie", "74": "Haute-Savoie",
        "75": "Paris", "77": "Seine-et-Marne", "78": "Yvelines",
        "91": "Essonne", "92": "Hauts-de-Seine", "93": "Seine-Saint-Denis",
        "94": "Val-de-Marne", "95": "Val-d'Oise",
        "13": "Bouches-du-Rhône", "83": "Var", "84": "Vaucluse",
        "04": "Alpes-de-Haute-Provence", "05": "Hautes-Alpes", "06": "Alpes-Maritimes",
        "31": "Haute-Garonne", "33": "Gironde",
    }
    
    def __init__(self):
        """Initialiser la connexion PostgreSQL"""
        database_url = os.getenv("DATABASE_URL")
        if not database_url:
            raise ValueError("❌ DATABASE_URL requis dans .env")
        
        self.engine = create_engine(database_url)
        Session = sessionmaker(bind=self.engine)
        self.session = Session()
        
        logger.info("✅ Connexion PostgreSQL établie")
    
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
    
    def get_or_create_location(self, offer: Dict) -> int:
        """Récupère ou crée une localisation"""
        city = offer.get("location_city", "").strip()
        postal_code = offer.get("location_postal_code", "")
        
        # Extraire le code département
        dept_code = ""
        insee = offer.get("location_insee", "")
        
        if insee and len(insee) >= 2:
            dept_code = insee[:2]
        elif postal_code and len(postal_code) >= 2:
            dept_code = postal_code[:2]
        
        if not city and not dept_code:
            return None
        
        # Chercher location existante
        q = text("""
            SELECT location_id FROM dim_locations
            WHERE (city = :city OR :city = '') 
              AND (department_code = :dept OR :dept = '')
            LIMIT 1
        """)
        r = self.session.execute(q, {
            "city": city if city else "",
            "dept": dept_code if dept_code else ""
        }).fetchone()
        
        if r:
            return r[0]
        
        # Créer nouvelle location
        region = self.DEPT_TO_REGION.get(dept_code, "Non spécifié")
        dept_name = self.DEPT_NAMES.get(dept_code, "Non spécifié")
        
        q = text("""
            INSERT INTO dim_locations
            (city, postal_code, department, department_code, region, latitude, longitude)
            VALUES (:city, :pc, :dept_name, :dept_code, :region, :lat, :lon)
            RETURNING location_id
        """)
        
        r = self.session.execute(q, {
            "city": city or "Non spécifié",
            "pc": postal_code,
            "dept_name": dept_name,
            "dept_code": dept_code,
            "region": region,
            "lat": offer.get("location_lat"),
            "lon": offer.get("location_lon")
        })
        self.session.commit()
        
        return r.fetchone()[0]
    
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
        
        elif any(kw in title_lower for kw in ['data engineer', 'ingénieur data', 'ingénieur de données']):
            return ('Data Engineer', 'WTTJ_DE')
        
        elif any(kw in title_lower for kw in ['tech lead', 'lead data', 'lead dev']):
            return ('Tech Lead Data', 'WTTJ_TL')
        
        elif any(kw in title_lower for kw in ['consultant data', 'consultant bi', 'consultant analytics', 'consultant amoa']):
            return ('Consultant Data / BI', 'WTTJ_CD')
        
        elif any(kw in title_lower for kw in ['stage', 'stagiaire', 'intern', 'alternance']):
            return ('Stage / Alternance Data', 'WTTJ_ST')
        
        elif any(kw in title_lower for kw in ['business intelligence', 'bi engineer', 'bi analyst']):
            return ('Business Intelligence', 'WTTJ_BI')
        
        else:
            return ('Autre métier Data', 'WTTJ_OTHER')
    
    def get_or_create_job_category(self, offer: Dict) -> int:
        """Récupère ou crée une catégorie de poste"""
        name = offer.get("romeLibelle")
        code = offer.get("romeCode")
        
        # Si pas de ROME (ex: WTTJ), déduire depuis le titre
        if not name and not code:
            title = offer.get("title", "")
            if title:
                name, code = self.get_job_category_from_title(title)
            else:
                return None
        
        # Chercher par code si disponible
        if code:
            q = text("SELECT job_category_id FROM dim_job_categories WHERE category_code=:code")
            r = self.session.execute(q, {"code": code}).fetchone()
            if r:
                return r[0]
        
        # Créer nouvelle catégorie
        q = text("""
            INSERT INTO dim_job_categories (category_name, category_code, level)
            VALUES (:name, :code, 1)
            RETURNING job_category_id
        """)
        
        r = self.session.execute(q, {
            "name": name or "Non spécifié",
            "code": code
        })
        self.session.commit()
        
        return r.fetchone()[0]
    
    def clean_description(self, description: str) -> str:
        """
        Nettoyer la description pour l'insertion en BDD
        
        Args:
            description: Description brute
        
        Returns:
            Description nettoyée
        """
        if not description:
            return ""
        
        # Remplacer le caractère ¶ (U+00B6) par des sauts de ligne
        description = description.replace('¶', '\n')
        
        # Supprimer les sauts de ligne multiples
        import re
        description = re.sub(r'\n{3,}', '\n\n', description)
        
        # Supprimer les espaces en début/fin
        description = description.strip()
        
        return description
    
    def extract_salary_from_description(self, description: str) -> str:
        """
        Extraire le salaire depuis la description (pour WTTJ notamment)
        
        Patterns recherchés:
        - "45K à 55K"
        - "Salaire : 40000€ - 50000€"
        - "Entre 35K et 45K€"
        
        Returns:
            Texte du salaire ou ""
        """
        if not description:
            return ""
        
        import re
        
        # Pattern 1: "XXK à YYK" ou "XXK - YYK"
        match = re.search(r'(\d+K?\s*[€]?\s*[àa-]\s*\d+K?\s*[€]?)', description, re.IGNORECASE)
        if match:
            return match.group(1)
        
        # Pattern 2: "Salaire : XXX€"
        match = re.search(r'[Ss]alaire\s*:?\s*(\d+\s*K?\s*[€]?\s*[àa-]?\s*\d*\s*K?\s*[€]?)', description)
        if match:
            return match.group(1)
        
        # Pattern 3: "Entre XXK et YYK"
        match = re.search(r'[Ee]ntre\s*(\d+K?\s*et\s*\d+K?)', description)
        if match:
            return match.group(1)
        
        return ""
    
    def parse_salary(self, salary_text: str):
        """
        Parser le salaire depuis le texte
        
        Formats supportés:
        - "Annuel de 30000.0 Euros à 35000.0 Euros sur 12.0 mois"
        - "Mensuel de 2500 Euros à 3000 Euros"
        - "Entre 40K et 50K"
        
        Returns:
            (salary_min, salary_max) ou (None, None)
        """
        if not salary_text:
            return None, None
        
        import re
        
        # Détecter format "K" (milliers)
        has_k = bool(re.search(r'\d+\s*K', salary_text, re.IGNORECASE))
        
        # Capturer nombres
        numbers = re.findall(r'(\d+(?:\.\d+)?)', salary_text)
        
        # Filtrage intelligent
        if has_k:
            # Format K: ne pas filtrer < 100
            numbers = [float(n) for n in numbers]
            # Multiplier par 1000 si < 1000
            numbers = [n * 1000 if n < 1000 else n for n in numbers]
        else:
            # Format normal: filtrer < 100 (évite "12 mois")
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
            location_id = self.get_or_create_location(offer)
            category_id = self.get_or_create_job_category(offer)
            
            # Parser le salaire
            salary_text_to_parse = offer.get("salary_text", "")
            
            # Si salary_text vide, essayer d'extraire depuis description (WTTJ)
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
                    source_id, date_id, location_id, job_category_id,
                    external_id, title, description, url, company_name,
                    contract_type, salary_min, salary_max,
                    published_date, collected_date
                ) VALUES (
                    :source, :date, :loc, :cat,
                    :eid, :title, :desc, :url, :company,
                    :contract, :sal_min, :sal_max,
                    :pub, NOW()
                )
            """)
            
            self.session.execute(q, {
                "source": source_id,
                "date": date_id,
                "loc": location_id,
                "cat": category_id,
                "eid": offer["external_id"],
                "title": offer["title"],
                "desc": self.clean_description(offer["description"]),
                "url": offer.get("url"),  # ← URL ajoutée ici
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
        logger.info(f"💾 INSERTION DE {len(offers)} OFFRES")
        logger.info("=" * 70)
        
        inserted = 0
        duplicates = 0
        errors = 0
        
        for i, offer in enumerate(offers, 1):
            if i % 10 == 0:
                logger.info(f"\n⏳ Progression: {i}/{len(offers)}")
            
            result = self.insert_offer(offer)
            
            if result:
                inserted += 1
            else:
                duplicates += 1
        
        stats = {
            "total": len(offers),
            "inserted": inserted,
            "duplicates": duplicates,
            "errors": errors
        }
        
        logger.info("\n" + "=" * 70)
        logger.info("📊 RÉSUMÉ")
        logger.info("=" * 70)
        logger.info(f"Total:      {stats['total']}")
        logger.info(f"Insérées:   {stats['inserted']}")
        logger.info(f"Doublons:   {stats['duplicates']}")
        logger.info(f"Erreurs:    {stats['errors']}")
        logger.info(f"Succès:     {stats['inserted']/stats['total']*100:.1f}%")
        logger.info("=" * 70)
        
        return stats
    
    def close(self):
        """Fermer la connexion"""
        self.session.close()
        logger.info("🔚 Connexion fermée")


# ============================================================================
# TEST STANDALONE
# ============================================================================
if __name__ == "__main__":
    import json
    
    print("\n🧪 TEST DB INSERTER\n")
    
    # Créer des offres de test
    test_offers = [
        {
            "external_id": "test_001",
            "title": "Data Analyst",
            "description": "Test description",
            "company_name": "Test Company",
            "contract_type": "CDI",
            "salary_text": "40K - 50K €",
            "location_city": "Paris",
            "location_postal_code": "75001",
            "published_date": datetime.now().isoformat(),
            "source": "test"
        }
    ]
    
    inserter = DBInserter()
    
    try:
        stats = inserter.insert_batch(test_offers)
        print(f"\n✅ Test terminé: {stats['inserted']} insertion(s)")
    
    finally:
        inserter.close()