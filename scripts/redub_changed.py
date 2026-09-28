"""Rebuild only the voiceovers whose text has changed since they were made.

    python scripts/redub_changed.py --dry-run
    python scripts/redub_changed.py

A voiceover is stale when its manifest is newer than the .wav: the subtitle has
been corrected and the audio still says the old word. Re-processing the item
would fix it, but that also re-runs transcription and translation, which were
fine -- an hour of GPU time to change one noun.

This re-synthesises just the affected tracks. One subprocess per (item,
language), because MMS-TTS holds about a gigabyte and a crash in a native
extension takes the whole interpreter with it rather than raising.
"""
from __future__ import annotations
import os
import subprocess
import sys
import time

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
APP = os.path.join(REPO, "app")
sys.path.insert(0, APP)


def stale(folder: str, lang: str, segs) -> bool:
    """Is this voiceover older than the words it is supposed to be speaking?

    By digest when one exists, which is exact. By modification time otherwise,
    which is not: one manifest holds four languages, so correcting a single
    English line makes every one of the four .wav files look stale and would
    re-synthesise three tracks that did not change. The digest is written by
    dub_worker from now on, so that over-reporting disappears as tracks are
    rebuilt.
    """
    wav = os.path.join(folder, f"dub.{lang}.wav")
    man = os.path.join(folder, "manifest.json")
    if not os.path.exists(wav) or not os.path.exists(man):
        return False                      # nothing to refresh
    sidecar = wav + ".txt"
    if os.path.exists(sidecar):
        sys.path.insert(0, os.path.join(REPO, "app"))
        from dub_worker import text_digest
        try:
            with open(sidecar, encoding="utf-8") as f:
                return f.read().strip() != text_digest(segs, lang)
        except Exception:
            pass
    return os.path.getmtime(man) > os.path.getmtime(wav)


def main() -> None:
    dry = "--dry-run" in sys.argv
    import json
    import paths
    # --only "401.3.mp4:en,604.3.mp4:mr" restricts the run. Needed once, because
    # the tracks that predate the digest can only be judged by mtime and that
    # over-reports; after this run every rebuilt track judges itself exactly.
    only = None
    for i, a_ in enumerate(sys.argv):
        if a_ == "--only" and i + 1 < len(sys.argv):
            only = {p.strip() for p in sys.argv[i + 1].split(",") if p.strip()}

    jobs = []
    for _vid, folder in paths.list_work():
        with open(os.path.join(folder, "manifest.json"), encoding="utf-8") as f:
            m = json.load(f)
        name = m.get("video") or _vid
        segs = sorted(m["segments"], key=lambda s: s["start"])
        for lang in m.get("langs", []):
            if only is not None and f"{name}:{lang}" not in only:
                continue
            if only is not None or stale(folder, lang, segs):
                jobs.append((name, folder, lang))

    if not jobs:
        print("every voiceover is current")
        print("REDUB_DONE")
        return
    print(f"{len(jobs)} voiceover(s) are older than their transcript:")
    for name, _f, lang in jobs:
        print(f"  {name[:40]:42} {lang}")
    if dry:
        print("REDUB_DONE")
        return

    env = dict(os.environ)
    env.setdefault("HF_HOME", os.path.join(REPO, "models", "hf-cache"))
    env["HF_HUB_OFFLINE"] = "1"
    env["TRANSFORMERS_OFFLINE"] = "1"
    env["CUDA_VISIBLE_DEVICES"] = ""       # MMS-TTS on CPU; CUDA here segfaults
    env["PYTHONIOENCODING"] = "utf-8"

    ok = bad = 0
    for i, (name, folder, lang) in enumerate(jobs, 1):
        t0 = time.time()
        out = os.path.join(folder, f"dub.{lang}.wav")
        r = subprocess.run(
            [sys.executable, os.path.join(APP, "dub_worker.py"),
             os.path.join(folder, "manifest.json"), lang, out],
            capture_output=True, text=True, env=env, timeout=3600)
        if r.returncode == 0 and os.path.exists(out) and os.path.getsize(out) > 10000:
            ok += 1
            print(f"  [{i}/{len(jobs)}] {name[:34]:36} {lang}  "
                  f"{os.path.getsize(out)/1e6:5.1f} MB  {time.time()-t0:5.0f}s", flush=True)
        else:
            bad += 1
            tail = (r.stderr or "").strip().splitlines()
            print(f"  [{i}/{len(jobs)}] {name[:34]:36} {lang}  FAILED: "
                  f"{tail[-1][:90] if tail else 'no output'}", flush=True)
    print(f"\n{ok} rebuilt, {bad} failed")
    print("REDUB_DONE")


if __name__ == "__main__":
    main()
