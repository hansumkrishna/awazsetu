"""Remove compiled Python caches whose sources this update replaced.

    python scripts/clean_caches.py [--all] [--dry-run]

Why it matters at all: Python reuses a `.pyc` when it looks newer than its
`.py`. Extracting an archive preserves the archive's timestamps, so a source
file you just replaced can end up looking OLDER than the cache built from the
previous version -- and the interpreter then runs the old code while the new
file sits on disk. The update appears to have done nothing, and nothing
anywhere reports an error.

Scoped by default, and that is the point. Sweeping every `__pycache__` in the
installation also clears the thousands under site-packages for libraries this
update never touched; Python recompiles them all on the next launch, which
costs about a minute of startup to fix a problem those libraries do not have.
`--all` does the sweep anyway, for when something is genuinely confusing.
"""
from __future__ import annotations
import os
import shutil
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = os.path.join(REPO, "runtime", "python", "Lib", "site-packages")

# The application, its tooling, and the libraries this release installs or
# replaces. Anything else in site-packages is untouched by the update, so its
# caches are still valid.
SCOPED = [
    os.path.join(REPO, "app"),
    os.path.join(REPO, "scripts"),
] + [os.path.join(SITE, p) for p in
     ("IndicTransToolkit", "indicnlp", "sacremoses", "joblib",
      "morfessor", "pandas", "pytz", "dateutil")]


def sweep(roots, dry: bool) -> tuple[int, int]:
    dirs = files = 0
    for root in roots:
        if not os.path.isdir(root):
            continue
        for base, subdirs, names in os.walk(root, topdown=False):
            for n in names:
                if n.endswith((".pyc", ".pyo")):
                    p = os.path.join(base, n)
                    if not dry:
                        try:
                            os.remove(p)
                        except OSError:
                            continue
                    files += 1
            if os.path.basename(base) == "__pycache__":
                if not dry:
                    shutil.rmtree(base, ignore_errors=True)
                dirs += 1
    return dirs, files


def main() -> None:
    dry = "--dry-run" in sys.argv
    roots = [REPO] if "--all" in sys.argv else SCOPED
    scope = "the whole installation" if "--all" in sys.argv else \
            "app, scripts and the replaced libraries"
    dirs, files = sweep(roots, dry)
    verb = "would remove" if dry else "removed"
    print(f"  {verb} {dirs} cache folder(s) and {files} loose .pyc under {scope}")
    print("CACHES_CLEAN")


if __name__ == "__main__":
    main()
