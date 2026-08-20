"""AwazSetu — core pipeline: video -> transcript -> hi/mr/en switchable subtitles.

    python pipeline.py [video_path]

Writes to app/data/work/<id>/: audio.wav, subs.<lang>.vtt (one per language),
manifest.json (segments with per-language text + timings). This manifest feeds
the player (Phase 2), chat index (Phase 3) and dub (Phase 4).
"""
from __future__ import annotations
import os
import sys
import gc
import json
import time
import hashlib

from asr import extract_audio, WhisperASR
from mt import get_mt
from subs import write_vtt


def video_id(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()[:16]


def process_video(video_path: str, work_root: str, src_lang: str = "hi",
                  targets=("mr", "en"), asr=None, mt=None, log=print) -> dict:
    vid = video_id(video_path)
    work = os.path.join(work_root, vid)
    os.makedirs(work, exist_ok=True)
    if not os.path.exists(os.path.join(work, "video.mp4")):
        try:
            import shutil
            shutil.copy(video_path, os.path.join(work, "video.mp4"))
        except Exception:
            pass
    wav = os.path.join(work, "audio.wav")

    log(f"[1/4] extract audio -> {wav}")
    extract_audio(video_path, wav)

    raw = os.path.join(work, "transcript.raw.json")
    if os.path.exists(raw):
        with open(raw, encoding="utf-8") as f:
            cached = json.load(f)
        segs, detected = cached["segments"], cached["lang"]
        log(f"[2/4] transcript cached ({len(segs)} segs, lang={detected}) — skip ASR")
    else:
        own_asr = asr is None
        asr = asr or WhisperASR()
        log(f"[2/4] transcribe (whisper {asr.size} / {asr.device}) ...")
        t0 = time.time()
        segs, detected = asr.transcribe(wav, language=src_lang)
        log(f"      {len(segs)} segments, lang={detected}, {time.time() - t0:.1f}s")
        with open(raw, "w", encoding="utf-8") as f:
            json.dump({"lang": detected, "segments": segs}, f, ensure_ascii=False)
        if own_asr:  # STAGED LOADING: free ASR before MT so peak RAM stays flat
            del asr
            gc.collect()
            asr = None
    try:  # domain glossary: fix common source-language ASR mishears before translating
        from glossary import correct_source
        for s in segs:
            s["text"] = correct_source(s["text"], src_lang)
    except Exception:
        pass
    for s in segs:
        s["t"] = {src_lang: s["text"]}

    mt = mt or get_mt()
    tgts = [t for t in targets if t != src_lang]
    src_texts = [s["text"] for s in segs]
    log(f"[3/4] translate {src_lang}->{tgts} ({mt.NAME}) ...")
    t0 = time.time()
    if hasattr(mt, "translate_multi"):
        res = mt.translate_multi(src_texts, src_lang, tgts)
    else:
        res = {tgt: mt.translate(src_texts, src=src_lang, tgt=tgt) for tgt in tgts}
    for tgt in tgts:
        for s, tr in zip(segs, res.get(tgt, [])):
            s["t"][tgt] = tr
    log(f"      {time.time() - t0:.1f}s")

    all_langs = [src_lang] + tgts
    vtts = {}
    for L in all_langs:
        p = os.path.join(work, f"subs.{L}.vtt")
        write_vtt(segs, p, L)
        vtts[L] = os.path.basename(p)

    manifest = {
        "id": vid, "video": os.path.basename(video_path),
        "src_lang": src_lang, "langs": all_langs,
        "duration": segs[-1]["end"] if segs else 0.0,
        "mt_engine": mt.NAME, "vtts": vtts, "segments": segs,
    }
    with open(os.path.join(work, "manifest.json"), "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=1)
    log(f"[4/4] wrote {len(all_langs)} VTTs + manifest -> {work}")
    return manifest


if __name__ == "__main__":
    if len(sys.argv) < 2:
        raise SystemExit("usage: python pipeline.py <video_path>")
    vp = sys.argv[1]
    work = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "work")
    m = process_video(vp, work)
    print("\n=== SAMPLE (first 4 segments) ===")
    for s in m["segments"][:4]:
        print(f"[{s['start']:6.1f}-{s['end']:6.1f}]")
        for L in m["langs"]:
            print(f"    {L}: {s['t'][L]}")
    print(f"\nid={m['id']}  langs={m['langs']}  engine={m['mt_engine']}")
