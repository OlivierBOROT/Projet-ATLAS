"""
Script pour ajouter les coordonnées GPS à ref_communes_france
==============================================================
Utilise geopy (Nominatim) pour géocoder les communes françaises

⚠️ ATTENTION:
- Nominatim a une limite de 1 requête/seconde
- Pour 35,000 communes ≈ 10 heures
- Recommandé : géocoder par batch ou utiliser une API payante

Usage:
    # Géocoder toutes les communes sans GPS
    python add_gps_to_communes.py --all

    # Géocoder seulement les N premières
    python add_gps_to_communes.py --limit 100

    # Géocoder une région spécifique
    python add_gps_to_communes.py --region "Île-de-France"
"""

import pandas as pd
from sqlalchemy import create_engine, text
import os
from dotenv import load_dotenv
from time import sleep
from tqdm import tqdm
import argparse
from pathlib import Path

# Charger .env
env_path = Path(__file__).parent.parent / ".env"
if env_path.exists():
    load_dotenv(dotenv_path=env_path)
else:
    load_dotenv()

# Installer avec: pip install geopy
try:
    from geopy.geocoders import Nominatim
    from geopy.exc import GeocoderTimedOut, GeocoderServiceError
except ImportError:
    print("❌ geopy non installé. Installez avec: pip install geopy")
    exit(1)


def geocode_commune(row, geolocator, retries=3):
    """
    Géocode une commune française

    Args:
        row: Ligne du DataFrame (commune)
        geolocator: Instance de Nominatim
        retries: Nombre de tentatives

    Returns:
        (latitude, longitude) ou (None, None)
    """
    # Construire la requête optimale
    query = (
        f"{row['nom_commune']}, {row['code_postal']}, {row['nom_departement']}, France"
    )

    for attempt in range(retries):
        try:
            location = geolocator.geocode(query, timeout=10)
            if location:
                return location.latitude, location.longitude

            # Si échec, essayer sans département
            query_simple = f"{row['nom_commune']}, {row['code_postal']}, France"
            location = geolocator.geocode(query_simple, timeout=10)
            if location:
                return location.latitude, location.longitude

            return None, None

        except (GeocoderTimedOut, GeocoderServiceError):
            if attempt < retries - 1:
                sleep(2)
            else:
                return None, None

    return None, None


def add_gps_to_communes(limit=None, region=None):
    """
    Ajouter les coordonnées GPS aux communes

    Args:
        limit: Limiter à N communes (pour test)
        region: Ne traiter qu'une région spécifique
    """
    print("=" * 70)
    print("AJOUT DES COORDONNÉES GPS À REF_COMMUNES_FRANCE")
    print("=" * 70)

    # Connexion
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        raise ValueError("❌ DATABASE_URL requis dans .env")

    engine = create_engine(db_url)

    # Charger les communes sans GPS
    print("\n📥 Chargement des communes sans GPS...")

    query = """
        SELECT * FROM ref_communes_france
        WHERE latitude IS NULL OR longitude IS NULL
    """

    if region:
        query += f" AND nom_region = '{region}'"

    query += " ORDER BY population DESC NULLS LAST"

    if limit:
        query += f" LIMIT {limit}"

    df = pd.read_sql(query, engine)

    print(f"   ✅ {len(df)} communes à géocoder")

    if len(df) == 0:
        print("\n✅ Toutes les communes ont déjà des coordonnées GPS !")
        return

    # Estimation temps
    estimated_minutes = (len(df) * 1.2) / 60

    print(f"\n⏱️  Estimation:")
    print(
        f"   • Temps: ~{estimated_minutes:.0f} minutes ({estimated_minutes/60:.1f} heures)"
    )
    print(f"   • Limite Nominatim: 1 requête/seconde")

    # Afficher échantillon
    print(f"\n📋 Échantillon des communes à géocoder:")
    for i, row in df.head(5).iterrows():
        print(
            f"   {i+1}. {row['nom_commune']} ({row['code_postal']}) - {row['nom_departement']}"
        )

    if len(df) > 5:
        print(f"   ... et {len(df) - 5} autres")

    # Confirmation
    response = input(f"\n   Continuer? (y/n): ").strip().lower()
    if response != "y":
        print("❌ Annulé")
        return

    # Initialiser le géocodeur
    print("\n🌍 Initialisation du géocodeur Nominatim...")
    geolocator = Nominatim(user_agent="atlas_job_analysis")

    # Géocoder
    print("\n🔄 Géocodage en cours...")

    success_count = 0
    fail_count = 0

    for idx in tqdm(df.index, desc="Géocodage"):
        row = df.loc[idx]

        lat, lon = geocode_commune(row, geolocator)

        if lat and lon:
            # Mettre à jour directement en base
            with engine.begin() as conn:
                conn.execute(
                    text(
                        """
                        UPDATE ref_communes_france
                        SET latitude = :lat, longitude = :lon, updated_at = NOW()
                        WHERE commune_id = :id
                    """
                    ),
                    {
                        "lat": float(lat),
                        "lon": float(lon),
                        "id": int(row["commune_id"]),
                    },
                )
            success_count += 1
        else:
            fail_count += 1

        # Respecter la limite de taux (1 req/sec)
        sleep(1.1)

    # Résultats
    print(f"\n" + "=" * 70)
    print("📊 RÉSULTATS")
    print("=" * 70)
    print(f"Total traité:     {len(df)}")
    print(f"Succès:           {success_count} ({success_count/len(df)*100:.1f}%)")
    print(f"Échecs:           {fail_count}")

    # Stats finales
    with engine.connect() as conn:
        result = conn.execute(
            text(
                """
            SELECT 
                COUNT(*) as total,
                COUNT(latitude) as with_gps,
                COUNT(*) - COUNT(latitude) as without_gps
            FROM ref_communes_france
        """
            )
        )
        stats = result.fetchone()

        print(f"\n📍 État global:")
        print(f"   • Total communes: {stats[0]:,}")
        print(f"   • Avec GPS: {stats[1]:,} ({stats[1]/stats[0]*100:.1f}%)")
        print(f"   • Sans GPS: {stats[2]:,} ({stats[2]/stats[0]*100:.1f}%)")

    print("=" * 70 + "\n")


def main():
    parser = argparse.ArgumentParser(
        description="Ajouter les coordonnées GPS aux communes françaises"
    )

    parser.add_argument("--limit", type=int, help="Limiter à N communes (pour test)")

    parser.add_argument(
        "--region",
        type=str,
        help="Ne traiter qu'une région spécifique (ex: 'Île-de-France')",
    )

    parser.add_argument(
        "--all",
        action="store_true",
        help="Géocoder toutes les communes (peut prendre 10h+)",
    )

    args = parser.parse_args()

    if not args.all and not args.limit and not args.region:
        parser.error("Utilisez --all, --limit N ou --region 'Region'")

    limit = args.limit if args.limit else (None if args.all else 100)

    add_gps_to_communes(limit=limit, region=args.region)


if __name__ == "__main__":
    main()
