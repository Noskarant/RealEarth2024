# Statue de la Vierge — Saint-Maurice-sur-Dargoire (Madone du Peu)

**Modèle retrouvé le 2 novembre 2026 :** l'utilisateur a fourni
`monument_vierge.gltf`, `monument_vierge.bin`, `monument_vierge.glb`
et `mesh_Model_4_u1_v1_diffuse.png`. Il s'agit d'une photogrammétrie
de 297 014 sommets, 563 947 triangles et environ 12,29 m de haut.
Le fichier glTF externe et le chunk BIN du GLB sont cohérents.

## Pourquoi le matériau pouvait apparaître violet

- Texture référencée directement au niveau racine, sans dossier ModelLib
  `texture/` conforme au projet du simulateur.
- Fichier de configuration `*.png.xml` absent : le SDK MSFS 2024
  ne générait potentiellement pas le KTX2 correspondant.
- Matériau `alphaMode: BLEND` alors que le PNG est RGBA mais son canal
  alpha est **entièrement opaque** (255 partout).
- Extension `KHR_materials_specular` et deux attributs COLOR non
  nécessaires à l'affichage de la texture de base.

Ces points sont corrigés dans l'archive livrée dans la conversation :
`vierge_saint_maurice_corrigee_MSFS2024.zip`.

Les originaux et la géométrie sont conservés ; l'image a été convertie
en RGB sans modifier sa couleur ni son mappage UV. Le GLB fourni embarquait une texture 4096×4096, plus détaillée que le PNG externe 2048×2048. Une archive HD 4K distincte, `vierge_saint_maurice_HD_4K_MSFS2024.zip`, a été préparée pour préserver cette résolution originale. Le script accepte 2K et 4K.

## Organisation du dépôt

Cette branche contient :
- `statue_saint_maurice/prepare_statue.py` : génère la ModelLib et
  les XML en utilisant les fichiers 3D dans `source/`.
- `statue_saint_maurice/compile_statue.py` : appelle le SDK Windows
  puis vérifie que le fichier KTX2 et les BGL ont été compilés.
- `statue_saint_maurice/TEST_STATUE.bat` : exécute le test en un clic.

**Les gros fichiers 3D binaires ne sont pas encore dans cette branche.**
Ils sont dans l'archive corrigée téléchargeable dans la conversation.
Extraire le contenu du ZIP à la racine de `D:\RealEarth2024` pour
obtenir `D:\RealEarth2024\statue_saint_maurice\source\...`.

Ensuite, lancer `statue_saint_maurice\TEST_STATUE.bat` avec FS2024 fermé.
La compilation de contrôle **n'installe rien dans Community**.

Pour les ajouter sur la branche GitHub ultérieurement, les copier dans
un worktree séparé sur `feature/vierge-saint-maurice`, puis commiter
les fichiers source. Éviter d'ajouter le projet compilé ou les caches.

## Emplacement GPS

Une source municipale confirme qu'il s'agit de la **Madone du Peu**,
sur la colline du Peu à environ 507 m d'altitude.
https://www.chabaniere.fr/Patrimoine/168/

**Point GPS exact non confirmé :** `placement.json` est volontairement
initialisé avec `latitude: null` et `longitude: null`. Le script
compile la ModelLib sans la placer tant qu'on ne fournit pas une position
vérifiée au centre de la base du monument. L'altitude 507 m n'est pas
injectée comme AGL : la pose se fait sur le sol du simulateur.

Ne pas confondre la Madone du Peu avec le lac de la Madone.
Le fichier original `dsfsdsdf.xml` était un projet SDK vide, pas un
placement exploitable.

## Statut

- Test local de validité des fichiers JSON, PNG, BIN, XML : réussi.
- Recréation du projet SDK et test de géolocalisation simulée : réussis.
- Compilation sur le SDK Windows : **à faire**.
- Rendu dans MSFS2024 / disparition du violet : **non confirmé**.
- Emplacement précis et orientation : **à valider**.

## Lien fourni pour le placement (2 novembre 2026)

Lien Google Maps communiqué par l'utilisateur :
https://maps.app.goo.gl/jKMSu8kzVjR1cien6

Le raccourci Google Maps ne pouvait pas être développé depuis notre
environnement serveur : **ne pas convertir un centre de carte en
coordonnées du socle**. Un système indépendant `resolve_google_maps.py`
a été ajouté pour suivre le lien depuis le PC Windows. Si le lien ne
contient aucune épingle GPS exploitable, le programme demande de copier
manuellement les coordonnées depuis un clic droit sur le centre de la tour.

La version HD 4K du monument avec `LOCALISER_COMPILER_INSTALLER.bat`
est livrée dans une archive de conversation séparée :
`vierge_saint_maurice_4K_GPS_installation.zip`.
Elle comprend les fichiers 3D binaires et la texture, absents de GitHub.
Extraire l'archive dans `D:\RealEarth2024`, puis lancer le .bat avec
FS2024 fermé. Il résout la position, compile, vérifie le KTX2, choisit le
Community actif, sauvegarde l'ancien package de la statue et installe la
nouvelle version. **Valmorel n'est pas modifié.**

Statut technique : l'assemblage du ModelInfo, du XML placement avec
coordonnées synthétiques et du sidecar PNG a été vérifié hors Windows.
La compilation réelle du SDK et le rendu dans MSFS 2024 restent à valider.


## Correctif de visibilité 0.1.1 (2 novembre 2026)

Le premier package a bien produit 2 BGL et 1 texture KTX2, mais la
capture en jeu ne montre **aucun monument**. L'existence d'un BGL ne
démontre pas à elle seule que le modèle est affiché.

