"""
info_extractor.py

Module d'extraction d'informations structurées depuis les offres d'emploi.

Fonctionnalités :
- Extraction des salaires (fourchettes)
- Extraction des années d'expérience requises
- Extraction des niveaux d'études (Bac+X, Master, etc.)
- Extraction des types de contrat
- Extraction des localisations
"""

import re
from typing import Optional, Dict, List, Tuple
from datetime import datetime


class InfoExtractor:
    """Classe pour extraire des informations structurées depuis les offres"""

    def __init__(self):
        """Initialise les patterns de reconnaissance"""

        # Patterns pour les salaires
        self.salary_patterns = [
            # Formats avec "k", "K", "k€"
            r"(\d{1,3})\s*(?:à|a|-|–|et)\s*(\d{1,3})\s*k€?\s*(?:brut)?",  # 40 à 50 k€
            r"(\d{1,3})\s*k€?\s*(?:à|a|-|–|et)\s*(\d{1,3})\s*k€?\s*(?:brut)?",  # 40k à 50k
            # Formats avec montants complets
            r"(\d{1,3}[\s\.]?\d{3})\s*(?:à|a|-|–|et)\s*(\d{1,3}[\s\.]?\d{3})\s*€?\s*(?:brut)?",  # 40 000 à 50 000
            r"(\d{1,3}[\s\.,]\d{3})\s*(?:à|a|-|–|et)\s*(\d{1,3}[\s\.,]\d{3})\s*€?\s*(?:brut)?",  # 40,000 à 50,000
            # Format unique "45k€"
            r"(\d{1,3})\s*k€?\s*(?:brut)?",
            # "Salaire : XXk" ou "Rémunération : XXk"
            r"(?:salaire|rémunération|remuneration)\s*:?\s*(\d{1,3})\s*(?:à|a|-|–|et)\s*(\d{1,3})\s*k€?",
        ]

        # Patterns pour l'expérience
        self.experience_patterns = [
            # "2 à 5 ans", "2-5 ans"
            r"(\d{1,2})\s*(?:à|a|-|–)\s*(\d{1,2})\s*ans?\s*(?:d\')?(?:expérience|experience)",
            # "5 ans d'expérience"
            r"(\d{1,2})\s*ans?\s*(?:d\')?(?:expérience|experience)",
            # "Expérience : 3 ans"
            r"(?:expérience|experience)\s*:?\s*(\d{1,2})\s*(?:à|a|-|–)?\s*(\d{1,2})?\s*ans?",
            # "Junior", "Senior", "Confirmé"
            r"\b(junior|senior|confirmé|confirme|débutant|debutant)\b",
        ]

        # Patterns pour les diplômes
        self.diploma_patterns = [
            # Bac+X
            r"bac\s*\+\s*(\d)",
            # Master, Licence, etc.
            r"\b(master|licence|doctorat|phd|ingénieur|ingenieur|mba)\b",
            # Niveau d'études
            r"niveau\s*(bac\s*\+\s*\d|master|licence)",
        ]

        # Types de contrat
        self.contract_patterns = {
            "CDI": r"\b(cdi|contrat à durée indéterminée|contrat a duree indeterminee)\b",
            "CDD": r"\b(cdd|contrat à durée déterminée|contrat a duree determinee)\b",
            "Stage": r"\b(stage|stagiaire|internship)\b",
            "Alternance": r"\b(alternance|apprentissage|apprenti|contrat de professionnalisation)\b",
            "Freelance": r"\b(freelance|indépendant|independant|portage salarial)\b",
            "Intérim": r"\b(intérim|interim|mission)\b",
        }

        # Patterns pour télétravail
        self.remote_patterns = [
            r"(télétravail|teletravail|remote|home office|travail à distance)",
            r"(\d+)\s*(?:jour|jours|j)(?:/semaine)?\s*(?:de\s*)?(?:télétravail|teletravail|remote)",
            r"(\d+)%\s*(?:de\s*)?(?:télétravail|teletravail|remote)",
            r"(full remote|100% remote|100% télétravail)",
        ]

    def extract_salary(self, text: str) -> Dict[str, Optional[int]]:
        """
        Extrait les informations de salaire

        Args:
            text: Description de l'offre

        Returns:
            Dict avec min, max, currency (en €/an brut)
        """
        if not text:
            return {"min": None, "max": None, "currency": "EUR", "period": "annual"}

        text_lower = text.lower()

        for pattern in self.salary_patterns:
            matches = re.finditer(pattern, text_lower, re.IGNORECASE)

            for match in matches:
                groups = match.groups()

                # Cas fourchette (2 valeurs)
                if len(groups) >= 2 and groups[0] and groups[1]:
                    val1 = self._parse_salary_value(groups[0])
                    val2 = self._parse_salary_value(groups[1])

                    if val1 and val2:
                        return {
                            "min": min(val1, val2),
                            "max": max(val1, val2),
                            "currency": "EUR",
                            "period": "annual",
                        }

                # Cas valeur unique
                elif len(groups) >= 1 and groups[0]:
                    val = self._parse_salary_value(groups[0])

                    if val:
                        # Approximation : ±10% pour créer une fourchette
                        return {
                            "min": int(val * 0.9),
                            "max": int(val * 1.1),
                            "currency": "EUR",
                            "period": "annual",
                        }

        return {"min": None, "max": None, "currency": "EUR", "period": "annual"}

    def _parse_salary_value(self, value_str: str) -> Optional[int]:
        """
        Parse une valeur de salaire (gère 'k', espaces, etc.)

        Returns:
            Salaire en € annuel
        """
        if not value_str:
            return None

        # Nettoyer
        value_str = (
            value_str.replace(" ", "")
            .replace(".", "")
            .replace(",", "")
            .replace("€", "")
        )

        # Extraire le nombre
        numbers = re.findall(r"\d+", value_str)
        if not numbers:
            return None

        value = int(numbers[0])

        # Si la valeur est en milliers (< 1000), multiplier par 1000
        if value < 1000:
            value *= 1000

        return value

    def extract_experience(self, text: str) -> Dict[str, any]:
        """
        Extrait les années d'expérience requises

        Args:
            text: Description de l'offre

        Returns:
            Dict avec min, max, level
        """
        if not text:
            return {"min": None, "max": None, "level": None}

        text_lower = text.lower()

        # Chercher des années explicites
        for pattern in self.experience_patterns[
            :-1
        ]:  # Exclure le pattern "junior/senior"
            matches = re.finditer(pattern, text_lower, re.IGNORECASE)

            for match in matches:
                groups = match.groups()

                # Cas fourchette
                if len(groups) >= 2 and groups[0] and groups[1]:
                    min_exp = int(groups[0])
                    max_exp = int(groups[1])

                    level = self._infer_level(min_exp, max_exp)

                    return {"min": min_exp, "max": max_exp, "level": level}

                # Cas valeur unique
                elif len(groups) >= 1 and groups[0]:
                    try:
                        years = int(groups[0])
                        level = self._infer_level(years, years)

                        return {"min": years, "max": years, "level": level}
                    except ValueError:
                        pass

        # Chercher des niveaux textuels (junior, senior, etc.)
        level_match = re.search(self.experience_patterns[-1], text_lower)
        if level_match:
            level_text = level_match.group(1)

            level_mapping = {
                "junior": (0, 2, "Junior"),
                "débutant": (0, 1, "Débutant"),
                "debutant": (0, 1, "Débutant"),
                "confirmé": (3, 5, "Confirmé"),
                "confirme": (3, 5, "Confirmé"),
                "senior": (5, 10, "Senior"),
            }

            if level_text in level_mapping:
                min_exp, max_exp, level = level_mapping[level_text]
                return {"min": min_exp, "max": max_exp, "level": level}

        return {"min": None, "max": None, "level": None}

    def _infer_level(self, min_years: int, max_years: int) -> str:
        """Infère le niveau à partir des années d'expérience"""
        avg = (min_years + max_years) / 2

        if avg < 2:
            return "Junior"
        elif avg < 5:
            return "Confirmé"
        else:
            return "Senior"

    def extract_education(self, text: str) -> Dict[str, any]:
        """
        Extrait le niveau d'études requis

        Args:
            text: Description de l'offre

        Returns:
            Dict avec level (Bac+X), degree_type
        """
        if not text:
            return {"level": None, "degree_type": None, "raw": None}

        text_lower = text.lower()

        # Chercher Bac+X
        bac_match = re.search(self.diploma_patterns[0], text_lower)
        if bac_match:
            level = int(bac_match.group(1))

            # Mapper vers type de diplôme
            degree_mapping = {
                2: "BTS/DUT",
                3: "Licence",
                5: "Master/Ingénieur",
                8: "Doctorat",
            }

            degree_type = degree_mapping.get(level, f"Bac+{level}")

            return {"level": level, "degree_type": degree_type, "raw": f"Bac+{level}"}

        # Chercher diplômes textuels
        degree_match = re.search(self.diploma_patterns[1], text_lower)
        if degree_match:
            degree_text = degree_match.group(1)

            degree_level_mapping = {
                "licence": 3,
                "master": 5,
                "ingénieur": 5,
                "ingenieur": 5,
                "doctorat": 8,
                "phd": 8,
                "mba": 5,
            }

            level = degree_level_mapping.get(degree_text, None)

            return {
                "level": level,
                "degree_type": degree_text.capitalize(),
                "raw": degree_text,
            }

        return {"level": None, "degree_type": None, "raw": None}

    def extract_contract_type(self, text: str) -> List[str]:
        """
        Extrait le(s) type(s) de contrat

        Args:
            text: Description de l'offre

        Returns:
            Liste des types de contrat trouvés
        """
        if not text:
            return []

        text_lower = text.lower()
        found_types = []

        for contract_type, pattern in self.contract_patterns.items():
            if re.search(pattern, text_lower):
                found_types.append(contract_type)

        return found_types

    def extract_remote(self, text: str) -> Dict[str, any]:
        """
        Extrait les informations de télétravail

        Args:
            text: Description de l'offre

        Returns:
            Dict avec remote_possible, remote_days, remote_percentage
        """
        if not text:
            return {
                "remote_possible": False,
                "remote_days": None,
                "remote_percentage": None,
            }

        text_lower = text.lower()

        # Vérifier si télétravail mentionné
        if not re.search(self.remote_patterns[0], text_lower):
            return {
                "remote_possible": False,
                "remote_days": None,
                "remote_percentage": None,
            }

        # Full remote
        if re.search(self.remote_patterns[3], text_lower):
            return {"remote_possible": True, "remote_days": 5, "remote_percentage": 100}

        # Nombre de jours
        days_match = re.search(self.remote_patterns[1], text_lower)
        if days_match:
            days = int(days_match.group(1))
            return {
                "remote_possible": True,
                "remote_days": days,
                "remote_percentage": int((days / 5) * 100),
            }

        # Pourcentage
        pct_match = re.search(self.remote_patterns[2], text_lower)
        if pct_match:
            pct = int(pct_match.group(1))
            return {
                "remote_possible": True,
                "remote_days": int((pct / 100) * 5),
                "remote_percentage": pct,
            }

        # Télétravail possible mais pas de détails
        return {"remote_possible": True, "remote_days": None, "remote_percentage": None}

    def extract_all(self, text: str) -> Dict[str, any]:
        """
        Extrait toutes les informations structurées

        Args:
            text: Description de l'offre

        Returns:
            Dictionnaire complet avec toutes les infos
        """
        return {
            "salary": self.extract_salary(text),
            "experience": self.extract_experience(text),
            "education": self.extract_education(text),
            "contract_types": self.extract_contract_type(text),
            "remote": self.extract_remote(text),
        }


# Instance globale
_info_extractor_instance = None


def get_info_extractor() -> InfoExtractor:
    """Retourne une instance singleton du InfoExtractor"""
    global _info_extractor_instance
    if _info_extractor_instance is None:
        _info_extractor_instance = InfoExtractor()
    return _info_extractor_instance


def extract_all_info(text: str) -> Dict[str, any]:
    """Extrait toutes les infos (raccourci)"""
    return get_info_extractor().extract_all(text)


def extract_salary(text: str) -> Dict[str, Optional[int]]:
    """Extrait le salaire (raccourci)"""
    return get_info_extractor().extract_salary(text)


def extract_experience(text: str) -> Dict[str, any]:
    """Extrait l'expérience (raccourci)"""
    return get_info_extractor().extract_experience(text)
