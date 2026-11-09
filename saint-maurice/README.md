# RealEarth Saint-Maurice HD — branche de développement

Prototype indépendant du mod Valmorel, pour Saint-Maurice-sur-Dargoire et les collines proches.

## État
- Branche isolée : aucun changement sur `main` ni sur les modèles existants.
- Prototype local ZIP v0.1 disponible dans la conversation ChatGPT du 9 novembre 2026 ; son code doit encore être importé dans `saint-maurice/` avant exécution depuis GitHub.
- Génération des bâtiments à partir des emprises IGN : tests synthétiques seulement, pas encore de compilation SDK ni de test dans FS2024.

## Protection des monuments existants
Les modèles existants de l'église, de la Madone/chapelle et des bancs doivent être **préservés sans modification**. Avant la génération réelle, ajouter une liste d'exclusion géographique (polygones ou identifiants IGN vérifiés) pour empêcher les bâtiments procéduraux et leurs exclusions d'autogen d'empiéter sur ces objets. Ne pas supposer que les coordonnées des monuments sont connues sans les relever.

## Prochaines étapes
1. Importer les sources du ZIP dans `saint-maurice/` (sans les sorties de démonstration).
2. Vérifier le périmètre de la scène et les identifiants IGN.
3. Définir et tester les zones protégées autour des monuments.
4. Télécharger les bâtiments IGN, produire le package SDK, compiler et tester en vol.
5. Valider les performances, l'altitude et les doublons avant toute fusion.

**Ne pas modifier `project/PackageSources/Scenery/valmorel` ni les packages de Saint-Maurice préexistants.**
