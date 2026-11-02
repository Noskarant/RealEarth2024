# Valmorel — étape 1 : centre du Bourg

## Références vérifiables
- [Histoire de Valmorel / office du tourisme](https://www.valmorel.com/la-destination/histoire/) : architecture de station-village, bois, pierre de parement, lauze, décors peints.
- [Patrimoines de Savoie, Valmorel (CAUE)](https://patrimoines.savoie.fr/upload/docs/application/pdf/2021-02/la-rubrique-n46-mail_2021-02-04_14-38-44_678.pdf) : rue du Bourg, enduits colorés et trompe-l'œil.
- [Hôtel du Bourg : coordonnées officielles](https://hoteldubourg.com/fr/acces.html) : 45.461427, 6.443471.
- [Wikimedia Commons, photos des bâtiments de Valmorel](https://commons.wikimedia.org/wiki/Category:Buildings_in_Valmorel) : photographies de la rue, des façades et de la place du Morel. **Ne pas réutiliser les images comme textures sans vérifier leur licence et attribution.**

## Modifications de cette étape
- Un rayon de référence de 165 m autour de l'Hôtel du Bourg sert à **identifier les bâtiments candidats** à un traitement architectural. Ce n'est **pas** un zonage cadastral exact et certains bâtiments peuvent être en dehors de la rue du Bourg.
- Les dimensions, altitudes et empreintes IGN sont conservées.
- Lorsque la matière de façade est « Inconnu », affectation reproductible d'un enduit ocre, crème, rosé, blanc chaud ou d'un bardage bois. Les codes de matériaux identifiés sont conservés.
- Lorsque la matière de couverture n'est pas connue et qu'une pente existe, utilisation de la texture de lauze grise.
- Pour une partie des façades sans donnée matière : bardage bois au dernier étage. **Hypothèse visuelle**, pas observation bâtiment par bâtiment.
- Pour les bâtiments sélectionnés en détail : volets en bois, balustrades ouvertes à poteaux et lisses plutôt que des panneaux pleins.
- Pour les bâtiments que l'inventaire identifie comme « Commercial et services » : vitrines simplifiées, sans enseignes inventées.

Les textures PNG utilisées viennent de `assets/valmorel_complete`. Elles sont **générées/stylisées**, non photographiques, et devront être remplacées par des matériaux photo-sourcés légitimement réutilisables pour améliorer le réalisme.

## Vérification avant reconstruction globale
Depuis PowerShell sur le PC Windows équipé du SDK :

```powershell
cd D:\RealEarth2024
git fetch origin
git switch fix/valmorel-sdk-textures
.\.venv\Scripts\python.exe scripts\qa_bourg.py
.\.venv\Scripts\python.exe scripts\build_texture_probe.py
& "D:\RealEarth2024\build\tools\fspackagetool.exe" "D:\RealEarth2024\build\texture_probe_official\realearth-texture-probe.xml"
```

Le test de textures produit un **bâtiment** avant de déclencher la reconstruction des milliers de bâtiments. Vérifier les KTX2 sous `build/texture_probe_official/Packages/realearth-texture-probe/` et le rendu dans le simulateur. La compilation SDK et l'essai in-game ne sont pas exécutables depuis GitHub seul.

## Travaux suivants
1. Relever les positions de chaque bâtiment sur les photos de la rue du Bourg, pour éviter les façades attribuées par heuristique.
2. Construire des passages sous arcades et des volumes spécifiques seulement lorsque les emplacements et dimensions sont identifiés.
3. Faire le même relevé par quartier pour Crève-Cœur, Planchamp, Le Mottet et le reste de la station.
4. Réaliser une validation visuelle in-game, corriger les décalages et vérifier performances et textures KTX2.

## Retour visuel après premier essai FS2024 — 2 novembre 2026
La scène v0.1.3 compile et ses 20 KTX2 sont présents. La capture en jeu
montre une architecture encore très simplifiée : beaucoup de bâtiments
groupés sont des blocs dont les façades n'ont pas de fenêtres.

**Diagnostic vérifié dans les sources :** le générateur utilise `wall_*_win`
pour les bâtiments groupés, mais `pack_textures.py` pointait ces clés
vers les mêmes PNG `*_basecolor.png` que les murs nus.

### Correction v0.1.4 (à compiler et tester)
- `scripts/window_facades.py` prélève une fenêtre du fichier RGB
  `assets/valmorel_complete/windows_atlas.png` et la superpose aux textures
  de mur originales.
- Les versions `wall_*_win` sont des PNG **distincts** dans
  `build/generated_window_facades/` (dossier ignoré par Git). Aucune texture
  originale du pack n'est modifiée.
- Les glTF continuent de faire référence à `texture/<nom>.png` et le
  compilateur SDK convertit les PNG avec leurs XML sidecar.
- C'est une solution visuelle légère : l'emplacement des fenêtres reste
  **illustratif**, non relevé sur chaque façade réelle.

### Test isolé v0.1.4
Sur la branche `fix/valmorel-sdk-textures` :

```powershell
cd D:\RealEarth2024
git pull --ff-only
.\.venv\Scripts\python.exe scripts\qa_bourg.py
.\.venv\Scripts\python.exe scripts\build_texture_probe.py --window-facade
& "D:\RealEarth2024\build\tools\fspackagetool.exe" "D:\RealEarth2024\build\texture_probe_official\realearth-texture-probe.xml"
Get-ChildItem "D:\RealEarth2024\build\texture_probe_official\Packages" -Recurse -Filter "*.KTX2" | Select-Object Name,Length
```

Attendu : `BAKED WINDOW FACADES: ... OK`, `SOURCE GEOMETRY / PNG REFERENCE QA: OK`,
références d'images valides dans le glTF, puis des KTX2 de taille non nulle.
Ne pas confondre cela avec une preuve de rendu correct dans FS2024.

**Compilation complète seulement après validation :**

```powershell
.\.venv\Scripts\python.exe scripts\build_models.py
.\.venv\Scripts\python.exe scripts\build_scenery.py
& "D:\RealEarth2024\build\tools\fspackagetool.exe" "D:\RealEarth2024\project\realearth-valmorel-hd.xml"
.\.venv\Scripts\python.exe scripts\publish_package.py
.\.venv\Scripts\python.exe scripts\validate_package.py
```

Avant de remplacer le package dans Community, conserver une copie
de la v0.1.3 qui fonctionne. La qualité de la volumétrie (toits complexes,
arcades, façades individuelles) exige des relevés ciblés supplémentaires.
