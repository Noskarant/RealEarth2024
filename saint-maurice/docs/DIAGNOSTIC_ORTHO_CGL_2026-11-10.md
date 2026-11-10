# Diagnostic orthophotos CGL — Saint-Maurice-sur-Dargoire HD

Date : 10 novembre 2026
Branche : `feature/saint-maurice-hd`
Périmètre : overlay orthophoto IGN LOD20 (3 km autour du bourg), 40 632 tuiles.

## 1. Symptôme rapporté

Survol du bourg (45.5829444 N, 4.6312222 E) : voile rose uniforme, mosaïque en
damier de blocs de luminosités différentes, bord de zone en escalier.
Bâtiments 3D corrects par ailleurs.

## 2. Méthode

Chaque hypothèse a été testée par mesure, sans recompiler 4 Go à chaque fois.

### 2.1 Donnée source : innocentée

| Vérification | Mesure |
| --- | --- |
| Tuile stockée vs WMS IGN fraîche (même tuile, `12022033210010110003`) | écart moyen **0,0** sur R, V et B |
| Permutations de canaux testées (BGR, GRB, GBR, BRG, RBG) | la meilleure alternative donne 5,6 d'écart → aucun échange de canaux |
| Format réel du PNG (lecture des chunks IHDR) | 256×256, **bit depth 16**, color type 6 (RGBA), non entrelacé |
| Conformité XML `CGLBuilderConfig.xml` | identique à la documentation Asobo |
| Coutures entre blocs WMS voisins | écart moyen 12,34 (front) vs 12,50 (intra), **ratio 0,99** → aucune couture |
| Mosaïque de contrôle 8×8 tuiles | village, toits orangés, verdure, aucune teinte parasite |
| Distribution de l'alpha (1 500 tuiles) | 96,1 % opaques, 3,7 % partiels (bord), 0,2 % nuls |
| En-tête de notre CGL vs CGL tiers fonctionnel (`france-dpt-974`, `CGL/301/sai023.cgl`) | structure identique, version 3 |

Conclusion : ni la donnée, ni le format, ni le conteneur CGL ne sont en cause.

### 2.2 Cause racine

Le découpage en deux packages (`realearth-sm-hd-ortho-a` et `-b`) était
imposé par une contrainte technique, mais les deux packages déclarent le
**même chemin VFS** :

```
CGL\120\sai220.cgl
```

Le chemin VFS d'un CGL est dérivé des 6 premiers chiffres du quadkey
(`CGL\<quadkey[0:3]>\sai<quadkey[3:6]>.cgl`). Les 40 632 tuiles de la zone
partagent toutes le préfixe `120220` : il est donc **impossible** de produire
deux CGL à chemins distincts sur ce secteur.

Or chaque package embarque son propre arbre quadtree complet
(27 343 nœuds pour A, 27 449 pour B), construit à partir de la moitié
seulement des tuiles. À distance, les niveaux de LOD bas des deux arbres se
superposent et se contredisent : c'est la mosaïque. Les zones non couvertes
laissent apparaître l'imagerie par défaut, teintée automne : c'est le voile
rose. L'alpha écrasé à ces niveaux produit le bord en escalier.

## 3. Correctif retenu

Un **seul** CGL pour l'ensemble du secteur, au lieu de deux packages
concurrents. C'est la seule option qui conserve la pleine résolution LOD20.

Contrainte vérifiée : la limite de **4 GiB par fichier CGL** est réelle et non
contournable (confirmé sur le DevSupport Asobo : « no workaround for this
limitation of 4Gb per cgl file, except creating different package »).

Mesure de faisabilité, sur les CGL réellement produits :

| Élément | Valeur |
| --- | --- |
| PNG sources | 3,233 Go (40 632 fichiers) |
| CGL A produit | 2 207 297 909 octets (ratio 1,293) |
| CGL B produit | 1 995 047 986 octets (ratio 1,308) |
| **CGL unique attendu** | **4 202 345 895 octets = 3,914 GiB** |
| Marge sous la limite 4 GiB | 92 621 401 octets |

Le CGL unique tient donc sous la limite, sans aucune perte de détail.

## 4. Correction de la chaîne de compilation

`compiler_fiable.py` concluait à l'échec dès que `fspackagetool` rendait la
main, même lorsqu'une instance du simulateur poursuivait encore la
compilation. Deux cas réels l'ont prouvé :

- une instance relancée après un crash à l'initialisation continuait de copier
  les tuiles pendant plusieurs minutes après la sortie du lanceur ;
- le script tuait alors cette instance et perdait le build.

Ajout de `builder_sim_running()` : l'orchestrateur interroge la ligne de
commande des processus `FlightSimulator2024.exe` et ne conclut à l'échec que
lorsqu'aucune instance en mode `BuildAssetPackages` ne subsiste.

Ajout de `diag_cgl_couleur.py` : mini-package de 8 tuiles de couleurs pures
qui valide la chaîne de build en 28 s, sans toucher aux 40 632 tuiles réelles.

## 5. Ce qui n'est pas un défaut

Les bâtiments « en caisses » ne sont pas cassés :

- 430 modèles possèdent bien `_facade_glass`, `_facade_trim`, `_facade_door` ;
- 1 050 modèles sont des bâtiments agricoles sans ouvertures, par conception ;
- les 4 textures de façade sont volontairement unies (2 beiges, 2 briques).

C'est une **limite de fidélité**, pas une régression.

## 6. Limites restantes

- **Relief** : le terrain reste celui du simulateur ; aucun LiDAR n'est
  intégré à ce package. Les bâtiments sont posés sur l'altitude MSFS.
- **Façades** : textures unies, pas de photo-façade ; les ouvertures sont
  géométriques.
- **Plafond 4 GiB** : toute extension du périmètre au-delà de ~4 GiB de CGL
  imposera soit une baisse de résolution, soit un secteur distinct avec un
  autre préfixe de quadkey.
