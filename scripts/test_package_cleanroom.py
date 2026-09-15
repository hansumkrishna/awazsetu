"""Run a BUILT package as if the machine had nothing installed.

    python scripts/test_package_cleanroom.py dist/awazsetu-lite

This is the claim that matters most, so it is tested rather than asserted. The package's
own interpreter is launched with a deliberately hostile environment:

  * no inherited variables at all — no PATH to a system Python, no HF_HOME, no
    AWAZ_* left over from development;
  * PATH reduced to the Windows system directories, so a system FFmpeg or Python
    cannot be found even by accident;
  * paths resolved only from the package folder.

If it passes here, it passes on a freshly imaged laptop. If it only passes with the
developer's environment inherited, the package is not self-contained and the whole
zero-install claim is false.
"""
from __future__ import annotations
import os
import sys
import subprocess

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def run(pkg: str) -> int:
    pkg = os.path.abspath(pkg)
    py = os.path.join(pkg, "runtime", "python", "python.exe")
    if not os.path.exists(py):
        print(f"FAIL: {py} does not exist — the package has no interpreter")
        return 1

    windir = os.environ.get("SystemRoot", r"C:\Windows")
    env = {
        # Deliberately minimal. Anything the package needs, the package must provide.
        "SystemRoot": windir,
        "windir": windir,
        "PATH": os.pathsep.join([os.path.join(pkg, "runtime", "bin"),
                                 os.path.join(windir, "System32"), windir]),
        "TEMP": os.environ.get("TEMP", os.path.join(windir, "Temp")),
        "TMP": os.environ.get("TEMP", os.path.join(windir, "Temp")),
        "PYTHONIOENCODING": "utf-8",
        # exactly what AwazSetu.bat sets, and nothing else
        "AWAZ_MODELS_DIR": os.path.join(pkg, "models"),
        "AWAZ_BIN_DIR": os.path.join(pkg, "runtime", "bin"),
        "AWAZ_LLM_DIR": os.path.join(pkg, "models", "llm"),
        "HF_HOME": os.path.join(pkg, "models", "hf-cache"),
        "HF_HUB_OFFLINE": "1",
        "TRANSFORMERS_OFFLINE": "1",
        "AWAZ_OFFLINE": "1",
    }

    print("=" * 78)
    print(f" CLEAN ROOM: {os.path.basename(pkg)}")
    print(" No inherited environment. No system Python or FFmpeg reachable on PATH.")
    print("=" * 78)

    doctor = os.path.join(pkg, "scripts", "doctor.py")
    r = subprocess.run([py, doctor], env=env, cwd=pkg, capture_output=True,
                       text=True, encoding="utf-8", errors="replace", timeout=1800)
    out = (r.stdout or "") + (r.stderr or "")
    print(out.strip())

    # the app must also be importable and able to serve a page, not merely pass checks
    probe = (
        "import sys, os;"
        "sys.path.insert(0, os.path.join(os.getcwd(), 'app'));"
        "import server;"
        "c = server.app.test_client();"
        "rs = [(p, c.get(p).status_code) for p in ('/', '/settings', '/garden', '/api/garden')];"
        "print('PAGES', rs);"
        "assert all(s == 200 for _p, s in rs), 'a page did not return 200'"
    )
    r2 = subprocess.run([py, "-c", probe], env=env, cwd=pkg, capture_output=True,
                        text=True, encoding="utf-8", errors="replace", timeout=900)
    pages = ((r2.stdout or "") + (r2.stderr or "")).strip()
    print("\n" + "-" * 78)
    print(pages[-500:] if pages else "(no output)")

    ok_doctor = "0 failures" in out
    ok_pages = r2.returncode == 0 and "PAGES" in pages
    print("-" * 78)
    print(f" preflight : {'PASS' if ok_doctor else 'FAIL'}")
    print(f" web pages : {'PASS' if ok_pages else 'FAIL'}")
    print(f" VERDICT   : {'self-contained' if (ok_doctor and ok_pages) else 'NOT self-contained'}")
    print("=" * 78)
    return 0 if (ok_doctor and ok_pages) else 1


if __name__ == "__main__":
    pkgs = sys.argv[1:] or [os.path.join(REPO, "dist", "awazsetu-lite")]
    sys.exit(max(run(p) for p in pkgs))
