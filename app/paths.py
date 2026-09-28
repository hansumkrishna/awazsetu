"""AwazSetu — where this installation is allowed to write.

The .zip package is a folder you own: the app writes its library, uploads and
settings right next to itself, and deleting the folder uninstalls it. An MSIX
install is not. It lands in `C:\\Program Files\\WindowsApps\\...`, which is
read-only to the application itself, and a `settings.json` write there fails
with PermissionError rather than being redirected anywhere useful.

So the location is decided at runtime by TESTING it, not by guessing from an
environment variable that might be wrong:

    writable install  -> everything stays beside the app, exactly as before
    read-only install -> the shipped library stays where it is and is served
                         read-only; new work goes to %LOCALAPPDATA%\\AwazSetu

That makes the read-only case a strict superset: the fifteen shipped videos are
still there, still instant, and an upload still works. The alternative — copying
a gigabyte of shipped library into the user profile on first run — would double
the disk cost to solve a problem only new files actually have.
"""
from __future__ import annotations
import os

APP_DIR = os.path.dirname(os.path.abspath(__file__))
SHIPPED_DATA = os.path.join(APP_DIR, "data")
SHIPPED_WORK = os.path.join(SHIPPED_DATA, "work")

_data_root: str | None = None


def _can_write(d: str) -> bool:
    """Probe with a real file. Read-only-ness on Windows comes from ACLs, package
    containment and volume flags; none of those are visible in os.access, which
    happily reports a WindowsApps directory as writable right up until the write
    raises PermissionError."""
    try:
        os.makedirs(d, exist_ok=True)
        probe = os.path.join(d, ".awaz-write-test")
        with open(probe, "w") as f:
            f.write("ok")
        os.remove(probe)
        return True
    except Exception:
        return False


def data_root() -> str:
    """The folder this installation may write to. Decided once per process."""
    global _data_root
    if _data_root:
        return _data_root
    forced = os.environ.get("AWAZ_DATA_DIR")
    if forced:
        os.makedirs(forced, exist_ok=True)
        _data_root = forced
        return _data_root
    if _can_write(SHIPPED_DATA):
        _data_root = SHIPPED_DATA
    else:
        base = os.environ.get("LOCALAPPDATA") or os.path.expanduser("~")
        _data_root = os.path.join(base, "AwazSetu")
        os.makedirs(_data_root, exist_ok=True)
    return _data_root


def is_read_only_install() -> bool:
    return os.path.abspath(data_root()) != os.path.abspath(SHIPPED_DATA)


def work_rw() -> str:
    """Where NEW work is written. Always writable, always exists."""
    d = os.path.join(data_root(), "work")
    os.makedirs(d, exist_ok=True)
    return d


def work_roots() -> list[str]:
    """Every folder that may hold processed items, writable one first.

    Order is the resolution order, so a re-processed copy of a shipped video
    shadows the shipped one instead of fighting it.
    """
    roots = [work_rw()]
    if os.path.isdir(SHIPPED_WORK) and os.path.abspath(SHIPPED_WORK) not in (
            os.path.abspath(r) for r in roots):
        roots.append(SHIPPED_WORK)
    return roots


def work_dir(vid: str) -> str:
    """The folder for one item: wherever it already is, else where it would go."""
    for r in work_roots():
        if os.path.exists(os.path.join(r, vid, "manifest.json")):
            return os.path.join(r, vid)
    for r in work_roots():
        if os.path.isdir(os.path.join(r, vid)):
            return os.path.join(r, vid)
    return os.path.join(work_rw(), vid)


def list_work() -> list[tuple[str, str]]:
    """(id, folder) for every processed item, sorted, first root wins."""
    seen: dict[str, str] = {}
    for r in work_roots():
        if not os.path.isdir(r):
            continue
        for d in os.listdir(r):
            if d not in seen and os.path.exists(os.path.join(r, d, "manifest.json")):
                seen[d] = os.path.join(r, d)
    return sorted(seen.items())


def uploads_dir() -> str:
    d = os.path.join(data_root(), "uploads")
    os.makedirs(d, exist_ok=True)
    return d


def settings_path() -> str:
    """settings.json, seeded from the shipped copy the first time it is needed on
    a read-only install so the packaged defaults are not silently lost."""
    if not is_read_only_install():
        return os.path.join(APP_DIR, "settings.json")
    p = os.path.join(data_root(), "settings.json")
    if not os.path.exists(p):
        src = os.path.join(APP_DIR, "settings.json")
        try:
            if os.path.exists(src):
                import shutil
                shutil.copy2(src, p)
        except Exception:
            pass
    return p


def describe() -> dict:
    """For the doctor and the Settings page — what was actually chosen, and why."""
    return {
        "app_dir": APP_DIR,
        "data_root": data_root(),
        "read_only_install": is_read_only_install(),
        "work_roots": work_roots(),
        "settings": settings_path(),
        "items": len(list_work()),
    }
