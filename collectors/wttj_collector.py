"""
Collecteur Welcome To The Jungle (WTTJ) - Web Scraping
=======================================================
Collecte d'offres d'emploi Data/IA via scraping Selenium.

Requirements:
    - pip install selenium

Usage:
    from wttj_collector import WTTJCollector
    collector = WTTJCollector()
    offers = collector.collect(max_offers=50)
"""

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
import time
import re
import logging
from typing import List, Dict
from datetime import datetime

# Configuration
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("WTTJ")


class WTTJCollector:
    """Collecteur Welcome To The Jungle avec Selenium"""
    
    BASE_URL = "https://www.welcometothejungle.com/fr/jobs"
    
    # Requêtes par défaut pour Data/IA
    DEFAULT_QUERIES = [
        "data analyst",
        "data scientist",
        "data engineer",
        "business intelligence"
    ]
    
    # Villes principales
    DEFAULT_CITIES = [
        "Paris",
        "Lyon",
        "Marseille",
        "Toulouse",
        "Bordeaux"
    ]
    
    def __init__(self, headless: bool = True):
        """
        Initialiser le collecteur
        
        Args:
            headless: Mode headless (sans interface graphique)
        """
        chrome_options = Options()
        if headless:
            chrome_options.add_argument('--headless')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')
        
        self.driver = webdriver.Chrome(options=chrome_options)
        self.collected_urls = set()
        
        logger.info("✅ WTTJCollector initialisé")
    
    def close_cookie_popup(self):
        """Fermer le popup de cookies"""
        try:
            time.sleep(2)
            btn = self.driver.find_element(By.XPATH, "//button[contains(text(), 'OK pour moi')]")
            btn.click()
            logger.info("  ✅ Popup cookies fermé")
            time.sleep(1)
        except:
            pass
    
    def get_job_urls(self, query: str, city: str, max_pages: int = 2) -> List[str]:
        """
        Récupérer les URLs des offres depuis la page de recherche
        
        Args:
            query: Requête de recherche (ex: "data analyst")
            city: Ville (ex: "Paris")
            max_pages: Nombre de pages à scraper
        
        Returns:
            Liste d'URLs d'offres
        """
        urls = []
        
        for page in range(1, max_pages + 1):
            search_url = f"{self.BASE_URL}?query={query}&page={page}&aroundQuery={city}"
            
            logger.info(f"  📄 Page {page}/{max_pages}")
            self.driver.get(search_url)
            
            if page == 1:
                self.close_cookie_popup()
            
            time.sleep(3)
            
            # Scroll pour charger le lazy-loading
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(2)
            
            # Extraire les liens d'offres
            links = self.driver.find_elements(By.CSS_SELECTOR, "a[href*='/companies/'][href*='/jobs/']")
            
            for link in links:
                href = link.get_attribute('href')
                if href and '/jobs/' in href and href not in self.collected_urls:
                    urls.append(href)
                    self.collected_urls.add(href)
            
            logger.info(f"     → {len(urls)} nouvelles offres")
            time.sleep(2)
        
        return urls
    
    def extract_text_safe(self, selector: str, multiple: bool = False):
        """
        Extraction sécurisée d'élément(s) HTML
        
        Args:
            selector: Sélecteur CSS
            multiple: Si True, retourne une liste
        
        Returns:
            Texte extrait ou liste de textes
        """
        try:
            if multiple:
                elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                return [el.text.strip() for el in elements if el.text.strip()]
            else:
                elem = self.driver.find_element(By.CSS_SELECTOR, selector)
                return elem.text.strip()
        except:
            return "" if not multiple else []
    
    def extract_company_from_url(self, url: str) -> str:
        """
        Extraire le nom de l'entreprise depuis l'URL WTTJ
        
        Format URL: https://www.welcometothejungle.com/fr/companies/COMPANY/jobs/...
        
        Args:
            url: URL de l'offre
        
        Returns:
            Nom de l'entreprise en majuscules
        """
        try:
            import re
            match = re.search(r'/companies/([^/]+)/jobs/', url)
            if match:
                company_slug = match.group(1)
                # Convertir en majuscules et remplacer les tirets
                company_name = company_slug.upper().replace('-', ' ')
                return company_name
        except:
            pass
        
        return ""
    
    def extract_city_from_url(self, url: str) -> str:
        """
        Extraire la ville depuis l'URL WTTJ
        
        Format URL: .../jobs/job-title_CITY_...
        
        Args:
            url: URL de l'offre
        
        Returns:
            Nom de la ville
        """
        try:
            import re
            # Format: job-title_city_code
            match = re.search(r'/jobs/[^_]+_([^_/]+)', url)
            if match:
                city_slug = match.group(1)
                # Nettoyer et capitaliser
                city = city_slug.replace('-', ' ').title()
                
                # Mapping des villes courantes
                city_mapping = {
                    'Paris': 'Paris',
                    'Lyon': 'Lyon',
                    'Marseille': 'Marseille',
                    'Toulouse': 'Toulouse',
                    'Bordeaux': 'Bordeaux',
                    'Nantes': 'Nantes',
                    'Lille': 'Lille',
                    'Strasbourg': 'Strasbourg',
                    'Levallois Perret': 'Levallois-Perret',
                    'Saint Herblain': 'Saint-Herblain',
                    'Les Ulis': 'Les Ulis'
                }
                
                # Vérifier si c'est une ville connue
                for key, value in city_mapping.items():
                    if key.lower() in city.lower():
                        return value
                
                return city
        except:
            pass
        
        return ""
    
    def extract_job_details(self, url: str) -> Dict:
        """
        Extraire les détails d'une offre
        
        Args:
            url: URL de l'offre
        
        Returns:
            Dictionnaire avec les détails de l'offre
        """
        try:
            self.driver.get(url)
            time.sleep(3)
            
            # Cliquer sur "Voir plus" pour charger la description complète
            try:
                voir_plus = self.driver.find_elements(By.XPATH, 
                    "//a[contains(@data-testid, 'view-more')] | //a[contains(., 'Voir plus')]")
                for btn in voir_plus:
                    try:
                        self.driver.execute_script("arguments[0].click();", btn)
                        time.sleep(0.5)
                    except:
                        pass
            except:
                pass
            
            # Initialiser l'offre
            job_data = {
                'url': url,
                'external_id': f"wttj_{url.split('/')[-1]}",
                'source': 'welcome_to_the_jungle',
                'collected_at': datetime.now().isoformat(),
                'salary_text': ""  # Initialiser dès le début
            }
            
            # TITRE - Essayer plusieurs sélecteurs
            for selector in ["h2.sc-ikZCWJ", "h2", "h1"]:
                title = self.extract_text_safe(selector)
                if title and 5 < len(title) < 200:
                    job_data['title'] = title
                    break
            
            # ENTREPRISE - Priorité 1: URL, Priorité 2: DOM
            company_from_url = self.extract_company_from_url(url)
            if company_from_url:
                job_data['company_name'] = company_from_url
            else:
                # Fallback: extraire depuis le DOM
                for selector in [
                    "a[href*='/companies/'] span.sc-ikZCWJ",
                    "a.sc-deTYHS span",
                    "span.sc-ikZCWJ.iPoSFg"
                ]:
                    company = self.extract_text_safe(selector)
                    if company and 2 < len(company) < 100:
                        job_data['company_name'] = company
                        break
            
            # DESCRIPTION
            desc = self.extract_text_safe("div[data-testid='job-section-description']")
            if desc:
                desc = desc.replace('\nVoir plus', '').strip()
                job_data['description'] = desc
            
            # MÉTADONNÉES (badges)
            badges = self.extract_text_safe("div.sc-ifpNTt, span", multiple=True)
            
            for badge_text in badges:
                if not badge_text or len(badge_text) > 100:
                    continue
                
                # Type de contrat
                if not job_data.get('contract_type'):
                    for contract in ['CDI', 'CDD', 'Stage', 'Alternance', 'Freelance']:
                        if contract.lower() in badge_text.lower():
                            job_data['contract_type'] = contract
                            break
                
                # Ville
                if not job_data.get('location_city'):
                    for city in self.DEFAULT_CITIES:
                        if city in badge_text:
                            job_data['location_city'] = city
                            break
            
            # Si ville toujours manquante, essayer de l'extraire de l'URL
            if not job_data.get('location_city'):
                city_from_url = self.extract_city_from_url(url)
                if city_from_url:
                    job_data['location_city'] = city_from_url
                
                # Salaire - Chercher pattern "XXK à YYK €" ou "Salaire : XXK à YYK"
                if not job_data.get('salary_text'):
                    # Pattern 1: "XXK à YYK €"
                    if re.search(r'\d+K?\s*[àa]\s*\d+K?\s*€', badge_text):
                        job_data['salary_text'] = badge_text
                    # Pattern 2: "Salaire :" suivi de montants
                    elif 'salaire' in badge_text.lower() and ('€' in badge_text or 'k' in badge_text.lower()):
                        job_data['salary_text'] = badge_text
            
            # DATE DE PUBLICATION
            try:
                time_elem = self.driver.find_element(By.CSS_SELECTOR, "time[datetime]")
                job_data['published_date'] = time_elem.get_attribute('datetime')
            except:
                pass
            
            # REMOTE/TÉLÉTRAVAIL
            remote_text = self.extract_text_safe("div.sc-ifpNTt:has(i[name='remote'])")
            if 'télétravail' in remote_text.lower() or 'remote' in remote_text.lower():
                job_data['remote'] = remote_text
            
            return job_data
            
        except Exception as e:
            logger.error(f"    ❌ Erreur extraction: {e}")
            return None
    
    def collect(
        self,
        queries: List[str] = None,
        cities: List[str] = None,
        max_pages_per_query: int = 2,
        max_offers: int = 50
    ) -> List[Dict]:
        """
        Collecter des offres depuis WTTJ
        
        Args:
            queries: Liste de requêtes de recherche
            cities: Liste de villes
            max_pages_per_query: Nombre de pages par requête
            max_offers: Nombre maximum d'offres à collecter
        
        Returns:
            Liste d'offres normalisées
        """
        queries = queries or self.DEFAULT_QUERIES
        cities = cities or ["Paris"]
        
        logger.info("=" * 70)
        logger.info("🚀 COLLECTE WTTJ")
        logger.info("=" * 70)
        logger.info(f"Requêtes: {len(queries)} | Villes: {len(cities)}")
        logger.info(f"Pages/requête: {max_pages_per_query} | Max offres: {max_offers}")
        logger.info("=" * 70)
        
        all_urls = []
        
        # ÉTAPE 1: Collecter les URLs
        logger.info("\n📋 ÉTAPE 1/2: Collecte des URLs")
        
        for query in queries:
            for city in cities:
                logger.info(f"\n🔍 '{query}' à {city}")
                
                urls = self.get_job_urls(query, city, max_pages_per_query)
                all_urls.extend(urls)
                
                if len(all_urls) >= max_offers:
                    logger.info(f"\n⚠️ Limite {max_offers} atteinte")
                    break
            
            if len(all_urls) >= max_offers:
                break
        
        all_urls = all_urls[:max_offers]
        logger.info(f"\n✅ {len(all_urls)} offres uniques à extraire")
        
        # ÉTAPE 2: Extraire les détails
        logger.info("\n📦 ÉTAPE 2/2: Extraction des détails")
        
        jobs = []
        
        for i, url in enumerate(all_urls, 1):
            logger.info(f"\n[{i}/{len(all_urls)}] {url.split('/')[-1][:50]}...")
            
            job = self.extract_job_details(url)
            
            if job:
                jobs.append(job)
                logger.info(f"   ✅ {job.get('title', '?')[:50]}")
                logger.info(f"   🏢 {job.get('company_name', '?')[:40]}")
                logger.info(f"   📍 {job.get('location_city', '?')}")
                logger.info(f"   📄 Description: {len(job.get('description', ''))} chars")
            
            time.sleep(1.5)  # Rate limiting
        
        logger.info("\n" + "=" * 70)
        logger.info(f"✅ {len(jobs)} offres collectées")
        logger.info("=" * 70)
        
        return jobs
    
    def close(self):
        """Fermer le navigateur"""
        self.driver.quit()
        logger.info("🔚 Navigateur fermé")


