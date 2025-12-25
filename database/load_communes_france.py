"""
Script de chargement du référentiel des communes françaises
Source: Base Officielle des Codes Postaux (data.gouv.fr)
"""

import pandas as pd
import requests
from sqlalchemy import create_engine, text
import os
from dotenv import load_dotenv
from io import StringIO
import zipfile
from tqdm import tqdm
from pathlib import Path

# Charger .env depuis le dossier parent
env_path = Path(__file__).parent.parent / '.env'
load_dotenv(dotenv_path=env_path)

print(f"📁 Chargement de .env depuis: {env_path}")
print(f"🔗 DATABASE_URL trouvé: {'Oui' if os.getenv('DATABASE_URL') else 'Non'}")
print()

# URLs des données officielles
LAPOSTE_CSV_URL = "https://datanova.laposte.fr/data-fair/api/v1/datasets/laposte-hexasmal/raw"
INSEE_COMMUNES_URL = "https://www.insee.fr/fr/statistiques/fichier/7766585/v_commune_2024.csv"

# Mapping région code -> nom (référentiel 2024)
REGIONS = {
    '01': 'Guadeloupe', '02': 'Martinique', '03': 'Guyane', '04': 'La Réunion',
    '06': 'Mayotte', '11': 'Île-de-France', '24': 'Centre-Val de Loire',
    '27': 'Bourgogne-Franche-Comté', '28': 'Normandie', '32': 'Hauts-de-France',
    '44': 'Grand Est', '52': 'Pays de la Loire', '53': 'Bretagne',
    '75': 'Nouvelle-Aquitaine', '76': 'Occitanie', '84': "Auvergne-Rhône-Alpes",
    '93': "Provence-Alpes-Côte d'Azur", '94': 'Corse'
}

# Mapping département -> région
DEPT_TO_REGION = {
    '01': '84', '02': '32', '03': '84', '04': '93', '05': '93', '06': '93',
    '07': '84', '08': '44', '09': '76', '10': '44', '11': '76', '12': '76',
    '13': '93', '14': '28', '15': '84', '16': '75', '17': '75', '18': '24',
    '19': '75', '21': '27', '22': '53', '23': '75', '24': '75', '25': '27',
    '26': '84', '27': '28', '28': '24', '29': '53', '2A': '94', '2B': '94',
    '30': '76', '31': '76', '32': '76', '33': '75', '34': '76', '35': '53',
    '36': '24', '37': '24', '38': '84', '39': '27', '40': '75', '41': '24',
    '42': '84', '43': '84', '44': '52', '45': '24', '46': '76', '47': '75',
    '48': '76', '49': '52', '50': '28', '51': '44', '52': '44', '53': '52',
    '54': '44', '55': '44', '56': '53', '57': '44', '58': '27', '59': '32',
    '60': '32', '61': '28', '62': '32', '63': '84', '64': '75', '65': '76',
    '66': '76', '67': '44', '68': '44', '69': '84', '70': '27', '71': '27',
    '72': '52', '73': '84', '74': '84', '75': '11', '76': '28', '77': '11',
    '78': '11', '79': '75', '80': '32', '81': '76', '82': '76', '83': '93',
    '84': '93', '85': '52', '86': '75', '87': '75', '88': '44', '89': '27',
    '90': '27', '91': '11', '92': '11', '93': '11', '94': '11', '95': '11',
    '971': '01', '972': '02', '973': '03', '974': '04', '976': '06'
}

