# Retour de tests FS2024 — Pierrafort / Planchamp (14 novembre 2026)

## Observation confirmée

La V0.5 est compilée et installée. Les captures du simulateur montrent une gare aval Pierrafort reconnaissable, mais une gare amont Pierrafort chevauchant des volumes immobiliers environnants. Les modèles `Cabine_Type_A` et `Pylone_Type` existent dans la ModelLib mais n'étaient pas placés sur les lignes : le XML V0.5 comptait exactement quatre `SceneryObject`, un par gare.

## Prototype correctif V0.6 (ZIP joint à la conversation)

L'archive `VALMOREL_TELECABINES_V06_LIGNES_ET_EXCLUSION.zip` contient les sources **locales** du nouveau générateur (non encore poussées intégralement sur cette branche) :
- Une exclusion rectangulaire **60 × 44 m** avec `excludeGenericBuildingObjects=TRUE` et `excludeAllObjects=FALSE`, uniquement près de Pierrafort amont. Une exclusion générique n'est pas garantie d'effacer les bâtiments *detected* / OSM ; le Scenery Editor peut nécessiter une exclusion `Exclude Buildings` dédiée.
- Deux câbles doubles, 26 pylônes et 48 cabines **statiques** générés seulement après identification des deux lignes aériennes dans OpenStreetMap, et lecture des altitudes IGN RGE ALTI.
- Les pylônes sont interpolés, pas géodésiquement relevés ; les différences de relief FS2024/IGN exigent un contrôle visuel.
- SDK V0.1.1, compilation par le SDK officiel, sauvegarde/restauration du seul package `realearth-valmorel-telecabines`, sans anciens bâtiments, sans modification globale de terrain.
- Générateur testé en local avec une **route de test synthétique non fournie dans l'archive** : 80 placements, 1 exclusion, contrôles de source OK. Le vrai build SDK Windows et son rendu ne sont pas testés.
- Si OSM/IGN est inaccessible ou ambigu, aucun remplacement du package V0.5 dans Community.

## Suite
1. Compiler et tester la V0.6 sur le PC Windows, relever tout premier message d'erreur SDK.
2. Contrôler l'exclusion amont dans FS2024 ; si les maisons persistent, faire une exclusion de bâtiments détectés/OSM via Scenery Editor, sans toucher aux vrais bâtiments alentour.
3. Mesurer l'écart de hauteur des câbles/pylônes/gares avec des captures et ajuster.
4. Après vérification, importer le générateur et les correctifs complets dans la branche, avec les sources binaires Blender selon la politique de stockage du dépôt.

Documentation SDK:
- https://docs.flightsimulator.com/msfs2024/flighting/content-configuration/environment/scenery-objects/scenery-xml-properties/
- https://docs.flightsimulator.com/msfs2024/retail/devmode/editors/scenery-editor/objects/rectangle-objects/
