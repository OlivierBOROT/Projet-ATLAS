"""
__init__.py

Module NLP pour le projet ATLAS.

Extraction de compétences et informations depuis les offres d'emploi.
"""

from .text_cleaner import TextCleaner, clean_text, lemmatize, clean_and_lemmatize
from .skill_extractor import (
    SkillExtractor,
    extract_skills,
    get_top_skills,
    categorize_offer,
)
from .info_extractor import (
    InfoExtractor,
    extract_all_info,
    extract_salary,
    extract_experience,
)

__all__ = [
    # Text Cleaner
    "TextCleaner",
    "clean_text",
    "lemmatize",
    "clean_and_lemmatize",
    # Skill Extractor
    "SkillExtractor",
    "extract_skills",
    "get_top_skills",
    "categorize_offer",
    # Info Extractor
    "InfoExtractor",
    "extract_all_info",
    "extract_salary",
    "extract_experience",
]

__version__ = "1.0.0"
