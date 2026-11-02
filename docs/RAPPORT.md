# RealEarth Valmorel HD — rapport d'état

Dernière mise à jour : 2026-11-02
Version du package : 0.1.1 (`CUSTOM_SCENERY_PATCH`, min. simulateur 1.9.21)

---

## 1. Statut

| Point | État |
|---|---|
| Package compilé | **oui** — `D:\RealEarth2024\dist\realearth-valmorel-hd` (16,99 Mio) |
| Validation technique | **réussie** — `scripts/validate_package.py` : 0 erreur |
| Test réel dans MSFS 2024 | **non effectué** (aucun vol de contrôle lancé) |
| Relief personnalisé | **non réalisé** — bloqué par le SDK, voir §6 |
| Végétation / sols | **non réalisés** — décor natif conservé |

---

## 2. Ce qui est réellement produit

### Bâtiments

| Indicateur | Valeur |
|---|---|
| Bâtiments inventoriés (IGN BD TOPO v3) | 4 398 |
| Emprises issues du vecteur réel | 4 398 (100 %) |
| Modèles détaillés (centre de Valmorel) | 155 |
| Modèles de masse (hameaux et versants) | 2 022 |
| Objets placés dans la scène | 2 177 |
| Triangles totaux | 940 999 |
| Exclusions d'autogen | 2 177 rectangles ajustés aux emprises |

Chaque bâtiment conserve son empreinte IGN réelle (pas de rectangle
approximatif), son altitude sol/égout/faîtage, sa hauteur, son nombre
d'étages quand il est connu, son type de toiture (plat / 2 pans / croupe)
et ses matériaux BD TOPO quand ils sont renseignés.

Catégories de fidélité (champ `fidelity` de l'inventaire) :

| Catégorie | Nombre | Signification |
|---|---|---|
| A — reconstitution détaillée | **0** | aucune référence photographique exploitable |
| B — reconstitution géométrique | 4 140 | emprise + volumes + toiture depuis données IGN |
| D — non vérifié | 258 | données 3D incomplètes, géométrie plausible seulement |

Aucun bâtiment n'est déclaré « A » : sans photographies de façade
légalement réutilisables, une façade n'est pas reproductible. Les baies,
balcons, cheminées et soubassements sont **procéduraux**, placés d'après les
dimensions réelles mais pas d'après un relevé.

### Inventaire livré

- `docs/valmorel_buildings_delivery.csv` — 4 398 lignes, une par bâtiment,
  avec `model` (modèle compilé) et `modelling_level`.
- `buildings/buildings_inventory.geojson` — mêmes données en géométrie.
- `docs/delivery_summary.json` — agrégats.

### Données sources

| Donnée | Source | Licence |
|---|---|---|
| Emprises, hauteurs, matériaux | IGN BD TOPO v3 (WFS Géoplateforme) | Licence Ouverte 2.0 |
| Limites communales | IGN ADMINEXPRESS | Licence Ouverte 2.0 |
| Toponymie (points de contrôle) | IGN BD TOPO — toponymie | Licence Ouverte 2.0 |

---

## 3. Méthode de placement (point critique corrigé)

Un objet MSFS possède **une seule altitude d'ancrage**. Fusionner les
bâtiments par grandes tuiles produisait, sur les versants de Valmorel, des
écarts allant jusqu'à **±50 m** : bâtiments flottants ou enterrés.

Correction appliquée : regroupement par **cellule de 100 m ET bande
d'altitude de 2,5 m**. L'écart vertical résiduel maximal mesuré est de
**2,4 m**, absorbé par un soubassement de 4 m. Les 155 bâtiments du centre
sont posés individuellement.

Autres garde-fous :

- `snapToGround="TRUE"` : l'origine de chaque objet est posée sur le terrain
  réel du simulateur.
- Exclusions `excludeGenericBuildingObjects` calculées sur la boîte
  englobante réelle de chaque modèle (+6 m), et non sur un rayon forfaitaire.
- Aucun fichier natif de FS2024, du SDK ou de `Community` n'a été modifié.

---

## 4. Validation effectuée

| Contrôle | Résultat |
|---|---|
| Lecture/parse des 2 177 glTF | OK |
| Extensions de modèle (max) | 209,6 m (un grand bâtiment isolé) |
| UV hors tuile (contrainte CLAMP) | 0 modèle |
| Altitudes aberrantes | 0 |
| Emprises dupliquées (grille 2 m) | 0 |
| Emprise de la scène | 8,6 km × 10,4 km |
| Compilation `fspackagetool` | exit 0, `_RPTErrors.xml` vide |
| Cohérence `layout.json` / tailles disque | OK |
| Signature des BGL | OK |
| Textures | aucune (couleurs PBR échantillonnées sur les textures de référence) |

Rendus de contrôle hors simulateur : `logs/qa_core0.png`,
`logs/qa_core1.png`, `logs/qa_cluster.png`,
`logs/qa_coverage.png` (carte de couverture : orange = centre détaillé,
bleu = clusters).

---

## 5. Points de contrôle en vol (coordonnées IGN officielles)

| Lieu | Latitude | Longitude |
|---|---|---|
| Valmorel (village) | 45.462025 | 6.442515 |
| Le Meiller | 45.478136 | 6.446517 |
| Les Avanchers | 45.477272 | 6.455189 |
| Planchamp | 45.460049 | 6.441130 |
| Montolivet | 45.471098 | 6.437883 |
| Col du Mottet | 45.429957 | 6.426605 |
| Crève-Tête | 45.450700 | 6.467535 |
| Cheval Noir (sommet) | 45.422082 | 6.413602 |
| Pointe du Niélard | 45.428224 | 6.438453 |

À vérifier : absence de bâtiment flottant/enterré, toitures orientées comme
sur l'orthophoto, absence de doublon avec l'autogen natif, routes dégagées.

---

## 6. Limites techniques constatées (SDK FS2024)

1. **Relief non remplaçable automatiquement.** La documentation SDK des
   pages *DEM* et *Terrain* est vide (« TO DO »). Le seul type CGL
   documenté est `SecondaryAerialImage` (images aériennes 256×256, PNG
   16 bits, nomenclature quadkey). Remplacer le MNT par un LiDAR HD
   nécessiterait le Scenery Editor en mode graphique, hors chaîne
   automatisable. Le relief reste donc celui de FS2024. En complément, le
   service WCS de la Géoplateforme renvoie actuellement 404 : le MNT n'a pas
   pu être téléchargé non plus par cette voie.
2. **Pas d'overlay orthophoto réaliste** dans cette version : à
   0,1493 m/pixel, la zone demandée représente ≈ 80 000 tuiles.
3. **Façades** : aucune photo libre et géolocalisée n'a été trouvée pour
   Valmorel ; les façades restent procédurales.
4. **Textures de bâtiments : couleurs unies.** MSFS 2024 ne consomme que des
   textures `KTX2` produites par sa propre étape de build. Sur ce poste,
   cette étape réécrit bien les glTF en `TEXTURE\*.PNG.KTX2` mais n'écrit
   aucun fichier : les matériaux texturés s'affichent en magenta (texture
   manquante). Aucun convertisseur n'est livré avec le SDK
   (`Tools\bin` ne contient que `fspackagetool`, `bglcomp`, `BglExplorer`).
   Les 19 PNG de référence ont donc été remplacés par leur **couleur moyenne
   convertie en linéaire**, ce qui conserve la palette (ardoise, mélèze,
   enduit, granite) sans dépendance externe. Conséquence : pas de grain de
   bois ni de trame d'ardoise en gros plan. Piste d'amélioration : fournir
   des `KTX2` déjà encodés (BC7 + mipmaps) et les déclarer dans `layout.json`.
