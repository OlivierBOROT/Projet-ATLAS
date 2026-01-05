"""
Script de test des embeddings
Calcule et compare les embeddings des offres d'exemple
"""

import json
import sys
import os
from pathlib import Path
import numpy as np

# Ajouter le chemin des modules NLP
sys.path.insert(0, str(Path(__file__).parent.parent / "modules"))

from text_cleaner import TextCleaner
from embedding_generator import EmbeddingGenerator


def main():
    print("=" * 80)
    print("🧪 TEST DES EMBEDDINGS")
    print("=" * 80)
    print()

    # Charger les offres d'exemple
    json_path = Path(__file__).parent / "example_emb_offers.json"

    print(f"📂 Chargement des offres depuis : {json_path.name}")
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    offers = data["offers"]
    print(f"✅ {len(offers)} offres chargées\n")

    # Initialiser les modules
    print("⏳ Initialisation des modules...")
    cleaner = TextCleaner()
    embedding_gen = EmbeddingGenerator()

    # Afficher les infos du modèle
    model_info = embedding_gen.get_model_info()
    print(f"✅ Modèle : {model_info['model_name']}")
    print(f"   Dimensions : {model_info['embedding_dimension']}")
    print()

    # Traiter chaque offre
    results = []

    print("🔬 TRAITEMENT DES OFFRES")
    print("-" * 80)

    for offer in offers:
        offer_id = offer["offer_id"]
        text = offer["text"]

        print(f"\n📄 Offre #{offer_id}")
        print(f"   Texte original : {len(text)} caractères")

        # Nettoyer et lemmatiser
        cleaned = cleaner.clean_text(text)
        lemmas = cleaner.lemmatize(cleaned)
        text_cleaned = " ".join(lemmas)

        print(f"   Texte nettoyé : {len(text_cleaned)} caractères")
        print(f"   Extrait : {text_cleaned[:100]}...")

        # Calculer l'embedding
        embedding = embedding_gen.generate(text_cleaned)

        print(f"   Embedding : vecteur de {len(embedding)} dimensions")
        print(f"   Norme L2 : {np.linalg.norm(embedding):.4f}")
        print(f"   Min/Max : [{embedding.min():.4f}, {embedding.max():.4f}]")

        results.append(
            {
                "offer_id": offer_id,
                "text": text,
                "text_cleaned": text_cleaned,
                "embedding": embedding,
                "text_length": len(text),
                "cleaned_length": len(text_cleaned),
            }
        )

    # Analyse des similarités
    print("\n" + "=" * 80)
    print("📊 ANALYSE DES SIMILARITÉS")
    print("=" * 80)
    print()

    # Matrice de similarité
    n = len(results)
    similarity_matrix = np.zeros((n, n))

    for i in range(n):
        for j in range(n):
            similarity_matrix[i, j] = embedding_gen.cosine_similarity(
                results[i]["embedding"], results[j]["embedding"]
            )

    print("📐 Matrice de similarité cosinus :")
    print()

    # Header
    header = "        " + "".join([f"  Off#{r['offer_id']}" for r in results])
    print(header)
    print("-" * len(header))

    # Lignes
    for i, result in enumerate(results):
        row = f"Off#{result['offer_id']:<3} |"
        for j in range(n):
            sim = similarity_matrix[i, j]
            if i == j:
                row += f"  1.0000"
            else:
                row += f"  {sim:.4f}"
        print(row)

    # Statistiques
    print("\n📊 STATISTIQUES :")
    print()

    # Similarités entre offres différentes
    off_diagonal = []
    for i in range(n):
        for j in range(i + 1, n):
            off_diagonal.append(similarity_matrix[i, j])

    if off_diagonal:
        print(
            f"   Similarité moyenne (offres différentes) : {np.mean(off_diagonal):.4f}"
        )
        print(f"   Similarité min : {np.min(off_diagonal):.4f}")
        print(f"   Similarité max : {np.max(off_diagonal):.4f}")
        print(f"   Écart-type : {np.std(off_diagonal):.4f}")

    # Vérification des textes identiques
    print("\n🔍 VÉRIFICATION DES TEXTES :")
    print()

    unique_texts = {}
    for result in results:
        text_hash = hash(result["text"])
        if text_hash not in unique_texts:
            unique_texts[text_hash] = [result["offer_id"]]
        else:
            unique_texts[text_hash].append(result["offer_id"])

    if len(unique_texts) == 1:
        print("   ⚠️  TOUTES les offres ont le MÊME texte !")
        print(
            f"   Offres identiques : {', '.join([f'#{oid}' for oid in list(unique_texts.values())[0]])}"
        )
    else:
        print(f"   ✅ {len(unique_texts)} textes uniques détectés")
        for i, (text_hash, offer_ids) in enumerate(unique_texts.items(), 1):
            if len(offer_ids) > 1:
                print(
                    f"   Groupe {i} : Offres {', '.join([f'#{oid}' for oid in offer_ids])} (texte identique)"
                )

    # Vérification de la cohérence des embeddings
    print("\n✅ VALIDATION :")
    print()

    # Si textes identiques, embeddings doivent être presque identiques
    if len(unique_texts) == 1:
        max_diff = 0
        for i in range(n):
            for j in range(i + 1, n):
                diff = np.abs(results[i]["embedding"] - results[j]["embedding"]).max()
                max_diff = max(max_diff, diff)

        print(f"   Différence max entre embeddings : {max_diff:.6f}")

        if max_diff < 1e-6:
            print("   ✅ Embeddings identiques (différence négligeable)")
        elif max_diff < 1e-3:
            print("   ✅ Embeddings très similaires (différence acceptable)")
        else:
            print(
                "   ⚠️  Embeddings diffèrent plus que prévu pour des textes identiques"
            )

    print("\n" + "=" * 80)
    print("✅ TEST TERMINÉ")
    print("=" * 80)


if __name__ == "__main__":
    main()