La cause technique principale soupçonnée est le modèle original de
**297 014 sommets sans aucun LOD allégé**. La documentation officielle
explique que MSFS2024 applique un `minSize` effectif basé sur le
nombre de sommets : un objet dense peut être entièrement masqué à
distance normale. Voir :
https://docs.flightsimulator.com/msfs2024/flighting/models-and-textures/modeling/lods/lod-selection-system/

`generate_lods.py` produit désormais quatre versions de visibilité
à partir des sommets, faces et UV de la photogrammétrie fournie :

| LOD | Sommets vérifiés localement | Triangles | minSize XML |
| --- | ---: | ---: | ---: |
| LOD00 | 55 891 | 99 949 | 20 % |
| LOD01 | 17 165 | 28 082 | 6 % |
| LOD02 | 5 611 | 7 876 | 2 % |
| LOD03 | 2 122 | 2 312 | 0,1 % |

L'original reste dans `source/`. Les fichiers de scène générés
utilisent la texture 4K inchangée et des références d'images
`texture/monument_vierge_albedo.png`, avec le sidecar de conversion
KTX2. L'ancienne source `monument_vierge.gltf` trop lourde est
retirée de la *ModelLib de compilation* pour empêcher son chargement
comme niveau unique.

Une archive locale `CORRECTIF_VIERGE_INVISIBLE_MSFS2024_v011.zip`
contient les quatre scripts Python et un seul .bat
`CORRIGER_ET_INSTALLER_VIERGE.bat`, qui remplace uniquement les scripts
du projet Windows déjà présent, puis exécute préparation, compilation
et installation. Aucune manipulation de Valmorel ou de `placement.json`.

**Vérifications locales :** quatre fichiers glTF/BIN cohérents,
bounds géométriques conservés, chemins PNG valides, XML ModelInfo avec
quatre LOD. **Encore à tester :** compilation Windows du package 0.1.1,
taille du BGL de ModelLib et visibilité effective en jeu. Si toujours
invisible, contrôler aussi le GPS exact en vol et l'activation dans
Marketplace > My Library > Community.

## V0.1.2 — terrain flottant, légères déchirures et orientation de la Vierge

**Retour utilisateur, capture du 2 novembre 2026 :** le monument est désormais
visible dans FS2024, mais il est posé sur un gros bloc vert de terrain
photogrammétrique flottant et la Vierge est vue de profil. L'arcade de la tour
est déjà orientée vers le point de vue et doit rester ainsi.

**Analyse directe du modèle utilisateur :**
- Le GLB original contient 297 014 sommets / 563 947 faces et mesure
  12,2928 m en hauteur brute.
- La masse du terrain environnant est un composant 3D distinct d'environ
  99 712 sommets, qui s'étend sur près de 8 m de largeur.
- Le pied réel du monument commence à Y=2,6754057 m dans ce fichier,
  au-dessus du plan d'origine du modèle.
- En conservant seulement les composants 3D qui montent au-delà de 3,55 m
  et qui appartiennent à la tour, on obtient 189 482 sommets.
- 91 trous topologiques extrêmement petits (bord à trois ou quatre arêtes)
  sont refermés, soit 163 faces de réparation. L'arche majeure est préservée.
- Le modèle source nettoyé comporte 357 173 triangles. Son pied est à Y=0 m.
- L'analyse des composants distingue 11 630 sommets correspondant à la
  figure de la Vierge seule. La rotation +90° de cette figure n'affecte donc
  ni le cylindre ni l'arcade.

**LOD source nettoyé testé hors SDK :** LOD00 34 669 sommets /
61 298 triangles, LOD01 10 722 / 17 354, LOD02 3 394 / 4 785,
LOD03 1 245 / 1 426. Les matériaux OPAQUE / texture 4K restent les mêmes.

Le livrable autonome `CORRECTIF_MADONE_SOL_ORIENTATION_MSFS2024_v012.zip`
est disponible dans la conversation : il transporte les **vrais fichiers
BIN et glTF nettoyés** et un sélecteur compressé pour tourner la Vierge seule,
sans avoir besoin d'installer SciPy/Trimesh sur le PC Windows.

**Procédure :** fermer FS2024, extraire le ZIP n'importe où, double-cliquer
`CORRIGER_MADONE_V012.bat`. Le lanceur :
1. Vérifie le chemin déjà confirmé
   `D:\\RealEarth2024\\vierge_saint_maurice_4K_GPS_installation\\statue_saint_maurice`
   et l'empreinte SHA256 de la source ;
2. Sauvegarde le .gltf/.bin et les scripts source originaux ;
3. Remplace uniquement ces fichiers, conserve les coordonnées GPS et la
   texture originale 4096×4096 ;
4. Crée le package 0.1.2 avec ses quatre nouveaux LOD via le SDK Windows ;
5. Valide les 2 BGL/1 KTX2, sauvegarde l'ancienne version Community et installe.

**Deuxième lanceur :** `REGLER_ORIENTATION_MADONE.bat` demande une rotation
de la statue seule (par exemple -90°, 0°, +90°, 180°), puis recompile et
réinstalle sans toucher à l'orientation de la tour.

**Important :** le +90° est un **premier essai**, pas un angle déterminé
depuis le cap de la caméra (inconnu sur la capture). Le modèle nettoyé et les
LOD ont été générés et contrôlés localement ; la compilation SDK v0.1.2
et le résultat visuel en jeu restent à vérifier sur le PC utilisateur.
