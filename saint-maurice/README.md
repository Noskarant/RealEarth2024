# REAL EARTH — SAINT-MAURICE HD 3 KM ULTRA (FS2024)

**Statut au 9 novembre 2026 : SOURCES ET OUTILS DE PRÉPARATION, PAS UN MOD PRÊT À INSTALLER.**

Objectif : recréer le **cercle complet de rayon 3 000 m autour du centre de Saint-Maurice-sur-Dargoire** (28,27 km²), avec un rendu aérien et à basse altitude nettement plus reconnaissable que la scène standard.

Ce projet est **autonome** : il n'édite pas les modèles existants de l'église, de la Madone du Peu, de la chapelle, des bancs, ni Valmorel. Leurs secteurs sont **protégés contre la génération des bâtiments et de la végétation**.

## Ce que produit le programme

| Couche | Donnée officielle / méthode | Usage | État |
|---|---|---|---|
| Bâtiments | IGN BD TOPO v3 WFS | Géométrie des emprises réelles, volumes, hauteurs si renseignées | Générateur codé et testé avec données fictives |
| Toits et murs | Matériaux PBR originaux procéduraux, tuiles de terre cuite/ardoise, enduit et pierre | Visibilité améliorée en vol rapproché | glTF exporté avec images ; SDK à valider |
| Doubles bâtiments | Polygones FS2024 : `ExcludeDetectedBuildings`, `ExcludeOSMBuildings` | Retire les bâtiments procéduraux sous les nouveaux volumes | XML vérifié, rendu SDK à valider |
| Orthophotos 20 cm | IGN BD ORTHO WMS, `HR.ORTHOIMAGERY.ORTHOPHOTOS` | 40 633 tuiles SDK quadkey niveau LOD20, PNG 16 bits, fondu à 3 km | Téléchargeur testé sur serveur simulé ; vraie IGN non téléchargée ici |
| Bois et forêts | IGN BD TOPO, `zone_de_vegetation` | Polygones d'arbres FS2024 d'après zones réelles | XML généré et testé sur données fictives |
| Routes, ruisseaux, plans d'eau | IGN BD TOPO | GeoJSON d'audit pour corriger le terrain/sol dans Scenery Editor | Extracteur testé, **pas de modification forcée du décor natif** |
| Toits LiDAR HD | IGN LiDAR HD MNT+MNS GeoTIFF 50 cm ou nuages classés LAZ | Hauteurs du sol, égouts et faîtages estimées statistiquement | Chaîne optionnelle testée sur petit rasters fictifs |
| Relief | Terrain natif FS2024 conservé tant que la correspondance vertical datum / terrain n'est pas validée | Évite les ruptures de terrain irréversibles | Pas encore de remplacement automatique du terrain |
| Monuments existants | Modèles précédents | Église, Madone, chapelle, bancs inchangés | Aucun fichier original modifié |

**Attention** : une emprise 3D n'est pas de la photogrammétrie. Les façades, fenêtres, cheminées et pentes exactes de chaque maison ne peuvent pas être garanties sans photographies / mesures supplémentaires. Les ortho IGN améliorent *la vue du sol*, pas les façades.

## Installation des OUTILS sur ton PC Windows

Prérequis : Python 3.11/3.12 64 bits, connexion Internet, espace disque disponible, MSFS2024 avec SDK et Developer Mode.

1. Extraire l'archive dans un dossier de travail, par exemple `D:\RealEarth-SaintMaurice-Ultra`.
2. Double-cliquer sur **`DEMARRER_ULTRA_3KM.bat`**. La commande crée un environnement Python, lance les tests, télécharge les bâtiments et couches IGN puis génère les **40 633 images aériennes**, sauf si une interruption survient (reprise possible).
3. Ouvrir le fichier produit **`output\realearth-saint-maurice-hd.xml`** dans le Project Editor SDK de FS2024 et compiler les groupes BGL, ModelLib, CGL. Contrôler les logs.
4. Installer seulement le dossier **compilé** `output\Packages\realearth-saint-maurice-hd` dans `Community`, et uniquement après validation visuelle.
5. Contrôler les bâtiments côte à côte avec le jeu natif, les pentes et le rendu des matériaux. Désactiver le nouveau package en cas de conflit, sans toucher aux anciens.

Le téléchargement orthophoto représente **environ 40 600 tuiles et plusieurs gigaoctets** ; ne pas le lancer sur une connexion limitée ou avec un stockage faible. Les services de l'IGN peuvent limiter les requêtes ; le script reprend les fichiers déjà enregistrés. Le chiffre de 40 633 est dérivé du périmètre/LOD et peut varier si les paramètres changent.

### Commandes utiles

```powershell
# Préparer toutes les maisons et paysages, mais SANS les dizaines de milliers de tuiles :
.\LANCER_ULTRA_WINDOWS.ps1 -SansOrthophoto

# Générer toute la zone, orthophoto IGN incluse :
.\LANCER_ULTRA_WINDOWS.ps1

# Calculer le nombre de tuiles sans télécharger :
.\.venv\Scripts\python.exe fetch_ortho_ign.py --dry-run

# Compiler après création des sources si chemin SDK connu :
.\LANCER_ULTRA_WINDOWS.ps1 -Compiler -SDKTool 'C:\chemin\vers\fspackagetool.exe'

# Vérifier avant SDK :
.\.venv\Scripts\python.exe valider_sortie.py
.\.venv\Scripts\python.exe build_quality_report.py
```

