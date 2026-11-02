# Valmorel — lanceur 1 clic

Ouvrir **MAJ_VALMOREL.bat** (a la racine de `D:\RealEarth2024`) avec MSFS 2024 ferme.

Le lanceur :
1. verifie qu'il est sur la branche `fix/valmorel-sdk-textures` et fait `git pull --ff-only` ;
2. execute les controles `scripts/qa_bourg.py` ;
3. reconstruit les modeles 3D, les textures et les placements IGN ;
4. recompile le package MSFS 2024 avec `fspackagetool.exe` ;
5. attend la presence des 2 BGL, du manifest/layout actualise, des textures KTX2 et surtout des nouvelles textures de fenetres ;
6. publie le package, puis execute `validate_package.py` ;
7. detecte le dossier Community de MSFS 2024 avec `UserCfg.opt` (ou les chemins par defaut) ;
8. sauvegarde l'ancien `realearth-valmorel-hd` dans `D:\RealEarth2024\build\backups\community` ;
9. installe la nouvelle version par remplacement apres copie de preparation.

**En cas d'erreur** de compilation, de texture, de chemin Community ou de validation, la version presente dans Community n'est pas remplacee. En cas de panne pendant le remplacement, le lanceur tente de restaurer l'ancien package.

**Premier lancement, une seule commande PowerShell :**

```powershell
cd D:\RealEarth2024; git pull --ff-only; if ($LASTEXITCODE -eq 0) { .\MAJ_VALMOREL.bat }
```

**Ensuite :** double-cliquer sur `MAJ_VALMOREL.bat`. A la fin du message SUCCESS, lancer FS2024 normalement.

Si la recherche automatique du Community echoue, consulter le dossier exact depuis FS2024 : **Marketplace > My Library > Settings > Open**, puis utiliser la commande PowerShell suivante en remplacant le chemin par le dossier confirme :

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "D:\RealEarth2024\scripts\maj_valmorel.ps1" -CommunityPath "E:\chemin\reel\Community"
```

Le fichier `UserCfg.opt` est **lu, jamais modifie**. Aucun autre add-on n'est touche.

## Etat des tests
Le pipeline 0.1.3 a ete valide avec 20 textures KTX2 et visible dans FS2024. Le lanceur complet et les nouvelles textures de fenetres de la 0.1.4 sont **non testes localement** : il faut confirmer la sortie SUCCESS et verifier visuellement dans le simulateur.
