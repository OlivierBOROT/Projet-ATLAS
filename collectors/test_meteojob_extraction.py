"""
Extraction Company Name via Météo Jobs (Version FINALE V2)
===========================================================
✅ Gestion cookies France Travail
✅ Gestion cookies Météo Jobs (TarteAuCitron)
✅ Selectors corrects pour company_name

Usage:
    python extract_company_final_v2.py 6645696
"""

import sys
import time
import argparse
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, ElementClickInterceptedException


def extract_company_from_meteojob(offer_id: str, headless: bool = False, save_html: bool = True):
    """Extraire company_name depuis Météo Jobs avec gestion complète cookies"""
    
    url = f"https://candidat.francetravail.fr/offres/recherche/detail/{offer_id}"
    
    print("=" * 80)
    print("🔍 EXTRACTION COMPANY_NAME VIA MÉTÉO JOBS V2")
    print("=" * 80)
    print(f"Offre: {offer_id}")
    print(f"URL: {url}\n")
    
    # Configuration Chrome
    chrome_options = Options()
    if headless:
        chrome_options.add_argument('--headless=new')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--disable-blink-features=AutomationControlled')
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option('useAutomationExtension', False)
    
    # Initialiser driver
    try:
        driver = webdriver.Chrome(options=chrome_options)
    except Exception as e:
        print(f"❌ Erreur initialisation Chrome: {e}")
        return None
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    company_name = None
    
    try:
        # =================================================================
        # ÉTAPE 1: Charger la page
        # =================================================================
        print("📄 ÉTAPE 1: Chargement...")
        driver.get(url)
        time.sleep(3)
        
        # =================================================================
        # ÉTAPE 2: FERMER COOKIES FRANCE TRAVAIL
        # =================================================================
        print("🍪 ÉTAPE 2: Gestion cookies France Travail...")
        
        cookie_closed = False
        
        # Tentative 1: Bouton "Tout accepter"
        try:
            cookie_btn = WebDriverWait(driver, 5).until(
                EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Tout accepter')]"))
            )
            cookie_btn.click()
            print("   ✅ Cookies acceptés (Tout accepter)")
            time.sleep(2)
            cookie_closed = True
        except TimeoutException:
            print("   ⏭️ Pas de bouton 'Tout accepter'")
        
        # Tentative 2: Shadow DOM
        if not cookie_closed:
            try:
                pe_cookies = driver.find_element(By.TAG_NAME, "pe-cookies")
                driver.execute_script("""
                    var peCookies = arguments[0];
                    var shadowRoot = peCookies.shadowRoot;
                    if (shadowRoot) {
                        var acceptBtn = shadowRoot.querySelector('button');
                        if (acceptBtn) {
                            acceptBtn.click();
                        }
                    }
                """, pe_cookies)
                print("   ✅ Cookies fermés (Shadow DOM)")
                time.sleep(2)
                cookie_closed = True
            except:
                print("   ⏭️ Pas de shadow DOM cookies")
        
        # Tentative 3: Continuer sans accepter
        if not cookie_closed:
            try:
                continuer_btn = driver.find_element(By.LINK_TEXT, "Continuer sans accepter")
                continuer_btn.click()
                print("   ✅ Continuer sans accepter")
                time.sleep(2)
                cookie_closed = True
            except:
                print("   ℹ️ Aucune popup cookies détectée")
        
        if save_html:
            with open(f"html_1_ft_{offer_id}_{timestamp}.html", "w", encoding="utf-8") as f:
                f.write(driver.page_source)
            print(f"   💾 HTML: html_1_ft_{offer_id}_{timestamp}.html")
        
        # =================================================================
        # ÉTAPE 3: Cliquer sur "Postuler"
        # =================================================================
        print("\n🖱️ ÉTAPE 3: Clic sur 'Postuler'...")
        
        postuler_clicked = False
        max_retries = 3
        
        for attempt in range(max_retries):
            try:
                postuler_btn = WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable((By.ID, "detail-apply"))
                )
                
                driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", postuler_btn)
                time.sleep(0.5)
                
                try:
                    postuler_btn.click()
                    print(f"   ✅ Clic réussi (tentative {attempt + 1})")
                    postuler_clicked = True
                    break
                except ElementClickInterceptedException:
                    print(f"   ⚠️ Clic intercepté (tentative {attempt + 1})")
                    driver.execute_script("arguments[0].click();", postuler_btn)
                    print(f"   ✅ Clic JavaScript réussi")
                    postuler_clicked = True
                    break
                    
            except Exception as e:
                print(f"   ⚠️ Tentative {attempt + 1} échouée: {e}")
                time.sleep(1)
        
        if not postuler_clicked:
            print("   ❌ Impossible de cliquer après 3 tentatives")
            return None
        
        time.sleep(3)
        
        # =================================================================
        # ÉTAPE 4: Attendre le menu déroulant
        # =================================================================
        print("⏳ ÉTAPE 4: Attente du menu...")
        
        try:
            dropdown = WebDriverWait(driver, 10).until(
                EC.visibility_of_element_located((By.ID, "contactZone"))
            )
            print("   ✅ Menu chargé")
            time.sleep(2)
            
            if save_html:
                with open(f"html_2_dropdown_{offer_id}_{timestamp}.html", "w", encoding="utf-8") as f:
                    f.write(driver.page_source)
                print(f"   💾 HTML: html_2_dropdown_{offer_id}_{timestamp}.html")
            
        except TimeoutException:
            print("   ❌ Menu non chargé")
            return None
        
        # =================================================================
        # ÉTAPE 5: Trouver et cliquer sur Météo Jobs
        # =================================================================
        print("\n🔍 ÉTAPE 5: Recherche Météo Jobs...")
        
        try:
            links = driver.find_elements(By.CSS_SELECTOR, "#contactZone a, .dropdown-apply a")
            print(f"   📊 {len(links)} lien(s) trouvé(s)")
            
            meteojob_link = None
            for i, link in enumerate(links, 1):
                href = link.get_attribute("href") or ""
                text = link.text.strip()
                
                print(f"   {i}. {text[:40] if text else '(vide)'}")
                
                if "meteojob" in href.lower() or "meteojob" in text.lower():
                    meteojob_link = link
                    print(f"   ✅ TROUVÉ: {href[:60]}...")
                    break
            
            if not meteojob_link:
                print("\n   ❌ Pas de lien Météo Jobs")
                return None
            
            # Cliquer
            print("\n🖱️ ÉTAPE 6: Clic Météo Jobs...")
            meteojob_url = meteojob_link.get_attribute("href")
            print(f"   URL: {meteojob_url}")
            
            try:
                meteojob_link.click()
            except:
                driver.execute_script("arguments[0].click();", meteojob_link)
            
            time.sleep(4)
            
            # Basculer vers nouvelle fenêtre
            if len(driver.window_handles) > 1:
                driver.switch_to.window(driver.window_handles[-1])
                print(f"   ✅ Nouvelle fenêtre")
            
            print(f"   📍 URL: {driver.current_url}")
            
        except Exception as e:
            print(f"   ❌ Erreur: {e}")
            return None
        
        # =================================================================
        # ÉTAPE 7: FERMER COOKIES MÉTÉO JOBS (TarteAuCitron)
        # =================================================================
        print("\n🍪 ÉTAPE 7: Gestion cookies Météo Jobs...")
        
        time.sleep(2)
        
        meteojob_cookie_closed = False
        
        # Tentative 1: Bouton "Tout accepter" (tarteaucitronPersonalize2)
        try:
            accept_btn = WebDriverWait(driver, 5).until(
                EC.element_to_be_clickable((By.ID, "tarteaucitronPersonalize2"))
            )
            accept_btn.click()
            print("   ✅ Cookies Météo Jobs acceptés (Tout accepter)")
            time.sleep(2)
            meteojob_cookie_closed = True
        except TimeoutException:
            print("   ⏭️ Pas de bouton 'Tout accepter'")
        
        # Tentative 2: Bouton "Tout refuser" (tarteaucitronAllDenied2)
        if not meteojob_cookie_closed:
            try:
                deny_btn = WebDriverWait(driver, 3).until(
                    EC.element_to_be_clickable((By.ID, "tarteaucitronAllDenied2"))
                )
                deny_btn.click()
                print("   ✅ Cookies Météo Jobs refusés")
                time.sleep(2)
                meteojob_cookie_closed = True
            except TimeoutException:
                print("   ⏭️ Pas de bouton 'Tout refuser'")
        
        # Tentative 3: Bouton fermer (X)
        if not meteojob_cookie_closed:
            try:
                close_btn = WebDriverWait(driver, 3).until(
                    EC.element_to_be_clickable((By.ID, "tarteaucitronCloseCross"))
                )
                close_btn.click()
                print("   ✅ Popup cookies fermée (X)")
                time.sleep(2)
                meteojob_cookie_closed = True
            except TimeoutException:
                print("   ℹ️ Aucune popup cookies Météo Jobs")
        
        time.sleep(2)
        
        if save_html:
            with open(f"html_3_meteojob_{offer_id}_{timestamp}.html", "w", encoding="utf-8") as f:
                f.write(driver.page_source)
            print(f"   💾 HTML: html_3_meteojob_{offer_id}_{timestamp}.html")
        
        # =================================================================
        # ÉTAPE 8: Extraire company_name avec les BONS selectors
        # =================================================================
        print("\n🏢 ÉTAPE 8: Extraction company_name...")
        
        time.sleep(2)
        
        # Selectors précis basés sur l'analyse HTML
        selectors = [
            # SELECTOR PRINCIPAL - trouvé dans le HTML
            ("cc-font-weight-headings", By.CSS_SELECTOR, "h1.cc-font-size-base span.cc-font-weight-headings"),
            
            # Alternatives
            ("h1 company span", By.CSS_SELECTOR, "h1 span.cc-font-weight-headings"),
            ("company-name class", By.CSS_SELECTOR, ".offer-company-name"),
            ("h2.company", By.CSS_SELECTOR, "h2.company, h2[class*='company']"),
            ("itemprop", By.XPATH, "//*[@itemprop='hiringOrganization']"),
            (".employer", By.CSS_SELECTOR, ".employer, [class*='employer']"),
        ]
        
        print("\n   🔍 Recherche avec selectors...")
        for name, by_type, selector in selectors:
            try:
                elements = driver.find_elements(by_type, selector)
                if elements:
                    print(f"   ✓ {name}: {len(elements)} trouvé(s)")
                    for elem in elements[:3]:
                        text = elem.text.strip()
                        if text and 3 < len(text) < 100:
                            # Exclure les mots-clés génériques
                            if text.lower() not in ['entreprise', 'company', 'voir', 'postuler', 
                                                     'recruteurs', 'se connecter', 'rechercher']:
                                print(f"      → '{text}'")
                                if not company_name:
                                    company_name = text
                                    print(f"      ✅ RETENU!")
            except Exception as e:
                print(f"   ✗ {name}: {e}")
                continue
        
        if not company_name:
            print("\n   ⚠️ Extraction automatique échouée")
            print("   💡 Analysez html_3_meteojob_*.html manuellement")
            print("   💡 Recherchez 'cc-font-weight-headings' dans le HTML")
        
    except Exception as e:
        print(f"\n❌ ERREUR: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        if not headless:
            print("\n⏸️ Pause 5 secondes...")
            time.sleep(5)
        
        driver.quit()
    
    print("\n" + "=" * 80)
    if company_name:
        print(f"✅ RÉSULTAT: '{company_name}'")
    else:
        print("❌ Non trouvé automatiquement")
    print("=" * 80)
    
    return company_name


def main():
    parser = argparse.ArgumentParser(
        description="Extraction company_name via Météo Jobs avec gestion complète cookies"
    )
    parser.add_argument("offer_id", help="ID de l'offre France Travail")
    parser.add_argument("--headless", action="store_true", help="Mode headless")
    parser.add_argument("--no-save", action="store_true", help="Ne pas sauvegarder HTML")
    args = parser.parse_args()
    
    print("╔══════════════════════════════════════════════════════════════════╗")
    print("║  EXTRACTION COMPANY_NAME - VERSION FINALE V2                     ║")
    print("║  ✅ Cookies France Travail + Météo Jobs                         ║")
    print("║  ✅ Selectors corrects                                          ║")
    print("╚══════════════════════════════════════════════════════════════════╝\n")
    
    company_name = extract_company_from_meteojob(
        args.offer_id,
        headless=args.headless,
        save_html=not args.no_save
    )
    
    return 0 if company_name else 1


if __name__ == "__main__":
    sys.exit(main())