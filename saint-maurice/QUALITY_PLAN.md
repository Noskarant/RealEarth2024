# QUALITÉ — RealEarth Saint-Maurice, bourg + 3 km

## Ce qui est prêt dans les sources 0.2

- Rayon strict de 3 000 m (en Lambert-93), centre sur l'église, cartes GeoJSON de contrôle.
- Génération complète depuis IGN BD TOPO, sans limite artificielle du nombre de bâtiments : `--limit 0`.
- 900 premiers mètres : maison individuelle (forme, pente de toit, hauteur) ; 900–3 000 m : regroupement 75 m / altitude 1,5 m.
- Église, Madone, chapelle et bancs existants protégés par des marges géographiques, sans déplacer ni modifier leur package.
- Format source MSFS2024 glTF + ModelInfo et BGL scenery XML.
- Conversion optionnelle de GeoTIFF vers CGL LOD20, **sans images incluses**.
- Huit tests automatisés réussis sur données synthétiques, puis audit pré-SDK.

## Ce qui manque avant d'appeler le rendu « photoréaliste »

- Téléchargement des données IGN réelles au poste Windows.
- Compilations SDK (ModelLib, BGL, puis CGL si utilisé) et logs sans erreurs.
- Validation visuelle des doubles bâtiments détectés, et corrections manuelles dans le Scenery Editor.
- Phototextures de haute qualité effectivement intégrées, relief contrôlé à l'aide des données LiDAR, végétation locale et matériaux avancés.
- Test de performances à différentes altitudes dans le simulateur, avec et sans mod.

## Procédure QA

1. Compiler bâtiments seuls ; tester au-dessus du clocher, de la Madone, des hameaux, des collines et de la vallée du Bozançon.
2. Contrôler **église et Madone inchangées**, avec anciens packages activés.
3. Corriger les doublons autogen via les outils d'exclusion adaptés, après observation réelle.
4. Tester l'overlay orthophoto CGL sur 450 m de rayon avec une image IGN autorisée.
5. Élargir les orthophotos après estimation du nombre de tuiles, du stockage et de la compatibilité.
6. Ne promettre un rendu photoréaliste qu'après comparaison en vol avec des clichés de référence.
