# RealEarth Saint-Maurice HD — MAXIMUM 3 KM — v0.4 (FS2024)

**État au 9 novembre 2026 : générateur source, PAS une scène compilée et validée dans FS2024.**

**Périmètre : rayon métrique de 3 000 m autour du bourg de Saint-Maurice-sur-Dargoire, soit 28,27 km².** Toute la zone est couverte par le générateur, sans plafond artificiel de bâtiments. La fidélité visuelle dépend des données effectivement présentes dans les services IGN/OSM, de leur résolution et du SDK local.

### Contenu développé

| Couche | Traitement réel | Limitation à ne pas masquer |
|---|---|---|
| Bâtiments | IGN BD TOPO v3 : emprises réelles, hauteurs si disponibles, placement de chaque maison du rayon | Le générateur simplifie les toitures ; les fenêtres exactes ne sont pas connues |
| Façades de proximité | Fenêtres, encadrements et portes **procéduraux** sur les habitations proches, avec différents étages | Ouvertures **estimées**, non relevées photo par photo ; désactivables |
| Matériaux | Tuiles, pierre, enduit, ardoise et métal : PNG PBR **externes mutualisés**, XML sidecars SDK | Texture procédurale, pas photogrammétrie des maisons |
| Toits LiDAR | Enrichissement facultatif des hauteurs MNT/MNS ou LAZ IGN LiDAR HD | Nécessite les rasters ; pente et formes exactes des combles non garanties |
| Orthophoto intégrale | Extraction IGN BD ORTHO sur **tout le disque 3 km**, fichiers 16 bits RGBA, tuiles quadtree LOD20 et fondu périphérique | Le LOD20 **rééchantillonne** la source IGN (habituellement 20 cm) : il ne crée pas une meilleure résolution native. Compilation CGL à valider |
| Forêts | Polygones IGN, végétation SDK ajustée | Pas de relevé individuel de tous les arbres |
| Micro-détails | Tracés **réellement cartographiés** de murs et haies OSM, groupes de modèles géoréférencés | Hauteur, épaisseur, aspect et altitude locale estimés ; option disponible uniquement si Overpass répond |
| Arbres isolés | Points OSM inventoriés ; placement exact par Tree SDK possible une fois un véritable modèleGUID indiqué | **Aucun arbre isolé n'est automatiquement ajouté sans GUID SDK réel** |
| Routes et eau | Extraits IGN dans audit GeoJSON pour corrections manuelles | Routes, talus et fossés natifs **non remplacés** automatiquement |
| Terrain | Analyse des modèles MNT/MNS pour affiner hauteurs des bâtiments | **Relief natif conservé** : le SDK ne fournit pas ici de chaîne DEM complète fiable et automatisable |
| Monuments | Église, Madone, chapelle, bancs : zones protégées | Aucune modification des anciens modèles ; positions/protections à confirmer en vol |

### Lancer sous Windows

Prérequis : **Python 3.11 ou 3.12 64 bits**, SDK MSFS2024, 15+ Go d'espace libre pour une tentative intégrale, connexion Internet correcte.

1. Extraire le ZIP dans un dossier simple, par exemple `D:\RealEarth-SaintMaurice-MAX`.
2. Lancer **`DEMARRER_ULTRA_3KM.bat`** (le fichier exécute `LANCER_ULTRA_WINDOWS.ps1`).
3. Il installe les dépendances, exécute les tests, récupère les **données réelles** IGN et OSM, génère les bâtiments, les paysages et les **orthophotos de toute la zone**, puis vérifie les références glTF.
4. Dans DevMode FS2024, ouvrir `output\realearth-saint-maurice-hd.xml`, construire les AssetGroups et consulter les erreurs du compilateur. Le programme ne dépose **rien** automatiquement dans `Community`.
5. Dans le simulateur, activer le mod compilé et vérifier la vue du village en tournant autour de 45.5829444 N / 4.6312222 E, puis les pentes, les murs, les forêts et l’absence de doublons.

**La génération d'environ 40 000 tuiles CGL** peut demander de nombreux gigaoctets et des heures en fonction du serveur IGN et du disque. Elle est **reprise** lorsqu'on relance le fichier. Le SDK doit générer les `.cgl` finaux. Éviter de publier l'imagerie avant de revérifier ses conditions de réutilisation et l'attribution `© IGN`.

Pour contrôler d’abord les bâtiments et les détails sans image aérienne :

```powershell
.\LANCER_ULTRA_WINDOWS.ps1 -SansOrthophoto
```

Pour autoriser explicitement l’omission d’OSM si Overpass est indisponible (comportement par défaut) :

```powershell
.\LANCER_ULTRA_WINDOWS.ps1 -SansOrthophoto
# ou, pour exiger absolument les données OSM :
.\LANCER_ULTRA_WINDOWS.ps1 -OSMObligatoire
```

Pour compiler automatiquement **uniquement si le SDK local est accessible** :

