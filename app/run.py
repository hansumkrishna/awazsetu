"""AwazSetu launcher — sets offline/CPU defaults, then serves or processes.

    python run.py                 # start the web app at http://127.0.0.1:5000
    python run.py <video.mp4>     # process a new video (transcribe + translate + subs)

Everything runs locally on CPU. Chat needs Ollama running with `qwen2.5:3b`.
"""
import os
import sys

try:  # Windows consoles default to cp1252 and choke on Devanagari / arrows
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, HERE)

# All downloaded weights live in one portable folder (the "separate downloads" dir).
# Point the HF cache here too, so whisper / MMS-TTS / IndicTrans2 load from inside the
# project and the whole thing is self-contained & relocatable.
MODELS = os.environ.get("AWAZ_MODELS_DIR") or os.path.join(REPO, "models")
if not os.path.isdir(MODELS):                      # fallback to legacy app/models
    MODELS = os.path.join(HERE, "models")
_hf = os.path.join(MODELS, "hf-cache")
if os.path.isdir(_hf):
    os.environ.setdefault("HF_HOME", _hf)
# Strict offline once models are present (set AWAZ_OFFLINE=0 to allow downloads).
if os.environ.get("AWAZ_OFFLINE", "1") == "1":
    os.environ.setdefault("HF_HUB_OFFLINE", "1")
    os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")

try:  # apply persisted operator settings (settings.json) to the env the modules read
    import config as _cfg
    _cfg.apply_to_env()
except Exception as _e:
    print("warn: could not apply settings:", _e)
os.environ.setdefault("AWAZ_DEVICE", "cpu")
os.environ.setdefault("AWAZ_CPU_THREADS", "4")
# NLLB is UNGATED and does every hi/mr/en direction -> the self-sufficient default
# (no HF login needed). IndicTrans2 is an optional higher-Indic upgrade after login.
os.environ.setdefault("AWAZ_MT", "nllb")
os.environ.setdefault("PYTHONIOENCODING", "utf-8")

# Plain local NLLB dir (real files, eviction-proof, native-path safe). Use a WINDOWS-
# style absolute path — ctranslate2's native lib can't open MSYS /c/... paths.
_local_nllb = os.path.join(MODELS, "nllb-int8")
if os.path.exists(os.path.join(_local_nllb, "model.bin")):
    os.environ.setdefault("AWAZ_NLLB_CT2_DIR", _local_nllb)
elif os.environ.get("AWAZ_OFFLINE", "1") != "1":
    try:
        from huggingface_hub import snapshot_download
        os.environ.setdefault(
            "AWAZ_NLLB_CT2_DIR",
            snapshot_download("JustFrederik/nllb-200-distilled-600M-ct2-int8"))
    except Exception as e:
        print("warn: could not locate NLLB CT2 model:", e)
else:
    print("warn: NLLB model not found in", MODELS, "— run scripts/download_models.py")

sys.path.insert(0, HERE)

if len(sys.argv) > 1:
    import json
    from pipeline import process_video, video_id
    vp = sys.argv[1]
    work_root = os.path.join(HERE, "data", "work")
    work = os.path.join(work_root, video_id(vp))
    os.makedirs(work, exist_ok=True)

    import subprocess
    from progress import Progress

    try:
        import config as _cfg
        _targets = tuple(_cfg.load().get("langs") or ("hi", "mr", "en"))
    except Exception:
        _targets = ("hi", "mr", "en")

    # Every asset the viewer consumes is built HERE, behind the progress bar:
    # transcript, translations, subtitles AND all voiceovers. Nothing is
    # synthesised at playback — only chat and voice chat run in real time.
    prog = Progress(work, langs=_targets)

    def log(msg):
        print(msg)
        for tag, key in (("[1/4]", "extract"), ("[2/4]", "asr"),
                         ("[3/4]", "mt"), ("[4/4]", "subs")):
            if tag in msg:
                for k in ("extract", "asr", "mt", "subs"):
                    if k == key:
                        break
                    prog.done(k)
                prog.start(key)

    try:
        m = process_video(vp, work_root, targets=_targets, log=log)
        for k in ("extract", "asr", "mt", "subs"):
            prog.done(k)

        # --- voiceovers, precomputed one language at a time -------------------
        langs = [L for L in m.get("langs", []) if L in ("hi", "mr", "en")]
        prog.add_dubs(langs)
        worker = os.path.join(HERE, "dub_worker.py")
        manifest = os.path.join(work, "manifest.json")
        for L in langs:
            out = os.path.join(work, f"dub.{L}.wav")
            if os.path.exists(out) and os.path.getsize(out) > 10000:
                prog.done(f"dub:{L}")
                continue
            prog.start(f"dub:{L}")
            try:
                subprocess.run([sys.executable, worker, manifest, L, out],
                               check=True, timeout=2400)
                prog.done(f"dub:{L}")
            except Exception as e:
                print(f"warn: dub {L} failed: {e}")
                prog.fail(f"dub:{L}", "not available")
        prog.finish()
    except Exception as e:
        prog.error(str(e))
        raise
    print("done:", m["id"], "langs:", m["langs"], "engine:", m["mt_engine"])
else:
    import server
    port = int(os.environ.get("AWAZ_PORT", "5000"))
    print(f"AwazSetu → http://127.0.0.1:{port}")
    server.app.run(host="127.0.0.1", port=port, threaded=True)
