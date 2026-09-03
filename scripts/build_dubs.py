"""Build any missing voiceovers for already-processed videos.

Playback never synthesises audio, so every language offered in the player must have
a dub.<lang>.wav on disk. Videos processed before that rule need a backfill; this
does it without touching the transcript or translations.

    python scripts/build_dubs.py            # all videos, all their languages
    python scripts/build_dubs.py <id> ...   # only these work-folder ids
"""
import os
import sys
import glob
import json
import time
import subprocess

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault("HF_HOME", os.path.join(REPO, "models", "hf-cache"))
os.environ.setdefault("HF_HUB_OFFLINE", "1")
os.environ["CUDA_VISIBLE_DEVICES"] = ""      # MMS-TTS runs on CPU
APP = os.path.join(REPO, "app")
WORK = os.path.join(APP, "data", "work")
MIN_BYTES = 10000


def main():
    wanted = set(sys.argv[1:])
    todo = []
    for mp in sorted(glob.glob(os.path.join(WORK, "*", "manifest.json"))):
        d = os.path.dirname(mp)
        vid = os.path.basename(d)
        if wanted and vid not in wanted:
            continue
        m = json.load(open(mp, encoding="utf-8"))
        for L in m.get("langs", []):
            out = os.path.join(d, f"dub.{L}.wav")
            if not (os.path.exists(out) and os.path.getsize(out) > MIN_BYTES):
                todo.append((vid, m.get("video", vid), L, mp, out))

    if not todo:
        print("all voiceovers already present")
        return
    print(f"{len(todo)} voiceover(s) to build", flush=True)
    worker = os.path.join(APP, "dub_worker.py")
    ok = fail = 0
    for i, (vid, name, L, mp, out) in enumerate(todo, 1):
        t0 = time.time()
        print(f"[{i}/{len(todo)}] {name[:34]:36} {L} ...", end="", flush=True)
        try:
            subprocess.run([sys.executable, worker, mp, L, out],
                           check=True, timeout=2400, capture_output=True)
            good = os.path.exists(out) and os.path.getsize(out) > MIN_BYTES
            ok, fail = (ok + 1, fail) if good else (ok, fail + 1)
            print(f" {'OK' if good else 'EMPTY'} {time.time()-t0:.0f}s", flush=True)
        except Exception as e:
            fail += 1
            print(f" FAILED {type(e).__name__}", flush=True)
    print(f"\nDUBS_DONE ok={ok} failed={fail}", flush=True)


if __name__ == "__main__":
    main()
