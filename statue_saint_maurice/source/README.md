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
