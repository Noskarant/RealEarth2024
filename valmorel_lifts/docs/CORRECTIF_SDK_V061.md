# Correctif V0.6.1 — arrêt PowerShell sur message SDK

## Erreur observée
Sur Windows PowerShell 5.1 avec `$ErrorActionPreference='Stop'`, la commande V0.6 :
```powershell
& $sdk $ProjectXml '-rebuild' '-nopause' 2>&1 | Tee-Object -FilePath $sdkLog
```
pouvait lever une exception dès le message SDK `Attached to EXE - waiting for completion.`, même si ce message n'indiquait pas une erreur de compilation.

La V0.6 avait déjà généré les routes OSM / relief IGN (Planchamp ~1842,9 m, Pierrafort ~1826,6 m), 26 pylônes statiques, 48 cabines statiques et 1 zone d'exclusion locale. **La validation SDK n'a pas encore été confirmée**.

## Fix dans archive de livraison
Archive `VALMOREL_TELECABINES_V061_CORRECTIF_COMPILATION.zip` remise dans la conversation :
- lance le SDK avec `Start-Process -RedirectStandardOutput -RedirectStandardError -Wait -PassThru -NoNewWindow` (sorties capturées séparément pour éviter les `NativeCommandError` liés à stderr sous PowerShell 5.1) ;
- journalise `logs/sdk_build_v061_stdout.txt` et `logs/sdk_build_v061_stderr.txt` ;
- applique le contrôle du code de sortie et l'inspection des binaires compilés avant de toucher à Community ;
- corrige aussi les expressions de recherche des chemins Windows dans la validation des BGL : les BGL ModelLib et placements doivent être retrouvés sous leurs sous-dossiers respectifs.

L'archive comprend les sources et le lanceur complet, à extraire sur `D:\RealEarth2024` dans un **nouveau dossier**, sans copier de vieux fichiers de V0.5/V0.6.

La V0.5 doit être préservée jusqu'à validation/installation V0.6.1. Les fichiers d'installateurs complets et GLB restent distribués dans le ZIP, pas sur GitHub.

Sources :
- https://learn.microsoft.com/en-us/powershell/module/microsoft.powershell.core/about/about_preference_variables?view=powershell-5.1
- https://docs.flightsimulator.com/msfs2024/retail/sdk-tools/package-tool/package-tool/
