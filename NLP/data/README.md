# Ajouter des Skills

## Skills Techniques

Éditer `skills_tech.json` :

```json
{
  "languages": {
    "rust": {
      "synonyms": ["rust"],
      "context_patterns": ["développement rust", "programmation rust"]
    }
  }
}
```

### Catégories disponibles

- `languages` - Langages de programmation
- `frameworks` - Frameworks et bibliothèques
- `databases` - Bases de données
- `cloud` - Cloud et infrastructure
- `bi_analytics` - Business Intelligence
- `methodologies` - Agile, Scrum, etc.
- `tools` - Jira, Git, etc.
- `data_concepts` - Data Engineering, ETL, etc.

### Structure

```json
"nom_skill": {
  "synonyms": ["nom", "alias1", "alias2"],
  "context_patterns": [
    "pattern regex 1",
    "pattern regex 2"
  ]
}
```

### Patterns Regex

- **Simple** : `"développement python"`
- **Optional s** : `"langage(s)?"`
- **Optional word** : `"base(s)?\\s+de\\s+données"`
- **Wildcard** : `"modélisation.*données"`

⚠️ **Échapper les caractères spéciaux** : `?` → `\\?`, `.` → `\\.`

### Exemples

**Détecter SQL via contexte :**

```json
"sql": {
  "synonyms": ["sql", "t-sql"],
  "context_patterns": [
    "langages?(\\s+de)?\\s+requêtes?",
    "modélisation.*données.*requêtes?"
  ]
}
```

**Détecter Python :**

```json
"python": {
  "synonyms": ["python", "python3", "py"],
  "context_patterns": ["développement python", "scripts python"]
}
```

## Skills Soft

Éditer `skills_soft.json` :

```json
{
  "leadership": {
    "leadership": {
      "synonyms": ["leadership", "leader"],
      "context_patterns": ["compétences.*leadership", "qualités.*leadership"]
    }
  }
}
```

### Catégories disponibles

- `communication`
- `teamwork`
- `autonomy`
- `organization`
- `adaptability`
- `leadership`
- `problem_solving`
- `personal_qualities`
- `stress_management`
- `interpersonal`
- `commitment`

## Test Rapide

```bash
python NLP/scripts/test_contextual_detection.py
```

## Exemple Complet

Ajouter **Terraform** avec détection contextuelle :

```json
"terraform": {
  "synonyms": ["terraform", "tf"],
  "context_patterns": [
    "infrastructure\\s+as\\s+code",
    "iac",
    "automatisation.*infrastructure",
    "provisionning.*infrastructure"
  ]
}
```

Résultat : détectera Terraform même si le texte dit "infrastructure as code" sans mentionner "terraform".