### Option LiDAR HD 50 cm (recommandée pour une version haut de gamme)

L'IGN permet de télécharger des MNT/MNS par dalles de 1 km, pas de 50 cm, depuis sa carte. Exporter depuis l'interface IGN les listes de liens de dalles recouvrant le cercle 3 km, puis les enregistrer sous :

- `data\lidar\mnt_urls.txt` : liste des URL HTTPS directes des GeoTIFF MNT
- `data\lidar\mns_urls.txt` : liste des URL HTTPS directes des GeoTIFF MNS

Le lanceur téléchargera les deux séries, fabriquera les mosaïques et enrichira **uniquement** les hauteurs des bâtiments pour lesquels la mesure est fiable. En absence de données LiDAR, l'IGN BD TOPO reste utilisé. Les sources brutes sont conservées.

Alternative : placer directement les rasters mosaïqués `data\lidar\mnt_0m50.tif` et `data\lidar\mns_0m50.tif`. Pour les nuages `.laz`, `laz_to_rasters.py` permet un raster MNT/roof par classes de points, après `pip install -r requirements-lidar.txt`.

**On ne remplace pas automatiquement le relief de FS2024 par ces altitudes IGN69** : une conversion verticale et un test d'alignement géodésique sont nécessaires pour ne pas faire flotter ou enterrer routes et bâtiments.

## Contenu du projet

- `generate.py` : WFS bâtiments -> géométries 3D et modèles PBR -> projet FS2024 ; **toutes** les emprises de rayon 3 km (`--limit 0`).
- `sdk_polygons.py` : exclusions des constructions natives sans supprimer les LibraryObjects ; création des surfaces forestières.
- `materials_hd.py` : textures de toits (tuiles, ardoise, métal) et murs (enduit, pierre) **procédurales**.
- `landscape.py` : bois, routes, eau, hydro et polygones FS2024 de végétation depuis l'IGN.
- `fetch_ortho_ign.py` : BD ORTHO WMS 20 cm -> 16-bit PNG/quadkeys CGL LOD20 complets ; téléchargement par blocs de 4x4 et reprise.
- `prepare_ortho.py` : autre entrée si on possède déjà une orthophoto GeoTIFF locale.
- `lidar_download.py`, `lidar_mosaic.py`, `lidar_roofs.py`, `laz_to_rasters.py` : chaîne LiDAR facultative.
- `valider_sortie.py` : contrôle des protections monument, du SDK XML et des glTF.
- `build_quality_report.py` : rapport exact des composants présents et des éléments non vérifiés.
- `tests/` : tests automatiques sur données artificielles, **pas des images de Saint-Maurice**.

## Protections et sécurité

Les deux disques de protection dans `config.json` couvrent les anciens éléments de l'église et de la Madone/chapelle/bancs. Ils reposent sur les coordonnées précédemment utilisées ; **vérifier les emprises exactes des packages installés sur le PC avant le premier vol**. Les arbres et bâtiments nouveaux sont interdits dans ces zones et le code ne supprime aucun élément déjà installé.

Des ponts, murs, fenêtres, poteaux, fossés et détails de la circulation ne sont **pas** recréés automatiquement. Les chemins et cours d'eau sont audités avec l'IGN, mais laissés aux couches natives tant que leur correction n'a pas été validée.

## Sources et documentation vérifiées

- [FS2024 SDK, images aériennes CGL](https://docs.flightsimulator.com/msfs2024/flighting/devmode/editors/project-editor/file-formats/cgl-files/) — 256 × 256 px, 16-bit PNG, LOD20.
- [FS2024 SDK, polygones d'exclusion/forçage de végétation](https://docs.flightsimulator.com/msfs2024/flighting/content-configuration/environment/scenery-objects/scenery-xml-properties/).
- [IGN BD ORTHO, mise à jour 2026](https://cartes.gouv.fr/aide/fr/partenaires/ign/generalites-ign/actualites/2026-09-mises-a-jour/).
- [IGN LiDAR HD MNT 50 cm](https://www.data.gouv.fr/datasets/mnt-lidar-hd), [MNS 50 cm](https://www.data.gouv.fr/datasets/mns-lidar-hd).
- IGN BD TOPO WFS `https://data.geopf.fr/wfs/ows`, **Licence Ouverte 2.0 © IGN**.

## Statut réel et limites

- Tests locaux sur jeu synthétique : réalisés.
- Vraies données IGN de Saint-Maurice : **non téléchargées par cet environnement** (accès Internet externe bloqué).
- Build SDK / CGL / KTX2 : **non effectué ici**.
- Test en vol à 200–500 m AGL : **non effectué**.
- Effet « j'y suis » : **objectif visuel à vérifier**, pas une promesse de rendu déjà obtenu.
