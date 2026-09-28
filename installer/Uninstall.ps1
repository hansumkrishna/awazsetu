<#
    AwazSetu - remove the MSIX package.

        Right-click this file and choose "Run with PowerShell".

    By default this removes the application and leaves your data alone: the
    videos you processed and your settings live in %LOCALAPPDATA%\AwazSetu and
    are kept, so reinstalling puts you back where you were.

        -PurgeData     also delete that folder
        -RemoveCert    also stop trusting the signing certificate (needs admin)
#>
[CmdletBinding()]
param(
    [switch] $PurgeData,
    [switch] $RemoveCert
)

$ErrorActionPreference = 'Stop'

function Say($m) { Write-Host $m }
function Ok ($m) { Write-Host "  $m" -ForegroundColor Green }
function Warn($m) { Write-Host "  $m" -ForegroundColor Yellow }

Say ''
Say 'AwazSetu uninstaller'
Say '===================='
Say ''

$pkgs = @(Get-AppxPackage -Name 'FluentFusion.AwazSetu*')
if ($pkgs.Count -eq 0) {
    Warn 'AwazSetu is not installed for this user.'
} else {
    foreach ($p in $pkgs) {
        Say ("Removing " + $p.Name + " " + $p.Version)
        Remove-AppxPackage -Package $p.PackageFullName
        Ok 'Removed.'
    }
}

$data = Join-Path $env:LOCALAPPDATA 'AwazSetu'
if (Test-Path $data) {
    if ($PurgeData) {
        Remove-Item -LiteralPath $data -Recurse -Force
        Ok "Deleted $data"
    } else {
        $mb = [math]::Round(((Get-ChildItem $data -Recurse -File -ErrorAction SilentlyContinue |
                              Measure-Object Length -Sum).Sum / 1MB), 1)
        Say ''
        Say ("Your data is kept: $data  ($mb MB)")
        Say '  Re-run with -PurgeData to delete it too.'
    }
}

if ($RemoveCert) {
    $isAdmin = ([Security.Principal.WindowsPrincipal] `
                [Security.Principal.WindowsIdentity]::GetCurrent()
               ).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
    if (-not $isAdmin) {
        Warn 'Removing the certificate needs administrator rights; skipped.'
    } else {
        $found = Get-ChildItem 'Cert:\LocalMachine\TrustedPeople' |
                 Where-Object { $_.Subject -eq 'CN=Fluent Fusion' }
        foreach ($c in $found) {
            Remove-Item -LiteralPath $c.PSPath -Force
            Ok ('Certificate removed: ' + $c.Thumbprint)
        }
        if (-not $found) { Warn 'No AwazSetu certificate was trusted.' }
    }
}
Say ''
