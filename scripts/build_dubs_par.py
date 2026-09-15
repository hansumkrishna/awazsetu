"""Rebuild voiceovers for the whole library, several at a time.

    python scripts/build_dubs_par.py                # only missing or stale voiceovers
    python scripts/build_dubs_par.py --force        # rebuild every one
    python scripts/build_dubs_par.py --workers=4

A voiceover is STALE when it is older than the manifest that produced it. That matters
after a re-transcription: the audio still plays, so nothing looks broken, but it is
speaking the previous transcript. Comparing modification times catches it.

MMS-TTS is CPU-only by design (dub_worker.py hides CUDA), so this phase can run several
items at once without contending with anything on the GPU. Each voice is roughly 400 MB
resident, which is what bounds the worker count.
"""
from __future__ import annotations
import os
import sys
import json
import time
import subprocess

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
APP = os.path.join(REPO, "app")
WORK = os.path.join(APP, "data", "work")
sys.path.insert(0, APP)

os.environ.setdefault("HF_HOME", os.path.join(REPO, "models", "hf-cache"))
os.environ.setdefault("HF_HUB_OFFLINE", "1")
os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")
os.environ.setdefault("PYTHONIOENCODING", "utf-8")

LOG = os.path.join(REPO, "dist", "dubs.log")
MIN_BYTES = 10_000


def log(msg, fh=None):
    line = f"[{time.strftime('%H:%M:%S')}] {msg}"
    print(line, flush=True)
    if fh:
        fh.write(line + "\n")
        fh.flush()


def jobs(force: bool):
    """(work_id, lang, out_path, title) for every voiceover that needs building."""
    from langs import MMS
    out = []
    for d in sorted(os.listdir(WORK)):
        p = os.path.join(WORK, d)
        mf = os.path.join(p, "manifest.json")
        if not os.path.isdir(p) or not os.path.exists(mf):
            continue
        try:
            m = json.load(open(mf, encoding="utf-8"))
        except Exception:
            continue
        m_mtime = os.path.getmtime(mf)
        for L in m.get("langs", []):
            if L not in MMS:
                continue
            wav = os.path.join(p, f"dub.{L}.wav")
            need = True
            if os.path.exists(wav) and os.path.getsize(wav) > MIN_BYTES:
                # stale = built before the manifest it should be speaking
                need = force or os.path.getmtime(wav) < m_mtime
            if need:
                out.append((d, L, wav, m.get("video", d)))
    return out


def main():
    force = "--force" in sys.argv
    workers = 4
    for a in sys.argv:
        if a.startswith("--workers"):
            workers = int(a.split("=")[1]) if "=" in a else 4

    todo = jobs(force)
    os.makedirs(os.path.dirname(LOG), exist_ok=True)
    fh = open(LOG, "a", encoding="utf-8")
    if not todo:
        log("every voiceover is present and current", fh)
        print("DUBS_DONE")
        return
    log(f"=== {len(todo)} voiceover(s) to build, {workers} parallel worker(s)"
        f"{' [forced]' if force else ''} ===", fh)

    worker = os.path.join(APP, "dub_worker.py")
    env = dict(os.environ)
    # Each VITS process is small; splitting threads keeps them from fighting.
    env["AWAZ_CPU_THREADS"] = str(max(2, ((os.cpu_count() or 8) - 2) // max(1, workers)))

    queue, running = list(todo), []
    done = fails = 0
    t_all = time.time()
    while queue or running:
        while queue and len(running) < workers:
            vid, L, wav, title = queue.pop(0)
            manifest = os.path.join(WORK, vid, "manifest.json")
            p = subprocess.Popen([sys.executable, worker, manifest, L, wav],
                                 stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                 text=True, encoding="utf-8", errors="replace", env=env)
            running.append((p, vid, L, title, time.time()))
        time.sleep(2)
        for rec in running[:]:
            p, vid, L, title, t0 = rec
            if p.poll() is None:
                continue
            running.remove(rec)
            out = (p.stdout.read() or "").strip() if p.stdout else ""
            wav = os.path.join(WORK, vid, f"dub.{L}.wav")
            ok = (p.returncode == 0 and os.path.exists(wav)
                  and os.path.getsize(wav) > MIN_BYTES)
            if ok:
                done += 1
                log(f"  [{done + fails}/{len(todo)}] {L} {title[:34]}: "
                    f"{os.path.getsize(wav)/1e6:.1f} MB in {time.time()-t0:.0f}s", fh)
            else:
                fails += 1
                log(f"  [{done + fails}/{len(todo)}] {L} {title[:34]} FAILED "
                    f"rc={p.returncode} :: {out[-260:]}", fh)
    log(f"=== {done} built, {fails} failed in {(time.time()-t_all)/60:.1f} min ===", fh)
    fh.close()
    print("DUBS_DONE")


if __name__ == "__main__":
    main()