DEPARTEMENTS = {
    '01': 'Ain', '02': 'Aisne', '03': 'Allier', '04': 'Alpes-de-Haute-Provence',
    '05': 'Hautes-Alpes', '06': 'Alpes-Maritimes', '07': 'Ardèche', '08': 'Ardennes',
    '09': 'Ariège', '10': 'Aube', '11': 'Aude', '12': 'Aveyron',
    '13': 'Bouches-du-Rhône', '14': 'Calvados', '15': 'Cantal', '16': 'Charente',
    '17': 'Charente-Maritime', '18': 'Cher', '19': 'Corrèze', '21': "Côte-d'Or",
    '22': "Côtes-d'Armor", '23': 'Creuse', '24': 'Dordogne', '25': 'Doubs',
    '26': 'Drôme', '27': 'Eure', '28': 'Eure-et-Loir', '29': 'Finistère',
    '2A': 'Corse-du-Sud', '2B': 'Haute-Corse',
    '30': 'Gard', '31': 'Haute-Garonne', '32': 'Gers', '33': 'Gironde',
    '34': 'Hérault', '35': 'Ille-et-Vilaine', '36': 'Indre', '37': 'Indre-et-Loire',
    '38': 'Isère', '39': 'Jura', '40': 'Landes', '41': 'Loir-et-Cher',
    '42': 'Loire', '43': 'Haute-Loire', '44': 'Loire-Atlantique', '45': 'Loiret',
    '46': 'Lot', '47': 'Lot-et-Garonne', '48': 'Lozère', '49': 'Maine-et-Loire',
    '50': 'Manche', '51': 'Marne', '52': 'Haute-Marne', '53': 'Mayenne',
    '54': 'Meurthe-et-Moselle', '55': 'Meuse', '56': 'Morbihan', '57': 'Moselle',
    '58': 'Nièvre', '59': 'Nord', '60': 'Oise', '61': 'Orne',
    '62': 'Pas-de-Calais', '63': 'Puy-de-Dôme', '64': 'Pyrénées-Atlantiques',
    '65': 'Hautes-Pyrénées', '66': 'Pyrénées-Orientales', '67': 'Bas-Rhin',
    '68': 'Haut-Rhin', '69': 'Rhône', '70': 'Haute-Saône', '71': 'Saône-et-Loire',
    '72': 'Sarthe', '73': 'Savoie', '74': 'Haute-Savoie', '75': 'Paris',
    '76': 'Seine-Maritime', '77': 'Seine-et-Marne', '78': 'Yvelines',
    '79': 'Deux-Sèvres', '80': 'Somme', '81': 'Tarn', '82': 'Tarn-et-Garonne',
    '83': 'Var', '84': 'Vaucluse', '85': 'Vendée', '86': 'Vienne',
    '87': 'Haute-Vienne', '88': 'Vosges', '89': 'Yonne', '90': 'Territoire de Belfort',
    '91': 'Essonne', '92': 'Hauts-de-Seine', '93': 'Seine-Saint-Denis',
    '94': 'Val-de-Marne', '95': "Val-d'Oise",
    '971': 'Guadeloupe', '972': 'Martinique', '973': 'Guyane',
    '974': 'La Réunion', '976': 'Mayotte'
}

def download_laposte_data():
    """Télécharge les données La Poste (codes postaux)"""
    print("📥 Téléchargement des données La Poste...")
    
    try:
        response = requests.get(LAPOSTE_CSV_URL, timeout=30)
        response.raise_for_status()
        
        # Lire le CSV
        df = pd.read_csv(StringIO(response.text), sep=';', dtype=str)
        
        print(f"   ✅ {len(df)} codes postaux téléchargés")
        return df
    
    except Exception as e:
        print(f"   ❌ Erreur: {e}")
        return None

def process_communes_data(df):
    """Traite et normalise les données"""
    print("\n🔧 Traitement des données...")
    
    # Afficher les colonnes disponibles pour debug
    print(f"   Colonnes disponibles: {list(df.columns)[:10]}")
    
    # Noms de colonnes possibles (selon la source)
    # La Poste peut avoir: code_commune_insee, nom_commune, code_postal, coordonnees_gps
    # OU: Code_commune_INSEE, Nom_commune, Code_postal, coordonnees_gps
    
    # Normaliser les noms de colonnes (minuscules, sans espaces)
    df.columns = df.columns.str.lower().str.strip().str.replace(' ', '_')
    
    # Enlever le # du début si présent
    df.columns = df.columns.str.replace('#', '', regex=False)
    
    print(f"   Colonnes normalisées: {list(df.columns)[:10]}")
    
    communes = []
    seen = set()
    
    for _, row in tqdm(df.iterrows(), total=len(df), desc="Traitement"):
        # Essayer différents noms de colonnes
        code_insee = str(row.get('code_commune_insee', row.get('code_insee', ''))).strip()
        code_postal = str(row.get('code_postal', '')).strip()
        nom_commune = str(row.get('nom_commune', row.get('nom_de_la_commune', row.get('libelle_acheminement', '')))).strip()
        coords_gps = str(row.get('coordonnees_gps', row.get('latitude', ''))).strip()
        
        # Clé unique
        key = f"{code_insee}_{code_postal}"
        if key in seen or not code_insee or not code_postal or code_postal == 'nan':
            continue
        seen.add(key)
        
        # Extraire département
        if len(code_postal) == 5:
            if code_postal.startswith('97'):
                code_dept = code_postal[:3]
            else:
                code_dept = code_postal[:2]
        else:
            continue
        
        # Skip si pas de nom
        if not nom_commune or nom_commune == 'nan':
            continue
        
        # Coordonnées GPS
        latitude, longitude = None, None
        if coords_gps and coords_gps != 'nan' and ',' in coords_gps:
            try:
                lat_str, lon_str = coords_gps.split(',')
                latitude = float(lat_str.strip())
                longitude = float(lon_str.strip())
            except:
                pass
        
        # Région
        code_region = DEPT_TO_REGION.get(code_dept, '')
        nom_region = REGIONS.get(code_region, 'Inconnu')
        nom_departement = DEPARTEMENTS.get(code_dept, 'Inconnu')
        
        communes.append({
            'code_insee': code_insee,
            'code_postal': code_postal,
            'code_departement': code_dept,
            'code_region': code_region,
            'nom_commune': nom_commune,
            'nom_commune_complet': nom_commune,
            'nom_departement': nom_departement,
            'nom_region': nom_region,
            'latitude': latitude,
            'longitude': longitude,
            'population': None,
            'superficie_km2': None
        })
    
    df_communes = pd.DataFrame(communes)
    print(f"   ✅ {len(df_communes)} communes uniques")
    
    if len(df_communes) == 0:
        print("\n   ⚠️ ERREUR: Aucune commune extraite!")
        print("   Vérifiez les noms de colonnes du CSV:")
        print(f"   Colonnes trouvées: {list(df.columns)}")
    
    return df_communes

