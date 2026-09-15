"""Build the two distributable packages. Both are ZERO-INSTALL.

    python scripts/package.py lite            # everything needed to run and demo
    python scripts/package.py full            # + spare models and a rescue kit
    python scripts/package.py both --zip
    python scripts/package.py lite --zip --split 1900

A package is self-contained: an embedded Python, FFmpeg, every model, and the
processed library. The user extracts the folder and double-clicks `AwazSetu.bat`.
There is no Python to install, no pip, no PATH to edit, no Ollama, no internet.

Three things keep the size sane:

  * **No duplicate weights.** Every HF repo ships `pytorch_model.bin` AND an identical
    `model.safetensors`. Transformers loads the safetensors and ignores the .bin, so
    the .bin is dropped — 3.7 GB across the model tree, verified to change nothing.
  * **LITE drops NLLB.** IndicTrans2 is the default engine and is strictly better for
    every language here; NLLB is a fallback that LITE does not need.
  * **Ollama is gone.** Its 1.5 GB installer and 2.8 GB blob store are replaced by the
    two GGUF files, which are the same weights the blobs contained.
"""
from __future__ import annotations
import os
import sys
import json
import shutil
import time
import hashlib

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DIST = os.path.join(REPO, "dist")

# --- what each build carries -------------------------------------------------
LITE_HUB = [
    "models--Systran--faster-whisper-medium",   # new uploads
    "models--Systran--faster-whisper-small",    # microphone / voice chat
    "models--ai4bharat--indictrans2-indic-en-dist-200M",
    "models--ai4bharat--indictrans2-en-indic-dist-200M",
    "models--ai4bharat--indictrans2-indic-indic-dist-320M",
    "models--facebook--mms-tts-hin",
    "models--facebook--mms-tts-mar",
    "models--facebook--mms-tts-eng",
    "models--facebook--mms-tts-ory",
]
LITE_GGUF = ["qwen2.5-3b-instruct-q4_k_m.gguf", "qwen2.5-1.5b-instruct-q4_k_m.gguf"]

CODE = ["app", "scripts", "docs", "requirements.txt", "requirements-pinned.txt",
        "README.md", ".gitattributes", "AwazSetu.bat", "AwazSetu-Check.bat"]

# Regenerated on demand; shipping them wastes ~160 MB and they are derived data.
WORK_SKIP_EXACT = {"audio.wav", "status.json", "voice_in.webm", "voice_q.json",
                   "voice_ans.txt", "voice_ans.wav", "bundle.mkv"}
WORK_SKIP_PREFIX = ("_t_", "_q_")

# Never ship: duplicate weights, caches, and the git metadata of the source tree.
DROP_FILES = ("pytorch_model.bin",)
DROP_DIRS = ("__pycache__", ".git", ".locks", "data")


def log(*a):
    print(*a, flush=True)


def _ignore(_dir, names):
    out = set()
    for n in names:
        if n in DROP_DIRS or n.endswith(".pyc"):
            out.add(n)
    return out


def copy_models(hub_src, hub_dst, wanted) -> tuple[int, int]:
    """Copy model repos, skipping the duplicate .bin weights. Returns (files, bytes)."""
    n = saved = 0
    for m in wanted:
        s = os.path.join(hub_src, m)
        if not os.path.isdir(s):
            log(f"    !! missing model {m}")
            continue
        for root, dirs, files in os.walk(s):
            dirs[:] = [d for d in dirs if d not in DROP_DIRS]
            rel = os.path.relpath(root, hub_src)
            dst = os.path.join(hub_dst, rel)
            os.makedirs(dst, exist_ok=True)
            for f in files:
                src_f = os.path.join(root, f)
                if f in DROP_FILES:
                    try:
                        saved += os.path.getsize(src_f)
                    except OSError:
                        pass
                    continue
                shutil.copy2(src_f, os.path.join(dst, f))
                n += 1
    return n, saved


