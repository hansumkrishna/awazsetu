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

    def _status(stage, pct):
        try:
            with open(os.path.join(work, "status.json"), "w", encoding="utf-8") as f:
                json.dump({"stage": stage, "pct": pct}, f)
        except Exception:
            pass

    def log(msg):
        print(msg)
        for tag, st, pct in (("[1/4]", "Extracting audio", 8),
                             ("[2/4]", "Transcribing (ASR)", 20),
                             ("[3/4]", "Translating", 65),
                             ("[4/4]", "Finalizing subtitles", 95)):
            if tag in msg:
                _status(st, pct)

    _status("Queued", 2)
    m = process_video(vp, work_root, log=log)
    _status("done", 100)
    print("done:", m["id"], "langs:", m["langs"], "engine:", m["mt_engine"])
else:
    import server
    print("AwazSetu → http://127.0.0.1:5000")
    server.app.run(host="127.0.0.1", port=5000, threaded=True)
