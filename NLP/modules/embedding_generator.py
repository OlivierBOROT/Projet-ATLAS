"""
Module de génération et comparaison d'embeddings
================================================
Encapsule le modèle SentenceTransformer pour la création et comparaison
d'embeddings de textes.
"""

import numpy as np
from sentence_transformers import SentenceTransformer
from typing import List, Union, Tuple


class EmbeddingGenerator:
    """
    Génère et compare des embeddings de textes
    """

    def __init__(self, model_name: str = "paraphrase-multilingual-MiniLM-L12-v2"):
        """
        Initialise le générateur d'embeddings

        Args:
            model_name: Nom du modèle SentenceTransformer à utiliser
        """
        self.model_name = model_name
        self.model = SentenceTransformer(model_name)
        self.embedding_dim = self.model.get_sentence_embedding_dimension()

    def generate(
        self, text: Union[str, List[str]]
    ) -> Union[np.ndarray, List[np.ndarray]]:
        """
        Génère un embedding pour un ou plusieurs textes

        Args:
            text: Texte unique (str) ou liste de textes (List[str])

        Returns:
            Embedding(s) sous forme de numpy array(s)
        """
        if isinstance(text, str):
            return self.model.encode(text)
        else:
            return self.model.encode(text)

    def cosine_similarity(
        self, embedding1: np.ndarray, embedding2: np.ndarray
    ) -> float:
        """
        Calcule la similarité cosinus entre deux embeddings

        Args:
            embedding1: Premier embedding
            embedding2: Deuxième embedding

        Returns:
            Score de similarité entre -1 et 1 (1 = identique)
        """
        return np.dot(embedding1, embedding2) / (
            np.linalg.norm(embedding1) * np.linalg.norm(embedding2)
        )

    def euclidean_distance(
        self, embedding1: np.ndarray, embedding2: np.ndarray
    ) -> float:
        """
        Calcule la distance euclidienne entre deux embeddings

        Args:
            embedding1: Premier embedding
            embedding2: Deuxième embedding

        Returns:
            Distance euclidienne (0 = identique, plus grand = plus différent)
        """
        return np.linalg.norm(embedding1 - embedding2)

    def find_most_similar(
        self,
        query_embedding: np.ndarray,
        embeddings: List[np.ndarray],
        top_k: int = 5,
    ) -> List[Tuple[int, float]]:
        """
        Trouve les embeddings les plus similaires à une requête

        Args:
            query_embedding: Embedding de la requête
            embeddings: Liste d'embeddings à comparer
            top_k: Nombre de résultats à retourner

        Returns:
            Liste de tuples (index, similarité) triée par similarité décroissante
        """
        similarities = []
        for idx, emb in enumerate(embeddings):
            sim = self.cosine_similarity(query_embedding, emb)
            similarities.append((idx, sim))

        # Trier par similarité décroissante
        similarities.sort(key=lambda x: x[1], reverse=True)

        return similarities[:top_k]

    def batch_cosine_similarity(
        self, embeddings1: List[np.ndarray], embeddings2: List[np.ndarray]
    ) -> np.ndarray:
        """
        Calcule la matrice de similarité entre deux listes d'embeddings

        Args:
            embeddings1: Première liste d'embeddings
            embeddings2: Deuxième liste d'embeddings

        Returns:
            Matrice de similarité (n1 x n2)
        """
        # Convertir en matrices
        matrix1 = np.vstack(embeddings1)
        matrix2 = np.vstack(embeddings2)

        # Normaliser
        matrix1_norm = matrix1 / np.linalg.norm(matrix1, axis=1, keepdims=True)
        matrix2_norm = matrix2 / np.linalg.norm(matrix2, axis=1, keepdims=True)

        # Produit matriciel pour calculer toutes les similarités
        return np.dot(matrix1_norm, matrix2_norm.T)

    def get_model_info(self) -> dict:
        """
        Retourne les informations du modèle

        Returns:
            Dictionnaire avec les infos du modèle
        """
        return {
            "model_name": self.model_name,
            "embedding_dimension": self.embedding_dim,
            "max_seq_length": self.model.max_seq_length,
        }
