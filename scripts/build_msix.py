"""Build a signed MSIX installer for AwazSetu.

    python scripts/build_msix.py test          # tiny package, proves the chain
    python scripts/build_msix.py lite          # from dist/awazsetu-lite/
    python scripts/build_msix.py full          # from dist/awazsetu-full/
    python scripts/build_msix.py lite --stage  # build that folder first
    python scripts/build_msix.py both --stage

Output lands in installer/ as AwazSetu-<kind>.msix, signed, beside the .cer a
machine needs in order to trust it.

WHAT AN MSIX BUYS, AND WHAT IT COSTS
------------------------------------
Buys: a Start Menu entry, a real uninstall, per-user install with no admin
rights, no files loose on disk, and a form the IT department can deploy through
Intune. The .zip does none of that.

Costs, stated plainly because they are not negotiable:

  * **It must be signed.** Windows refuses to install an unsigned MSIX. There is
    no developer-mode switch that changes this. So the package is signed with a
    certificate generated here, and the receiving machine has to trust that
    certificate once -- which takes one elevated command. Install.ps1 does it.
  * **The install directory is read-only.** Everything under WindowsApps is.
    app/paths.py handles this: the shipped library is served from where it lands
    and anything new is written to %LOCALAPPDATA%\\AwazSetu.
  * **It is not smaller.** A 10.7 GB folder makes a 10.7 GB package; the payload
    is already-compressed model weights and MSIX cannot squeeze them either.

None of that makes the .zip obsolete. On a locked-down laptop where nobody can
run an elevated command, the .zip is still the only thing that works, and it
remains the supported route.
"""
from __future__ import annotations
import os
import re
import sys
import zlib
import shutil
import struct
import secrets
import subprocess

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DIST = os.path.join(REPO, "dist")
INST = os.path.join(REPO, "installer")
ASSETS = os.path.join(INST, "Assets")
CERTDIR = os.path.join(INST, "cert")

PUBLISHER = "CN=Fluent Fusion"          # must match the certificate subject exactly
PUBLISHER_NAME = "Fluent Fusion"
VERSION = "1.0.0.0"
RED = (0xC0, 0x27, 0x2D)

KINDS = {
    "lite": ("AwazSetu", "FluentFusion.AwazSetu",
             "Offline Hindi, Marathi, English and Odia video translation, "
             "subtitles, voiceover and a local assistant."),
    "full": ("AwazSetu Full", "FluentFusion.AwazSetu.Full",
             "AwazSetu with every model: Whisper large-v3, the NLLB fallback "
             "engine and the rescue kit."),
    "test": ("AwazSetu Packaging Test", "FluentFusion.AwazSetu.Test",
             "Packaging self-test. Not for distribution."),
}


def log(*a):
    print(*a, flush=True)


def run(cmd, **kw):
    r = subprocess.run(cmd, capture_output=True, text=True, **kw)
    return r.returncode, (r.stdout or "") + (r.stderr or "")


# --------------------------------------------------------------- SDK tooling
def sdk_tool(name: str) -> str:
    """Newest makeappx/signtool from the installed Windows SDK.

    Sorted by parsed version rather than by string, so 10.0.9 does not sort
    above 10.0.19041 -- which is exactly the kind of thing that makes a build
    silently use a decade-old tool.
    """
    exe = name + ".exe"
    roots = [r"C:\Program Files (x86)\Windows Kits\10\bin",
             r"C:\Program Files\Windows Kits\10\bin"]
    found = []
    for root in roots:
        if not os.path.isdir(root):
            continue
        for d in os.listdir(root):
            p = os.path.join(root, d, "x64", exe)
            if os.path.exists(p):
                m = re.match(r"(\d+)\.(\d+)\.(\d+)\.(\d+)", d)
                found.append((tuple(int(x) for x in m.groups()) if m else (0,), p))
    if not found:
        raise SystemExit(
            f"{exe} not found. It ships with the Windows 10/11 SDK "
            "(Windows App Certification Kit component). Install the SDK, or "
            "build the .zip package instead with scripts/package.py.")
    return max(found)[1]


