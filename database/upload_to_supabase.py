# upload_to_supabase.py
import psycopg2

DATABASE_URL = "postgresql://postgres:sHN4IwQDZDEmVcZZ@db.dpiwrpxflnlwkjucunka.supabase.co:5432/postgres"

print("📡 Connexion à Supabase...")
conn = psycopg2.connect(DATABASE_URL)
conn.autocommit = False  # Transaction pour tout ou rien

print("📖 Lecture du fichier seed...")
with open('seed_data.sql', 'r', encoding='utf-8') as f:
    sql = f.read()

print("⬆️ Upload en cours (cela peut prendre 5-10 minutes)...")
print("☕ Va prendre un café, c'est normal que ça prenne du temps !")

cursor = conn.cursor()
try:
    cursor.execute(sql)
    conn.commit()
    print("✅ Import terminé avec succès !")
    
    # Vérifie
    cursor.execute("SELECT COUNT(*) FROM fact_job_offers;")
    count = cursor.fetchone()[0]
    print(f"🎉 {count} offres importées dans Supabase !")
    
except Exception as e:
    conn.rollback()
    print(f"❌ Erreur: {e}")
    
finally:
    cursor.close()
    conn.close()