```powershell
.\LANCER_ULTRA_WINDOWS.ps1 -Compiler -SDKTool 'C:\CHEMIN_SDK\Tools\bin\fspackagetool.exe'
```

### Paramètres de fidélité

`config.json` :

- `radius_m: 3000` : rayon entier, sans zone oubliée ;
- `core_radius_m: 1300` : chaque maison du centre reste un modèle individuel ;
- `facades_radius_m: 1100` et `procedural_facades: true` : fenêtres/portes vraisemblables, **non identiques aux bâtiments réels** ;
- `experimental_pbr_textures: true` : vraies textures PNG externes, mutualisées, avec sidecars SDK ;
- `osm_tree_model_guid`, `osm_tree_species_name` : laisser vides tant que les modèles d’arbre FS2024 valides n’ont pas été repérés dans Scenery Editor ;
- `monuments_proteges` : secteurs bloqués autour des objets existants. Ne pas réduire leur marge sans vérification.

### LiDAR HD automatique (sans sélection manuelle de tuiles)

Le lanceur détecte maintenant **automatiquement les dalles MNT/MNS LiDAR HD officielles** (WFS IGN) qui intersectent le disque de 3 km, puis télécharge les GeoTIFF disponibles, les regroupe et estime les altitudes de sol / toiture **sans modifier les données originales**. Le service IGN n'a pas encore été vérifié sur ce poste ; les éventuelles cellules non couvertes sont explicitement signalées et les valeurs BD TOPO sont conservées. L'ensemble MNT + MNS à 50 cm peut nécessiter **plusieurs gigaoctets** sur disque. En cas d'interruption réseau, relancer le script reprend les fichiers déjà complets.

- `python lidar_autofetch.py discover` : obtenir les URL des dalles LiDAR officielles et le rapport de couverture **sans télécharger les GeoTIFF**.
- `python lidar_autofetch.py download` : télécharger les dalles indexées, avec reprise après interruption.
- `-SansLidar` au lanceur Windows : désactiver cette étape très lourde si nécessaire.

Le terrain FS2024 n'est **pas** automatiquement remplacé par le MNT ; le LiDAR sert ici aux volumes des bâtiments. Il faudra vérifier un workflow terrain SDK officiellement pris en charge avant de modifier la géométrie du sol.

Pour utiliser des données déjà téléchargées, placer les données dans `data\lidar\mnt_0m50.tif` et `data\lidar\mns_0m50.tif` ou fournir les fichiers texte de liens comme dans les instructions V0.3 ; le lanceur crée un nouveau GeoJSON enrichi, **sans modifier les fichiers IGN d’origine**. La précision des toitures doit être contrôlée contre des photographies ; les données MNS peuvent inclure de la végétation.

### Exigences de qualité / vérification

- `python -m pytest -q` : tests de code sur bâtiments et géométries **synthétiques**.
- `python valider_sortie.py` : géométrie et protections, toutes les images glTF avec URI externes et XML de texture, modèles présents.
- `python build_quality_report.py` : quantités effectivement produites, sources manquantes, état CGL et LiDAR.
- `output\report.json`, `output\validation_pre_sdk.json`, `output\quality_report.json` : audit inspectable.
- Compiler **puis tester réellement en vol** avant de déclarer la V0.4 fonctionnelle. Le nombre de modèles/arbres réels sera connu seulement après le téléchargement IGN/OSM.

**Ne jamais remplacer les packages :** `realearth-saint-maurice-eglise`, `realearth-saint-maurice-vierge`, `realearth-saint-maurice-bancs`, `realearth-valmorel-hd`. Ce projet utilise son propre package `realearth-saint-maurice-hd`.

### Sources officielles

- MSFS2024 SDK glTF : https://docs.flightsimulator.com/msfs2024/retail/models-and-textures/msfs-2024-gltf-format/
- MSFS2024 textures : https://docs.flightsimulator.com/msfs2024/retail/content-configuration/textures/texture-xml-properties/
- MSFS2024 CGL : https://docs.flightsimulator.com/msfs2024/flighting/devmode/editors/project-editor/file-formats/cgl-files/
- MSFS2024 scenery XML : https://docs.flightsimulator.com/msfs2024/flighting/content-configuration/environment/scenery-objects/scenery-xml-properties/
- IGN WFS : https://data.geopf.fr/wfs/ows — © IGN Licence Ouverte 2.0
- IGN WMS : https://data.geopf.fr/wms-r/wms — © IGN, licences de la couche à vérifier
- OpenStreetMap / Overpass : © OpenStreetMap contributors, ODbL.

**Génération IGN réelle vérifiée sur GitHub Actions (9 novembre 2026) :** 2 855 bâtiments dans les 3 km, 1 897 objets placés, 320 polygones boisés IGN. Il s'agit toujours de **sources SDK non compilées** ; l'orthophoto n'a pas encore été téléchargée sur GitHub, et aucun vol n'a été contrôlé.

**Test en simulateur / SDK sur cette machine : non réalisé.** L’archive est du code et des sources de projet, pas un package `.cgl`/`.bgl` déjà opérationnel.
