"""Build the two distributable packages.

    python scripts/package.py lite      # ~4 GB  - code + only the models the defaults use
    python scripts/package.py full      # ~19 GB - everything, incl. installers & spare models
    python scripts/package.py both
    python scripts/package.py lite --zip

LITE is sized for an internet transfer. It ships exactly the models the shipped
settings select (whisper medium for video, small for the mic, NLLB, the three MMS
voices) and nothing else, so no feature can point at a model that is not there.

FULL is the USB build: every model, the offline installer kit (Python, Ollama,
FFmpeg, wheels, Ollama blobs) and the spare ASR/MT engines.

Both include the processed videos, so the app is usable the moment it starts.
"""
from __future__ import annotations
import os
import sys
import json
import shutil
import time

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DIST = os.path.join(REPO, "dist")

# Models the default settings actually use. Everything else is optional extra.
LITE_HUB = [
    "models--Systran--faster-whisper-medium",   # asr_model default
    "models--Systran--faster-whisper-small",    # mic_model default
    "models--facebook--mms-tts-hin",
    "models--facebook--mms-tts-mar",
    "models--facebook--mms-tts-eng",
    "models--facebook--nllb-200-distilled-600M",  # tokenizer for the CT2 engine
]
CODE = ["app", "scripts", "docs", "requirements.txt", "README.md",
        ".gitignore", ".gitattributes", "generate_deck.py"]
# Regenerated automatically; no need to ship them.
WORK_SKIP_EXACT = {"audio.wav", "status.json", "voice_in.webm", "voice_q.json",
                   "voice_ans.txt", "voice_ans.wav"}
WORK_SKIP_PREFIX = ("_t_", "_q_")


def log(*a):
    print(*a, flush=True)


def copy_tree(src, dst, ignore=None):
    if not os.path.exists(src):
        return
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    shutil.copytree(src, dst, dirs_exist_ok=True, ignore=ignore)


def copy_work(dst_root):
    """Processed videos: keep video, subtitles, dubs, manifest and raw transcript."""
    src_root = os.path.join(REPO, "app", "data", "work")
    n_v = n_f = 0
    for vid in sorted(os.listdir(src_root)) if os.path.isdir(src_root) else []:
        d = os.path.join(src_root, vid)
        if not os.path.isdir(d) or not os.path.exists(os.path.join(d, "manifest.json")):
            continue
        out = os.path.join(dst_root, "app", "data", "work", vid)
        os.makedirs(out, exist_ok=True)
        for fn in os.listdir(d):
            if fn in WORK_SKIP_EXACT or fn.startswith(WORK_SKIP_PREFIX):
                continue
            if os.path.isfile(os.path.join(d, fn)):
                shutil.copy2(os.path.join(d, fn), os.path.join(out, fn))
                n_f += 1
        n_v += 1
    return n_v, n_f


def build(kind: str) -> str:
    name = f"awazsetu-{kind}"
    root = os.path.join(DIST, name)
    if os.path.exists(root):
        shutil.rmtree(root)
    os.makedirs(root, exist_ok=True)
    t0 = time.time()
    log(f"\n=== building {name} ===")

    # 1) code + docs
    for item in CODE:
        src = os.path.join(REPO, item)
        if os.path.isdir(src):
            copy_tree(src, os.path.join(root, item),
                      ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "data"))
        elif os.path.isfile(src):
            shutil.copy2(src, os.path.join(root, item))
    os.makedirs(os.path.join(root, "app", "data"), exist_ok=True)
    open(os.path.join(root, "app", "data", ".gitkeep"), "w").close()
    log("  code + docs copied")

    # 2) models
    hub_src = os.path.join(REPO, "models", "hf-cache", "hub")
    hub_dst = os.path.join(root, "models", "hf-cache", "hub")
    os.makedirs(hub_dst, exist_ok=True)
    wanted = LITE_HUB if kind == "lite" else sorted(os.listdir(hub_src))
    for m in wanted:
        s = os.path.join(hub_src, m)
        if os.path.isdir(s):
            log(f"  model {m}")
            copy_tree(s, os.path.join(hub_dst, m))
    v = os.path.join(hub_src, "version.txt")
    if os.path.exists(v):
        shutil.copy2(v, os.path.join(hub_dst, "version.txt"))
    copy_tree(os.path.join(REPO, "models", "nllb-int8"),
              os.path.join(root, "models", "nllb-int8"))
    mr = os.path.join(REPO, "models", "README.md")
    if os.path.exists(mr):
        shutil.copy2(mr, os.path.join(root, "models", "README.md"))
    log("  models copied")

    # 3) processed videos
    nv, nf = copy_work(root)
    log(f"  processed videos: {nv} ({nf} files)")

    # 4) settings pinned to what this package actually contains
    settings = {"asr_model": "medium", "mic_model": "small", "translate_engine": "nllb",
                "chat_llm": "qwen2.5:3b", "chat_llm_fallback": "qwen2.5:1.5b",
                "langs": ["hi", "mr", "en"], "cpu_threads": 0, "device": "cpu",
                "beam": 5, "memory_saver": True, "retrieval_mode": "foreground",
                "temperature": 0.2, "auto_speak": True}
    with open(os.path.join(root, "app", "settings.json"), "w", encoding="utf-8") as f:
        json.dump(settings, f, ensure_ascii=False, indent=1)

    # 5) full build also carries the offline installer kit
    if kind == "full":
        copy_tree(os.path.join(REPO, "offline_kit"), os.path.join(root, "offline_kit"))
        log("  offline installer kit copied")

    write_start_files(root, kind)
    size = dir_size(root)
    log(f"  DONE {name}: {size/1e9:.2f} GB in {time.time()-t0:.0f}s -> {root}")
    return root