# -------------------------------------------------------------------- assets
def _png(path: str, w: int, h: int, draw):
    """Write an RGBA PNG. Hand-rolled because Pillow is not in the runtime and
    adding it would put a build-only dependency into a shipped package."""
    raw = bytearray()
    for y in range(h):
        raw.append(0)                                   # filter: none
        for x in range(w):
            raw.extend(draw(x, y, w, h))
    def chunk(tag, data):
        return (struct.pack(">I", len(data)) + tag + data
                + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF))
    png = (b"\x89PNG\r\n\x1a\n"
           + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 6, 0, 0, 0))
           + chunk(b"IDAT", zlib.compress(bytes(raw), 9))
           + chunk(b"IEND", b""))
    with open(path, "wb") as f:
        f.write(png)


def _mark(x: int, y: int, w: int, h: int):
    """A red rounded rectangle carrying a white waveform: sound, in five bars.

    Drawn full-bleed rather than as a transparent glyph, because a transparent
    icon with white content disappears entirely on a light taskbar.
    """
    side = float(min(w, h))
    r = side * 0.22                                      # corner radius
    cx = min(max(x + 0.5, r), w - r)
    cy = min(max(y + 0.5, r), h - r)
    if (x + 0.5 - cx) ** 2 + (y + 0.5 - cy) ** 2 > r * r:
        return (0, 0, 0, 0)                              # outside the rounded corner
    heights = (0.30, 0.56, 0.84, 0.56, 0.30)
    n = len(heights)
    span = side * 0.62
    bw = span / (2 * n - 1)                              # bar, gap, bar, ...
    x0 = (w - span) / 2.0
    for i, hh in enumerate(heights):
        left = x0 + i * 2 * bw
        if left <= x + 0.5 <= left + bw:
            half = side * hh / 2.0
            if abs(y + 0.5 - h / 2.0) <= half:
                return (255, 255, 255, 255)
    return (RED[0], RED[1], RED[2], 255)


def ensure_assets(force: bool = False) -> None:
    os.makedirs(ASSETS, exist_ok=True)
    # Windows requires the wide tile whenever the large square one is offered,
    # so the set is fixed as a group rather than a la carte.
    for name, w, h in (("Square44x44Logo.png", 44, 44),
                       ("Square150x150Logo.png", 150, 150),
                       ("Wide310x150Logo.png", 310, 150),
                       ("Square310x310Logo.png", 310, 310),
                       ("StoreLogo.png", 50, 50)):
        p = os.path.join(ASSETS, name)
        if force or not os.path.exists(p):
            _png(p, w, h, _mark)
            log(f"  asset {name} ({w}x{h})")


# ------------------------------------------------------------------ launcher
def ensure_launcher(force: bool = False) -> str:
    src = os.path.join(INST, "launcher", "AwazSetu.cs")
    exe = os.path.join(INST, "launcher", "AwazSetu.exe")
    if not force and os.path.exists(exe) and \
            os.path.getmtime(exe) >= os.path.getmtime(src):
        return exe
    csc = r"C:\Windows\Microsoft.NET\Framework64\v4.0.30319\csc.exe"
    if not os.path.exists(csc):
        raise SystemExit("csc.exe not found. It ships with the .NET Framework "
                         "that is part of Windows; this machine is unusual.")
    # csc treats '/' as an option prefix, so every path here must use backslashes.
    code, out = run([csc, "-nologo", "-target:winexe", "-optimize+",
                     "-out:" + exe.replace("/", "\\"),
                     "-reference:System.dll", "-reference:System.Core.dll",
                     "-reference:System.Windows.Forms.dll",
                     src.replace("/", "\\")])
    if code != 0 or not os.path.exists(exe):
        raise SystemExit("launcher build failed:\n" + out)
    log(f"  launcher compiled ({os.path.getsize(exe)/1024:.0f} KB)")
    return exe


