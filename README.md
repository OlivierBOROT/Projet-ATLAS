# Projet ATLAS
### A.T.L.A.S. — Analyse Textuelle et Localisation des Annonces Spécialisées

<div style="display: flex; align-items: center; gap: 20px;">

  <img src="images/Logo.jpg" alt="Logo ATLAS" width="150">

  <div>
    ATLAS est un projet de Text Mining / NLP appliqué aux offres d’emploi, 
    avec une dimension géographique, une couche de web scraping, une base de 
    données modélisée en entrepôt, et une application interactive pour explorer 
    et visualiser les analyses.
  </div>

</div>



# Objectifs du projet

Le projet vise à :
- Collecter automatiquement des offres d’emploi (web scraping / API).
- Construire un corpus annoté et structuré, centré sur un domaine (IA, data, ML…).
- Modéliser une base de données entrepôt (table de faits + dimensions).
- Développer une application interactive (Dash, Bokeh, Streamlit…) permettant :

    - L’exploration du corpus
    - La recherche d’annonces
    - L’analyse de texte (NLP)
    - La visualisation cartographique
    - La possibilité d’ajouter dynamiquement de nouvelles offres

- Déployer l’ensemble avec Docker