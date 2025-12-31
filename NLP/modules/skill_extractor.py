"""
skill_extractor.py

Module d'extraction des compétences techniques et soft skills depuis les offres d'emploi.

Fonctionnalités :
- Détection des compétences techniques (langages, frameworks, outils)
- Détection des soft skills
- Détection des certifications
- Scoring de pertinence
"""

import re
from typing import List, Dict, Set
from collections import Counter


class SkillExtractor:
    """Classe pour extraire les compétences depuis les descriptions d'offres"""

    def __init__(self):
        """Initialise les dictionnaires de compétences"""

        # ============================================
        # COMPÉTENCES TECHNIQUES
        # ============================================

        # Langages de programmation
        self.languages = {
            "python",
            "java",
            "javascript",
            "js",
            "typescript",
            "ts",
            "php",
            "c++",
            "c#",
            "csharp",
            "c",
            "ruby",
            "go",
            "golang",
            "rust",
            "swift",
            "kotlin",
            "scala",
            "r",
            "matlab",
            "perl",
            "shell",
            "bash",
            "powershell",
            "sql",
            "pl/sql",
        }

        # Frameworks & Bibliothèques
        self.frameworks = {
            # Frontend
            "react",
            "angular",
            "vue",
            "vuejs",
            "svelte",
            "next.js",
            "nextjs",
            "jquery",
            "bootstrap",
            "tailwind",
            "material-ui",
            "mui",
            # Backend
            "django",
            "flask",
            "fastapi",
            "spring",
            "spring boot",
            "springboot",
            "express",
            "express.js",
            "node.js",
            "nodejs",
            "nest.js",
            "nestjs",
            "laravel",
            "symfony",
            "rails",
            "ruby on rails",
            ".net",
            "dotnet",
            "asp.net",
            # Data Science / ML
            "tensorflow",
            "pytorch",
            "keras",
            "scikit-learn",
            "sklearn",
            "pandas",
            "numpy",
            "scipy",
            "matplotlib",
            "seaborn",
            "plotly",
            "spark",
            "pyspark",
            "hadoop",
            "airflow",
            "kafka",
            "hugging face",
            "transformers",
            "langchain",
        }

        # Bases de données
        self.databases = {
            "postgresql",
            "postgres",
            "mysql",
            "mariadb",
            "sql server",
            "mssql",
            "oracle",
            "mongodb",
            "cassandra",
            "redis",
            "elasticsearch",
            "elastic",
            "neo4j",
            "dynamodb",
            "firebase",
            "supabase",
            "snowflake",
            "bigquery",
            "redshift",
            "sqlite",
        }

        # Cloud & Infrastructure
        self.cloud = {
            "aws",
            "amazon web services",
            "azure",
            "microsoft azure",
            "gcp",
            "google cloud",
            "google cloud platform",
            "alibaba cloud",
            "s3",
            "ec2",
            "lambda",
            "cloudfront",
            "rds",
            "dynamodb",
            "kubernetes",
            "k8s",
            "docker",
            "openshift",
            "helm",
            "terraform",
            "ansible",
            "jenkins",
            "gitlab ci",
            "github actions",
            "circleci",
            "travis",
            "argocd",
            "prometheus",
            "grafana",
        }

        # DevOps & Outils
        self.devops = {
            "git",
            "github",
            "gitlab",
            "bitbucket",
            "svn",
            "ci/cd",
            "devops",
            "sre",
            "iac",
            "infrastructure as code",
            "docker",
            "kubernetes",
            "ansible",
            "terraform",
            "vagrant",
            "jenkins",
            "travis",
            "bamboo",
            "teamcity",
            "nginx",
            "apache",
            "tomcat",
            "linux",
            "unix",
            "windows server",
        }

        # BI & Analytics
        self.bi = {
            "power bi",
            "powerbi",
            "tableau",
            "looker",
            "qlik",
            "qliksense",
            "datastudio",
            "metabase",
            "superset",
            "dbt",
            "talend",
            "informatica",
            "sap",
            "sap bo",
            "business objects",
            "cognos",
        }

        # Méthodes & Concepts
        self.methods = {
            "agile",
            "scrum",
            "kanban",
            "safe",
            "devops",
            "lean",
            "ci/cd",
            "tdd",
            "bdd",
            "pair programming",
            "code review",
            "microservices",
            "api rest",
            "restful",
            "graphql",
            "grpc",
            "mvc",
            "mvvm",
            "clean architecture",
            "solid",
            "design patterns",
            "machine learning",
            "deep learning",
            "nlp",
            "computer vision",
            "data science",
            "big data",
            "etl",
            "elt",
            "data engineering",
        }

        # Sécurité & Certifications
        self.security = {
            "cybersécurité",
            "cybersecurite",
            "sécurité",
            "securite",
            "owasp",
            "pen test",
            "pentest",
            "ethical hacking",
            "soc",
            "siem",
            "firewall",
            "vpn",
            "ssl",
            "tls",
            "rgpd",
            "gdpr",
            "iso 27001",
            "pci dss",
        }

        # ERP / CRM / Logiciels métier
        self.business_software = {
            "salesforce",
            "sap",
            "oracle",
            "dynamics",
            "odoo",
            "servicenow",
            "workday",
            "jira",
            "confluence",
            "trello",
            "monday",
            "asana",
            "notion",
            "slack",
            "teams",
        }

        # ============================================
        # SOFT SKILLS
        # ============================================

        self.soft_skills = {
            # Communication
            "communication",
            "écoute",
            "ecoute",
            "pédagogie",
            "pedagogie",
            "présentation",
            "presentation",
            "rédaction",
            "redaction",
            # Travail d'équipe
            "esprit d'équipe",
            "esprit d'equipe",
            "collaboration",
            "coopération",
            "cooperation",
            "travail en équipe",
            "travail en equipe",
            "team work",
            "teamwork",
            # Autonomie & Organisation
            "autonomie",
            "autonome",
            "initiative",
            "proactif",
            "proactive",
            "organisation",
            "organisé",
            "organise",
            "rigueur",
            "rigoureux",
            "méthodique",
            "methodique",
            "structuré",
            "structure",
            # Adaptation
            "adaptabilité",
            "adaptabilite",
            "flexible",
            "flexibilité",
            "flexibilite",
            "polyvalence",
            "polyvalent",
            "agilité",
            "agilite",
            "curiosité",
            "curiosite",
            # Leadership
            "leadership",
            "management",
            "encadrement",
            "mentor",
            "mentoring",
            "coaching",
            "motivation",
            "fédérateur",
            "federateur",
            # Résolution de problèmes
            "analytique",
            "analyse",
            "résolution de problèmes",
            "resolution de problemes",
            "problem solving",
            "créatif",
            "creatif",
            "créativité",
            "creativite",
            "innovation",
            "innovant",
            # Qualités personnelles
            "passion",
            "passionné",
            "passionne",
            "motivation",
            "motivé",
            "motive",
            "dynamique",
            "dynamisme",
            "enthousiasme",
            "persévérance",
            "perseverance",
            "patience",
            "diplomatie",
            "empathie",
        }

        # Toutes les compétences techniques regroupées
        self.all_tech_skills = (
            self.languages
            | self.frameworks
            | self.databases
            | self.cloud
            | self.devops
            | self.bi
            | self.methods
            | self.security
            | self.business_software
        )

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

        result = {
            "languages": self._find_skills(text_lower, self.languages),
            "frameworks": self._find_skills(text_lower, self.frameworks),
            "databases": self._find_skills(text_lower, self.databases),
            "cloud": self._find_skills(text_lower, self.cloud),
            "devops": self._find_skills(text_lower, self.devops),
            "bi": self._find_skills(text_lower, self.bi),
            "methods": self._find_skills(text_lower, self.methods),
            "security": self._find_skills(text_lower, self.security),
            "business_software": self._find_skills(text_lower, self.business_software),
            "soft_skills": self._find_skills(text_lower, self.soft_skills),
        }

        # Ajouter un résumé
        result["all_tech_skills"] = sorted(
            set(
                result["languages"]
                + result["frameworks"]
                + result["databases"]
                + result["cloud"]
                + result["devops"]
                + result["bi"]
                + result["methods"]
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
            "frameworks": [],
            "databases": [],
            "cloud": [],
            "devops": [],
            "bi": [],
            "methods": [],
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

        # Frameworks & Databases (poids moyen-fort)
        for skill in skills["frameworks"] + skills["databases"]:
            weighted_skills[skill] = weighted_skills.get(skill, 0) + 2

        # Autres tech (poids moyen)
        for skill in (
            skills["cloud"]
            + skills["devops"]
            + skills["bi"]
            + skills["methods"]
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
