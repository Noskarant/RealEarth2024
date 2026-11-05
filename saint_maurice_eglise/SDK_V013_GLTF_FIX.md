# v0.1.3 — erreur GLTFData / ModelLib (5 novembre 2026)

Sur le PC utilisateur, le SDK FS2024 1.9.24.0 fonctionne, mais l'ancienne scène échouait avec `#C2024 Failed to process closing element tag <GLTFData>`. Cette erreur finale n'identifie pas la cause racine. La recherche des messages GLTFValidator / GltfCompiler en amont est prioritaire.

## ZIP privé corrigé

`SAINT_MAURICE_EGLISE_SEULE_FS2024_v013_GLTFCORRECTIF.zip`, livré dans la conversation, contient le GLB original, la géométrie glTF exportée, les huit textures, les fichiers XML, les tests et l'installateur complet.

Corrections réalisées :
- XML ModelInfo compatible avec le guide officiel MSFS2024 : GUID minuscule et attribut `modelFile` pour le LOD.
- Suppression des bufferViews/buffers/accessors inutilisés, notamment les images initialement intégrées au GLB puis externalisées en fichiers PNG.
- Suppression physique du mesh `Sol` et de son nœud orphelin dans le glTF compilé. **GLB source original conservé intact**.
- Diagnostics `DERNIER_JOURNAL_SDK.txt` et `DIAGNOSTIC_COMPILATION.txt` à fournir si le SDK échoue encore.

**Vérification :** 12 tests statiques réussis, archive ZIP intègre. Le compilateur Windows (`fspackagetool.exe`) n'a pas pu être exécuté dans cet environnement, donc le BGL n'est pas confirmé.

**Isolation :** le package s'appelle exclusivement `realearth-saint-maurice-eglise` et n'édite ni Madone, ni bancs, ni végétation, ni Valmorel. Le modèle et les textures n'ont pas été publiés sur GitHub.

## Procédure Windows
Extraire le ZIP v0.1.3 dans un dossier nouveau ; fermer le simulateur ; lancer `saint_maurice_eglise/INSTALLER_EGLISE.bat`.

Si échec, envoyer le début du journal `DERNIER_JOURNAL_SDK.txt`, ou le diagnostic spécifique `DIAGNOSTIC_COMPILATION.txt`. `#C2024` isolément ne suffit pas à conclure.