# ------------------------------------------------------------------ manifest
MANIFEST = '''<?xml version="1.0" encoding="utf-8"?>
<Package
  xmlns="http://schemas.microsoft.com/appx/manifest/foundation/windows10"
  xmlns:uap="http://schemas.microsoft.com/appx/manifest/uap/windows10"
  xmlns:rescap="http://schemas.microsoft.com/appx/manifest/foundation/windows10/restrictedcapabilities"
  IgnorableNamespaces="uap rescap">

  <Identity Name="{ident}" Publisher="{publisher}" Version="{version}"
            ProcessorArchitecture="x64" />

  <Properties>
    <DisplayName>{display}</DisplayName>
    <PublisherDisplayName>{pubname}</PublisherDisplayName>
    <Logo>Assets\\StoreLogo.png</Logo>
  </Properties>

  <Dependencies>
    <TargetDeviceFamily Name="Windows.Desktop"
                        MinVersion="10.0.17763.0" MaxVersionTested="10.0.26100.0" />
  </Dependencies>

  <Resources>
    <Resource Language="en-IN" />
    <Resource Language="hi-IN" />
    <Resource Language="mr-IN" />
    <Resource Language="or-IN" />
  </Resources>

  <Applications>
    <Application Id="AwazSetu" Executable="AwazSetu.exe"
                 EntryPoint="Windows.FullTrustApplication">
      <uap:VisualElements
        DisplayName="{display}"
        Description="{description}"
        BackgroundColor="transparent"
        Square150x150Logo="Assets\\Square150x150Logo.png"
        Square44x44Logo="Assets\\Square44x44Logo.png">
        <uap:DefaultTile Wide310x150Logo="Assets\\Wide310x150Logo.png"
                         Square310x310Logo="Assets\\Square310x310Logo.png" />
      </uap:VisualElements>
    </Application>
  </Applications>

  <Capabilities>
    <!-- Full trust: the app is an embedded CPython serving a local web page.
         Inside an AppContainer it could not listen on loopback, so the browser
         would never reach it. -->
    <rescap:Capability Name="runFullTrust" />
  </Capabilities>
</Package>
'''


def write_manifest(stage: str, kind: str) -> None:
    display, ident, description = KINDS[kind]
    xml = MANIFEST.format(ident=ident, publisher=PUBLISHER, version=VERSION,
                          display=display, pubname=PUBLISHER_NAME,
                          description=description)
    with open(os.path.join(stage, "AppxManifest.xml"), "w", encoding="utf-8") as f:
        f.write(xml)


# --------------------------------------------------------------- certificate
def ensure_cert() -> tuple[str, str, str]:
    """(pfx, cer, password). Created once and reused; never committed.

    A self-signed certificate is the only option here: a real code-signing
    certificate costs money and is issued to a legal entity, which a hackathon
    team is not. The consequence is honest and documented -- the receiving
    machine trusts this specific certificate, once, deliberately.
    """
    os.makedirs(CERTDIR, exist_ok=True)
    pfx = os.path.join(CERTDIR, "AwazSetu.pfx")
    cer = os.path.join(INST, "AwazSetu.cer")
    pwfile = os.path.join(CERTDIR, "password.txt")
    if os.path.exists(pfx) and os.path.exists(cer) and os.path.exists(pwfile):
        return pfx, cer, open(pwfile, encoding="utf-8").read().strip()

    pw = secrets.token_urlsafe(18)
    ps = (
        "$ErrorActionPreference='Stop';"
        "$c = New-SelfSignedCertificate -Type Custom"
        " -Subject '" + PUBLISHER + "'"
        " -KeyUsage DigitalSignature -FriendlyName 'AwazSetu sideload signing'"
        " -CertStoreLocation 'Cert:\\CurrentUser\\My'"
        " -TextExtension @('2.5.29.37={text}1.3.6.1.5.5.7.3.3',"
        "'2.5.29.19={text}Subject Type:End Entity');"
        "$p = ConvertTo-SecureString -String '" + pw + "' -Force -AsPlainText;"
        "Export-PfxCertificate -Cert $c -FilePath '" + pfx + "' -Password $p | Out-Null;"
        "Export-Certificate -Cert $c -FilePath '" + cer + "' | Out-Null;"
        "Write-Output $c.Thumbprint"
    )
    code, out = run(["powershell", "-NoProfile", "-Command", ps])
    if code != 0 or not os.path.exists(pfx):
        raise SystemExit("could not create the signing certificate:\n" + out)
    with open(pwfile, "w", encoding="utf-8") as f:
        f.write(pw)
    # Pick the thumbprint out by shape. PowerShell interleaves its own notices
    # with the output, so "the last line" is not reliably the value.
    tp = next((ln.strip() for ln in out.splitlines()
               if re.fullmatch(r"[0-9A-Fa-f]{40}", ln.strip())), "unknown")
    log(f"  certificate created, thumbprint {tp}")
    return pfx, cer, pw


