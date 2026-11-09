# REAL EARTH — Saint-Maurice-sur-Dargoire HD, bourg + 3 km (MSFS 2024)

**Version sources 0.2 — 9 novembre 2026.** Générateur local IGN → bâtiments 3D → projet SDK MSFS2024, avec protections des monuments existants et option orthophoto CGL. **Ce ZIP n'est pas un mod `Community` prêt à l'emploi.**

## Ce qui est livré et testé

- **Périmètre exact** : cercle de rayon **3 000 m** centré sur le bourg / église de Saint-Maurice-sur-Dargoire, **45.5829444 N, 4.6312222 E**, soit environ **28,27 km²**. Le téléchargement WFS utilise une boîte englobante, mais le filtre final utilise les distances métriques Lambert-93.
- **Maisons et fermes** : emprises réelles BD TOPO/IGN ; hauteur et différence faîtage/égout si renseignées ; estimation clairement étiquetée autrement. Toits en pente et palettes de tuiles terre cuite, murs d'enduit/pierre stylisés. **Le toit et les façades individuels ne sont pas photogrammétriques.**
- **Optimisation** : les bâtiments centraux situés à **900 m ou moins** restent des objets individuels. Au-delà : regroupement par cellule de **75 m** et bande d'altitude IGN de **1,5 m**, pour réduire les objets et limiter le risque de maisons flottantes.
- **Protection impérative des modèles existants** : le générateur saute les empreintes voisines de l'église (**45.5829444, 4.6312222**) et de la Madone du Peu (**45.583269, 4.626721**), y compris chapelle et bancs à proximité. Les marges de sécurité utilisées sont de **45 m** et **65 m**. Aucun ancien dossier `realearth-saint-maurice-eglise`, `realearth-saint-maurice-vierge`, `realearth-saint-maurice-bancs` ni `realearth-valmorel-hd` n'est modifié.
- **Contrôle local** : tests automatiques, validation des coordonnées, des buffers glTF et des rectangles d'exclusion des objets protégés.
- **Option orthophoto** : convertisseur d'un GeoTIFF RGB géoréférencé, avec droits d'utilisation vérifiés, en **tuiles PNG 16 bits LOD20** + configuration CGL pour le SDK. **Aucune image IGN n'est incluse dans le ZIP.**

**Tests dans l'environnement de préparation : 8 réussis**, y compris l'export glTF synthétique, le cluster, la protection des deux monuments, et le codage PNG RGBA16. Aucune donnée IGN de Saint-Maurice n'a été téléchargée ici, et **aucune compilation ou validation réelle dans FS2024 n'a été effectuée**.

## Un clic sur Windows — préparation du mod complet

Prérequis : Windows 11, Python 3.11/3.12 installé, internet pour l'IGN, FS2024 + SDK pour compiler.

1. Extraire cette archive dans un dossier **distinct**, par exemple `D:\RealEarth-SaintMaurice-HD`. Ne surtout pas fusionner avec le dossier de l'église ou de la Madone.
2. Double-cliquer sur **`DEMARRER_TEST_3KM.bat`** (ou lancer `LANCER_QUALITE_WINDOWS.ps1` depuis PowerShell). Cela installe les dépendances Python dans `.venv`, crée les cartes du rayon et des monuments protégés, lance les tests, télécharge les données IGN, construit **tous les bâtiments du rayon de 3 km** et vérifie les sorties. Il **n'installe rien dans Community**.
3. Ouvrir le projet généré `output\realearth-saint-maurice-hd.xml` dans le SDK FS2024, puis **Build Package**. Examiner les erreurs, vérifier qu'il n'y a pas de doublons natifs et inspecter la zone en vol avant d'installer le résultat compilé dans Community. Les rectangles d'exclusion de bâtiments génériques ne garantissent pas à eux seuls l'effacement de tous les bâtiments auto-détectés : des ajustements dans le Scenery Editor peuvent être nécessaires.

### Compilation facultative en ligne de commande

Lorsque le chemin du SDK est connu :

```powershell
.\LANCER_QUALITE_WINDOWS.ps1 -Compiler -SDKTool "C:\chemin\vers\fspackagetool.exe"
```

L'exécutable est normalement dans le SDK FS2024, `Tools\bin`. Consulter son rapport de compilation ; ne pas déclarer le mod prêt si le build échoue. Ne pas remplacer les packages de l'église et de la Madone.

### Tester d'abord 200 bâtiments

```powershell
.\.venv\Scripts\python.exe generate.py fetch
.\.venv\Scripts\python.exe generate.py build --limit 200
.\.venv\Scripts\python.exe valider_sortie.py
```

