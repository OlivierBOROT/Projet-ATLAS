# setup_supabase.py
import psycopg2

DATABASE_URL = "postgresql://postgres:sHN4IwQDZDEmVcZZ@db.dpiwrpxflnlwkjucunka.supabase.co:5432/postgres"

print("📡 Connexion à Supabase...")
conn = psycopg2.connect(DATABASE_URL)
conn.autocommit = True

cursor = conn.cursor()

# Étape 1 : Crée les tables (init.sql)
print("🏗️ Création des tables...")
with open('init.sql', 'r', encoding='utf-8') as f:
    init_sql = f.read()

try:
    cursor.execute(init_sql)
    print("✅ Tables créées avec succès !")
except Exception as e:
    print(f"⚠️ Erreur lors de la création des tables: {e}")
    print("Les tables existent peut-être déjà, on continue...")

# Vérifie que les tables existent
cursor.execute("""
    SELECT table_name 
    FROM information_schema.tables 
    WHERE table_schema = 'public' 
    ORDER BY table_name;
""")
tables = cursor.fetchall()
print(f"\n📋 Tables dans la base: {[t[0] for t in tables]}")

cursor.close()
conn.close()

print("\n✅ Setup terminé ! Tu peux maintenant lancer upload_to_supabase.py")