def copy_work(dst_root) -> tuple[int, int]:
    """Processed media: source file, subtitles, voiceovers, manifest, transcript."""
    src_root = os.path.join(REPO, "app", "data", "work")
    n_v = n_f = 0
    if not os.path.isdir(src_root):
        return 0, 0
    for vid in sorted(os.listdir(src_root)):
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
    log(f"\n=== building {name} (zero-install) ===")

    # 1) code + docs + launchers
    for item in CODE:
        src = os.path.join(REPO, item)
        if os.path.isdir(src):
            shutil.copytree(src, os.path.join(root, item), dirs_exist_ok=True,
                            ignore=_ignore)
        elif os.path.isfile(src):
            shutil.copy2(src, os.path.join(root, item))
    os.makedirs(os.path.join(root, "app", "data"), exist_ok=True)
    open(os.path.join(root, "app", "data", ".gitkeep"), "w").close()
    log("  code, docs and launchers copied")

    # 2) the embedded runtime — this is what makes the package zero-install
    shutil.copytree(os.path.join(REPO, "runtime"), os.path.join(root, "runtime"),
                    dirs_exist_ok=True, ignore=_ignore)
    log(f"  runtime: embedded Python + FFmpeg ({dir_size(os.path.join(root,'runtime'))/1e9:.2f} GB)")

    # 3) models
    hub_src = os.path.join(REPO, "models", "hf-cache", "hub")
    hub_dst = os.path.join(root, "models", "hf-cache", "hub")
    os.makedirs(hub_dst, exist_ok=True)
    if kind == "lite":
        wanted = LITE_HUB
    else:
        wanted = [d for d in sorted(os.listdir(hub_src))
                  if d.startswith("models--")]
    nf, saved = copy_models(hub_src, hub_dst, wanted)
    log(f"  models: {len(wanted)} repos, {nf} files "
        f"({saved/1e9:.2f} GB of duplicate .bin weights skipped)")

    v = os.path.join(hub_src, "version.txt")
    if os.path.exists(v):
        shutil.copy2(v, os.path.join(hub_dst, "version.txt"))

    # NLLB: FULL keeps it as a fallback engine; LITE does not need it.
    if kind == "full":
        shutil.copytree(os.path.join(REPO, "models", "nllb-int8"),
                        os.path.join(root, "models", "nllb-int8"), dirs_exist_ok=True)
        log("  models: NLLB CT2 fallback included")

    # chat LLM weights
    llm_dst = os.path.join(root, "models", "llm")
    os.makedirs(llm_dst, exist_ok=True)
    for g in LITE_GGUF:
        s = os.path.join(REPO, "models", "llm", g)
        if os.path.exists(s):
            shutil.copy2(s, os.path.join(llm_dst, g))
    log(f"  models: {len(os.listdir(llm_dst))} GGUF chat model(s)")

    # 4) processed library
    nv, nfil = copy_work(root)
    log(f"  library: {nv} processed items ({nfil} files)")

    # 5) settings that match what this package ACTUALLY contains
    settings = {
        "asr_model": "large-v3" if kind == "full" else "medium",
        "mic_model": "small",
        "translate_engine": "indictrans2",
        "chat_llm": "qwen2.5:3b", "chat_llm_fallback": "qwen2.5:1.5b",
        "langs": ["hi", "mr", "en", "or"],
        "cpu_threads": 0, "device": "cpu", "beam": 5,
        "memory_saver": True, "retrieval_mode": "foreground",
        "temperature": 0.2, "auto_speak": True,
    }
    with open(os.path.join(root, "app", "settings.json"), "w", encoding="utf-8") as f:
        json.dump(settings, f, ensure_ascii=False, indent=1)

    # 6) FULL also carries a rescue kit: if the embedded runtime is ever rejected by
    #    a locked-down machine, these rebuild it. Ollama is deliberately NOT included.
    if kind == "full":
        kit_src, kit_dst = os.path.join(REPO, "offline_kit"), os.path.join(root, "rescue_kit")
        os.makedirs(kit_dst, exist_ok=True)
        for sub in ("wheels-pinned", "installers"):
            s = os.path.join(kit_src, sub) if sub != "wheels-pinned" else \
                os.path.join(kit_src, "wheels-pinned")
            if os.path.isdir(s):
                if sub == "installers":  # python only; the Ollama installer is obsolete
                    os.makedirs(os.path.join(kit_dst, sub), exist_ok=True)
                    for f in os.listdir(s):
                        if "python" in f.lower():
                            shutil.copy2(os.path.join(s, f), os.path.join(kit_dst, sub, f))
                else:
                    shutil.copytree(s, os.path.join(kit_dst, sub), dirs_exist_ok=True)
        log("  rescue kit: pinned wheels + Python installer (no Ollama — not needed)")

    write_readme(root, kind)
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


