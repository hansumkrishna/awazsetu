"""AwazSetu — one-time model downloader (needs internet ONCE; then the app is offline).

    python scripts/download_models.py            # core models (fully offline stack)
    python scripts/download_models.py --indictrans2   # also fetch gated IndicTrans2 (needs login)

Everything lands in the project's own  models/  folder so the install is portable and
self-contained. After this runs, the app makes zero network calls at runtime.
"""
import os
import sys
import shutil
import subprocess

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODELS = os.path.join(REPO, "models")
HF = os.path.join(MODELS, "hf-cache")
os.makedirs(HF, exist_ok=True)
# route ALL Hugging Face downloads into the project folder
os.environ["HF_HOME"] = HF
os.environ.pop("HF_HUB_OFFLINE", None)
os.environ.pop("TRANSFORMERS_OFFLINE", None)

WHISPER = ["small", "medium"]          # video + mic transcription
MMS = ["facebook/mms-tts-hin", "facebook/mms-tts-mar", "facebook/mms-tts-eng"]
NLLB_CT2 = "JustFrederik/nllb-200-distilled-600M-ct2-int8"
NLLB_TOK = "facebook/nllb-200-distilled-600M"
OLLAMA = ["qwen2.5:3b", "qwen2.5:1.5b"]
IT2 = ["ai4bharat/indictrans2-indic-en-dist-200M",
       "ai4bharat/indictrans2-indic-indic-dist-320M"]


def hr(t):
    print("\n" + "=" * 60 + f"\n{t}\n" + "=" * 60)


def dl_whisper():
    hr("Whisper (faster-whisper) — ASR + mic STT")
    from faster_whisper import WhisperModel
    for s in WHISPER:
        print(f"  · {s} ...")
        WhisperModel(s, device="cpu", compute_type="int8")


def dl_hf(repos):
    from huggingface_hub import snapshot_download
    for r in repos:
        print(f"  · {r} ...")
        snapshot_download(r)


def dl_nllb():
    hr("NLLB-200 distilled INT8 (CTranslate2) — the ungated default translator")
    from huggingface_hub import snapshot_download
    print(f"  · tokenizer {NLLB_TOK} ...")
    snapshot_download(NLLB_TOK)
    print(f"  · model {NLLB_CT2} ...")
    snap = snapshot_download(NLLB_CT2)
    dest = os.path.join(MODELS, "nllb-int8")
    os.makedirs(dest, exist_ok=True)
    # copy real files (deref symlinks) into a plain dir — ctranslate2 needs real files
    # and native Windows paths, not the HF symlink cache.
    for f in os.listdir(snap):
        src = os.path.join(snap, f)
        if os.path.isfile(src):
            shutil.copy(src, os.path.join(dest, f))
    print(f"  -> {dest}")


def dl_ollama():
    hr("Ollama chat models (external — needs the Ollama app installed & running)")
    exe = shutil.which("ollama") or "ollama"
    for m in OLLAMA:
        print(f"  · ollama pull {m} ...")
        try:
            subprocess.run([exe, "pull", m], check=True)
        except Exception as e:
            print(f"    !! skipped ({e}). Install Ollama from https://ollama.com then: ollama pull {m}")


def dl_indictrans2():
    hr("IndicTrans2 (optional, GATED) — higher-quality Indic")
    try:
        from huggingface_hub import whoami
        whoami()
    except Exception:
        print("  !! Not logged in. Run `huggingface-cli login` and accept the terms at:")
        for r in IT2:
            print("     https://huggingface.co/" + r)
        return
    dl_hf(IT2)


def main():
    print("Downloading into:", MODELS)
    dl_whisper()
    dl_nllb()
    dl_hf(MMS) if False else None
    hr("MMS-TTS voices — spoken subtitles / dub / voice answers")
    dl_hf(MMS)
    dl_ollama()
    if "--indictrans2" in sys.argv:
        dl_indictrans2()
    hr("Done — the app now runs fully offline. Start it with:  python app/run.py")


if __name__ == "__main__":
    main()


# --- added after benchmarking on real BAIF Marathi video -----------------------
# medium is the recommended ASR model (small garbles Marathi); large-v3 is optional
# and needs either a >4GB GPU or patience on CPU.
EXTRA_WHISPER = ["medium", "large-v3"]

# IndicTrans2 (optional, higher Indic quality). All three repos are GATED: run
# `huggingface-cli login` AND click "Agree" on each model page first.
INDICTRANS2 = [
    "ai4bharat/indictrans2-indic-en-dist-200M",
    "ai4bharat/indictrans2-en-indic-dist-200M",
    "ai4bharat/indictrans2-indic-indic-dist-320M",
]


def fetch_extras(with_indictrans2: bool = False):
    """Pull the models the benchmark selected. Windows without Developer Mode cannot
    create symlinks, so disable them or the download aborts part-way."""
    import os
    os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS", "1")
    os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS_WARNING", "1")
    from huggingface_hub import snapshot_download
    for size in EXTRA_WHISPER:
        print("==> faster-whisper", size, flush=True)
        snapshot_download(f"Systran/faster-whisper-{size}", max_workers=4)
    if with_indictrans2:
        for repo in INDICTRANS2:
            try:
                print("==>", repo, flush=True)
                snapshot_download(repo, token=os.environ.get("HF_TOKEN"), max_workers=2)
            except Exception as e:
                print(f"    SKIPPED ({type(e).__name__}) - accept the licence at "
                      f"https://huggingface.co/{repo}", flush=True)
