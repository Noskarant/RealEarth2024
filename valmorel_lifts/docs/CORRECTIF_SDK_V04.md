# V0.4 — Xbox launcher exit after successful SDK compilation

## Observation

La console Windows de l'utilisateur du 14 novembre 2026 confirme :
- PackageValidator : **Validation SUCCESS** ;
- PackageBuilder : **33 done, 0 failed** ;
- exécutable/lanceur retourne ensuite **-2015035325**, soit **0x87E50043** ;
- l'installateur V0.3 refusait de copier vers Community sur la seule base du code de retour.

Ce cas ressemble aux avertissements Xbox de fin de compilation déjà évoqués sur le forum officiel SDK : https://devsupport.flightsimulator.com/t/weird-fspackage-tool-error-the-game-has-crashed/6202

## Fix

Le lanceur accepte **uniquement** ce code de sortie connu, sous réserve d'un package compilé récent, complet et vérifié : 8 GLB, au moins 1 BGL et 1 KTX2, manifest version 0.1.0, layout correspondant, contrôles des signatures et tailles des fichiers. Tout autre code de sortie non nul reste fatal. Aucune modification de WindowsApps ou Gaming Services.

Le lanceur prend aussi `-InstallExisting`, accessible via `INSTALLER_PACKAGE_DEJA_COMPILE.bat`, pour installer le **package V0.3 déjà compilé** sans refaire le build. Il suppose que l'utilisateur a bien observé `Validation SUCCESS` et `0 failed`, et revérifie les fichiers avant toute copie.

L'archive de correctif fournie dans la conversation doit être extraite **par-dessus le même dossier contenant déjà `valmorel_lifts\project\Packages\realearth-valmorel-telecabines`**. Sinon utiliser le ZIP complet V0.4.

## Prudence
Le SDK n'a pas été exécuté par cette session distante ; le résultat en jeu et le placement des gares restent non vérifiés. Aucun ancien bâtiment ou relief non validé n'est réintroduit.
