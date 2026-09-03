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

from asr import (extract_audio, WhisperASR, transcript_confidence,
                 sanitize_segments)
from mt import get_mt
from subs import write_vtt
from langs import DEFAULT_TARGETS

# Audio-only sources are fully supported: the pipeline only ever needed the audio
# track, so the sole difference is that the player renders an <audio> element.
AUDIO_EXT = {".mp3", ".wav", ".m4a", ".aac", ".ogg", ".oga", ".opus",
             ".flac", ".wma", ".amr", ".aiff", ".alac"}


def video_id(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()[:16]


def process_video(video_path: str, work_root: str, src_lang: str | None = None,
                  targets=None, asr=None, mt=None, log=print) -> dict:
    """Process one video end to end.

    `src_lang=None` AUTO-DETECTS the spoken language. Never assume: decoding
    Marathi audio with language="hi" yields fluent-looking Devanagari nonsense,
    which then propagates into the subtitles, the dub and the chat answers.
    """
    targets = tuple(targets) if targets else DEFAULT_TARGETS
    vid = video_id(video_path)
    work = os.path.join(work_root, vid)
    os.makedirs(work, exist_ok=True)
    # Keep the source in its own container: an .mp3 re-labelled .mp4 will not play.
    ext = os.path.splitext(video_path)[1].lower() or ".mp4"
    kind = "audio" if ext in AUDIO_EXT else "video"
    media_name = ("audio" if kind == "audio" else "video") + ext
    if not any(f.startswith(("video.", "audio.")) and f != "audio.wav"
               for f in os.listdir(work)):
        try:
            import shutil
            shutil.copy(video_path, os.path.join(work, media_name))
        except Exception:
            pass
    else:
        for f in sorted(os.listdir(work)):
            if f.startswith(("video.", "audio.")) and f != "audio.wav":
                media_name = f
                kind = "audio" if f.startswith("audio.") else "video"
                break
    wav = os.path.join(work, "audio.wav")

    log(f"[1/4] extract audio -> {wav}")
    extract_audio(video_path, wav)

    raw = os.path.join(work, "transcript.raw.json")
    if os.path.exists(raw):
        with open(raw, encoding="utf-8") as f:
            cached = json.load(f)
        segs, detected = cached["segments"], cached["lang"]
        conf = cached.get("confidence") or transcript_confidence(segs)
        src_lang = src_lang or detected
        log(f"[2/4] transcript cached ({len(segs)} segs, lang={detected}) - skip ASR")
    else:
        own_asr = asr is None
        asr = asr or WhisperASR()
        if src_lang in (None, "", "auto"):
            det, prob = asr.detect_language(wav)
            log(f"      language auto-detected: {det} (p={prob:.2f})")
            src_lang = det
        log(f"[2/4] transcribe (whisper {asr.size} / {asr.device}, lang={src_lang}) ...")
        t0 = time.time()
        segs, detected = asr.transcribe(wav, language=src_lang)
        conf = transcript_confidence(segs)
        log(f"      {len(segs)} segments, lang={detected}, {time.time() - t0:.1f}s, "
            f"mean_logprob={conf['mean_logprob']} low_conf={conf['low_conf_ratio']:.0%} "
            f"usable={conf['usable']}")
        if not conf["usable"]:
            log("      WARNING: ASR confidence is low — transcript may be unreliable. "
                "Consider a larger model (Settings -> ASR model).")
        with open(raw, "w", encoding="utf-8") as f:
            json.dump({"lang": detected, "segments": segs, "confidence": conf},
                      f, ensure_ascii=False)
        if own_asr:  # STAGED LOADING: free ASR before MT so peak RAM stays flat
            del asr
            gc.collect()
            asr = None
    # Drop ASR garbage BEFORE translating. Whisper can emit a degenerate loop
    # (e.g. "ব" x60) that scores high confidence; NLLB then invents fluent English
    # from it ("I have not seen any of you..."), which reaches the user as fact.
    segs, dropped = sanitize_segments(segs, src_lang)
    if dropped:
        log(f"      sanitiser dropped {len(dropped)} garbage segment(s): "
            + ", ".join(sorted({d['reason'] for d in dropped})))
    conf = transcript_confidence(segs)

    try:  # domain glossary: fix common source-language ASR mishears before translating
        from glossary import correct_source
        for s in segs:
            s["text"] = correct_source(s["text"], src_lang)
    except Exception:
        pass
    for s in segs:
        s["t"] = {src_lang: s["text"]}

    mt = mt or get_mt()
    tgts = [t for t in targets if t != src_lang]  # src is now known/detected
    src_texts = [s["text"] for s in segs]
    log(f"[3/4] translate {src_lang}->{tgts} ({mt.NAME}) ...")
    t0 = time.time()
    if hasattr(mt, "translate_multi"):
        res = mt.translate_multi(src_texts, src_lang, tgts)
    else:
        res = {tgt: mt.translate(src_texts, src=src_lang, tgt=tgt) for tgt in tgts}
    try:
        from glossary import correct_target
    except Exception:
        correct_target = lambda t, L: t
    for tgt in tgts:
        for s, tr in zip(segs, res.get(tgt, [])):
            s["t"][tgt] = correct_target(tr, tgt)
    log(f"      {time.time() - t0:.1f}s")

    all_langs = [src_lang] + tgts
    vtts = {}
    for L in all_langs:
        p = os.path.join(work, f"subs.{L}.vtt")
        write_vtt(segs, p, L)
        vtts[L] = os.path.basename(p)

    # Re-processing runs against the cached work/<id>/video.mp4, so os.path.basename
    # would rewrite every title to "video.mp4". Keep the name the library already knows.
    prev_name = None
    _mp = os.path.join(work, "manifest.json")
    if os.path.exists(_mp):
        try:
            with open(_mp, encoding="utf-8") as _f:
                prev_name = json.load(_f).get("video")
        except Exception:
            prev_name = None
    disp = os.path.basename(video_path)
    if disp in ("video.mp4", media_name) and prev_name:
        disp = prev_name
    manifest = {
        "id": vid, "video": disp,
        "src_lang": src_lang, "langs": all_langs,
        "duration": segs[-1]["end"] if segs else 0.0,
        "mt_engine": mt.NAME, "vtts": vtts, "segments": segs,
        "asr_confidence": conf,
        "media": media_name, "kind": kind,
        "asr_model": os.environ.get("AWAZ_WHISPER", "small"),
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
