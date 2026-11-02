# Valmorel HD 0.1.6 — corriger l'aspect de blocs (préversion)

## Constat utilisateur (2 novembre 2026)

La capture en hélicoptère de la v0.1.5 montre toujours de grandes résidences
claires/pastel, très peu de vraies ouvertures visibles, des toitures
simplifiées et peu de caractères d'un village alpin.

Les 23 modèles CC0 ont bien été convertis, mais **seulement 26 petits
bâtiments** IGN ont été remplacés ; les grandes résidences restent construites
par le générateur IGN. Ajouter davantage de racks à skis ou de dameuses ne
résoudrait donc pas le principal défaut.

## Causes vérifiées dans les sources

1. `_mark_core` sélectionnait les plus grandes surfaces sur **l'ensemble
   de la zone IGN**, sans privilégier assez les résidences de Valmorel ;
   de nombreuses empreintes complexes étaient exclues des fenêtres 3D.
2. `wall_ring` coupait les UV des matériaux `*_win` en fonction de la largeur
   et de la hauteur de chaque panneau. Lorsqu'une portion atteignait
   seulement `u=0.25`, elle ne montrait jamais la fenêtre centrée sur le
   PNG. Le matériau existait et le KTX2 compilait, mais la façade semblait
   vide.
3. Le profil architectural mixte de v0.1.5 n'était appliqué qu'à certaines
   résidences dont le matériau était inconnu et les volumes irréguliers
   ne recevaient presque jamais les détails d'une façade alpine.
4. Les enduits rosés attribués aléatoirement à la zone de référence du Bourg
   produisaient de grosses masses roses excessivement visibles.

## Changements v0.1.6

- Priorité à **255 modèles détaillés dans un rayon d'environ 1,8 km de
  Valmorel**, résidences en premier, y compris un nombre contrôlé de formes
  irrégulières. Conserve les grands bâtiments de plus de 3 000 m² dans
  les clusters plus légers, pour limiter les coûts.
- Profil typologique de résidences alpines pour les grands immeubles du
  secteur : soubassement/pierre/enduit modéré, deux niveaux supérieurs en
  bardage miel sur une proportion déterministe, garde-corps en lattes
  répétées et bande de rive sombre. Les *codes matière identifiés* sont
  préservés ; les matériaux inconnus reçoivent des couleurs sobres.
- Fenêtres `*_win` : UV 0–1 complets sur chaque panneau mural adapté ;
  les segments trop étroits reçoivent une texture unie au lieu d'une
  fenêtre exagérément compressée. Les KTX2 existants restent utilisés.
- Les 3D détaillées de grandes résidences sont limitées à 4 grandes
  façades et 10 fenêtres par travée, pour contenir les triangles.
- Pour les enduits inconnus du Bourg, utilisation de la palette crème /
  ocre / blanc chaud à la place du rose aléatoire.
- Nouveau contrôle `scripts/qa_residences.py` vérifiant la sélection des
  résidences détaillées, les UV de fenêtre complets et la présence de
  géométrie de balcons sur un échantillon.
- Les fonctionnalités 0.1.5 (23 modèles CC0, 26 chalets, 16 accessoires,
  tracé conditionnel de Pierrafort) sont conservées.

**Ce qui n'est pas résolu :** il n'existe toujours pas de relevé
photogrammétrique bâtiment par bâtiment pour les résidences de Valmorel.
Ces façades et balcons sont une **interprétation typologique**, pas la
reconstitution exacte des noms, commerces, menuiseries ou galeries de
chaque bâtiment. Les GLB gratuits sont aussi stylisés, non photographiques.
Le relief du simulateur, les autogen concurrents et les performances sont
à vérifier en jeu.

## Installation de la préversion

**Conserver la v0.1.5 en sauvegarde.** FS2024 doit être fermé.

Commande PowerShell de première utilisation :

```powershell
cd D:\RealEarth2024; git fetch origin; if ($LASTEXITCODE -eq 0) { git switch feature/valmorel-residences-016; if ($LASTEXITCODE -eq 0) { .\MAJ_VALMOREL.bat } }
```

Le lanceur vérifie les sources, génère et compile avec le SDK officiel,
exige `RESULT : OK`, sauvegarde l'ancienne version dans
`build/backups/community`, puis installe dans le dossier Community déjà
identifié. En cas d'échec, la version précédente n'est pas remplacée.

**État des tests :** analyse du code et corrections commitées sur GitHub.
La QA Python, la compilation SDK MSFS 2024 et la qualité/performance
visuelle de la v0.1.6 ne sont pas encore validées sur Windows.

### Contrôle visuel attendu

Photographier la **même zone, à altitude et angle comparables** à la capture
v0.1.5, idéalement vers le Bourg et Crève-Cœur ; contrôler :
- les fenêtres sur les blocs qui étaient vides ;
- les bardages bois des étages supérieurs, balustrades, arêtes des toits ;
- les volumes artificiellement roses ou entièrement cubiques ;
- le scintillement, les modèles qui disparaissent et les FPS.

Si les résidences restent trop génériques, la priorité suivante est la
reproduction individuelle à partir de photos de référence du Bourg,
Crève-Cœur et Planchamp. Les bibliothèques génériques ne suffiront pas.
