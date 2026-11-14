# Valmorel — télécabines Planchamp / Pierrafort (MSFS 2024)

**Branche isolée, sans ancienne reconstruction des bâtiments.**

## But

Reprendre le master Blender 3.6 remis le 14 novembre 2026 (quatre gares, deux cabines, deux pylônes-types), convertir les huit GLB en glTF 2.0 + ModelInfo XML, puis compiler une scène MSFS 2024 indépendante du mod `realearth-valmorel-hd`.

**Package cible :** `realearth-valmorel-telecabines`.

## Situation réelle (aperçu initial)

- 8 modèles statiques présents dans l'archive Blender fournie : 4 gares, 2 cabines-types, 2 pylônes-types. Les câbles n'ont pas d'export GLB isolé.
- 4 gares sont placées en **prévisualisation provisoire** ; leurs coordonnées/orientations doivent être ajustées dans FS2024.
- Les cabines/pylônes sont dans la bibliothèque 3D, mais leurs positions géographiques ne sont **pas vérifiées** ; ne pas créer une ligne de câbles fictive.
- **Aucune animation**, aucune exclusion d'autogen, aucun remplacement de chalet/résidence, aucun écrasement d'un autre mod.
- Aucun terrain/relief de crête n'est inclus à ce stade : le dépôt antérieur ne prouve pas qu'un module de correction de terrain indépendant existe et fonctionne.

## Livraison locale

L'archive autonome `VALMOREL_TELECABINES_SDK_SOURCE_v01.zip` est livrée séparément dans la conversation et contient la modélisation, les scripts de préparation/compilation, les sources glTF et le lanceur Windows.

Décompresser le dossier `valmorel_lifts` dans `D:\\RealEarth2024\\` puis fermer FS2024 et double-cliquer `valmorel_lifts\\INSTALLER_VALMOREL_TELECABINES.bat`.

Le lanceur utilise le SDK **déjà installé** (`D:\\RealEarth2024\\build\\tools\\fspackagetool.exe`) ; son exécutable n'est pas redistribué. Il installe le package dans le chemin Community Windows fourni par l'utilisateur, après compilation et validation. Sauvegarde et rollback limités au seul package `realearth-valmorel-telecabines`.

**Attention :** les scripts et GLB ont été inspectés/contrôlés hors jeu, mais le SDK et FS2024 ne peuvent pas être exécutés depuis cet environnement distant. La compilation réelle et le contrôle de rendu restent à effectuer sur le PC Windows.

## Suite

1. Vérifier les positions et orientations des gares dans FS2024 et corriger les détails visibles par comparaison aux photographies.
2. Récupérer des traces GPS / positions réelles des pylônes et un profil altimétrique cohérent avec le terrain FS2024 avant de placer câbles/cabines en ligne.
3. Rechercher un asset de relief indépendamment construit, réellement compilé et vérifié, sans importer l'ancien mod des bâtiments.
4. Ajouter les LODs et valider FPS et affichage à distance.

Références dans l'archive : `docs/rapport_final.txt`, `assets/renders/planche_apercus_v01.jpg` et `docs/implantation_preview.json`.
