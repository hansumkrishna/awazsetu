# Launch the voiceover build as a DETACHED process.
#
# The build takes roughly half an hour and must survive the tooling that started
# it: two earlier attempts were killed part-way because they ran as child
# processes of a background shell. Start-Process with -WindowStyle Hidden gives
# it its own process tree, so it keeps going regardless.
#
#   powershell -ExecutionPolicy Bypass -File scripts\run_dubs_detached.ps1
#
# Progress: dist\dubs.log     Raw output: dist\dubs_detached.out / .err

$ErrorActionPreference = "Stop"
$repo = Split-Path -Parent $PSScriptRoot
$py   = "C:\Users\hansu\AppData\Local\Programs\Python\Python310\python.exe"

$env:PYTHONIOENCODING = "utf-8"

$args = @("-u", (Join-Path $repo "scripts\build_dubs_par.py"), "--workers=4")

$p = Start-Process -FilePath $py `
                   -ArgumentList $args `
                   -WorkingDirectory $repo `
                   -RedirectStandardOutput (Join-Path $repo "dist\dubs_detached.out") `
                   -RedirectStandardError  (Join-Path $repo "dist\dubs_detached.err") `
                   -WindowStyle Hidden `
                   -PassThru

Write-Output "detached PID: $($p.Id)"