def write_readme(root: str, kind: str):
    extra = ("\nThis is the **FULL** build: every model (including Whisper large-v3 and the\n"
             "NLLB fallback engine) plus `rescue_kit/` — pinned offline wheels and a Python\n"
             "installer, needed only if a locked-down machine refuses the embedded runtime.\n"
             if kind == "full" else
             "\nThis is the **LITE** build, sized for transfer over the internet. It carries\n"
             "exactly what the shipped settings use:\n\n"
             "  * Whisper `medium` — transcribing a newly added file\n"
             "  * Whisper `small`  — the microphone / voice chat\n"
             "  * IndicTrans2 (all three directions) — translation\n"
             "  * MMS-TTS hin / mar / eng / ory — voiceovers and spoken answers\n"
             "  * Qwen 2.5 3B + 1.5B — the chat assistant\n\n"
             "Whisper large-v3 and the NLLB fallback are in the FULL build. The Model Garden\n"
             "shows them as *not installed* here, so nothing offers a choice that is absent.\n")
    with open(os.path.join(root, "READ_ME_FIRST.md"), "w", encoding="utf-8") as f:
        f.write(f"""# AwazSetu — {kind.upper()} package

Offline Hindi / Marathi / English / **Odia** video & audio translation, dubbing,
subtitles, and a grounded chat + voice assistant. Everything runs on this machine.
{extra}
## How to run it

1. Extract this folder anywhere (a USB stick is fine).
2. Double-click **`AwazSetu.bat`**.
3. A browser opens at <http://127.0.0.1:5000>.

That is the whole procedure.

**There is nothing to install.** No Python, no pip, no FFmpeg, no Ollama, no PATH
changes, no internet — not even on a freshly imaged Windows machine. An embedded
Python 3.10 and FFmpeg live in `runtime\\`, and every model is in `models\\`.
Nothing is written outside this folder; delete the folder to uninstall completely.

## Check the machine before a demo

Double-click **`AwazSetu-Check.bat`**. It verifies the runtime, FFmpeg, every model,
the chat backend (by actually generating an answer), the library, and the memory
budget — then prints READY or names exactly what is wrong. It changes nothing.

## What you get

The library is **already processed**: subtitles in four languages and a full voiceover
in each language are built in, so playback is instant. Only the chat and the voice
assistant run in real time — everything else was computed once, up front.

* **Model Garden** (`/garden`) — every model scored per language, per task, against
  this machine's memory and cores, with one-click presets.
* **Settings** (`/settings`) — switch any individual model.

## Offline by construction

`run.py` sets `HF_HUB_OFFLINE=1` and `TRANSFORMERS_OFFLINE=1`, so the app cannot
download anything even if a network is present. Turning Wi-Fi off changes nothing —
which is the cleanest way to prove the claim to an audience.

Full documentation is in `docs/`: runbook, handover and training plan, test evidence,
architecture, and the comparison against Bhashini.
""")


def make_zip(root: str, split_mb: int = 0) -> list:
    """Store-only archive: the payload is already-compressed weights and video, so
    deflate costs minutes and saves almost nothing."""
    import zipfile
    base = os.path.dirname(root)
    out = root + ".zip"
    if os.path.exists(out):
        os.remove(out)
    n = 0
    t0 = time.time()
    with zipfile.ZipFile(out, "w", zipfile.ZIP_STORED, allowZip64=True) as z:
        for r, _d, fs in os.walk(root):
            for fn in fs:
                p = os.path.join(r, fn)
                z.write(p, os.path.relpath(p, base))
                n += 1
                if n % 1000 == 0:
                    log(f"    zipped {n} files…")
    sz = os.path.getsize(out)
    log(f"  ZIP {out}  {sz/1e9:.2f} GB, {n} files, {time.time()-t0:.0f}s")
    parts = [out]
    if split_mb and sz > split_mb * 1024 * 1024:
        parts = split_file(out, split_mb)
        os.remove(out)
    return parts


def split_file(path: str, part_mb: int) -> list:
    """Split into <part_mb> chunks + a .bat that rejoins them.

    GitHub releases and many mail/drive systems refuse a single multi-GB file, and a
    half-copied 11 GB zip gives no signal that it is broken. Parts carry a SHA-256
    manifest so a bad transfer is caught before the demo, not during it.
    """
    size = part_mb * 1024 * 1024
    parts, sums = [], []
    with open(path, "rb") as f:
        i = 0
        while True:
            chunk = f.read(size)
            if not chunk:
                break
            i += 1
            pp = f"{path}.{i:03d}"
            with open(pp, "wb") as o:
                o.write(chunk)
            parts.append(pp)
            sums.append((os.path.basename(pp), hashlib.sha256(chunk).hexdigest(),
                         len(chunk)))
            log(f"    part {i:03d}: {len(chunk)/1e9:.2f} GB")
    stem = os.path.basename(path)
    d = os.path.dirname(path)
    with open(os.path.join(d, stem + ".parts.txt"), "w", encoding="utf-8") as f:
        f.write(f"{stem} split into {len(parts)} parts\nsha256  size  name\n")
        for nm, h, sz in sums:
            f.write(f"{h}  {sz}  {nm}\n")
    with open(os.path.join(d, "JOIN-" + stem.replace(".zip", "") + ".bat"), "w") as f:
        f.write("@echo off\r\nREM Rejoin the downloaded parts into one zip, then extract it.\r\n"
                "cd /d \"%~dp0\"\r\n"
                f"echo Joining {len(parts)} parts into {stem} ...\r\n"
                f"copy /b {stem}.001")
        for i in range(2, len(parts) + 1):
            f.write(f"+{stem}.{i:03d}")
        f.write(f" {stem}\r\n"
                f"echo Done. Extract {stem}, then double-click AwazSetu.bat inside it.\r\n"
                "pause\r\n")
    return parts


if __name__ == "__main__":
    args = sys.argv[1:]
    do_zip = "--zip" in args
    split = 0
    for a in args:
        if a.startswith("--split"):
            split = int(a.split("=")[1]) if "=" in a else 1900
    kinds = [a for a in args if a in ("lite", "full", "both")] or ["both"]
    if "both" in kinds:
        kinds = ["lite", "full"]
    os.makedirs(DIST, exist_ok=True)
    for k in kinds:
        r = build(k)
        if do_zip:
            make_zip(r, split)
    log("\nPACKAGE_DONE")