# ============================================================================
# TEST STANDALONE
# ============================================================================
if __name__ == "__main__":
    import json
    
    print("\n🧪 TEST WTTJ COLLECTOR\n")
    
    collector = WTTJCollector(headless=False)
    
    try:
        # Collecter 10 offres pour test
        offers = collector.collect(
            queries=["data analyst"],
            cities=["Paris"],
            max_pages_per_query=1,
            max_offers=10
        )
        
        if offers:
            # Afficher les résultats
            print(f"\n📋 {len(offers)} OFFRES COLLECTÉES:\n")
            print("=" * 70)
            
            for i, offer in enumerate(offers, 1):
                print(f"\n[{i}] {offer.get('title', 'N/A')}")
                print(f"    🏢 {offer.get('company_name', 'N/A')}")
                print(f"    📍 {offer.get('location_city', 'N/A')}")
                print(f"    📄 {offer.get('contract_type', 'N/A')}")
                print(f"    💰 {offer.get('salary_text', 'Non spécifié')}")
                print(f"    📝 Description: {len(offer.get('description', ''))} chars")
                print(f"    🔗 {offer['url']}")
            
            print("\n" + "=" * 70)
            
            # Sauvegarder
            filename = "wttj_test.json"
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(offers, f, ensure_ascii=False, indent=2)
            
            print(f"\n💾 Sauvegardé: {filename}")
        else:
            print("❌ Aucune offre collectée")
    
    finally:
        collector.close()
    
    print("\n✅ Test terminé!")