from api.routers.scraper import process_nlp

# Test avec une description simple
test_data = {
    "description": "Vous êtes un expert en stratégie des systèmes d'information et souhaitez dynamiser votre carrière ? En choisissant GROUPEACTIVE, vous optez pour un projet entrepreneurial encadré par des pairs expérimentés et soutenu par un collectif d'experts passionnés, tous bénéficiaires de notre modèle unique. Rejoignez GROUPEACTIVE et son réseau DSIACTIVE, dédié à aider les dirigeants de TPE/PME à surmonter leurs défis quotidiens. Chez GROUPEACTIVE, nous croyons fermement que chaque TPE/PME peut réussir. Nous aidons les dirigeants à identifier et exprimer leurs besoins réels pour leur offrir un accompagnement stratégique et personnalisé. Notre modèle repose sur cinq expertises à forte valeur ajoutée : PROSPACTIVE : Catalyseur de croissance. PROD-ACTIVE : Optimisation de la supply chain. DSIACTIVE : Défis du digital. DAF-ACTIVE : Performance administrative et financière. DRH-ACTIVE : Stratégie RH. Vos Missions Diagnostics approfondis : Utiliser nos outils d'audit digitalisés pour identifier les axes d'amélioration. Plans d'actions : Élaborer et mettre en oeuvre des plans détaillés pour optimiser la performance des entreprises. Accompagnement : Aider les dirigeants à mettre en place des pratiques pour améliorer productivité, rayonnement et réduction des coûts. Suivi régulier : Ajuster les actions selon l'évolution de la demande. Contribution au réseau : Partager votre expérience pour enrichir mutuellement le réseau GROUPEACTIVE. Pourquoi Nous Rejoindre ? DSIACTIVE offre un modèle de collaboration unique alliant autonomie et support structuré : Formation continue : Pour rester à la pointe des meilleures pratiques et faciliter le démarchage de clients. Outils avancés : Diagnostics, plans d'actions détaillés, plateforme en ligne, outils d'aide à la vente, outil d'intelligence artificielle générative intégrée à notre plateforme collaborative. Back-office : Support marketing et commercial, infrastructure technique. Suivi personnalisé : Coordinateurs et mentors dédiés pour optimiser votre stratégie de développement. Réseau étendu : Opportunités de collaboration et échanges de savoir-faire. Participation à des événements : Ateliers, conférences, salons professionnels pour renforcer votre présence sur le marché. Vous êtes avant tout, un cadre en gestion des systèmes d'information (DSI, RSI, RSSI...) et avez plus de 10 ans d'expérience. Vous êtes un professionnel aguerri du développement de votre fonction stratégique et souhaitez exercer votre métier différemment. Ou vous venez/vous vous êtes déjà lancé en tant que consultant indépendant mais avez pris conscience qu'être seul à ses limites. Ou vous êtes manager de transition en mission ou en intermission et souhaitez maintenant vous projeter à plus d'un an. Votre Carrière chez DSIACTIVE - GROUPEACTIVE Liberté Professionnelle : Évoluez sans les contraintes hiérarchiques traditionnelles. Sécurité Innovante : Exploitez votre potentiel dans un cadre rassurant. Valorisation de vos compétences : Utilisez votre expérience pour bâtir une activité indépendante pérenne. Chez DSIACTIVE, votre indépendance s'allie à un esprit collaboratif pour avancer ensemble vers la réussite. Soyez authentique, soyez audacieux, et transformez vos expériences en un partenariat enrichissant avec notre réseau. Un engagement personnel et financier, mesuré mais nécessaire, vous permettra de bénéficier pleinement de notre modèle et de l'ensemble des ressources mises à votre disposition."
}

print("🧪 Test du traitement NLP...\n")

try:
    result = process_nlp(test_data)

    if "error" in result:
        print(f"❌ Erreur: {result['error']}")
    else:
        print("✅ Test réussi!\n")

        # Afficher le résumé
        final = result["final"]
        print(f"📊 Résumé:")
        print(f"  - Total compétences: {final['skills_count']}")
        print(f"  - Top 10: {final['top_skills']}")
        print(f"  - Profil détecté: {final.get('profile_category', 'N/A')}")
        print(f"  - Dimensions embedding: {final['embedding_dimensions']}")

        # Afficher les compétences par catégorie
        if "skills_by_category" in final:
            print(f"\n🎯 Compétences par catégorie:")
            for category, skills in final["skills_by_category"].items():
                if skills:
                    print(f"  - {category}: {skills}")

except Exception as e:
    print(f"❌ Erreur durant le test: {e}")
    import traceback

    traceback.print_exc()
