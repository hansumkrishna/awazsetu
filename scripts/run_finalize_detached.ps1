# Launch the whole remaining delivery as a DETACHED process.
#
# finalize_delivery.py waits for the voiceovers, builds both packages, splits the
# LITE archive, regenerates the Documentation Pack, and runs both verification
# passes. It takes well over an hour, so it must not be a child of whatever shell
# started it -- two earlier long builds were killed that way.
#
#   powershell -ExecutionPolicy Bypass -File scripts\run_finalize_detached.ps1
#
# Progress: dist\finalize.log     Result: dist\FINAL_REPORT.txt

$ErrorActionPreference = "Stop"
$repo = Split-Path -Parent $PSScriptRoot
$py   = "C:\Users\hansu\AppData\Local\Programs\Python\Python310\python.exe"

$env:PYTHONIOENCODING = "utf-8"

$p = Start-Process -FilePath $py `
                   -ArgumentList @("-u", (Join-Path $repo "scripts\finalize_delivery.py")) `
                   -WorkingDirectory $repo `
                   -RedirectStandardOutput (Join-Path $repo "dist\finalize.out") `
                   -RedirectStandardError  (Join-Path $repo "dist\finalize.err") `
                   -WindowStyle Hidden `
                   -PassThru

Write-Output "finalize detached PID: $($p.Id)"
