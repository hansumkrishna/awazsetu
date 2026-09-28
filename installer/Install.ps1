<#
    AwazSetu - install the MSIX package.

        Right-click this file and choose "Run with PowerShell".

    It does exactly two things, and tells you before it does them:

      1. Trusts the certificate the package is signed with. Windows refuses to
         install any MSIX whose signature it does not trust, and a hackathon
         team cannot buy a commercial code-signing certificate, so the package
         is self-signed and the certificate has to be trusted once. This step
         needs administrator rights; nothing else here does.

      2. Installs the package for the current user.

    If you would rather not trust a certificate -- a reasonable position -- use
    the .zip package instead. It needs no administrator rights and no trust
    decision at all: extract the folder, double-click AwazSetu.bat. Nothing in
    this installer makes the application itself work any better.

    To remove everything again, run Uninstall.ps1.
#>
[CmdletBinding()]
param(
    # Which package to install. Defaults to the only .msix beside this script,
    # or to AwazSetu-lite.msix when both are present.
    [string] $Package,
    # Skip the certificate step, for a machine where it is already trusted.
    [switch] $SkipCertificate
)

$ErrorActionPreference = 'Stop'
$here = Split-Path -Parent $MyInvocation.MyCommand.Path

function Say($m) { Write-Host $m }
function Ok ($m) { Write-Host "  $m" -ForegroundColor Green }
function Warn($m) { Write-Host "  $m" -ForegroundColor Yellow }
function Die ($m) { Write-Host "  $m" -ForegroundColor Red; exit 1 }

Say ''
Say 'AwazSetu installer'
Say '=================='
Say ''

# ---- pick the package ------------------------------------------------------
if (-not $Package) {
    $found = @(Get-ChildItem -Path $here -Filter '*.msix' -File |
               Where-Object { $_.Name -notlike '*-test.msix' } |
               Sort-Object Name)
    if ($found.Count -eq 0) { Die 'No .msix found beside this script.' }
    $pick = $found | Where-Object { $_.Name -like '*lite*' } | Select-Object -First 1
    if (-not $pick) { $pick = $found[0] }
    $Package = $pick.FullName
    if ($found.Count -gt 1) {
        Warn ("Found " + $found.Count + " packages; installing " + $pick.Name)
        Warn 'Use  -Package <file>  to choose the other one.'
    }
}
if (-not (Test-Path $Package)) { Die "Not found: $Package" }
$sizeGb = [math]::Round((Get-Item $Package).Length / 1GB, 2)
Say ("Package : " + (Split-Path -Leaf $Package) + "  ($sizeGb GB)")

# ---- re-launch elevated if we need to trust the certificate ----------------
$isAdmin = ([Security.Principal.WindowsPrincipal] `
            [Security.Principal.WindowsIdentity]::GetCurrent()
           ).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)

if (-not $SkipCertificate -and -not $isAdmin) {
    Say ''
    Say 'Trusting the signing certificate needs administrator rights.'
    Say 'Windows will now ask for permission. Nothing is installed until it does.'
    $argList = @('-NoProfile', '-ExecutionPolicy', 'Bypass',
                 '-File', "`"$PSCommandPath`"", '-Package', "`"$Package`"")
    try {
        $p = Start-Process -FilePath 'powershell.exe' -ArgumentList $argList `
                           -Verb RunAs -PassThru -Wait
        exit $p.ExitCode
    } catch {
        Die ('Permission was declined. Nothing has been changed. ' +
             'You can use the .zip package instead, which needs no rights at all.')
    }
}

# ---- 1. trust the certificate ---------------------------------------------
if (-not $SkipCertificate) {
    $cer = Join-Path $here 'AwazSetu.cer'
    if (-not (Test-Path $cer)) { Die "Certificate not found: $cer" }
    $c = New-Object Security.Cryptography.X509Certificates.X509Certificate2 $cer
    Say ''
    Say ('Certificate : ' + $c.Subject + '   expires ' + $c.NotAfter.ToString('d MMM yyyy'))
    Say ('Thumbprint  : ' + $c.Thumbprint)
    # TrustedPeople, deliberately, not Root: this lets Windows accept packages
    # signed by exactly this certificate without making it an authority that can
    # vouch for anything else on the machine.
    Import-Certificate -FilePath $cer -CertStoreLocation 'Cert:\LocalMachine\TrustedPeople' |
        Out-Null
    Ok 'Certificate trusted (LocalMachine\TrustedPeople).'
}

# ---- 2. install ------------------------------------------------------------
Say ''
Say 'Installing. A large package takes a few minutes and shows no progress bar.'
try {
    Add-AppxPackage -Path $Package -ErrorAction Stop
} catch {
    $m = $_.Exception.Message
    if ($m -match '0x800B0109') {
        Die ('The certificate is still not trusted. Re-run this script and ' +
             'accept the administrator prompt.')
    } elseif ($m -match '0x80073CF9|0x80073D0A') {
        Die ('Windows could not write the package. Check there is enough free ' +
             'disk space -- a 10 GB package needs about 12 GB free.')
    } else {
        Die $m
    }
}
Ok 'Installed.'

$app = Get-AppxPackage -Name 'FluentFusion.AwazSetu*' | Select-Object -First 1
if ($app) {
    Say ''
    Say ('  Name    : ' + $app.Name)
    Say ('  Version : ' + $app.Version)
    Say ('  Folder  : ' + $app.InstallLocation)
}
Say ''
Ok 'Start AwazSetu from the Start Menu. A browser tab opens at 127.0.0.1.'
Say '  Your videos and settings are kept in %LOCALAPPDATA%\AwazSetu'
Say '  and survive an upgrade. Uninstall.ps1 removes the app.'
Say ''
