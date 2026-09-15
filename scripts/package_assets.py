"""Bundle everything the Git repository cannot hold, for upload elsewhere.

    python scripts/package_assets.py            # build dist/awazsetu-assets.zip
    python scripts/package_assets.py --split 1900

The repository carries code and documentation only — models, the embedded runtime and
the processed library are gitignored because they are 15 GB of binaries. This produces
the other half, so that:

    git clone <repo>  +  extract this bundle over it  =  a working install

Contents:
  models/     ASR, translation, voice and chat weights (duplicate .bin weights dropped)
  runtime/    embedded Python 3.10 + FFmpeg — what makes it zero-install
  app/data/   the 15 processed items: media, subtitles, voiceovers, manifests

Deliberately NOT a second copy of the LITE package. LITE is a ready-to-run folder;
this is the companion to a clone.
"""
from __future__ import annotations
import os
import sys
import time
import zipfile

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DIST = os.path.join(REPO, "dist")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

SKIP_DIRS = {"__pycache__", ".git", ".locks"}
SKIP_FILES = {"pytorch_model.bin"}                      # identical to model.safetensors
WORK_SKIP = {"audio.wav", "status.json", "voice_in.webm", "voice_q.json",
             "voice_ans.txt", "voice_ans.wav", "bundle.mkv"}

TREES = [
    ("models", os.path.join(REPO, "models")),
    ("runtime", os.path.join(REPO, "runtime")),
    (os.path.join("app", "data", "work"), os.path.join(REPO, "app", "data", "work")),
]

README = """# AwazSetu — asset bundle

The Git repository holds code and documentation. This holds everything it cannot:
the models, the embedded runtime, and the processed library.

## To get a working install

1. `git clone https://github.com/hansumkrishna/awazsetu.git`
2. Extract this bundle **into that folder**, so `models\\`, `runtime\\` and
   `app\\data\\work\\` sit beside `app\\` and `scripts\\`.
3. Double-click `AwazSetu-Check.bat` — it should print READY.
4. Double-click `AwazSetu.bat`.

Nothing else is installed. No Python, no pip, no FFmpeg, no Ollama, no internet.

## What is in here

| Folder | Size | What it is |
|---|---|---|
| `models/hf-cache/` | ~8 GB | Whisper (5 sizes), IndicTrans2 (3 directions), MMS-TTS (4 voices) |
| `models/llm/` | ~2.7 GB | Qwen 2.5 3B and 1.5B, GGUF Q4_K_M — the chat assistant |
| `models/nllb-int8/` | ~0.6 GB | NLLB-200 CTranslate2, the fallback translation engine |
| `runtime/python/` | ~1.6 GB | Embedded Python 3.10.11 with every dependency preinstalled |
| `runtime/bin/` | ~0.17 GB | FFmpeg and FFprobe |
| `app/data/work/` | ~0.55 GB | 15 processed items: media, 60 subtitle tracks, 60 voiceovers |

Duplicate `pytorch_model.bin` weights are omitted — every model here ships an identical
`model.safetensors`, which is what transformers loads. That saves 3.7 GB and changes
nothing.

## If it arrived as parts

Run `JOIN-awazsetu-assets.bat` first; it rejoins them into one zip.
`awazsetu-assets.zip.parts.txt` lists a SHA-256 for each part, so a bad transfer is
caught before it wastes anyone's afternoon.
"""


def main():
    split_mb = 0
    for i, a in enumerate(sys.argv):
        if a == "--split":
            split_mb = int(sys.argv[i + 1])
        elif a.startswith("--split="):
            split_mb = int(a.split("=")[1])

    os.makedirs(DIST, exist_ok=True)
    out = os.path.join(DIST, "awazsetu-assets.zip")
    if os.path.exists(out):
        os.remove(out)

    t0 = time.time()
    n = skipped = 0
    print(f"building {out}", flush=True)
    # Store-only: the payload is already-compressed weights and media, so deflate
    # costs many minutes and saves almost nothing.
    with zipfile.ZipFile(out, "w", zipfile.ZIP_STORED, allowZip64=True) as z:
        z.writestr("READ_ME_FIRST.md", README)
        for arc_root, src in TREES:
            if not os.path.isdir(src):
                print(f"  !! missing {src}")
                continue
            is_work = arc_root.endswith("work")
            for root, dirs, files in os.walk(src):
                dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
                for f in files:
                    if f in SKIP_FILES or f.endswith(".pyc"):
                        skipped += 1
                        continue
                    if is_work and f in WORK_SKIP:
                        continue
                    p = os.path.join(root, f)
                    arc = os.path.join(arc_root, os.path.relpath(p, src))
                    try:
                        z.write(p, arc)
                    except OSError:
                        continue
                    n += 1
                    if n % 2000 == 0:
                        print(f"    {n} files…", flush=True)
    sz = os.path.getsize(out)
    print(f"  {sz/1e9:.2f} GB, {n} files, {skipped} duplicate weights skipped, "
          f"{time.time()-t0:.0f}s", flush=True)

    if split_mb and sz > split_mb * 1024 * 1024:
        import package as pkg          # reuse the verified split + join-script writer
        parts = pkg.split_file(out, split_mb)
        os.remove(out)
        print(f"  split into {len(parts)} part(s); original removed", flush=True)
    print("ASSETS_DONE", flush=True)


if __name__ == "__main__":
    main()
