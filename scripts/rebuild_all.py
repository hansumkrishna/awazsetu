"""Rebuild every distributable artefact, in the order that keeps disk use lowest.

    python scripts/rebuild_all.py            # lite, then full, then stage for Drive
    python scripts/rebuild_all.py lite       # one of them

For each build: make the folder, zip and split it, THEN add the MSIX payload and
pack that, then delete the folder. The order matters twice over.

  * MSIX bits last. `build_msix` drops AwazSetu.exe, Assets/ and AppxManifest.xml
    into the staged folder. Zipping first keeps those out of the .zip, where they
    would be three files nobody can explain.
  * Folder deleted straight after. The folder, its zip parts and its .msix are
    three copies of the same ten to sixteen gigabytes; only two of them are
    deliverable, and holding all three at once is what runs a laptop out of disk
    halfway through the second build.

Long: budget about forty minutes for both. Run it detached.
"""
from __future__ import annotations
import os
import shutil
import sys
import time

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DIST = os.path.join(REPO, "dist")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def log(*a):
    print(*a, flush=True)


def free_gb() -> float:
    return shutil.disk_usage(REPO).free / 1e9


def do(kind: str) -> None:
    import package
    import build_msix

    t0 = time.time()
    log(f"\n################  {kind.upper()}  ({free_gb():.1f} GB free)  ################")

    root = package.build(kind)
    log(f"  folder built, {free_gb():.1f} GB free")

    package.make_zip(root, 1900)
    log(f"  zip split into parts, {free_gb():.1f} GB free")

    try:
        build_msix.build_one(kind, restage=False, do_sign=True)
        log(f"  msix signed, {free_gb():.1f} GB free")
    except SystemExit as e:
        # A missing Windows SDK must not cost us the .zip that already succeeded.
        log(f"  !! MSIX skipped: {e}")

    shutil.rmtree(root, ignore_errors=True)
    log(f"  staging folder removed, {free_gb():.1f} GB free")
    log(f"  {kind} done in {(time.time()-t0)/60:.1f} min")


def main() -> None:
    kinds = [a for a in sys.argv[1:] if a in ("lite", "full")] or ["lite", "full"]
    log(f"rebuilding: {', '.join(kinds)}   ({free_gb():.1f} GB free)")
    for k in kinds:
        do(k)

    import stage_gdrive
    log("\n################  staging for Drive  ################")
    stage_gdrive.main()
    log("\nREBUILD_ALL_DONE")


if __name__ == "__main__":
    main()
