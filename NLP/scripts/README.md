# Scripts NLP

## Enrichissement des offres

### Test (10 offres)

```bash
cd NLP/scripts
python enrich_existing_offers.py --dry-run
```

### Traitement complet (~5000 offres)

```bash
cd NLP/scripts
python enrich_existing_offers.py --full --batch-size 100
```

### Reprendre après interruption

```bash
cd NLP/scripts
python enrich_existing_offers.py --full --resume
```

## Fonctionnalités

Le script `enrich_existing_offers.py` traite les offres avec les 3 modules NLP :

- **TextCleaner** : nettoyage + lemmatisation (description_cleaned)
- **SkillExtractor** : extraction compétences tech + soft skills
- **InfoExtractor** : extraction salaire, XP, formation, remote

## Logs

Tous les détails sont sauvegardés dans `enrichment_YYYYMMDD_HHMMSS.log` :

- Description originale vs description cleaned
- Profil identifié avec confiance (%)
- Compétences techniques et soft skills
- Informations extraites (formation, télétravail)

MAJS : 4001, 4636, 1177, 2662 (maj du code -> ajoute bien les skills), 313, 1579 (maj du code -> ajout des embeddings), 1986, 2317, 5042, 4091, 4804, 1443, 740, 1778
