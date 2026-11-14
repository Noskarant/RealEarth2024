# Incident compilation SDK du 14 novembre 2026

Après validation des 8 modèles GLB et des quatre placements XML, l'appel à `fspackagetool.exe` échoue :

```text
The given path does not exist:
C:\Program Files\WindowsApps\Microsoft.Limitless_1.9.21.0_x64__8wekyb3d8bbwe\FlightSimulator2024.exe
```

Ce message vient du lancement de l'exécutable FS2024 utilisé par le Package Tool, **pas d'une erreur constatée dans les modèles Blender**.

## Correctif livré

Archive autonome `VALMOREL_TELECABINES_SDK_SOURCE_v02.zip` fournie dans la conversation (non stockée comme binaire dans GitHub) :

- Priorité aux `fspackagetool.exe` des répertoires SDK officiels plutôt qu'à l'ancienne copie de `D:\RealEarth2024\build\tools\`.
- Lecture du package Microsoft Store enregistré via `Get-AppxPackage` et affichage de son chemin.
- `DIAGNOSTIC_SDK_FS2024.bat` : lecture seule des chemins/versions, rapport dans `logs/diagnostic-msfs2024.txt`.
- Aucune écriture dans WindowsApps, registre, UserCfg.opt ni dans les autres mods.

Si erreur inchangée : Microsoft Store → mettre à jour Xbox et Gaming Services ; Paramètres Windows → Applications installées → Gaming Services → Options avancées → Réparer ; redémarrer. Ne pas réinstaller le simulateur ni modifier WindowsApps avant diagnostic.

**Compilation et affichage en jeu toujours non validés :** aucun accès à la machine Windows depuis ce traitement. Les coordonnées des gares sont provisoires. Les anciennes modifications des bâtiments et du relief ne sont pas réactivées.

Sources SDK :
- https://docs.flightsimulator.com/msfs2024/retail/sdk-tools/package-tool/package-tool/
- https://devsupport.flightsimulator.com/t/fspackagetool-exe-launching-the-sim-2020-and-2024/14919?page=2
