"""
show_lemmas.py

Script simple pour afficher les lemmes extraits d'une offre d'emploi.
"""

import json
import sys
from pathlib import Path

# Ajouter le chemin des modules
sys.path.insert(0, str(Path(__file__).parent.parent / "modules"))

from text_cleaner import TextCleaner


def main():
    """Affiche les lemmes d'une offre"""

    # Charger les exemples
    json_path = Path(__file__).parent / "example_offers.json"

    with open(json_path, "r", encoding="utf-8") as f:
        offers = json.load(f)

    # Initialiser le cleaner
    cleaner = TextCleaner()

    # Pour chaque offre
    for i, offer in enumerate(offers, 1):
        print("\n" + "=" * 80)
        print(f"OFFRE {i} : {offer['title']}")
        print("=" * 80)

        # Nettoyer
        cleaned = cleaner.clean_text(offer["description"])

        # Extraire les lemmes
        lemmas = cleaner.lemmatize(cleaned)

        print(f"\n📊 Statistiques :")
        print(f"   - Texte original : {len(offer['description'])} caractères")
        print(f"   - Texte nettoyé  : {len(cleaned)} caractères")
        print(f"   - Nombre de lemmes : {len(lemmas)}")

        print(f"\n🔤 Liste des lemmes (par ordre d'apparition) :")
        print("-" * 80)

        # Afficher les lemmes, 10 par ligne
        for j in range(0, len(lemmas), 10):
            line_lemmas = lemmas[j : j + 10]
            print("   " + ", ".join(line_lemmas))

        print("\n" + "-" * 80)

        # Statistiques de fréquence
        from collections import Counter

        lemma_freq = Counter(lemmas)

        print(f"\n📈 Top 20 lemmes les plus fréquents :")
        print("-" * 80)
        for lemma, count in lemma_freq.most_common(20):
            bar = "█" * min(count, 50)
            print(f"   {lemma:25} : {count:3}x {bar}")

        # Lemmes uniques
        unique_lemmas = set(lemmas)
        print(f"\n💡 {len(unique_lemmas)} lemmes uniques sur {len(lemmas)} total")
        print(
            f"   Taux de répétition : {(1 - len(unique_lemmas)/len(lemmas))*100:.1f}%"
        )

        if i < len(offers):
            input("\nAppuyez sur Entrée pour voir l'offre suivante...")


if __name__ == "__main__":
    main()
