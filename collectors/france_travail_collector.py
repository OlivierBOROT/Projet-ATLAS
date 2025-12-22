"""
Collecteur France Travail (Pôle Emploi) - API OAuth2
====================================================
Collecte d'offres d'emploi Data/IA via l'API officielle France Travail.

Requirements:
    - POLE_EMPLOI_CLIENT_ID dans .env
    - POLE_EMPLOI_CLIENT_SECRET dans .env

Usage:
    from france_travail_collector import FranceTravailCollector
    collector = FranceTravailCollector()
    offers = collector.collect(max_offers=100)
"""

import os
import time
import re
import requests
import logging
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from pathlib import Path
from dotenv import load_dotenv

# Import extraction Météo Jobs
try:
    from selenium import webdriver
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.webdriver.chrome.options import Options
    from selenium.common.exceptions import TimeoutException, ElementClickInterceptedException
    SELENIUM_AVAILABLE = True
except ImportError:
    SELENIUM_AVAILABLE = False

# Configuration
load_dotenv()
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("FranceTravail")

# Avertissement si Selenium non disponible
if not SELENIUM_AVAILABLE:
    logger.warning("⚠️ Selenium non disponible - extraction Météo Jobs désactivée")


class FranceTravailCollector:
    """Collecteur France Travail avec authentification OAuth2"""
    
    AUTH_URL = "https://entreprise.francetravail.fr/connexion/oauth2/access_token"
    API_URL = "https://api.francetravail.io/partenaire/offresdemploi/v2/offres/search"
    
    # Grands domaines pertinents pour Data/IA
    GRAND_DOMAINES = [
        "M18",  # Informatique / Télécommunication
        "M14",  # Conseil / Études
        "M17",  # Marketing / Stratégie commerciale (analytics)
    ]
    
    # Regex pour filtrer les offres Data/IA
    DATA_AI_REGEX = re.compile(
        r"\b("
        # Data général
        r"data|dataset|donnée|données|base de données|database|bdd|"
        r"etl|elt|datawarehouse|data warehouse|datalake|data lake|lakehouse|"
        r"bi\b|business intelligence|analytics|analytique|analyse de données|"
        r"datamart|data mart|olap|oltp|"
        
        # SQL et bases de données
        r"sql|postgres|postgresql|mysql|oracle|snowflake|bigquery|redshift|"
        r"pl/sql|plsql|t-sql|tsql|nosql|mongodb|cassandra|dynamodb|elasticsearch|"
        r"databricks|synapse|teradata|vertica|clickhouse|"
        
        # Langages et outils Data
        r"python|pandas|numpy|pyspark|scala|julia|r\b|matlab|"
        r"spark|hadoop|kafka|airflow|dbt|dagster|prefect|luigi|"
        r"tableau|power bi|powerbi|qlik|looker|metabase|superset|"
        r"sas|spss|stata|alteryx|talend|informatica|"
        
        # Machine Learning et IA
        r"machine learning|ml\b|deep learning|dl\b|apprentissage automatique|"
        r"intelligence artificielle|\bia\b|ai\b|artificial intelligence|"
        r"scikit|sklearn|tensorflow|pytorch|keras|xgboost|lightgbm|catboost|"
        r"mlflow|mlops|kubeflow|sagemaker|vertex ai|"
        r"classification|régression|clustering|prédiction|prediction|"
        r"random forest|gradient boosting|neural network|réseau de neurones|"
        
        # NLP et LLM
        r"nlp|natural language processing|traitement du langage naturel|"
        r"llm|large language model|gpt|bert|transformer|attention|"
        r"chatbot|conversationnel|dialogue|assistant virtuel|"
        r"spacy|nltk|hugging face|huggingface|langchain|llamaindex|"
        r"text mining|topic modeling|sentiment analysis|analyse de sentiment|"
        r"word2vec|doc2vec|fasttext|glove|embedding|tokenization|"
        r"ner|named entity recognition|pos tagging|lemmatization|stemming|"
        
        # RAG et systèmes avancés
        r"rag|retrieval augmented generation|retrieval-augmented|"
        r"vector database|vectordb|chromadb|pinecone|weaviate|milvus|qdrant|faiss|"
        r"semantic search|recherche sémantique|similarity search|"
        r"prompt engineering|fine-tuning|finetuning|few-shot|zero-shot|"
        r"foundation model|modèle de fondation|génératif|generative|"
        
        # Computer Vision
        r"computer vision|vision par ordinateur|image processing|traitement d'image|"
        r"opencv|yolo|detectron|segmentation|object detection|détection d'objet|"
        r"cnn|convolutional neural network|resnet|vgg|inception|"
        r"ocr|reconnaissance de caractères|facial recognition|reconnaissance faciale|"
        
        # Cloud et Infrastructure
        r"cloud|aws|gcp|google cloud|azure|microsoft azure|alibaba cloud|"
        r"s3|ec2|lambda|emr|glue|athena|kinesis|redshift|"
        r"bigquery|dataflow|dataproc|pub/sub|cloud functions|"
        r"blob storage|cosmos db|synapse|databricks|"
        r"docker|kubernetes|k8s|containerisation|microservices|"
        
        # Métiers Data/IA
        r"data engineer|data scientist|data analyst|bi analyst|"
        r"analyste données|ingénieur données|scientifique des données|"
        r"ml engineer|mlops engineer|ai engineer|nlp engineer|"
        r"data architect|architecte données|chief data officer|cdo|"
        r"analytics engineer|research scientist|chercheur|"
        
        # Termes tech généraux
        r"développeur|developer|ingénieur|engineer|architect|architecte|"
        r"informatique|it\b|tech|digital|numérique|technologie|"
        r"backend|back-end|frontend|front-end|fullstack|full-stack|"
        r"devops|sre|site reliability|"
        r"api|rest|graphql|microservice|"
        
        # Big Data et temps réel
        r"big data|hadoop|hdfs|mapreduce|hive|pig|impala|presto|trino|"
        r"streaming|temps réel|real-time|realtime|flink|storm|samza|"
        r"message queue|rabbitmq|kafka|pulsar|nats|redis|"
        
        # Méthodes et concepts
        r"agile|scrum|kanban|devops|ci/cd|mlops|dataops|"
        r"a/b test|expérimentation|kpi|metrics|métriques|dashboard|reporting|"
        r"data quality|qualité des données|data governance|gouvernance|"
        r"data catalog|catalogue de données|metadata|métadonnées|lineage|"
        r"etl pipeline|data pipeline|orchestration|workflow|"
        
        # Visualisation et dashboarding
        r"visualisation|visualization|dataviz|dashboard|reporting|"
        r"matplotlib|seaborn|plotly|bokeh|d3\.js|d3js|highcharts|"
        r"grafana|kibana|prometheus|splunk|datadog|"
        
        # Statistiques et mathématiques
        r"statistique|statistics|probabilité|probability|bayésien|bayesian|"
        r"régression linéaire|linear regression|logistic regression|"
        r"hypothesis testing|test statistique|p-value|correlation|"
        r"time series|série temporelle|forecast|forecasting|prévision|arima|prophet|"
        
        # Domaines d'application
        r"recommandation|recommendation system|système de recommandation|"
        r"fraud detection|détection de fraude|anomaly detection|détection d'anomalie|"
        r"churn prediction|prédiction d'attrition|credit scoring|"
        r"personalization|personnalisation|optimisation|optimization|"
        r")\b",
        re.IGNORECASE
    )
    
    def __init__(self, use_selenium: bool = False):
        """
        Initialise le collecteur avec les credentials
        
        Args:
            use_selenium: Si True, utilise Selenium pour extraire company_name manquant (plus lent)
        """
        self.client_id = os.getenv("POLE_EMPLOI_CLIENT_ID")
        self.client_secret = os.getenv("POLE_EMPLOI_CLIENT_SECRET")
        
        if not self.client_id or not self.client_secret:
            raise ValueError("❌ POLE_EMPLOI_CLIENT_ID et POLE_EMPLOI_CLIENT_SECRET requis dans .env")
        
        self.access_token: Optional[str] = None
        self.token_expires_at: Optional[datetime] = None
        self.use_selenium = use_selenium
        
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "ATLAS-Collector/1.0",
            "Accept": "application/json"
        })
        
        selenium_status = "ON" if (use_selenium and SELENIUM_AVAILABLE) else "OFF"
        logger.info(f"✅ FranceTravailCollector initialisé (Selenium: {selenium_status})")
    
    def extract_company_from_meteojob(self, offer_id: str, headless: bool = True) -> Optional[str]:
        """
        Extraire company_name depuis Météo Jobs via Selenium
        
        Args:
            offer_id: ID de l'offre France Travail
            headless: Mode headless (True par défaut en production)
        
        Returns:
            company_name ou None si échec
        """
        if not SELENIUM_AVAILABLE:
            logger.warning(f"⚠️ Selenium non disponible pour offre {offer_id}")
            return None
        
        # 🎯 OPTIMISATION: Skip si l'ID n'est pas numérique
        # Les IDs alphanumériques (ex: 201PZTR) n'ont généralement pas de lien Météo Jobs
        # Seuls les IDs numériques (ex: 6662091) ont ce lien
        if not offer_id.isdigit():
            logger.info(f"⏭️ ID non-numérique ({offer_id}) - skip Météo Jobs")
            return None
        
        url = f"https://candidat.francetravail.fr/offres/recherche/detail/{offer_id}"
        logger.info(f"🔍 Extraction Météo Jobs pour offre {offer_id}")
        
        # Configuration Chrome
        chrome_options = Options()
        if headless:
            chrome_options.add_argument('--headless=new')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-blink-features=AutomationControlled')
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        chrome_options.add_argument('--log-level=3')  # Réduire les logs
        
        driver = None
        company_name = None
        
        try:
            driver = webdriver.Chrome(options=chrome_options)
            driver.set_page_load_timeout(30)  # Timeout de 30s pour le chargement des pages
        except Exception as e:
            logger.error(f"❌ Erreur initialisation Chrome: {e}")
            return None
        
        try:
            # ÉTAPE 1: Charger la page
            driver.get(url)
            time.sleep(3)
            
            # ÉTAPE 2: Cookies France Travail
            try:
                cookie_btn = WebDriverWait(driver, 5).until(
                    EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Tout accepter')]"))
                )
                cookie_btn.click()
                time.sleep(2)
            except TimeoutException:
                try:
                    pe_cookies = driver.find_element(By.TAG_NAME, "pe-cookies")
                    driver.execute_script("""
                        var peCookies = arguments[0];
                        var shadowRoot = peCookies.shadowRoot;
                        if (shadowRoot) {
                            var acceptBtn = shadowRoot.querySelector('button');
                            if (acceptBtn) { acceptBtn.click(); }
                        }
                    """, pe_cookies)
                    time.sleep(2)
                except:
                    pass
            
            # ÉTAPE 3: Cliquer sur "Postuler"
            postuler_clicked = False
            for attempt in range(3):
                try:
                    postuler_btn = WebDriverWait(driver, 10).until(
                        EC.element_to_be_clickable((By.ID, "detail-apply"))
                    )
                    driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", postuler_btn)
                    time.sleep(0.5)
                    
                    try:
                        postuler_btn.click()
                    except ElementClickInterceptedException:
                        driver.execute_script("arguments[0].click();", postuler_btn)
                    
                    postuler_clicked = True
                    break
                except Exception as e:
                    if attempt == 2:
                        logger.error(f"❌ Impossible de cliquer sur Postuler: {e}")
                    time.sleep(1)
            
            if not postuler_clicked:
                return None
            
            time.sleep(3)
            
            # ÉTAPE 4: Attendre le menu
            try:
                WebDriverWait(driver, 10).until(
                    EC.visibility_of_element_located((By.ID, "contactZone"))
                )
                time.sleep(2)
            except TimeoutException:
                logger.error("❌ Menu non chargé")
                return None
            
            # ÉTAPE 5: Trouver le lien Météo Jobs
            links = driver.find_elements(By.CSS_SELECTOR, "#contactZone a, .dropdown-apply a")
            
            meteojob_link = None
            for link in links:
                href = link.get_attribute("href") or ""
                text = link.text.strip()
                
                if "meteojob" in href.lower() or "meteojob" in text.lower():
                    meteojob_link = link
                    break
            
            if not meteojob_link:
                logger.info(f"ℹ️ Pas de lien Météo Jobs pour {offer_id} - skip")
                return None  # Le finally fermera le driver
            
            # ÉTAPE 6: Cliquer sur Météo Jobs
            try:
                meteojob_link.click()
            except:
                driver.execute_script("arguments[0].click();", meteojob_link)
            
            time.sleep(4)
            
            # Basculer vers nouvelle fenêtre
            if len(driver.window_handles) > 1:
                driver.switch_to.window(driver.window_handles[-1])
            
            # ÉTAPE 7: Cookies Météo Jobs (TarteAuCitron)
            try:
                accept_btn = WebDriverWait(driver, 5).until(
                    EC.element_to_be_clickable((By.ID, "tarteaucitronPersonalize2"))
                )
                accept_btn.click()
                time.sleep(2)
            except TimeoutException:
                try:
                    close_btn = WebDriverWait(driver, 3).until(
                        EC.element_to_be_clickable((By.ID, "tarteaucitronCloseCross"))
                    )
                    close_btn.click()
                    time.sleep(2)
                except:
                    pass
            
            time.sleep(2)
            
            # ÉTAPE 8: Extraire company_name
            selectors = [
                ("cc-font-weight-headings", By.CSS_SELECTOR, "h1.cc-font-size-base span.cc-font-weight-headings"),
                ("h1 company span", By.CSS_SELECTOR, "h1 span.cc-font-weight-headings"),
                ("company-name class", By.CSS_SELECTOR, ".offer-company-name"),
                ("h2.company", By.CSS_SELECTOR, "h2.company, h2[class*='company']"),
            ]
            
            for name, by_type, selector in selectors:
                try:
                    elements = driver.find_elements(by_type, selector)
                    if elements:
                        for elem in elements[:2]:
                            text = elem.text.strip()
                            if text and 3 < len(text) < 100:
                                if text.lower() not in ['entreprise', 'company', 'voir', 'postuler', 
                                                         'recruteurs', 'se connecter', 'rechercher']:
                                    company_name = text
                                    logger.info(f"✅ Company trouvée via {name}: {company_name}")
                                    break
                    if company_name:
                        break
                except:
                    continue
            
        except Exception as e:
            logger.error(f"❌ Erreur extraction Météo Jobs: {e}")
        
        finally:
            # 🔥 CRITIQUE : Fermeture propre du driver pour éviter les retries urllib3
            if driver:
                try:
                    # Fermer tous les onglets ouverts
                    while len(driver.window_handles) > 0:
                        driver.close()
                        if len(driver.window_handles) > 0:
                            driver.switch_to.window(driver.window_handles[0])
                except:
                    pass  # Ignorer les erreurs de fermeture d'onglets
                
                try:
                    driver.quit()
                except:
                    pass  # Ignorer les erreurs de quit
                
                # Petite pause pour laisser le driver se fermer complètement
                time.sleep(0.3)
        
        return company_name
    
    def authenticate(self) -> str:
        """Obtenir un token OAuth2"""
        if self.access_token and self.token_expires_at and datetime.now() < self.token_expires_at:
            return self.access_token
        
        logger.info("🔐 Authentification OAuth2...")
        
        response = self.session.post(
            self.AUTH_URL,
            params={"realm": "/partenaire"},
            data={
                "grant_type": "client_credentials",
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "scope": "api_offresdemploiv2 o2dsoffre"
            },
            timeout=30
        )
        response.raise_for_status()
        data = response.json()
        
        self.access_token = data["access_token"]
        expires_in = int(data.get("expires_in", 1500))
        self.token_expires_at = datetime.now() + timedelta(seconds=max(60, expires_in - 60))
        
        logger.info(f"✅ Token obtenu (expires in {expires_in}s)")
        return self.access_token
    
    def search_page(self, params: Dict) -> List[Dict]:
        """Effectuer une recherche (1 page)"""
        token = self.authenticate()
        headers = {"Authorization": f"Bearer {token}"}
        
        response = self.session.get(self.API_URL, headers=headers, params=params, timeout=30)
        
        if response.status_code == 204:  # Aucun résultat
            return []
        
        if response.status_code == 429:  # Rate limit
            logger.warning("⚠️ Rate limit atteint, pause 5s...")
            time.sleep(5)
            return self.search_page(params)  # Retry
        
        response.raise_for_status()
        data = response.json()
        
        return data.get("resultats", [])
    
    def search_with_pagination(
        self,
        grand_domaine: str,
        max_index: int = 3149,
        page_size: int = 150
    ) -> List[Dict]:
        """Collecter avec pagination (0..max_index)"""
        all_results = []
        start = 0
        
        while start <= max_index:
            end = min(start + page_size - 1, max_index)
            
            params = {
                "range": f"{start}-{end}",
                "grandDomaine": grand_domaine,
                "sort": "1"  # Par date de création
            }
            
            logger.info(f"  📡 Range {start}-{end} | Grand domaine: {grand_domaine}")
            
            try:
                items = self.search_page(params)
                all_results.extend(items)
                
                if len(items) == 0:
                    break  # Plus de résultats
                
                logger.info(f"     ✅ {len(items)} offres | Total: {len(all_results)}")
                
            except Exception as e:
                logger.error(f"  ❌ Erreur: {e}")
                break
            
            start += page_size
            time.sleep(0.2)  # Rate limiting
        
        return all_results
    
    def is_data_ai_offer(self, offer: Dict) -> bool:
        """Vérifier si l'offre concerne Data/IA"""
        text = " ".join([
            str(offer.get("intitule", "") or ""),
            str(offer.get("description", "") or ""),
            str(offer.get("romeLibelle", "") or ""),
            str(offer.get("appellationlibelle", "") or "")
        ])
        
        # Debug log pour voir ce qui est filtré
        match = self.DATA_AI_REGEX.search(text)
        if not match:
            logger.debug(f"❌ Filtré: {offer.get('intitule', '')[:50]}")
        
        return bool(match)
    
    def normalize_offer(self, raw_offer: Dict) -> Dict:
        """Normaliser une offre au format ATLAS"""
        lieu = raw_offer.get("lieuTravail", {}) or {}
        entreprise = raw_offer.get("entreprise", {}) or {}
        salaire = raw_offer.get("salaire", {}) or {}
        
        external_id = raw_offer.get("id")
        company_name = entreprise.get("nom")
        
        # 🆕 Si company_name vide, tenter extraction via Météo Jobs (si activé)
        if not company_name and external_id and SELENIUM_AVAILABLE and self.use_selenium:
            logger.info(f"🔍 Company_name vide pour {external_id}, tentative Météo Jobs...")
            try:
                extracted_company = self.extract_company_from_meteojob(external_id, headless=True)
                if extracted_company:
                    company_name = extracted_company
                    logger.info(f"✅ Company extraite via Météo Jobs: {company_name}")
                # Si None, l'info a déjà été loggée dans extract_company_from_meteojob
            except Exception as e:
                logger.error(f"❌ Erreur extraction Météo Jobs pour {external_id}: {e}")
        elif not company_name and not self.use_selenium:
            logger.debug(f"⏭️ Company_name vide pour {external_id} - Selenium désactivé")
        
        return {
            "external_id": external_id,
            "title": raw_offer.get("intitule"),
            "description": raw_offer.get("description"),
            "company_name": company_name,
            "contract_type": raw_offer.get("typeContratLibelle") or raw_offer.get("typeContrat"),
            "salary_text": salaire.get("libelle"),
            "location_city": lieu.get("libelle"),
            "location_postal_code": lieu.get("codePostal"),
            "location_insee": lieu.get("commune"),
            "location_lat": lieu.get("latitude"),
            "location_lon": lieu.get("longitude"),
            "romeCode": raw_offer.get("romeCode"),
            "romeLibelle": raw_offer.get("romeLibelle"),
            "published_date": raw_offer.get("dateCreation"),
            "updated_date": raw_offer.get("dateActualisation"),
            "url": f"https://candidat.francetravail.fr/offres/recherche/detail/{external_id}" if external_id else None,
            "source": "france_travail",
            "collected_at": datetime.utcnow().isoformat()
        }
    
    def dedupe_by_id(self, offers: List[Dict]) -> List[Dict]:
        seen = set()
        unique_offers = []

        for offer in offers:
            offer_id = offer.get("id")
            if offer_id and offer_id not in seen:
                seen.add(offer_id)
                unique_offers.append(offer)

        return unique_offers

    
    def collect(self, max_offers: int = 150) -> List[Dict]:
        """
        Collecter des offres Data/IA depuis France Travail
        
        Args:
            max_offers: Nombre maximum d'offres à collecter
        
        Returns:
            Liste d'offres normalisées
        """
        logger.info("=" * 70)
        logger.info("🚀 COLLECTE FRANCE TRAVAIL")
        logger.info("=" * 70)
        
        raw_offers = []
        
        # Collecter depuis chaque grand domaine
        for grand_domaine in self.GRAND_DOMAINES:
            logger.info(f"\n📂 Grand domaine: {grand_domaine}")
            
            offers = self.search_with_pagination(
                grand_domaine=grand_domaine,
                max_index=min(3149, max_offers)
            )
            
            raw_offers.extend(offers)
            
            if len(raw_offers) >= max_offers:
                break
        
        # Dédupliquer
        raw_offers = self.dedupe_by_id(raw_offers)
        logger.info(f"\n📦 Total brut (dédupliqué): {len(raw_offers)} offres")
        
        # Debug: afficher quelques titres
        if raw_offers:
            logger.info("\n📋 Exemples d'offres brutes:")
            for i, o in enumerate(raw_offers[:5], 1):
                logger.info(f"  {i}. {o.get('intitule', 'N/A')[:60]}")
        
        # Filtrer Data/IA
        filtered_offers = [o for o in raw_offers if self.is_data_ai_offer(o)]
        logger.info(f"\n🧠 Après filtre Data/IA: {len(filtered_offers)} offres")
        
        # Si aucune offre après filtre, désactiver le filtre
        if len(filtered_offers) == 0 and len(raw_offers) > 0:
            logger.warning("⚠️ Aucune offre ne passe le filtre Data/IA, désactivation du filtre...")
            filtered_offers = raw_offers[:max_offers]
        
        # Normaliser
        normalized_offers = [self.normalize_offer(o) for o in filtered_offers[:max_offers]]
        
        # 🚫 FILTRE CRITIQUE: Exclure les offres sans company_name
        before_filter = len(normalized_offers)
        normalized_offers = [
            offer for offer in normalized_offers 
            if offer.get('company_name') and offer['company_name'].strip()
        ]
        excluded_count = before_filter - len(normalized_offers)
        
        if excluded_count > 0:
            logger.info(f"\n🚫 {excluded_count} offres exclues (pas de company_name)")
        
        logger.info("=" * 70)
        logger.info(f"✅ {len(normalized_offers)} offres collectées et normalisées")
        logger.info("=" * 70)
        
        return normalized_offers


# ============================================================================
# TEST STANDALONE
# ============================================================================
if __name__ == "__main__":
    import json
    
    print("\n🧪 TEST FRANCE TRAVAIL COLLECTOR\n")
    
    collector = FranceTravailCollector()
    
    # Collecter 10 offres pour test
    offers = collector.collect(max_offers=10)
    
    if offers:
        # Afficher les résultats
        print(f"\n📋 {len(offers)} OFFRES COLLECTÉES:\n")
        print("=" * 70)
        
        for i, offer in enumerate(offers, 1):
            print(f"\n[{i}] {offer['title']}")
            print(f"    🏢 {offer['company_name']}")
            print(f"    📍 {offer['location_city']}")
            print(f"    📄 {offer['contract_type']}")
            print(f"    💰 {offer['salary_text'] or 'Non spécifié'}")
            print(f"    🔗 {offer['url']}")
        
        print("\n" + "=" * 70)
        
        # Sauvegarder
        filename = "france_travail_test.json"
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(offers, f, ensure_ascii=False, indent=2)
        
        print(f"\n💾 Sauvegardé: {filename}")
    else:
        print("❌ Aucune offre collectée")
    
    print("\n✅ Test terminé!")