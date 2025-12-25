"""
Script pour compléter les coordonnées GPS manquantes
Utilise geopy pour géocoder les adresses françaises
"""

import pandas as pd
from sqlalchemy import create_engine
import os
from dotenv import load_dotenv
from time import sleep
from tqdm import tqdm

# Installer avec: pip install geopy
try:
    from geopy.geocoders import Nominatim
    from geopy.exc import GeocoderTimedOut, GeocoderServiceError
except ImportError:
    print("❌ geopy non installé. Installez avec: pip install geopy")
    exit(1)

load_dotenv()

def geocode_location(city, postal_code, department, geolocator, retries=3):
    """
    Géocode une localisation française
    """
    # Construire la requête
    query_parts = []
    
    if pd.notna(city) and city != '':
        query_parts.append(city)
    
    if pd.notna(postal_code) and postal_code != '':
        query_parts.append(str(postal_code))
    
    if pd.notna(department) and department != 'Non spécifié':
        query_parts.append(department)
    
    query_parts.append('France')
    query = ', '.join(query_parts)
    
    # Essayer de géocoder avec retry
    for attempt in range(retries):
        try:
            location = geolocator.geocode(query, timeout=10)
            if location:
                return location.latitude, location.longitude
            return None, None
        except (GeocoderTimedOut, GeocoderServiceError):
            if attempt < retries - 1:
                sleep(2)
            else:
                return None, None
    
    return None, None

def add_coordinates():
    print("=" * 60)
    print("AJOUT DES COORDONNÉES GPS")
    print("=" * 60)
    
    # Connexion
    db_url = os.getenv('DATABASE_URL')
    engine = create_engine(db_url)
    
    # Charger depuis la table nettoyée si elle existe, sinon dim_locations
    try:
        df = pd.read_sql("SELECT * FROM dim_locations_clean", engine)
        print("✅ Chargement depuis dim_locations_clean")
    except:
        df = pd.read_sql("SELECT * FROM dim_locations", engine)
        print("✅ Chargement depuis dim_locations")
    
    # Identifier les lignes sans coordonnées
    missing_coords = df['latitude'].isna() | df['longitude'].isna()
    n_missing = missing_coords.sum()
    
    print(f"\n📍 {n_missing} localisations sans coordonnées GPS")
    
    if n_missing == 0:
        print("✅ Toutes les coordonnées sont déjà présentes !")
        return
    
    print(f"\n⚠️ ATTENTION:")
    print(f"   • Le géocodage peut prendre ~{n_missing * 1.5 / 60:.1f} minutes")
    print(f"   • Limite Nominatim: 1 requête/seconde")
    print(f"   • Certaines adresses peuvent échouer")
    
    response = input("\n   Continuer? (y/n): ").strip().lower()
    if response != 'y':
        print("❌ Annulé")
        return
    
    # Initialiser le géocodeur
    print("\n🌍 Initialisation du géocodeur...")
    geolocator = Nominatim(user_agent="job_analysis_app")
    
    # Géocoder les adresses manquantes
    print("\n🔄 Géocodage en cours...")
    success_count = 0
    fail_count = 0
    
    for idx in tqdm(df[missing_coords].index):
        row = df.loc[idx]
        
        lat, lon = geocode_location(
            row['city'],
            row['postal_code'],
            row['department'],
            geolocator
        )
        
        if lat and lon:
            df.at[idx, 'latitude'] = lat
            df.at[idx, 'longitude'] = lon
            success_count += 1
        else:
            fail_count += 1
        
        # Respecter la limite de taux
        sleep(1.1)
    
    print(f"\n✅ Géocodage terminé:")
    print(f"   • Succès: {success_count}")
    print(f"   • Échecs: {fail_count}")
    
    # Sauvegarder
    print("\n💾 Sauvegarde...")
    df.to_sql('dim_locations_with_coords', engine, if_exists='replace', index=False)
    print("   ✅ Table dim_locations_with_coords créée")
    
    df.to_csv('/home/claude/dim_locations_with_coords.csv', index=False)
    print("   ✅ CSV exporté")
    
    print("\n" + "=" * 60)

if __name__ == "__main__":
    add_coordinates()