def load_to_database(df):
    """Charge les données dans PostgreSQL"""
    print("\n💾 Chargement dans la base de données...")
    
    if len(df) == 0:
        print("   ❌ Aucune donnée à charger (DataFrame vide)")
        return False
    
    # DÉDUPLICATION - Garder seulement la première occurrence de chaque code_insee
    initial_count = len(df)
    df = df.drop_duplicates(subset=['code_insee'], keep='first')
    duplicates_removed = initial_count - len(df)
    
    if duplicates_removed > 0:
        print(f"   🔄 {duplicates_removed} doublons (code_insee) supprimés")
    
    db_url = os.getenv('DATABASE_URL')
    if not db_url:
        raise ValueError("❌ DATABASE_URL non trouvée dans .env")
    
    engine = create_engine(db_url)
    
    # Vérifier que la table existe
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name = 'ref_communes_france'
            )
        """))
        table_exists = result.scalar()
        
        if not table_exists:
            print("   ⚠️ Table ref_communes_france n'existe pas. Créez-la d'abord avec init_v2.sql")
            return False
    
    # Vider et charger - MÉTHODE DIRECTE
    print("   🗑️ Vidage de la table existante...")
    
    # Supprimer toutes les lignes directement avec DELETE (plus fiable que TRUNCATE avec pandas)
    with engine.begin() as conn:
        conn.execute(text("DELETE FROM ref_communes_france"))
        conn.execute(text("ALTER SEQUENCE ref_communes_france_commune_id_seq RESTART WITH 1"))
        print("   ✅ Table vidée")
        print("   📥 Insertion des données...")
        
        # Insérer les données dans la même transaction
        df.to_sql('ref_communes_france', conn, if_exists='append', index=False)
    
    print(f"   ✅ {len(df)} communes chargées")
    
    print(f"   ✅ {len(df)} communes chargées")
    
    # Statistiques
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT 
                COUNT(*) as total,
                COUNT(DISTINCT code_departement) as nb_departements,
                COUNT(DISTINCT code_region) as nb_regions,
                COUNT(latitude) as nb_avec_gps
            FROM ref_communes_france
        """))
        stats = result.fetchone()
        
        print(f"\n📊 Statistiques:")
        print(f"   • Total communes: {stats[0]:,}")
        print(f"   • Départements: {stats[1]}")
        print(f"   • Régions: {stats[2]}")
        print(f"   • Avec GPS: {stats[3]:,} ({stats[3]/stats[0]*100:.1f}%)")
    
    return True

def main():
    print("=" * 60)
    print("CHARGEMENT DU RÉFÉRENTIEL DES COMMUNES FRANÇAISES")
    print("=" * 60)
    
    # Télécharger
    df_raw = download_laposte_data()
    if df_raw is None:
        print("\n❌ Échec du téléchargement")
        return
    
    # Traiter
    df_communes = process_communes_data(df_raw)
    
    # Sauvegarder en CSV local
    csv_path = 'ref_communes_france.csv'
    df_communes.to_csv(csv_path, index=False, encoding='utf-8')
    print(f"\n💾 Backup CSV créé: {csv_path}")
    
    # Charger en BDD
    success = load_to_database(df_communes)
    
    if success:
        print("\n" + "=" * 60)
        print("✅ CHARGEMENT TERMINÉ AVEC SUCCÈS")
        print("=" * 60)
        print("\n📋 Prochaines étapes:")
        print("   1. Vérifiez les données: SELECT * FROM ref_communes_france LIMIT 10;")
        print("   2. Testez la recherche: SELECT find_commune('Paris', '75001');")
        print("   3. Adaptez vos collecteurs pour utiliser commune_id")
    else:
        print("\n❌ Échec du chargement")

if __name__ == "__main__":
    main()