5. **LOD unique** : 2 177 objets, 941 k triangles. Acceptable sur RTX 4070,
   mais des LOD seront utiles si la zone s'étend.
6. **Aucun test en simulateur** n'a été mené : ne pas considérer le rendu
   final comme validé visuellement.

---

## 7. Installation et test (5 étapes)

1. Supprimer l'ancienne version du `Community` si elle y est déjà, puis copier
   `D:\RealEarth2024\dist\realearth-valmorel-hd` dans
   `%LOCALAPPDATA%\Packages\Microsoft.Limitless_8wekyb3d8bbwe\LocalCache\Packages\Community\`
   (ou l'activer via MSFS Addons Linker). Version attendue : **0.1.1**.
2. Lancer FS2024, attendre la fin du chargement du contenu.
3. Dans le menu monde, vol libre, partir de `45.462025 / 6.442515`
   (Valmorel) à 2 500 ft.
4. Comparer avec/sans : renommer le dossier en `realearth-valmorel-hd.off`
   puis relancer pour revoir l'autogen natif.
5. Contrôler ensuite Le Meiller, Planchamp, le col du Mottet.

Désactivation : retirer (ou renommer) le dossier du `Community`.

---

## 8. Prochaines étapes utiles

1. Test en vol et relevé des défauts (flottement résiduel, orientation,
   doublons) — nécessite ton retour visuel.
2. Reprise des 258 bâtiments « D » avec des données 3D complémentaires.
3. LOD1/LOD2 automatiques sur les clusters les plus lourds.
4. Façades de catégorie A pour 10–20 bâtiments emblématiques, si tu fournis
   des photos dont tu détiens les droits.
5. Relief : export manuel via le Scenery Editor à partir d'un MNT IGN
   (RGE ALTI / LiDAR HD) que je peux préparer en GeoTIFF.
