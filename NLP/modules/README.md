# Ajouter des Catégories de Skills

## 1. Ajouter dans le JSON

**`data/skills_tech.json`** ou **`data/skills_soft.json`** :

```json
{
  "nouvelle_categorie": {
    "skill_name": {
      "synonyms": ["skill", "alias"],
      "context_patterns": ["pattern1", "pattern2"]
    }
  }
}
```

## 2. Modifier `skill_extractor.py`

### Dans `_build_skill_sets()`

Ajouter l'attribut :

```python
def _build_skill_sets(self):
    self.languages = set()
    self.frameworks = set()
    # ... existants ...
    self.nouvelle_categorie = set()  # ← AJOUTER ICI
```

Ajouter dans `all_tech_skills` :

```python
self.all_tech_skills = (
    self.languages
    | self.frameworks
    # ... existants ...
    | self.nouvelle_categorie  # ← AJOUTER ICI
)
```

### Dans `extract_skills()`

Ajouter dans le dict :

```python
result = {
    "languages": self._find_skills(text_lower, self.languages),
    # ... existants ...
    "nouvelle_categorie": self._find_skills(text_lower, self.nouvelle_categorie),  # ← AJOUTER ICI
}
```

Ajouter dans le résumé :

```python
result["all_tech_skills"] = sorted(
    set(
        result["languages"]
        # ... existants ...
        + result["nouvelle_categorie"]  # ← AJOUTER ICI
    )
)
```

### Dans `_find_skills_by_context()`

Ajouter dans le dict :

```python
found_skills = {
    "languages": [],
    # ... existants ...
    "nouvelle_categorie": [],  # ← AJOUTER ICI
}
```

### Dans `_get_skill_category()`

Ajouter la détection :

```python
def _get_skill_category(self, skill_name: str) -> str:
    if skill_lower in self.languages:
        return "languages"
    # ... existants ...
    elif skill_lower in self.nouvelle_categorie:
        return "nouvelle_categorie"  # ← AJOUTER ICI
```

Si besoin de mapping JSON → attribut :

```python
category_map = {
    "bi_analytics": "bi",
    "methodologies": "methods",
    "nom_json_categorie": "nouvelle_categorie"  # ← AJOUTER ICI
}
```

## 3. Test

```bash
python NLP/scripts/test_contextual_detection.py
```

## Exemple Complet

Ajouter catégorie **"mobile"** pour Android/iOS :

### 1. JSON (`skills_tech.json`)

```json
"mobile": {
  "android": {
    "synonyms": ["android", "kotlin", "android studio"],
    "context_patterns": ["développement android", "applications mobiles android"]
  },
  "ios": {
    "synonyms": ["ios", "swift", "xcode"],
    "context_patterns": ["développement ios", "applications mobiles ios"]
  }
}
```

### 2. Code (`skill_extractor.py`)

**\_build_skill_sets()** :

```python
self.mobile = set()
# ...
self.all_tech_skills = (... | self.mobile)
```

**extract_skills()** :

```python
result = {
    # ...
    "mobile": self._find_skills(text_lower, self.mobile),
}
# ...
+ result["mobile"]
```

**\_find_skills_by_context()** :

```python
found_skills = {
    # ...
    "mobile": [],
}
```

**\_get_skill_category()** :

```python
elif skill_lower in self.mobile:
    return "mobile"
```
