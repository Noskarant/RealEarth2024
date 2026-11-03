# Saint-Maurice-sur-Dargoire — clocher photo-texturé V2 (prototype)

Le projet modifie la géométrie glTF existante fournie par l'utilisateur, pas la chapelle ou la Madone. La V2 réemploie les mêmes photographies pour les quatre faces similaires du clocher, avec baies ogivales photo-projetées, cadran photographique répété et UV de la flèche recalculés pour des bandes horizontales de tuiles rouges et crème.

- **Livraison** : ZIP privé `CLOCHER_SAINT_MAURICE_PHOTO_TEXTURES_V2.zip`, partagé dans la conversation avec les sources 3D, les textures dérivées et l'installateur Windows.
- **Contenu** : GLB photo-texturé exporté, source GLB et Blender originaux inchangés, glTF/BIN ModelLib, 2 LOD, 10 textures photo, projet SDK et scripts de vérification/installation.
- **Test hors SDK** : validation structurelle (15 tests), intégrité des glTF/BIN, rendu de prévisualisation hors simulateur.
- **Test restant** : compiler avec le SDK MSFS 2024 sous Windows, contrôler le placement GPS et le rendu réel, vérifier un éventuel chevauchement avec l'église native.
- **GPS** : le centroïde OSM `45.58293, 4.63136` concerne le bâtiment de l'église, **pas** le clocher ; il ne doit pas être présenté comme une position vérifiée du clocher.
- **Indépendance** : aucun fichier de la Madone, des bancs, des bâtiments, du terrain ou de Valmorel n'est modifié. Le ZIP désactive le mod `realearth-saint-maurice-nature` uniquement après sauvegarde, et propose aussi un lanceur séparé.

**Limite de fidélité** : il s'agit d'un modèle photo-texturé basé sur une géométrie simplifiée, et non d'une photogrammétrie détaillée comparable à celle de la Madone. Les images des faces non photographiées sont réutilisées des côtés similaires.

**Licence / publication GitHub** : les photos envoyées et textures dérivées n'ont pas de licence de republication publique vérifiée ; elles ne sont pas publiées sur ce dépôt public. Les fichiers du projet complet restent dans le ZIP privé.

Référence descriptive : https://fr.geneawiki.com/wiki/69_-_Saint-Maurice-sur-Dargoire
