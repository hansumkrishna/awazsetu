"""Transcribe ONE item and cache the result. Spawned per item by reprocess_all.py.

    python scripts/_asr_one.py <work_id> <src_lang>

One process per item is deliberate. Running every item through a single long-lived
CUDA context exhausted the 4 GB card after two items:

    CUDA failed with error out of memory
    parallel_for failed: cudaErrorInvalidDevice: invalid device ordinal

— and once the context is destroyed every later item fails too, so a single bad
allocation wedges the whole batch. A fresh process per item costs ~7 s of model load
and makes each item independently recoverable.

On CUDA OOM it retries on CPU rather than losing the item.
"""
from __future__ import annotations
import os
import sys
import json
import time

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
APP = os.path.join(REPO, "app")
sys.path.insert(0, APP)

os.environ.setdefault("HF_HOME", os.path.join(REPO, "models", "hf-cache"))
os.environ.setdefault("HF_HUB_OFFLINE", "1")
os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")
os.environ.setdefault("PYTHONIOENCODING", "utf-8")

WORK = os.path.join(APP, "data", "work")


def run(vid: str, src: str, device: str) -> dict:
    os.environ["AWAZ_DEVICE"] = device
    if device == "cpu":
        os.environ["AWAZ_COMPUTE"] = "int8"
    from asr import WhisperASR, extract_audio, transcript_confidence
    d = os.path.join(WORK, vid)
    media = None
    for f in sorted(os.listdir(d)):
        if f.startswith(("video.", "audio.")) and f != "audio.wav":
            media = os.path.join(d, f)
            break
    if not media:
        raise SystemExit(f"{vid}: no source media")
    wav = os.path.join(d, "audio.wav")
    if not os.path.exists(wav) or os.path.getsize(wav) < 1000:
        extract_audio(media, wav)

    t0 = time.time()
    asr = WhisperASR()
    segs, detected = asr.transcribe(wav, language=(src if src != "auto" else None))
    conf = transcript_confidence(segs)
    with open(os.path.join(d, "transcript.raw.json"), "w", encoding="utf-8") as f:
        json.dump({"lang": detected, "segments": segs, "confidence": conf,
                   "asr_model": asr.size}, f, ensure_ascii=False)
    el = time.time() - t0
    dur = segs[-1]["end"] if segs else 0
    print(f"ASR_OK {vid} model={asr.size} dev={asr.device} segs={len(segs)} "
          f"dur={dur:.0f}s time={el:.0f}s rtf={el/max(dur,1):.2f} "
          f"logprob={conf['mean_logprob']}", flush=True)
    return conf


def main():
    vid, src = sys.argv[1], sys.argv[2]
    device = os.environ.get("AWAZ_DEVICE", "cuda")
    try:
        run(vid, src, device)
    except Exception as e:
        msg = str(e)
        if device == "cuda" and ("out of memory" in msg.lower() or "cuda" in msg.lower()):
            print(f"ASR_RETRY_CPU {vid}: {type(e).__name__}: {msg[:120]}", flush=True)
            run(vid, src, "cpu")
        else:
            raise


if __name__ == "__main__":
    main()