def dir_size(p):
    tot = 0
    for r, _d, fs in os.walk(p):
        for f in fs:
            try:
                tot += os.path.getsize(os.path.join(r, f))
            except OSError:
                pass
    return tot


def write_start_files(root: str, kind: str):
    with open(os.path.join(root, "START.bat"), "w", encoding="utf-8") as f:
        f.write(
            "@echo off\r\n"
            "REM AwazSetu launcher. Requires Python, FFmpeg and Ollama on PATH.\r\n"
            "cd /d \"%~dp0\"\r\n"
            "where ollama >nul 2>nul && (start \"ollama\" /min ollama serve)\r\n"
            "set PYTHONIOENCODING=utf-8\r\n"
            "python app\\run.py\r\n"
            "pause\r\n")
    extra = ("\nThis is the FULL build: every model plus `offline_kit/` with the Python,\n"
             "Ollama and FFmpeg installers and offline pip wheels. See\n"
             "`offline_kit/INSTALL_OFFLINE.md` for a machine with nothing installed.\n"
             if kind == "full" else
             "\nThis is the LITE build, sized for transfer over the internet. It contains\n"
             "exactly the models the shipped settings use:\n"
             "  * faster-whisper `medium` - video transcription\n"
             "  * faster-whisper `small`  - microphone speech-to-text\n"
             "  * NLLB-200 CT2 INT8       - translation (hi/mr/en, ungated)\n"
             "  * MMS-TTS hin/mar/eng     - voiceovers and spoken answers\n\n"
             "The Settings page lists only the models present, so nothing offers a\n"
             "choice that is not installed. To add `large-v3` or IndicTrans2 later, run\n"
             "`python scripts/download_models.py` with internet access.\n")
    with open(os.path.join(root, "READ_ME_FIRST.md"), "w", encoding="utf-8") as f:
        f.write(f"""# AwazSetu — {kind.upper()} package

Offline Hindi / Marathi / English video translation, dubbing and a grounded
chat + voice assistant. Everything runs on-device.
{extra}
## Prerequisites
| | |
|---|---|
| Python 3.10+ | `python --version` |
| FFmpeg on PATH | `ffmpeg -version` |
| Ollama running | `ollama serve`, then `ollama list` shows `qwen2.5:3b` |

## Install
```bat
pip install torch --index-url https://download.pytorch.org/whl/cpu
pip install -r requirements.txt
ollama pull qwen2.5:3b
ollama pull qwen2.5:1.5b
```

## Run
Double-click **START.bat**, or:
```bat
python app\\run.py
```
Then open <http://127.0.0.1:5000>.

The BAIF videos are already processed — subtitles and every voiceover are built in,
so playback is instant. Only the chat and voice assistant run in real time.

## Verify
```bat
python scripts\\test_e2e.py assets settings
```

Full documentation is in `docs/` — runbook, handover and training plan, test
evidence, and the comparison against Bhashini.
""")


def make_zip(root: str) -> str:
    """Store-only zip: model weights are already compressed, so deflate wastes minutes."""
    import zipfile
    out = root + ".zip"
    if os.path.exists(out):
        os.remove(out)
    base = os.path.dirname(root)
    n = 0
    t0 = time.time()
    with zipfile.ZipFile(out, "w", zipfile.ZIP_STORED, allowZip64=True) as z:
        for r, _d, fs in os.walk(root):
            for fn in fs:
                p = os.path.join(r, fn)
                z.write(p, os.path.relpath(p, base))
                n += 1
                if n % 500 == 0:
                    log(f"    zipped {n} files…")
    log(f"  ZIP {out}  {os.path.getsize(out)/1e9:.2f} GB, {n} files, {time.time()-t0:.0f}s")
    return out


def sync_work(kind: str):
    """Refresh ONLY the processed videos in an existing package.

    Voiceovers take minutes each, so a package built while they were still being
    generated is stale. This re-copies work/ without touching the multi-GB models.
    """
    root = os.path.join(DIST, f"awazsetu-{kind}")
    if not os.path.isdir(root):
        log(f"  {root} does not exist - build it first")
        return
    dst = os.path.join(root, "app", "data", "work")
    if os.path.isdir(dst):
        shutil.rmtree(dst)
    nv, nf = copy_work(root)
    log(f"  synced {kind}: {nv} videos, {nf} files -> {dst}")


if __name__ == "__main__":
    args = [a for a in sys.argv[1:]]
    do_zip = "--zip" in args
    kinds = [a for a in args if a in ("lite", "full", "both")] or ["both"]
    if "both" in kinds:
        kinds = ["lite", "full"]
    os.makedirs(DIST, exist_ok=True)
    for k in kinds:
        r = build(k)
        if do_zip:
            make_zip(r)
    log("\nPACKAGE_DONE")
