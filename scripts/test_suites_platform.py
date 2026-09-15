"""AwazSetu — acceptance suites for the platform and media claims.

Imported by test_e2e.py as the `platform` and `media` suites. These back the claims
the Documentation Pack makes about the zero-install package: that FFmpeg resolves
without PATH, that the embedded interpreter has every dependency, that the assistant
actually answers rather than merely loading, and that Odia and audio-only sources are
genuinely covered rather than merely declared.
"""
from __future__ import annotations
import os
import sys
import time
import subprocess

def _t():
    """Resolve test_e2e lazily (it imports this module, so a top-level import cycles).

    Prefer __main__: running `python scripts/test_e2e.py` executes that file as
    `__main__`, and a plain `import test_e2e` then loads a SECOND copy with its own
    RESULTS list. Results recorded here would land in the copy while the reporter read
    the original — which is exactly how a full run came out as "0/0 passed".
    """
    main = sys.modules.get("__main__")
    if main is not None and hasattr(main, "RESULTS") and hasattr(main, "rec"):
        return main
    import test_e2e
    return test_e2e


def suite_platform(ms):
    """The zero-install claims — what makes the package runnable on a bare PC."""
    T = _t()
    print("\n== platform ==")

    # 1) bundled FFmpeg must resolve WITHOUT any PATH entry
    t = time.time()
    try:
        import config
        exe = config.ffmpeg_exe()
        r = subprocess.run([exe, "-version"], capture_output=True, text=True, timeout=30)
        bundled = os.path.isabs(exe) and "runtime" in exe
        ver = (r.stdout or "").splitlines()[0][:44] if r.stdout else ""
        T.rec("platform", "ffmpeg_resolves", "-", r.returncode == 0,
              f"{'bundled' if bundled else 'system'}: {ver}", time.time() - t)
    except Exception as ex:
        T.rec("platform", "ffmpeg_resolves", "-", False, repr(ex), time.time() - t)

    # 2) the embedded interpreter must import every dependency on its own
    t = time.time()
    try:
        py = os.path.join(T.REPO, "runtime", "python", "python.exe")
        ok, detail = os.path.exists(py), "runtime/python/python.exe missing"
        if ok:
            probe = ("import torch,transformers,ctranslate2,faster_whisper,flask,"
                     "llama_cpp,soundfile,sentencepiece,rank_bm25,numpy,psutil;"
                     "import sys;print(sys.version.split()[0], torch.__version__)")
            r = subprocess.run([py, "-c", probe], capture_output=True, text=True,
                               timeout=600)
            ok = r.returncode == 0
            detail = (r.stdout or r.stderr).strip().splitlines()[-1][:120] if (r.stdout or r.stderr) else ""
        T.rec("platform", "embedded_runtime", "-", ok, detail, time.time() - t)
    except Exception as ex:
        T.rec("platform", "embedded_runtime", "-", False, repr(ex), time.time() - t)

    # 3) the assistant must ANSWER, not merely load. A model that loads and returns
    #    nothing is still a broken feature.
    t = time.time()
    try:
        import llm
        backend = llm.backend()
        name = (llm.available_models() or [None])[0]
        out = ""
        if name:
            out = llm.call(name, "Answer only from the text. Be brief.",
                           "TEXT: The shed holds 12 goats.\n\nQ: How many goats?")
            llm.unload()
        T.rec("platform", "llm_answers", "-", "12" in out,
              f"backend={backend} model={name} -> {out[:60]!r}", time.time() - t)
    except Exception as ex:
        T.rec("platform", "llm_answers", "-", False, repr(ex), time.time() - t)

    # 4) offline must be ENFORCED, not merely documented
    t = time.time()
    flag = os.environ.get("HF_HUB_OFFLINE")
    T.rec("platform", "offline_enforced", "-", flag == "1",
          f"HF_HUB_OFFLINE={flag}", time.time() - t)

    # 5) the Model Garden must cover every task, and every language for MT and TTS
    t = time.time()
    try:
        import garden
        g = garden.overview()
        tasks = {r["task"] for r in g["catalog"]}
        covered = all(any(r["q"].get(L) for r in g["catalog"] if r["task"] == task)
                      for task in ("mt", "tts") for L in T.LANGS)
        ok = tasks == {"asr", "mt", "tts", "llm"} and covered and bool(g["presets"])
        T.rec("platform", "garden_catalog", "-", ok,
              f"{len(g['catalog'])} models, tasks={sorted(tasks)}, "
              f"tier={g['hardware']['tier']}, presets={len(g['presets'])}", time.time() - t)
    except Exception as ex:
        T.rec("platform", "garden_catalog", "-", False, repr(ex), time.time() - t)

    # 6) a preset must never be offered when its models are absent
    t = time.time()
    try:
        import garden
        have = garden.installed_ids()
        wrong = []
        for k, p in garden.overview()["presets"].items():
            need = {garden.PRESETS[k]["settings"][x]
                    for x in ("asr_model", "mic_model", "translate_engine", "chat_llm")}
            truly_available = need <= have
            if p["available"] != truly_available:
                wrong.append(k)
        T.rec("platform", "presets_honest", "-", not wrong,
              "every preset's availability matches what is installed" if not wrong
              else f"misreported: {wrong}", time.time() - t)
    except Exception as ex:
        T.rec("platform", "presets_honest", "-", False, repr(ex), time.time() - t)

    # 7) Odia must never be offered as a transcription source
    t = time.time()
    try:
        from langs import can_transcribe
        T.rec("platform", "odia_not_a_source", "or", not can_transcribe("or"),
              "langs.py records Odia as target-only; no ASR model claims to read it",
              time.time() - t)
    except Exception as ex:
        T.rec("platform", "odia_not_a_source", "or", False, repr(ex), time.time() - t)


