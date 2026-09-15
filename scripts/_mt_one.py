"""Translate + subtitle ONE already-transcribed item. Spawned by reprocess_all.py.

    python scripts/_mt_one.py <work_id> <src_lang>

Runs as its own process so several items can translate at once: IndicTrans2 is
CPU-bound and single-item translation leaves most cores idle. `process_video` finds
the cached large-v3 transcript and skips ASR entirely, so no GPU is touched here.
"""
from __future__ import annotations
import os
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
APP = os.path.join(REPO, "app")
sys.path.insert(0, APP)

os.environ.setdefault("HF_HOME", os.path.join(REPO, "models", "hf-cache"))
os.environ.setdefault("HF_HUB_OFFLINE", "1")
os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")
os.environ.setdefault("AWAZ_MT", "indictrans2")
os.environ.setdefault("PYTHONIOENCODING", "utf-8")

WORK = os.path.join(APP, "data", "work")
TARGETS = ("hi", "mr", "en", "or")


def main():
    vid, src = sys.argv[1], sys.argv[2]
    d = os.path.join(WORK, vid)
    media = None
    for f in sorted(os.listdir(d)):
        if f.startswith(("video.", "audio.")) and f != "audio.wav":
            media = os.path.join(d, f)
            break
    if not media:
        raise SystemExit(f"{vid}: no source media")

    from pipeline import process_video
    m = process_video(media, WORK, src_lang=src, targets=TARGETS,
                      log=lambda s: print(f"  [{vid[:8]}] {s}", flush=True))
    print(f"MT_OK {vid} segs={len(m['segments'])} langs={m['langs']}", flush=True)


if __name__ == "__main__":
    main()
