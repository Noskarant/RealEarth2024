# Correctif V0.5 — le ModelLib compile dans un BGL

Constat screenshot (14/11/2026) : SDK **Validation SUCCESS**, **33 done, 0 failed**, puis installation V0.4 interrompue par `Modèles incomplets: 0/8 GLB`.

**Cause** : le validateur maison attendait 8 fichiers `.glb` séparés dans le package. En réalité, dans ce projet **ModelLib**, le SDK intègre les modèles dans un **BGL** compilé, distinct du BGL de placement. Documentation officielle : https://docs.flightsimulator.com/msfs2024/html/2_DevMode/Project_Editor/File_Formats/BGL_Files.htm

## Correctif
Le validateur contrôle maintenant :
- 1 BGL sous `Scenery/valmorel/modellib`, contenant la bibliothèque compilée ;
- 1 BGL sous `Scenery/valmorel/scenery`, contenant les positions des gares ;
- la présence des 8 triplets sources `.xml`, `_LOD00.gltf`, `_LOD00.bin` ;
- les signatures BGL, KTX2, le manifeste, le layout et les tailles des fichiers.
- Aucun ancien asset de bâtiments/résidences ou modification du relief.

**Installation sans recompilation** : la conversation fournit l'archive `CORRECTIF_VALMOREL_V05_SANS_RECOMPILER.zip`, qui contient un lanceur autonome. L'extraire n'importe où et exécuter `INSTALLER_VALMOREL_V05_SANS_RECOMPILER.bat`. Le script détecte automatiquement la V0.3 dans `D:\RealEarth2024\VALMOREL_TELECABINES_SDK_SOURCE_v03\valmorel_lifts`, valide le package déjà compilé, puis installe uniquement `realearth-valmorel-telecabines`, avec sauvegarde éventuelle et restauration en cas d'erreur. La compilation n'est pas relancée.

**Statut** : V0.5 validée sur les scripts et l'archive, mais non testée sur le PC Windows ni en jeu. Si un BGL manque, le script s'arrête et affiche les BGL trouvés ; ne pas contourner le contrôle.
