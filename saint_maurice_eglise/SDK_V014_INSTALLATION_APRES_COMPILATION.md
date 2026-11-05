# v0.1.4 : installation après compilation, sans nouveau lancement du SDK

**Diagnostic réel (5 novembre 2026) :** dans le ZIP v0.1.3, le SDK officiel MSFS2024 1.9.24.0 affiche `Validation SUCCESS` puis `PackageBuilder | Finished, 3 skipped, 13 done and 0 failed`. Pourtant, la fenêtre lancée par `INSTALLER_EGLISE.bat` ne retourne pas à l'instruction Python après `subprocess.run()`. **On ne peut donc pas affirmer que la copie dans Community a eu lieu.**

Le ZIP séparé `CORRECTIF_EGLISE_INSTALLATION_SANS_RECOMPILER_v014.zip`, livré dans la conversation du 5 novembre 2026, contient :
- `INSTALLER_EGLISE_COMPILATION_REUSSIE.bat`
- `INSTALLER_EGLISE_COMPILATION_REUSSIE.py`
- `LIRE_EN_PREMIER.txt`

Le correctif **n'exécute pas le SDK** : il localise le package compilé `project/Packages/realearth-saint-maurice-eglise` issu de la v0.1.3, vérifie `manifest.json`, `layout.json`, les fichiers BGL (dont `modellib.BGL`) et les textures KTX2, attend que les fichiers soient stables, puis copie **uniquement** `realearth-saint-maurice-eglise` dans le dossier Community actif. Il sauvegarde toute version antérieure de l'église. Il refuse d'installer en présence de FS2024 ou de fichiers incomplets.

**La Madone, les bancs, la nature et Valmorel ne sont pas modifiés.** Le script complet et les fichiers binaires restent distribués dans le ZIP privé, non dans la branche GitHub.

La vérification en environnement simulé de la validation et de la copie a réussi ; **l'installation réelle sur Windows reste à confirmer**.
