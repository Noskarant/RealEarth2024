# Valmorel HD 0.1.7 — correctif géométrique ciblé

## Retour utilisateur
Après installation confirmée de la v0.1.6, la capture montre encore des résidences cubiques, blanches/roses, avec des toitures peu réalistes.

## Erreur géométrique réelle identifiée
Dans scripts/building_gen.py / add_roof / slope_pt, pour un toit rectangulaire les deux pans devraient rejoindre le faîtage au milieu du bâtiment.

La formule v0.1.6 était :
```python
sv = (-W + 2 * W * t) if side < 0 else (W - 2 * W * t)
```
Elle plaçait la ligne haute de chaque pan sur **l'autre bord du toit**, donc deux surfaces se croisaient au lieu de former deux pentes convergentes.

La formule corrigée est :
```python
sv = (-W * (1.0 - t)) if side < 0 else (W * (1.0 - t))
```
À t=0, les égouts sont à -W/+W ; à t=1, ils rejoignent tous deux le centre (0).

## Autres changements
- Nombre maximal de bâtiments du coeur de station sélectionnés en modèle détaillé augmenté de 255 à 420, avec priorité aux résidences et au Bourg. La barrière à 4 millions de triangles est conservée.
- Les résidences hautes admissibles peuvent recevoir le profil typologique de façade alpine même si les données toiture les indiquent plates. Leur hauteur et géométrie de toiture ne sont PAS inventées.
- Test de régression scripts/qa_roofs_017.py intégré avant toute compilation : quatre rotations de toit, convergence au faîtage, normales vers le haut et quota de détails.
- Génération, sauvegarde de l'ancien package, compilation officielle SDK et remplacement dans Community restent gérés par le lanceur standard ; le package Madone et les autres addons sont hors périmètre.

## Installation
FS2024 complètement fermé, dans PowerShell :
```powershell
cd D:\RealEarth2024
git fetch origin
git switch feature/valmorel-roofs-facades-017
.\MAJ_VALMOREL.bat
```

## État de vérification
Le défaut a été confirmé à la lecture de la formule v0.1.6 et la correction est enregistrée sur la branche. Le test Python est intégré au pipeline Windows et doit réussir avant le build.
Compilation officielle SDK et rendu dans MSFS 2024 non exécutés depuis cet environnement.

Limite persistante : les grandes résidences restent des reconstructions typologiques basées sur empreintes/hauteurs IGN, et non de la photogrammétrie bâtiment par bâtiment. L'amélioration du toit est réelle mais ne garantit pas un réalisme photographique.