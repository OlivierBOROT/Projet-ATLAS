"""
skill_extractor.py

Module d'extraction des compétences techniques et soft skills depuis les offres d'emploi.

Fonctionnalités :
- Détection des compétences techniques (langages, frameworks, outils)
- Détection des soft skills
- Détection contextuelle avec patterns
- Scoring de pertinence
"""

import re
import json
import os
from pathlib import Path
from typing import List, Dict, Set
from collections import Counter


class SkillExtractor:
    """Classe pour extraire les compétences depuis les descriptions d'offres"""

    def __init__(self):
        """Initialise les dictionnaires de compétences depuis les fichiers JSON"""

        # Charger les fichiers JSON
        data_dir = Path(__file__).parent.parent / "data"

        with open(data_dir / "skills_tech.json", "r", encoding="utf-8") as f:
            self.tech_skills_data = json.load(f)

        with open(data_dir / "skills_soft.json", "r", encoding="utf-8") as f:
            self.soft_skills_data = json.load(f)

        # Construire les sets pour la compatibilité avec le code existant
        self._build_skill_sets()

    def _build_skill_sets(self):
        """Construit les sets de skills à partir des données JSON"""

        # Skills techniques
        self.languages = set()
        self.systems = set()
        self.frameworks = set()
        self.databases = set()
        self.cloud = set()
        self.bi = set()
        self.methods = set()
        self.devops = set()
        self.tools = set()
        self.data_concepts = set()
        self.security = set()
        self.business_software = set()

        # Parcourir les skills techniques et ajouter tous les synonymes
        for category, skills in self.tech_skills_data.items():
            for skill_name, skill_data in skills.items():
                # Déterminer le set cible
                if category == "bi_analytics":
                    target_set = self.bi
                elif category == "methodologies":
                    target_set = self.methods
                elif category == "data_concepts":
                    target_set = self.data_concepts
                else:
                    target_set = getattr(self, category, set())

                # Ajouter le nom principal et tous les synonymes
                target_set.add(skill_name.lower())
                for synonym in skill_data["synonyms"]:
                    target_set.add(synonym.lower())

        # Skills soft
        self.soft_skills = set()
        for category, skills in self.soft_skills_data.items():
            for skill_name, skill_data in skills.items():
                # Ajouter le nom principal
                self.soft_skills.add(skill_name.lower())
                # Ajouter tous les synonymes
                for synonym in skill_data["synonyms"]:
                    self.soft_skills.add(synonym.lower())

        # Regrouper toutes les skills techniques
        self.all_tech_skills = (
            self.languages
            | self.systems
            | self.frameworks
            | self.databases
            | self.cloud
            | self.devops
            | self.bi
            | self.methods
            | self.tools
            | self.data_concepts
            | self.security
            | self.business_software
        )

        # Construire le mapping skill -> patterns pour la détection contextuelle
        self.skill_patterns = {}

        # Patterns tech
        for category, skills in self.tech_skills_data.items():
            for skill_name, skill_data in skills.items():
                if skill_data.get("context_patterns"):
                    self.skill_patterns[skill_name.lower()] = skill_data[
                        "context_patterns"
                    ]

        # Patterns soft
        for category, skills in self.soft_skills_data.items():
            for skill_name, skill_data in skills.items():
                if skill_data.get("context_patterns"):
                    self.skill_patterns[skill_name.lower()] = skill_data[
                        "context_patterns"
                    ]

    def extract_skills(self, text: str) -> Dict[str, List[str]]:
        """
        Extrait toutes les compétences depuis un texte

        Args:
            text: Description de l'offre d'emploi

        Returns:
            Dictionnaire avec compétences par catégorie
        """
        if not text:
            return self._empty_result()

        text_lower = text.lower()

        # 1. Détection directe par mots-clés
        result = {
            "languages": self._find_skills(text_lower, self.languages),
            "systems": self._find_skills(text_lower, self.systems),
            "frameworks": self._find_skills(text_lower, self.frameworks),
            "databases": self._find_skills(text_lower, self.databases),
            "cloud": self._find_skills(text_lower, self.cloud),
            "devops": self._find_skills(text_lower, self.devops),
            "bi": self._find_skills(text_lower, self.bi),
            "methods": self._find_skills(text_lower, self.methods),
            "data_concepts": self._find_skills(text_lower, self.data_concepts),
            "tools": self._find_skills(text_lower, self.tools),
            "security": self._find_skills(text_lower, self.security),
            "business_software": self._find_skills(text_lower, self.business_software),
            "soft_skills": self._find_skills(text_lower, self.soft_skills),
        }

        # 2. Détection contextuelle via patterns
        contextual_skills = self._find_skills_by_context(text_lower)

        # Fusionner les résultats contextuels avec les résultats directs
        for category, skills in contextual_skills.items():
            if category in result:
                result[category] = sorted(set(result[category] + skills))

        # Ajouter un résumé
        result["all_tech_skills"] = sorted(
            set(
                result["languages"]
                + result["systems"]
                + result["frameworks"]
                + result["databases"]
                + result["cloud"]
                + result["devops"]
                + result["bi"]
                + result["methods"]
                + result["data_concepts"]
                + result["tools"]
                + result["security"]
                + result["business_software"]
            )
        )

        result["skill_count"] = {
            "tech": len(result["all_tech_skills"]),
            "soft": len(result["soft_skills"]),
            "total": len(result["all_tech_skills"]) + len(result["soft_skills"]),
        }

        return result

    def _find_skills_by_context(self, text: str) -> Dict[str, List[str]]:
        """
        Détecte les skills via des patterns contextuels

        Par exemple: "langages de requêtes" → détecte SQL
        "modélisation de données" → détecte SQL

        Args:
            text: Texte en minuscules

        Returns:
            Dictionnaire avec skills détectées par catégorie
        """
        found_skills = {
            "languages": [],
            "systems": [],
            "frameworks": [],
            "databases": [],
            "cloud": [],
            "devops": [],
            "bi": [],
            "methods": [],
            "security": [],
            "business_software": [],
            "soft_skills": [],
            "tools": [],
            "data_concepts": [],
        }

        # Parcourir tous les patterns définis
        for skill_name, patterns in self.skill_patterns.items():
            for pattern in patterns:
                try:
                    # Recherche avec regex (pattern déjà défini comme regex dans le JSON)
                    if re.search(pattern, text, re.IGNORECASE):
                        # Déterminer la catégorie de la skill
                        category = self._get_skill_category(skill_name)
                        if category and skill_name not in found_skills[category]:
                            found_skills[category].append(skill_name)
                        break  # Une fois trouvé, pas besoin de continuer
                except re.error as e:
                    # Si le pattern est invalide, ignorer
                    continue

        return found_skills

    def _get_skill_category(self, skill_name: str) -> str:
        """Détermine la catégorie d'une skill"""
        skill_lower = skill_name.lower()

        if skill_lower in self.languages:
            return "languages"
        elif skill_lower in self.systems:
            return "systems"
        elif skill_lower in self.frameworks:
            return "frameworks"
        elif skill_lower in self.databases:
            return "databases"
        elif skill_lower in self.cloud:
            return "cloud"
        elif skill_lower in self.devops:
            return "devops"
        elif skill_lower in self.bi:
            return "bi"
        elif skill_lower in self.methods:
            return "methods"
        elif skill_lower in self.data_concepts:
            return "data_concepts"
        elif skill_lower in self.tools:
            return "tools"
        elif skill_lower in self.security:
            return "security"
        elif skill_lower in self.business_software:
            return "business_software"
        elif skill_lower in self.soft_skills:
            return "soft_skills"

        # Si la skill n'est pas dans les sets, chercher dans les données JSON
        for category, skills in self.tech_skills_data.items():
            if skill_name in skills:
                # Mapper le nom de catégorie JSON au nom utilisé
                category_map = {
                    "bi_analytics": "bi",
                    "methodologies": "methods",
                }
                return category_map.get(category, category)

        for category, skills in self.soft_skills_data.items():
            if skill_name in skills:
                return "soft_skills"

        return None

    def _find_skills(self, text: str, skill_set: Set[str]) -> List[str]:
        """
        Trouve les compétences présentes dans le texte

        Args:
            text: Texte en minuscules
            skill_set: Ensemble de compétences à rechercher

        Returns:
            Liste des compétences trouvées
        """
        found = []

        for skill in skill_set:
            # Pattern pour matcher le mot complet (word boundaries)
            # Pour les skills avec espaces/tirets, on les cherche telles quelles
            if " " in skill or "-" in skill or "/" in skill or "." in skill:
                if skill in text:
                    found.append(skill)
            else:
                # Pour les mots simples, utiliser word boundaries
                pattern = r"\b" + re.escape(skill) + r"\b"
                if re.search(pattern, text):
                    found.append(skill)

        return sorted(found)

    def _empty_result(self) -> Dict:
        """Retourne un résultat vide"""
        return {
            "languages": [],
            "systems": [],
            "frameworks": [],
            "databases": [],
            "cloud": [],
            "devops": [],
            "bi": [],
            "methods": [],
            "data_concepts": [],
            "tools": [],
            "security": [],
            "business_software": [],
            "soft_skills": [],
            "all_tech_skills": [],
            "skill_count": {"tech": 0, "soft": 0, "total": 0},
        }

    def get_top_skills(self, text: str, n: int = 10) -> List[tuple]:
        """
        Retourne les N compétences les plus importantes

        Args:
            text: Description de l'offre
            n: Nombre de skills à retourner

        Returns:
            Liste de tuples (skill, score)
        """
        skills = self.extract_skills(text)

        # Créer un compteur avec pondération par catégorie
        weighted_skills = {}

        # Langages (poids fort)
        for skill in skills["languages"]:
            weighted_skills[skill] = weighted_skills.get(skill, 0) + 3

        # Systems & Frameworks & Databases (poids moyen-fort)
        for skill in skills["systems"] + skills["frameworks"] + skills["databases"]:
            weighted_skills[skill] = weighted_skills.get(skill, 0) + 2

        # Autres tech (poids moyen)
        for skill in (
            skills["cloud"]
            + skills["devops"]
            + skills["bi"]
            + skills["methods"]
            + skills["data_concepts"]
            + skills["tools"]
            + skills["security"]
            + skills["business_software"]
        ):
            weighted_skills[skill] = weighted_skills.get(skill, 0) + 1.5

        # Soft skills (poids faible)
        for skill in skills["soft_skills"]:
            weighted_skills[skill] = weighted_skills.get(skill, 0) + 0.5

        # Trier par score décroissant
        sorted_skills = sorted(
            weighted_skills.items(), key=lambda x: x[1], reverse=True
        )

        return sorted_skills[:n]

    def categorize_offer(self, text: str) -> Dict[str, any]:
        """
        Catégorise une offre selon les compétences dominantes

        Args:
            text: Description de l'offre

        Returns:
            Catégorisation avec profil dominant
        """
        skills = self.extract_skills(text)

        # Scores par profil
        profiles = {
            "Data Science / ML": 0,
            "Data Engineering": 0,
            "Backend Developer": 0,
            "Frontend Developer": 0,
            "Full Stack Developer": 0,
            "DevOps / SRE": 0,
            "Cloud Engineer": 0,
            "Business Intelligence": 0,
            "Cybersécurité": 0,
            "IT Management": 0,
        }

        # Data Science
        ml_keywords = {
            "python",
            "r",
            "tensorflow",
            "pytorch",
            "keras",
            "sklearn",
            "machine learning",
            "deep learning",
            "nlp",
            "computer vision",
        }
        profiles["Data Science / ML"] = len(
            [s for s in skills["all_tech_skills"] if s in ml_keywords]
        )

        # Data Engineering
        de_keywords = {
            "spark",
            "hadoop",
            "airflow",
            "kafka",
            "snowflake",
            "bigquery",
            "etl",
            "elt",
            "data engineering",
        }
        profiles["Data Engineering"] = len(
            [s for s in skills["all_tech_skills"] if s in de_keywords]
        )

        # Backend
        backend_keywords = {
            "java",
            "python",
            "php",
            "node.js",
            "django",
            "flask",
            "spring",
            "fastapi",
            "express",
        }
        profiles["Backend Developer"] = len(
            [s for s in skills["all_tech_skills"] if s in backend_keywords]
        )

        # Frontend
        frontend_keywords = {
            "react",
            "angular",
            "vue",
            "javascript",
            "typescript",
            "html",
            "css",
            "next.js",
        }
        profiles["Frontend Developer"] = len(
            [s for s in skills["all_tech_skills"] if s in frontend_keywords]
        )

        # DevOps
        devops_keywords = {
            "docker",
            "kubernetes",
            "jenkins",
            "terraform",
            "ansible",
            "ci/cd",
            "devops",
        }
        profiles["DevOps / SRE"] = len(
            [s for s in skills["all_tech_skills"] if s in devops_keywords]
        )

        # Cloud
        cloud_keywords = {"aws", "azure", "gcp", "kubernetes", "docker"}
        profiles["Cloud Engineer"] = len(
            [s for s in skills["all_tech_skills"] if s in cloud_keywords]
        )

        # BI
        bi_keywords = {"power bi", "tableau", "looker", "qlik", "dbt"}
        profiles["Business Intelligence"] = len(
            [s for s in skills["all_tech_skills"] if s in bi_keywords]
        )

        # Cybersécurité
        sec_keywords = {
            "cybersécurité",
            "cybersecurite",
            "owasp",
            "pentest",
            "soc",
            "siem",
        }
        profiles["Cybersécurité"] = len(
            [s for s in skills["all_tech_skills"] if s in sec_keywords]
        )

        # Profil dominant
        dominant_profile = max(profiles.items(), key=lambda x: x[1])

        return {
            "dominant_profile": (
                dominant_profile[0] if dominant_profile[1] > 0 else "Généraliste"
            ),
            "profile_score": dominant_profile[1],
            "all_profiles": profiles,
            "is_full_stack": profiles["Frontend Developer"] >= 2
            and profiles["Backend Developer"] >= 2,
        }


# Instance globale
_extractor_instance = None


def get_extractor() -> SkillExtractor:
    """Retourne une instance singleton du SkillExtractor"""
    global _extractor_instance
    if _extractor_instance is None:
        _extractor_instance = SkillExtractor()
    return _extractor_instance


def extract_skills(text: str) -> Dict[str, List[str]]:
    """Extrait les compétences (raccourci)"""
    return get_extractor().extract_skills(text)


def get_top_skills(text: str, n: int = 10) -> List[tuple]:
    """Top N compétences (raccourci)"""
    return get_extractor().get_top_skills(text, n)


def categorize_offer(text: str) -> Dict[str, any]:
    """Catégorise l'offre (raccourci)"""
    return get_extractor().categorize_offer(text)
