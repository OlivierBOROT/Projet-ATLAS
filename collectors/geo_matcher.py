"""
Module de matching géographique
================================
Recherche les communes dans ref_communes_france pour conversion location → commune_id

Usage:
    from geo_matcher import GeoMatcher
    
    matcher = GeoMatcher()
    commune_id = matcher.find_commune("Paris", "75001")
    
    # Ou avec un dictionnaire d'offre
    commune_id = matcher.find_commune_from_offer(offer)
"""

import re
import logging
from typing import Optional, Dict
from sqlalchemy import create_engine, text
import os
from dotenv import load_dotenv
from pathlib import Path

# Charger .env depuis le dossier parent si nécessaire
env_path = Path(__file__).parent.parent / '.env'
if env_path.exists():
    load_dotenv(dotenv_path=env_path)
else:
    load_dotenv()

logger = logging.getLogger("GeoMatcher")


class GeoMatcher:
    """
    Classe pour matcher les localisations scrapées avec ref_communes_france
    """
    
    def __init__(self, db_url: str = None):
        """
        Initialiser le matcher
        
        Args:
            db_url: URL de connexion PostgreSQL (ou depuis .env)
        """
        self.db_url = db_url or os.getenv('DATABASE_URL')
        if not self.db_url:
            raise ValueError("❌ DATABASE_URL requis (dans .env ou paramètre)")
        
        self.engine = create_engine(self.db_url)
        
        # Cache pour éviter les requêtes répétées
        self.cache = {}
        
        logger.info("✅ GeoMatcher initialisé")
    
    def clean_city_name(self, city: str) -> str:
        """
        Nettoie le nom de ville
        
        Args:
            city: Nom de ville brut
        
        Returns:
            Nom nettoyé
        
        Examples:
            "75 - Paris" → "PARIS"
            "LYON" → "LYON"
            "Paris 1er Arrondissement" → "PARIS 01"
            "Lyon 3e Arrondissement" → "LYON 03"
            "Saint-Étienne" → "ST ETIENNE"
            "Saint-Denis" → "ST DENIS"
            "Sainte-Foy" → "STE FOY"
            "Charleville-Mézières" → "CHARLEVILLE MEZIERES"
        """
        if not city:
            return ""
        
        # Enlever préfixe département (ex: "75 - Paris" -> "Paris")
        city = re.sub(r'^\d{2,3}\s*-\s*', '', city)
        
        # Convertir les arrondissements au format "XX 01", "XX 02", etc.
        # Pattern: "Paris 1er Arrondissement" → "Paris 01"
        match = re.search(
            r'^(.+?)\s+(\d{1,2})[eèr]{1,2}\s+arrondissement',
            city,
            flags=re.IGNORECASE
        )
        
        if match:
            ville = match.group(1).strip()
            numero = match.group(2).zfill(2)  # Pad avec 0: "1" → "01"
            city = f"{ville} {numero}"
        
        # Normaliser "Saint" et "Sainte" en "ST" et "STE"
        city = re.sub(r'\bSaint-', 'ST ', city, flags=re.IGNORECASE)
        city = re.sub(r'\bSainte-', 'STE ', city, flags=re.IGNORECASE)
        city = re.sub(r'\bSt-', 'ST ', city, flags=re.IGNORECASE)
        city = re.sub(r'\bSte-', 'STE ', city, flags=re.IGNORECASE)
        
        # Normaliser espaces multiples
        city = re.sub(r'\s+', ' ', city)
        
        # Normaliser casse (UPPERCASE pour matcher avec la base)
        city = city.strip().upper()
        
        return city
    
    def normalize_for_search(self, city: str) -> str:
        """
        Normalise un nom de ville pour la recherche (enlève accents, tirets, etc.)
        
        Args:
            city: Nom de ville
        
        Returns:
            Nom normalisé pour recherche
        
        Examples:
            "Charleville-Mézières" → "charleville mezieres"
            "Saint-Étienne" → "st etienne"
            "Nîmes" → "nimes"
            "ÉPINAL" → "epinal"
        """
        import unicodedata
        
        if not city:
            return ""
        
        # Normaliser "Saint" et "Sainte" en "ST" et "STE"
        city = re.sub(r'\bSaint-', 'ST ', city, flags=re.IGNORECASE)
        city = re.sub(r'\bSainte-', 'STE ', city, flags=re.IGNORECASE)
        city = re.sub(r'\bSt-', 'ST ', city, flags=re.IGNORECASE)
        city = re.sub(r'\bSte-', 'STE ', city, flags=re.IGNORECASE)
        
        # Enlever les accents
        city = unicodedata.normalize('NFD', city)
        city = ''.join(char for char in city if unicodedata.category(char) != 'Mn')
        
        # Remplacer tirets par espaces
        city = city.replace('-', ' ')
        
        # Remplacer apostrophes par espaces
        city = city.replace("'", ' ')
        
        # Normaliser espaces multiples
        city = re.sub(r'\s+', ' ', city)
        
        # Minuscules
        city = city.lower().strip()
        
        return city
    
    def find_commune_id(self, city_name: str, postal_code: str = None) -> Optional[int]:
        """
        Trouve l'ID de la commune à partir du nom et/ou code postal
        
        Args:
            city_name: Nom de la ville
            postal_code: Code postal (optionnel mais recommandé)
        
        Returns:
            commune_id ou None si non trouvé
        
        Examples:
            >>> matcher.find_commune_id("Paris", "75001")
            123
            
            >>> matcher.find_commune_id("Lyon")
            456
        """
        if not city_name:
            return None
        
        # Nettoyer le nom de ville
        city_clean = self.clean_city_name(city_name)
        
        # Clé de cache
        cache_key = f"{city_clean}|{postal_code or ''}"
        if cache_key in self.cache:
            return self.cache[cache_key]
        
        commune_id = None
        
        try:
            with self.engine.connect() as conn:
                # Normaliser pour recherche (sans accents, sans tirets)
                city_normalized = self.normalize_for_search(city_clean)
                
                # STRATÉGIE 1: Recherche exacte avec code postal
                if postal_code:
                    result = conn.execute(
                        text("""
                            SELECT commune_id FROM ref_communes_france
                            WHERE code_postal = :postal
                              AND (
                                  LOWER(nom_commune) = LOWER(:city)
                                  OR LOWER(REPLACE(REPLACE(
                                      TRANSLATE(nom_commune, 
                                          'àâäéèêëïîôùûüÿçÀÂÄÉÈÊËÏÎÔÙÛÜŸÇ',
                                          'aaaeeeeiioouuuycAAAEEEEIIOUUUYC'),
                                      '-', ' '), '''', ' ')
                                  ) = :city_norm
                              )
                            LIMIT 1
                        """),
                        {"city": city_clean, "postal": postal_code, "city_norm": city_normalized}
                    )
                    commune_id = result.scalar()
                
                # STRATÉGIE 2: Si pas trouvé, recherche par nom normalisé seul
                if not commune_id:
                    result = conn.execute(
                        text("""
                            SELECT commune_id FROM ref_communes_france
                            WHERE LOWER(REPLACE(REPLACE(
                                  TRANSLATE(nom_commune, 
                                      'àâäéèêëïîôùûüÿçÀÂÄÉÈÊËÏÎÔÙÛÜŸÇ',
                                      'aaaeeeeiioouuuycAAAEEEEIIOUUUYC'),
                                  '-', ' '), '''', ' ')
                              ) = :city_norm
                            ORDER BY population DESC NULLS LAST
                            LIMIT 1
                        """),
                        {"city_norm": city_normalized}
                    )
                    commune_id = result.scalar()
                
                # STRATÉGIE 3: Utiliser la fonction PostgreSQL find_commune() en dernier recours
                if not commune_id:
                    if postal_code:
                        result = conn.execute(
                            text("SELECT find_commune(:city, :postal)"),
                            {"city": city_clean, "postal": postal_code}
                        )
                    else:
                        result = conn.execute(
                            text("SELECT find_commune(:city)"),
                            {"city": city_clean}
                        )
                    
                    commune_id = result.scalar()
        
        except Exception as e:
            logger.error(f"❌ Erreur recherche commune '{city_clean}': {e}")
            commune_id = None
        
        # Mettre en cache
        self.cache[cache_key] = commune_id
        
        if commune_id:
            logger.debug(f"✅ Commune trouvée: {city_clean} ({postal_code}) → ID {commune_id}")
        else:
            logger.warning(f"⚠️ Commune non trouvée: {city_clean} ({postal_code})")
        
        return commune_id
    
    def find_commune_from_offer(self, offer: Dict) -> Optional[int]:
        """
        Trouve la commune à partir d'un dictionnaire d'offre
        
        Args:
            offer: Dictionnaire avec 'location_city' et optionnellement 'location_postal_code'
        
        Returns:
            commune_id ou None
        
        Examples:
            >>> offer = {
            ...     "location_city": "75 - Paris",
            ...     "location_postal_code": "75001"
            ... }
            >>> matcher.find_commune_from_offer(offer)
            123
        """
        city = offer.get("location_city", "")
        postal_code = offer.get("location_postal_code", "")
        
        return self.find_commune_id(city, postal_code)
    
    def get_commune_info(self, commune_id: int) -> Optional[Dict]:
        """
        Récupère les informations complètes d'une commune
        
        Args:
            commune_id: ID de la commune
        
        Returns:
            Dictionnaire avec les infos ou None
        
        Examples:
            >>> info = matcher.get_commune_info(123)
            >>> print(info['nom_commune'], info['nom_region'])
            Paris Île-de-France
        """
        if not commune_id:
            return None
        
        try:
            with self.engine.connect() as conn:
                result = conn.execute(
                    text("""
                        SELECT 
                            commune_id, code_insee, code_postal,
                            nom_commune, nom_departement, nom_region,
                            code_departement, code_region,
                            latitude, longitude, population
                        FROM ref_communes_france 
                        WHERE commune_id = :id
                    """),
                    {"id": commune_id}
                )
                
                row = result.fetchone()
                if not row:
                    return None
                
                return {
                    'commune_id': row[0],
                    'code_insee': row[1],
                    'code_postal': row[2],
                    'nom_commune': row[3],
                    'nom_departement': row[4],
                    'nom_region': row[5],
                    'code_departement': row[6],
                    'code_region': row[7],
                    'latitude': float(row[8]) if row[8] else None,
                    'longitude': float(row[9]) if row[9] else None,
                    'population': row[10]
                }
        
        except Exception as e:
            logger.error(f"❌ Erreur récupération commune {commune_id}: {e}")
            return None
    
    def get_stats(self) -> Dict:
        """
        Récupère des statistiques sur le référentiel
        
        Returns:
            Dictionnaire avec les stats
        """
        try:
            with self.engine.connect() as conn:
                result = conn.execute(text("""
                    SELECT 
                        COUNT(*) as total_communes,
                        COUNT(DISTINCT code_departement) as nb_departements,
                        COUNT(DISTINCT code_region) as nb_regions,
                        COUNT(latitude) as nb_avec_gps
                    FROM ref_communes_france
                """))
                
                row = result.fetchone()
                return {
                    'total_communes': row[0],
                    'nb_departements': row[1],
                    'nb_regions': row[2],
                    'nb_avec_gps': row[3],
                    'cache_size': len(self.cache)
                }
        
        except Exception as e:
            logger.error(f"❌ Erreur stats: {e}")
            return {}
    
    def close(self):
        """Fermer la connexion"""
        self.engine.dispose()
        logger.info("🔚 GeoMatcher fermé")