def suite_media(ms):
    """Audio-only sources and Odia output — the two newest capabilities."""
    T = _t()
    print("\n== media ==")

    aud = [m for m in ms if m.get("kind") == "audio"]
    vid = [m for m in ms if m.get("kind") != "audio"]
    T.rec("media", "audio_sources_processed", "-", bool(aud),
          f"{len(aud)} audio item(s), {len(vid)} video item(s)")

    # every manifest must point at a real source container, never at the 16 kHz
    # extraction — treating audio.wav as the source once corrupted nine manifests
    bad = []
    for m in ms:
        d = os.path.join(T.WORK, m["id"])
        media = m.get("media", "")
        if not media or media == "audio.wav" or not os.path.exists(os.path.join(d, media)):
            bad.append(f"{m['id'][:8]}:{media!r}")
    T.rec("media", "source_file_present", "-", not bad,
          "every manifest points at a real source container" if not bad
          else f"broken: {bad}")

    withor = [m for m in ms if "or" in m.get("langs", [])]
    if withor:
        subs = [m for m in withor
                if os.path.exists(os.path.join(T.WORK, m["id"], "subs.or.vtt"))]
        T.rec("media", "odia_subtitles", "or", len(subs) == len(withor),
              f"{len(subs)}/{len(withor)} items with an Odia target have an Odia track")
        dubs = [m for m in withor
                if os.path.exists(os.path.join(T.WORK, m["id"], "dub.or.wav"))
                and os.path.getsize(os.path.join(T.WORK, m["id"], "dub.or.wav")) > 10000]
        T.rec("media", "odia_voiceover", "or", len(dubs) == len(withor),
              f"{len(dubs)}/{len(withor)} items have an audible Odia voiceover")
    else:
        T.rec("media", "odia_subtitles", "or", False, "no item targets Odia")

    # the library must not contain an item that would render as a blank player
    broken = []
    for m in ms:
        d = os.path.join(T.WORK, m["id"])
        tracks = [f for f in os.listdir(d) if f.startswith("subs.") and f.endswith(".vtt")]
        if not tracks:
            broken.append(m["id"][:8])
    T.rec("media", "no_subtitleless_items", "-", not broken,
          "every item has at least one subtitle track" if not broken
          else f"items with no subtitles at all: {broken}")