# ------------------------------------------------------------------ packaging
def pack(stage: str, out: str) -> None:
    makeappx = sdk_tool("makeappx")
    if os.path.exists(out):
        os.remove(out)
    code, txt = run([makeappx, "pack", "/d", stage, "/p", out, "/o"])
    if code != 0 or not os.path.exists(out):
        raise SystemExit("makeappx failed:\n" + txt[-4000:])
    log(f"  packed {os.path.getsize(out)/1e9:.2f} GB -> {os.path.basename(out)}")


def sign(msix: str) -> None:
    signtool = sdk_tool("signtool")
    pfx, _cer, pw = ensure_cert()
    code, txt = run([signtool, "sign", "/fd", "SHA256", "/a",
                     "/f", pfx, "/p", pw, msix])
    if code != 0:
        raise SystemExit("signing failed:\n" + txt[-3000:])
    code, txt = run([signtool, "verify", "/pa", "/v", msix])
    # /pa checks the default authenticode policy; an untrusted-root complaint is
    # expected for a self-signed certificate and is not a signing failure.
    ok = "Successfully verified" in txt or "successfully signed" in txt.lower()
    log("  signed and verified" if ok
        else "  signed (chain is untrusted until the .cer is installed)")


def staged_folder(kind: str, restage: bool) -> str:
    if kind == "test":
        return make_test_payload()
    root = os.path.join(DIST, f"awazsetu-{kind}")
    if restage or not os.path.isdir(root):
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        import package
        log(f"  staging dist/awazsetu-{kind}/ ...")
        root = package.build(kind)
    return root


def make_test_payload() -> str:
    """A package with the real launcher and a real embedded-Python entry point,
    but no models. It proves the manifest, the assets, the signing and the
    install path in about two seconds instead of forty minutes."""
    root = os.path.join(DIST, "awazsetu-msix-test")
    if os.path.exists(root):
        shutil.rmtree(root)
    os.makedirs(os.path.join(root, "app"))
    os.makedirs(os.path.join(root, "runtime", "python"))
    # A stand-in for pythonw.exe and run.py: the launcher only checks they exist.
    for p, body in ((os.path.join(root, "runtime", "python", "pythonw.exe"), b"MZ"),
                    (os.path.join(root, "app", "run.py"), b"# packaging test\n")):
        with open(p, "wb") as f:
            f.write(body)
    return root


def build_one(kind: str, restage: bool, do_sign: bool) -> str:
    log(f"\n=== MSIX: {kind} ===")
    ensure_assets()
    exe = ensure_launcher()
    stage = staged_folder(kind, restage)

    shutil.copy2(exe, os.path.join(stage, "AwazSetu.exe"))
    dst_assets = os.path.join(stage, "Assets")
    os.makedirs(dst_assets, exist_ok=True)
    for f in os.listdir(ASSETS):
        shutil.copy2(os.path.join(ASSETS, f), os.path.join(dst_assets, f))
    write_manifest(stage, kind)
    log("  launcher, assets and AppxManifest.xml placed in the payload")

    os.makedirs(INST, exist_ok=True)
    out = os.path.join(INST, f"AwazSetu-{kind}.msix")
    pack(stage, out)
    if do_sign:
        sign(out)
    return out


def main() -> None:
    args = [a for a in sys.argv[1:]]
    restage = "--stage" in args
    do_sign = "--no-sign" not in args
    kinds = [a for a in args if not a.startswith("--")] or ["test"]
    if kinds == ["both"]:
        kinds = ["lite", "full"]
    for k in kinds:
        if k not in KINDS:
            raise SystemExit(f"unknown target {k!r}; expected one of "
                             + ", ".join(KINDS) + ", or both")
    made = [build_one(k, restage, do_sign) for k in kinds]
    log("\ninstallers:")
    for m in made:
        log(f"  {m}  ({os.path.getsize(m)/1e6:.1f} MB)")
    log("\nTo install one, run installer/Install.ps1 as administrator "
        "(it trusts the certificate, then installs).")
    log("MSIX_DONE")


if __name__ == "__main__":
    main()
