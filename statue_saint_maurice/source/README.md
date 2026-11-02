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
en RGB sans modifier sa couleur ni son mappage UV.

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
