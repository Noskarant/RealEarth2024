# Clocher de Saint-Maurice-sur-Dargoire — Photo V1

**Modèle indépendant pour MSFS 2024.** À partir du `.blend` / `.glb` fourni par l'utilisateur (17 maillages, hauteur du modèle 23,25 m), préparation d'une ModelLib avec 7 textures **dérivées des photographies transmises**, et un installateur Windows validant les BGL, KTX2, manifest et layout du SDK.

## État
- **Préparé hors SDK** : source Blender, GLTF/BIN texturé, 2 LOD, sidecars PNG XML, projet Scenery BGL et installateur.
- **Tests locaux réussis** : intégrité GLTF/BIN et UV, 7 textures, sécurité de désactivation du mod Nature et parsing XML.
- **Restent à tester sur Windows** : compilation réelle SDK, localisation du clocher et rendu dans MSFS 2024.
- **Position GPS** : la référence OpenStreetMap de l'église `45.58293, 4.63136` est le centre du **bâtiment**, non une position précise du clocher. Le lanceur permet une saisie manuelle et signale une pose approximative.
- **Nature 1 km** : le ZIP privé contient un outil de désactivation qui sauvegarde le mod `realearth-saint-maurice-nature` hors Community. Rien ne touche à la chapelle, à la Madone, aux bancs, aux bâtiments existants ou à Valmorel.

## Publication des assets
La livraison complète (photos, .blend, .glb, .bin, 7 PNG et scripts) a été fournie sous ZIP dans la conversation de travail. Les droits de redistribution **publique** des photographies transmises n'ont pas été vérifiés. Pour éviter de republier des photos potentiellement protégées dans ce dépôt public, les fichiers photos et les textures dérivées ne sont pas commités dans cette branche. Les sources doivent être diffusées uniquement avec autorisation appropriée.

## Sources et SDK
- Clocher et restauration après 1955 : https://fr.geneawiki.com/wiki/69_-_Saint-Maurice-sur-Dargoire
- Centre du bâtiment de l'église : https://mapcarta.com/fr/W138334703
- Documentation Microsoft Flight Simulator 2024 : https://docs.flightsimulator.com/msfs2024/retail/content-configuration/models/scenery-model-xml-and-cfg-setup/

## Nom du package
`realearth-saint-maurice-clocher-photo` (ModelLib + placement séparé).