Tous les bâtiments : `generate.py build --limit 0` (ou le lanceur qualité). Le test de 200 maisons n'a pas pour but de remplacer la scène complète.

## Pour améliorer le sol : option orthophoto (ne s'exécute pas automatiquement)

Pour une vraie fidélité vue du ciel, procurer une **orthophoto officielle géoréférencée en GeoTIFF RGB** couvrant le bourg, puis vérifier précisément sa licence et ses obligations d'attribution. Cette image n'est pas fournie. Commencer par un rayon de **450 m**, qui évite de générer des dizaines de milliers de tuiles :

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-ortho.txt
.\.venv\Scripts\python.exe prepare_ortho.py "D:\IGN\orthophoto_saint_maurice.tif" --radius 450
```

Cela ajoute `PackageSources\CGL\aerial_images\*.png` et `PackageSources\CGL\saintmaurice_aerial.xml` au projet SDK. La compilation CGL et l'application en jeu sont **à valider** ; ne pas considérer la conversion en PNG comme preuve du rendu réel. Pour modifier ou étendre le rayon, calculer la taille disque et la durée de build à l'avance. Les images source et les tuiles produites ne doivent pas être redistribuées sans droit.

## Livrables de contrôle

| Chemin | Utilité |
|---|---|
| `config.json` | Rayon, densité, marges de sécurité et positions des monuments |
| `data/cartographie/zone_3km.geojson` | Cercle vérifiable dans QGIS |
| `data/cartographie/monuments_a_preserver.geojson` | Marges de sécurité autour de l'église et de la Madone |
| `data/ign_buildings.geojson` | Données IGN téléchargées sur ton PC, non incluses |
| `output/inventory.csv` | Une ligne par bâtiment, hauteurs réelles/estimées, modèle associé |
| `output/report.json` | Statistiques du vrai secteur une fois généré |
| `output/validation_pre_sdk.json` | Vérification automatique de la protection des monuments |
| `output/realearth-saint-maurice-hd.xml` | Projet SDK **source**, pas un dossier Community |
| `output/PackageSources/...` | glTF, fichiers XML de placement et CGL éventuel |

## Limites, risques et prochaines corrections pour une vraie version « j'y suis »

1. **Pas de relief LiDAR livré** : les dénivelés sont ceux du FS2024 installé ; comparer le MNT du simulateur au RGE ALTI / LiDAR HD avant correction manuelle dans le Scenery Editor.
2. **Pas d'orthophoto intégrée par défaut** : le convertisseur CGL attend un GeoTIFF réel (facultatif et à vérifier dans le jeu).
3. **Façades et tuiles** : formes et couleurs procédurales, pas les photographies de chaque maison. Pour le rendu premium, ajouter des relevés des toits, matériaux PBR, fenêtres et accessoires selon les photographies autorisées.
4. **Autogen** : `ExclusionRectangle excludeGenericBuildingObjects` ne suffit pas toujours à supprimer les bâtiments issus de la détection automatique. Vérifier dans le SDK les `Rectangle` / `Polygon` avec exclusion des bâtiments détectés.
5. **Performances / LOD** : regroupement des hameaux disponible, mais pas encore de LOD multiples. Contrôler les FPS sur RTX 4070 en vol avec deux écrans.
6. **Pas de démonstration dans le jeu** : la qualité visuelle finale n'est pas certifiée tant qu'un package compilé n'a pas été testé au-dessus du bourg.

## Sources officielles

- IGN Géoplateforme WFS : https://data.geopf.fr/wfs/ows — BD TOPO v3 ; attribution IGN, Licence Ouverte 2.0 sous réserve des jeux de données effectivement utilisés.
- SDK FS2024 — model libraries et scenery : https://docs.flightsimulator.com/msfs2024/retail/devmode/editors/scenery-editor/objects/scenery-objects/
- SDK FS2024 — compilation : https://docs.flightsimulator.com/msfs2024/retail/sdk-tools/package-tool/package-tool/
- SDK FS2024 — tuiles aériennes : https://docs.flightsimulator.com/msfs2024/flighting/devmode/editors/project-editor/file-formats/cgl-files/
- SDK FS2024 — exclusions de bâtiments détectés : https://docs.flightsimulator.com/msfs2024/retail/devmode/editors/scenery-editor/objects/polygon-objects/

© Sources géographiques IGN et contributeurs OpenStreetMap selon les licences concernées. La position de l'église et la position de la Madone ont été retrouvées à partir des anciens projets de mod. **Ne jamais modifier ces modèles depuis ce générateur.**