# ============================================================================
# TEST STANDALONE
# ============================================================================
if __name__ == "__main__":
    import sys
    
    logging.basicConfig(level=logging.INFO)
    
    print("\n🧪 TEST GEO MATCHER\n")
    print("=" * 60)
    
    try:
        matcher = GeoMatcher()
        
        # Afficher les stats
        stats = matcher.get_stats()
        print(f"\n📊 Statistiques du référentiel:")
        print(f"   • Communes: {stats['total_communes']:,}")
        print(f"   • Départements: {stats['nb_departements']}")
        print(f"   • Régions: {stats['nb_regions']}")
        print(f"   • Avec GPS: {stats['nb_avec_gps']:,}")
        
        # Tests
        tests = [
            ("Paris", "75001"),
            ("Lyon", "69001"),
            ("Marseille", "13001"),
            ("Toulouse", None),
            ("75 - Paris", "75020"),  # Avec préfixe
            ("BORDEAUX", "33000"),  # Majuscules
            ("  grenoble  ", "38000"),  # Espaces
            ("Ville Inexistante", "99999"),  # Devrait échouer
        ]
        
        print(f"\n🔍 Tests de recherche:")
        print("=" * 60)
        
        for city, postal in tests:
            commune_id = matcher.find_commune_id(city, postal)
            
            if commune_id:
                info = matcher.get_commune_info(commune_id)
                print(f"✅ '{city}' ({postal or 'sans CP'})")
                print(f"   → ID: {info['commune_id']} | {info['nom_commune']} ({info['code_postal']})")
                print(f"   → {info['nom_departement']} - {info['nom_region']}")
            else:
                print(f"❌ '{city}' ({postal or 'sans CP'}) - NON TROUVÉ")
            
            print()
        
        # Test avec un dictionnaire d'offre
        print("\n📦 Test avec dictionnaire d'offre:")
        print("=" * 60)
        
        offer = {
            "location_city": "31 - Toulouse",
            "location_postal_code": "31000"
        }
        
        commune_id = matcher.find_commune_from_offer(offer)
        if commune_id:
            info = matcher.get_commune_info(commune_id)
            print(f"✅ Offre → Commune ID {commune_id}")
            print(f"   {info['nom_commune']} - {info['nom_region']}")
        
        # Stats finales
        print(f"\n📊 Cache: {len(matcher.cache)} entrées")
        
        print("\n" + "=" * 60)
        print("✅ Tests terminés avec succès")
        print("=" * 60 + "\n")
    
    except Exception as e:
        print(f"\n❌ Erreur: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    
    finally:
        matcher.close()