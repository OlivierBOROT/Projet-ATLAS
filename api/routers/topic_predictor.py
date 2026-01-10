"""
Topic Predictor pour les offres d'emploi
=========================================

Prédit le topic LDA d'une offre basé sur son titre.
Utilise le modèle LDA pré-entraîné.
"""

import pickle
import spacy
import re
from pathlib import Path
from typing import Dict, Optional, Tuple
import logging

logger = logging.getLogger("topic_predictor")


# Labels des 8 topics
TOPIC_LABELS = [
    "Ingénierie Cloud & Cybersécurité",
    "Consulting & Architecture IT",
    "Data Analysis & Transformation Digitale",
    "Direction Commerciale & Administration IT",
    "Gestion Commerciale & Qualité",
    "Gestion de Projet & Développement",
    "Ingénierie R&D & Data Science",
    "Product Management & Développement Java",
]

# Stopwords pour lemmatisation
TITLE_STOPWORDS = set(
    [
        "le",
        "la",
        "les",
        "un",
        "une",
        "des",
        "de",
        "du",
        "au",
        "aux",
        "et",
        "ou",
        "pour",
        "avec",
        "sans",
        "sur",
        "sous",
        "dans",
        "junior",
        "senior",
        "confirmé",
        "confirme",
        "expérimenté",
        "experimente",
        "indépendant",
        "independant",
        "adjoint",
        "multi",
        "sites",
        "alternance",
        "stage",
        "cdi",
        "cdd",
    ]
)


class TopicPredictor:
    """Prédit le topic d'une offre avec le modèle LDA"""

    def __init__(self, model_path: Optional[str] = None):
        """
        Initialiser le prédicateur de topics

        Args:
            model_path: Chemin vers le fichier .pkl du modèle LDA
                       Si None, cherche le fichier par défaut
        """
        # Trouver le modèle
        if model_path is None:
            # Chercher dans le dossier NLP/scripts
            nlp_scripts_dir = Path(__file__).parent.parent / "NLP" / "scripts"

            # Chercher tous les fichiers lda_model_*.pkl
            model_files = list(nlp_scripts_dir.glob("lda_model_*.pkl"))

            if not model_files:
                raise FileNotFoundError(
                    f"❌ Aucun modèle LDA trouvé dans {nlp_scripts_dir}\n"
                    "Exécutez d'abord NLP/scripts/topic_modeling_full.py"
                )

            # Prendre le plus récent
            model_path = max(model_files, key=lambda p: p.stat().st_mtime)
            logger.info(f"📦 Modèle LDA trouvé : {model_path.name}")

        # Charger le modèle
        try:
            with open(model_path, "rb") as f:
                saved = pickle.load(f)
                self.lda = saved["lda"]
                self.vectorizer = saved["vectorizer"]
                self.feature_names = saved["feature_names"]

            logger.info(f"✅ Modèle LDA chargé : {self.lda.n_components} topics")

        except Exception as e:
            raise RuntimeError(f"❌ Erreur chargement modèle LDA : {e}")

        # Charger spaCy
        try:
            self.nlp = spacy.load("fr_core_news_md")
            logger.info("✅ spaCy FR chargé")
        except:
            raise RuntimeError(
                "❌ spaCy FR non installé. Exécutez : "
                "python -m spacy download fr_core_news_md"
            )

    def clean_title(self, title: str) -> str:
        """Nettoie un titre d'offre"""
        if not title:
            return ""

        title = title.lower()

        # Supprimer (h/f), (f/h), etc.
        title = re.sub(r"\(h/f\)|\(f/h\)|\bh/f\b|\bf/h\b", "", title)

        # Supprimer mentions de contrat
        title = re.sub(
            r"\(cdi\)|\(cdd\)|\bstage\b|\balternance\b", "", title, flags=re.IGNORECASE
        )

        # Garder seulement lettres, chiffres, espaces, tirets
        title = re.sub(r"[^\w\s\-]", " ", title)

        # Normaliser les espaces
        title = re.sub(r"\s+", " ", title).strip()

        return title

    def lemmatize_title(self, title: str) -> str:
        """Lemmatise un titre"""
        if not title:
            return ""

        doc = self.nlp(title)

        lemmas = [
            token.lemma_.lower()
            for token in doc
            if (
                token.pos_ in ["NOUN", "ADJ", "PROPN"]
                and not token.is_stop
                and token.lemma_.lower() not in TITLE_STOPWORDS
                and len(token.lemma_) > 2
                and token.is_alpha
            )
        ]

        return " ".join(lemmas)

    def predict_topic(self, title: str) -> Dict:
        """
        Prédit le topic d'une offre depuis son titre

        Args:
            title: Titre de l'offre

        Returns:
            Dict avec topic_id, topic_label, topic_confidence
        """
        if not title:
            return {"topic_id": None, "topic_label": None, "topic_confidence": 0.0}

        try:
            # Preprocessing
            title_clean = self.clean_title(title)
            title_lemmatized = self.lemmatize_title(title_clean)

            if not title_lemmatized:
                # Fallback si lemmatisation vide
                return {"topic_id": None, "topic_label": None, "topic_confidence": 0.0}

            # Vectoriser
            title_vec = self.vectorizer.transform([title_lemmatized])

            # Prédire
            topic_dist = self.lda.transform(title_vec)
            topic_id = int(topic_dist.argmax())
            confidence = float(topic_dist.max())

            return {
                "topic_id": topic_id,
                "topic_label": TOPIC_LABELS[topic_id],
                "topic_confidence": round(confidence, 2),
            }

        except Exception as e:
            logger.error(f"❌ Erreur prédiction topic : {e}")
            return {"topic_id": None, "topic_label": None, "topic_confidence": 0.0}


# Instance globale (singleton)
_predictor_instance = None


def get_topic_predictor() -> TopicPredictor:
    """Retourne une instance singleton du TopicPredictor"""
    global _predictor_instance
    if _predictor_instance is None:
        _predictor_instance = TopicPredictor()
    return _predictor_instance


def predict_topic_for_offer(title: str) -> Dict:
    """
    Raccourci pour prédire le topic d'une offre

    Args:
        title: Titre de l'offre

    Returns:
        Dict avec topic_id, topic_label, topic_confidence
    """
    predictor = get_topic_predictor()
    return predictor.predict_topic(title)


# ============================================================================
# TEST
# ============================================================================
if __name__ == "__main__":
    print("\n🧪 TEST TOPIC PREDICTOR\n")

    test_titles = [
        "Data Analyst H/F - CDI",
        "Développeur Python Senior",
        "Chef de Projet IT",
        "Ingénieur Data Science - Machine Learning",
        "Consultant Cloud AWS",
    ]

    try:
        predictor = TopicPredictor()

        for title in test_titles:
            result = predictor.predict_topic(title)
            print(f"📊 {title}")
            print(f"   → Topic {result['topic_id']}: {result['topic_label']}")
            print(f"   → Confiance: {result['topic_confidence']:.0%}\n")

        print("✅ Test terminé avec succès!")

    except Exception as e:
        print(f"❌ Erreur: {e}")
        import traceback

        traceback.print_exc()
