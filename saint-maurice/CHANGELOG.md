# Historique

## V0.4.2 — IGN réel et LiDAR auto (9 novembre 2026)

- Génération **réelle** vérifiée dans GitHub Actions : 2 855 bâtiments IGN dans les 3 km, 1 897 glTF, 586 façades procédurales, 320 zones boisées (résultat SDK source, pas testé dans le simulateur).
- Découverte automatique officielle des dalles LiDAR HD MNT/MNS par WFS et téléchargement local GeoTIFF reprenable. Rapports de dalles manquantes et erreurs réseau.
- Fallback Overpass POST vers GET puis miroirs alternatifs pour augmenter les chances d'obtenir les haies/murs cartographiés.
- Corrections du lanceur Windows (liaison des arguments PowerShell, gestion optionnelle SDK et LiDAR).
- 24 tests locaux réussis sur jeux d'essai. Conversion LiDAR toiture et relief en jeu toujours à vérifier.

## V0.4 — 9 novembre 2026 — Qualité maximale disponible côté générateur

- Corrigé : textures glTF autrefois intégrées en `bufferView`, désormais exportées en **PNG externes** conformes aux exigences MSFS2024.
- Corrigé : mutualisation des textures PNG par SHA-256 et déclaration `.png.xml` (`MTL_BITMAP_DECAL0`) ; suppression des buffers images inutiles.
- Corrigé : requête WFS en `CRS:84` pour expliciter l'ordre longitude / latitude.
- Corrigé : `imageComplexity=VERY_SPARSE` selon la documentation SDK 2024.
- Ajouté : façades rapprochées procédurales avec fenêtres, linteaux et portes ; habitations uniquement, étages bornés, hauteur de corniche contrôlée.
- Ajouté : murs/haies 3D géoréférencés depuis OpenStreetMap, génération par petites cellules pour préserver la scène et éviter de longs éléments flottants.
- Ajouté : inventaire OSM des arbres isolés, possibilité de placer les vrais objets `Tree` une fois le GUID de modèle SDK connu (pas de GUID inventé).
- Ajouté : validation de chaque référence binaire et PNG des glTF, ainsi que des sidecars SDK ; QA compatible avec un ModelLib partagé entre maisons et micro-détails.
- Ajouté : rattrapage des défaillances temporaires Overpass, sans arrêter une construction IGN réussie (sauf si `-OSMObligatoire`).
- Non réalisé : compilation SDK, données IGN et OSM de Saint-Maurice depuis ce conteneur, test visuel, relief terrain remanié, façades photogrammétriques.

## V0.3

- Périmètre complet 3 km, orthophoto par quadkey LOD20, végétation IGN, LiDAR facultatif, exclusions bâtiments natifs, protection des monuments.
