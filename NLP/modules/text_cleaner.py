"""
text_cleaner.py

Module de nettoyage et prétraitement de texte pour les offres d'emploi.

Fonctionnalités :
- Correction encodage UTF-8 (résolution des caractères mal encodés)
- Suppression HTML/Markdown
- Normalisation des espaces et caractères spéciaux
- Lemmatisation avec spaCy
"""

import re
from typing import Optional
from bs4 import BeautifulSoup
import spacy


class TextCleaner:
    """Classe pour nettoyer et prétraiter du texte"""

    def __init__(self, spacy_model: str = "fr_core_news_md"):
        """
        Initialise le nettoyeur de texte

        Args:
            spacy_model: Nom du modèle spaCy à charger (défaut: fr_core_news_md)
        """
        try:
            self.nlp = spacy.load(spacy_model)
        except OSError:
            raise OSError(
                f"Modèle spaCy '{spacy_model}' non trouvé. "
                f"Installez-le avec : python -m spacy download {spacy_model}"
            )

        # Stop-words français étendus
        self.stopwords = set(
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
                "par",
                "ce",
                "cette",
                "ces",
                "son",
                "sa",
                "ses",
                "mon",
                "ma",
                "mes",
                "ton",
                "ta",
                "tes",
                "notre",
                "votre",
                "leur",
                "leurs",
                "qui",
                "que",
                "quoi",
                "dont",
                "où",
                "mais",
                "donc",
                "car",
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
                "h/f",
                "f/h",
                "hf",
                "fh",
            ]
        )

    def fix_encoding(self, text: str) -> str:
        """
        Corrige les problèmes d'encodage UTF-8

        Résout les cas comme : ├® → é, ├á → à, etc.

        Args:
            text: Texte avec problèmes d'encodage

        Returns:
            Texte avec encodage corrigé
        """
        if not text:
            return ""

        # Tentative de correction des encodages doubles (latin1 → utf8)
        try:
            # Essayer de réencoder si on détecte des caractères problématiques
            if any(char in text for char in ["├", "┬", "®", "®"]):
                # C'est probablement de l'UTF-8 mal décodé en latin1
                text = text.encode("latin1").decode("utf-8", errors="ignore")
        except (UnicodeDecodeError, UnicodeEncodeError):
            # Si ça échoue, on garde le texte original
            pass

        # Corrections manuelles pour les cas fréquents
        replacements = {
            "├®": "é",
            "├á": "à",
            "├¿": "ç",
            "├¿": "ù",
            "├®": "è",
            "├«": "ê",
            "├¬": "ô",
            "├¼": "û",
            "├ë": "É",
            "├Ç": "À",
            "├ä": "Ä",
            "┬░": "°",
            "┬½": "½",
            "┬¿": "¿",
            "→": "→",
            "•": "•",
        }

        for old, new in replacements.items():
            text = text.replace(old, new)

        return text

    def remove_html(self, text: str) -> str:
        """
        Supprime les balises HTML et nettoie le texte

        Args:
            text: Texte avec HTML

        Returns:
            Texte sans HTML
        """
        if not text:
            return ""

        # Parser avec BeautifulSoup
        soup = BeautifulSoup(text, "html.parser")

        # Retirer scripts et styles
        for element in soup(["script", "style", "meta", "link"]):
            element.decompose()

        # Extraire le texte
        text = soup.get_text(separator=" ")

        return text

    def normalize_whitespace(self, text: str) -> str:
        """
        Normalise les espaces, tabulations, sauts de ligne

        Args:
            text: Texte à normaliser

        Returns:
            Texte avec espaces normalisés
        """
        if not text:
            return ""

        # Remplacer les sauts de ligne multiples par un seul
        text = re.sub(r"\n{3,}", "\n\n", text)

        # Remplacer tabs et espaces multiples par un seul espace
        text = re.sub(r"[ \t]+", " ", text)

        # Nettoyer les espaces autour des sauts de ligne
        text = re.sub(r" *\n *", "\n", text)

        # Retirer espaces en début/fin
        text = text.strip()

        return text

    def remove_special_chars(self, text: str, keep_punctuation: bool = True) -> str:
        """
        Retire les caractères spéciaux problématiques

        Args:
            text: Texte à nettoyer
            keep_punctuation: Si True, garde la ponctuation de base

        Returns:
            Texte nettoyé
        """
        if not text:
            return ""

        if keep_punctuation:
            # Garder lettres, chiffres, ponctuation de base, espaces
            text = re.sub(r"[^\w\s\.,;:!?()\-\'\"°%€$]", "", text, flags=re.UNICODE)
        else:
            # Garder uniquement lettres, chiffres, espaces, tirets
            text = re.sub(r"[^\w\s\-]", "", text, flags=re.UNICODE)

        return text

    def clean_text(
        self,
        text: str,
        fix_encoding: bool = True,
        remove_html: bool = True,
        normalize_ws: bool = True,
        remove_special: bool = False,
    ) -> str:
        """
        Pipeline complet de nettoyage de texte

        Args:
            text: Texte brut à nettoyer
            fix_encoding: Corriger l'encodage
            remove_html: Supprimer le HTML
            normalize_ws: Normaliser les espaces
            remove_special: Retirer caractères spéciaux

        Returns:
            Texte nettoyé
        """
        if not text:
            return ""

        # Étape 1 : Correction encodage
        if fix_encoding:
            text = self.fix_encoding(text)

        # Étape 2 : Suppression HTML
        if remove_html:
            text = self.remove_html(text)

        # Étape 3 : Normalisation espaces
        if normalize_ws:
            text = self.normalize_whitespace(text)

        # Étape 4 : Caractères spéciaux (optionnel)
        if remove_special:
            text = self.remove_special_chars(text, keep_punctuation=True)

        return text

    def lemmatize(
        self,
        text: str,
        remove_stopwords: bool = True,
        min_length: int = 2,
        allowed_pos: tuple = ("NOUN", "VERB", "ADJ", "PROPN"),
    ) -> list:
        """
        Lemmatise le texte et retourne une liste de tokens

        Args:
            text: Texte à lemmatiser
            remove_stopwords: Retirer les stop-words
            min_length: Longueur minimale des tokens
            allowed_pos: Types grammaticaux à conserver (POS tags)

        Returns:
            Liste de lemmes
        """
        if not text:
            return []

        # Traiter avec spaCy
        doc = self.nlp(text.lower())

        lemmas = []
        for token in doc:
            # Filtres
            if not token.is_alpha:  # Ignorer chiffres et ponctuation
                continue

            if len(token.text) < min_length:  # Trop court
                continue

            if allowed_pos and token.pos_ not in allowed_pos:  # Mauvais POS
                continue

            if remove_stopwords and (
                token.is_stop or token.lemma_.lower() in self.stopwords
            ):
                continue

            lemmas.append(token.lemma_.lower())

        return lemmas

    def clean_and_lemmatize(self, text: str) -> dict:
        """
        Pipeline complet : nettoyage + lemmatisation

        Args:
            text: Texte brut

        Returns:
            Dictionnaire avec texte nettoyé et lemmes
        """
        cleaned = self.clean_text(text)
        lemmas = self.lemmatize(cleaned)

        return {
            "cleaned_text": cleaned,
            "lemmas": lemmas,
            "lemmas_str": " ".join(lemmas),
        }


# Instance globale pour usage simple
_cleaner_instance = None


def get_cleaner(spacy_model: str = "fr_core_news_md") -> TextCleaner:
    """
    Retourne une instance singleton du TextCleaner

    Args:
        spacy_model: Modèle spaCy à utiliser

    Returns:
        Instance de TextCleaner
    """
    global _cleaner_instance
    if _cleaner_instance is None:
        _cleaner_instance = TextCleaner(spacy_model)
    return _cleaner_instance


# Fonctions raccourcis pour usage direct
def clean_text(text: str) -> str:
    """Nettoie un texte (raccourci)"""
    return get_cleaner().clean_text(text)


def lemmatize(text: str) -> list:
    """Lemmatise un texte (raccourci)"""
    return get_cleaner().lemmatize(text)


def clean_and_lemmatize(text: str) -> dict:
    """Nettoie et lemmatise (raccourci)"""
    return get_cleaner().clean_and_lemmatize(text)
