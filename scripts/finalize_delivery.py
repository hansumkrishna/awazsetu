"""AwazSetu — run the entire remaining delivery, unattended.

    python scripts/finalize_delivery.py

Waits for the voiceover build to finish, then does everything left in order and
records the result. Designed to be launched detached and left alone:

    1. wait for the voiceover build to drain
    2. repair any item whose manifest lost segments relative to its transcript
    3. build the LITE package (zero-install)
    4. build the FULL package (zero-install + spare models + rescue kit)
    5. reclaim disk from superseded artefacts
    6. zip LITE and split it into transferable parts with checksums
    7. regenerate the Documentation Pack from the finished library
    8. run the delivery gate and the clean-room test
    9. write dist/FINAL_REPORT.txt

Every step is logged to dist/finalize.log with a timestamp. A failing step is
recorded and the run continues, so one bad step cannot cost the rest of the work.
"""
from __future__ import annotations
import os
import sys
import json
import time
import shutil
import subprocess

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
APP = os.path.join(REPO, "app")
WORK = os.path.join(APP, "data", "work")
DIST = os.path.join(REPO, "dist")
LOG = os.path.join(DIST, "finalize.log")
PY = sys.executable

RESULTS: list[tuple[str, str, str]] = []


def log(msg: str):
    line = f"[{time.strftime('%H:%M:%S')}] {msg}"
    print(line, flush=True)
    try:
        with open(LOG, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception:
        pass


def step(name: str, fn):
    log(f"=== {name} ===")
    t0 = time.time()
    try:
        detail = fn() or ""
        RESULTS.append(("OK", name, f"{detail} ({time.time()-t0:.0f}s)"))
        log(f"    OK  {name}: {detail}")
    except Exception as ex:
        RESULTS.append(("FAIL", name, f"{type(ex).__name__}: {ex}"))
        log(f"    FAIL {name}: {type(ex).__name__}: {ex}")


def run(cmd, timeout=14400, cwd=REPO):
    env = dict(os.environ)
    env.setdefault("PYTHONIOENCODING", "utf-8")
    r = subprocess.run(cmd, cwd=cwd, env=env, capture_output=True, text=True,
                       encoding="utf-8", errors="replace", timeout=timeout)
    return r


# ---------------------------------------------------------------- the steps
def dub_workers_alive() -> int:
    try:
        out = subprocess.run(
            ["powershell", "-NoProfile", "-Command",
             "(Get-CimInstance Win32_Process -Filter \"Name='python.exe'\" | "
             "Where-Object {$_.CommandLine -like '*dub_worker*' -or "
             "$_.CommandLine -like '*build_dubs_par*'} | Measure-Object).Count"],
            capture_output=True, text=True, timeout=60).stdout.strip()
        return int(out.splitlines()[-1])
    except Exception:
        return 0


def wait_for_dubs():
    """Block until the voiceover build drains. It was launched detached."""
    deadline = time.time() + 7200
    last = -1
    while time.time() < deadline:
        n = len([1 for d in os.listdir(WORK)
                 if os.path.isdir(os.path.join(WORK, d))
                 for f in os.listdir(os.path.join(WORK, d))
                 if f.startswith("dub.") and f.endswith(".wav")])
        alive = dub_workers_alive()
        if n != last:
            log(f"    voiceovers on disk: {n}, workers alive: {alive}")
            last = n
        if alive == 0:
            time.sleep(20)
            if dub_workers_alive() == 0:      # confirm, do not race a respawn
                return f"{n} voiceover files on disk"
        time.sleep(60)
    return "timed out waiting; continuing"


def repair_lost_segments():
    """Re-translate any item whose manifest holds fewer segments than its transcript.

    The degenerate-output detector used to delete long English segments; an item can
    therefore carry a good transcript and an empty manifest. Rebuilding is cheap and
    catching it here is far better than shipping silent subtitles.
    """
    fixed = []
    for d in sorted(os.listdir(WORK)):
        p = os.path.join(WORK, d)
        mf, rf = os.path.join(p, "manifest.json"), os.path.join(p, "transcript.raw.json")
        if not (os.path.exists(mf) and os.path.exists(rf)):
            continue
        try:
            m = json.load(open(mf, encoding="utf-8"))
            t = json.load(open(rf, encoding="utf-8"))
        except Exception:
            continue
        if len(m.get("segments", [])) < len(t.get("segments", [])):
            src = m.get("src_lang") or t.get("lang") or "auto"
            log(f"    repairing {d[:8]}: manifest {len(m.get('segments', []))} "
                f"< transcript {len(t.get('segments', []))}")
            r = run([PY, os.path.join(REPO, "scripts", "_mt_one.py"), d, src], timeout=3600)
            if r.returncode == 0:
                fixed.append(d[:8])
                # its voiceovers now speak the wrong (empty) transcript
                for f in os.listdir(p):
                    if f.startswith("dub.") and f.endswith(".wav"):
                        try:
                            os.remove(os.path.join(p, f))
                        except OSError:
                            pass
    if fixed:
        log(f"    rebuilding voiceovers for repaired items: {fixed}")
        run([PY, os.path.join(REPO, "scripts", "build_dubs_par.py"), "--workers=2"],
            timeout=7200)
    return f"{len(fixed)} item(s) repaired" if fixed else "nothing lost"


def free_disk():
    """Remove superseded artefacts so the builds have room."""
    freed = 0
    for name in ("awazsetu-lite.zip", "_garden_snapshot.html"):
        p = os.path.join(DIST, name)
        if os.path.exists(p):
            freed += os.path.getsize(p)
            os.remove(p)
            log(f"    removed stale {name}")
    for pat in os.listdir(DIST):
        if pat.startswith("awazsetu-lite.zip."):
            p = os.path.join(DIST, pat)
            freed += os.path.getsize(p)
            os.remove(p)
    return f"{freed/1e9:.2f} GB reclaimed"


def build_pkg(kind: str):
    r = run([PY, os.path.join(REPO, "scripts", "package.py"), kind], timeout=14400)
    tail = (r.stdout or "").strip().splitlines()[-3:]
    if r.returncode != 0:
        raise RuntimeError(((r.stdout or "") + (r.stderr or ""))[-500:])
    return " | ".join(t.strip() for t in tail)


def zip_lite():
    r = run([PY, os.path.join(REPO, "scripts", "package.py"), "lite",
             "--zip", "--split=1900"], timeout=14400)
    if r.returncode != 0:
        raise RuntimeError(((r.stdout or "") + (r.stderr or ""))[-500:])
    parts = sorted(f for f in os.listdir(DIST) if ".zip." in f and f[-3:].isdigit())
    return f"{len(parts)} part(s)" if parts else "single archive"


def docpack():
    r = run([PY, os.path.join(REPO, "scripts", "build_docpack.py"), "--pdf"], timeout=3600)
    out = (r.stdout or "") + (r.stderr or "")
    lines = [l for l in out.splitlines() if l.startswith(("HTML", "PDF"))]
    if "DOCPACK_DONE" not in out:
        raise RuntimeError(out[-400:])
    return " | ".join(lines)


def gate():
    r = run([PY, os.path.join(REPO, "scripts", "verify_delivery.py")], timeout=3600)
    out = (r.stdout or "")
    line = [l for l in out.splitlines() if "passed," in l]
    with open(os.path.join(DIST, "delivery_gate.txt"), "w", encoding="utf-8") as f:
        f.write(out)
    return line[-1].strip() if line else "no summary"


def cleanroom():
    r = run([PY, os.path.join(REPO, "scripts", "test_package_cleanroom.py"),
             os.path.join(DIST, "awazsetu-lite")], timeout=7200)
    out = (r.stdout or "")
    with open(os.path.join(DIST, "cleanroom.txt"), "w", encoding="utf-8") as f:
        f.write(out)
    line = [l for l in out.splitlines() if "VERDICT" in l]
    return line[-1].strip() if line else "no verdict"


def report():
    lines = ["AwazSetu — final delivery report",
             time.strftime("generated %Y-%m-%d %H:%M:%S"), "=" * 64, ""]
    for state, name, detail in RESULTS:
        lines.append(f"[{state:4}] {name}\n        {detail}")
    lines += ["", "=" * 64, "Artefacts in dist/:"]
    for f in sorted(os.listdir(DIST)):
        p = os.path.join(DIST, f)
        sz = (os.path.getsize(p) if os.path.isfile(p)
              else sum(os.path.getsize(os.path.join(r, x))
                       for r, _d, fs in os.walk(p) for x in fs
                       if os.path.exists(os.path.join(r, x))))
        lines.append(f"  {sz/1e9:8.2f} GB  {f}")
    txt = "\n".join(lines)
    with open(os.path.join(DIST, "FINAL_REPORT.txt"), "w", encoding="utf-8") as f:
        f.write(txt)
    print("\n" + txt, flush=True)
    return "written"


def main():
    os.makedirs(DIST, exist_ok=True)
    log("########## finalize_delivery starting ##########")
    step("wait for voiceovers", wait_for_dubs)
    step("repair items that lost segments", repair_lost_segments)
    step("reclaim disk", free_disk)
    step("build LITE package", lambda: build_pkg("lite"))
    step("build FULL package", lambda: build_pkg("full"))
    step("zip + split LITE", zip_lite)
    step("regenerate Documentation Pack", docpack)
    step("delivery gate", gate)
    step("clean-room test", cleanroom)
    step("final report", report)
    bad = [r for r in RESULTS if r[0] == "FAIL"]
    log(f"########## finalize_delivery done: {len(RESULTS)-len(bad)} ok, "
        f"{len(bad)} failed ##########")
    print("FINALIZE_DONE", flush=True)
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
