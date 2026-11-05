# Correctif SDK 0.1.2 — 5 novembre 2026

Le diagnostic Windows a confirmé Microsoft Flight Simulator 2024 **1.9.24.0**, alors que `D:\RealEarth2024\build\tools\fspackagetool.exe` lançait une ancienne référence `Microsoft.Limitless_1.9.21.0`.

Le ZIP privé `SAINT_MAURICE_EGLISE_SEULE_FS2024_v012_SDK_ACTUEL.zip` priorise désormais le nouveau compilateur officiel :

`C:\MSFS 2024 SDK\Tools\bin\fspackagetool.exe`

Si le SDK a été installé ailleurs, le programme permet de fournir le chemin complet de `fspackagetool.exe`. L'ancien compilateur `D:\RealEarth2024\build\tools` n'est plus sélectionné automatiquement. Aucun changement sur Madone, bancs, végétation ni autres scènes.

Procédure : fermer FS2024, extraire le ZIP v0.1.2, lancer `INSTALLER_EGLISE.bat`, vérifier la ligne `SDK utilise`. En cas d'échec, examiner `DERNIER_JOURNAL_SDK.txt`.

**Statut** : 7 tests statiques réussis. Compilation SDK Windows et rendu en jeu non encore vérifiés.
