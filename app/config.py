"""AwazSetu — operator settings (advanced page; the farmer flow stays zero-config).

Persists to settings.json and bridges to the env vars the workers/modules already
read, so a saved change takes effect on the next processing/chat/voice call without
a code change. Select-only + fully offline: this module never downloads anything —
it only reports what is installed and lets the operator switch among those.
"""
from __future__ import annotations
import os
import json

HERE = os.path.dirname(os.path.abspath(__file__))
PATH = os.path.join(HERE, "settings.json")

DEFAULTS = {
    "asr_model": "medium",              # video transcription (benchmarked best quality/speed for Indic)
    "mic_model": "small",               # voice-input STT (whisper size)
    "translate_engine": "nllb",         # nllb (ungated) | indictrans2 (needs login)
    "chat_llm": "qwen2.5:3b",           # Ollama model
    "chat_llm_fallback": "qwen2.5:1.5b",
    "langs": ["hi", "mr", "en"],        # target languages to generate
    "cpu_threads": 0,                   # 0 = auto (half the logical cores)
    "device": "cpu",                    # cpu | cuda
    "beam": 5,                          # ASR/MT beam (1=fast, 5=markedly better Indic accuracy)
    "memory_saver": True,               # unload LLM before mic STT (tight RAM)
    "retrieval_mode": "foreground",     # foreground (key lines + full) | retrieval
    "temperature": 0.2,                 # chat LLM temperature
    "auto_speak": True,                 # voice: auto-play spoken answer
}

# settings key -> env var the modules read
ENV_MAP = {
    "asr_model": "AWAZ_WHISPER",
    "mic_model": "AWAZ_MIC_WHISPER",
    "chat_llm": "AWAZ_LLM",
    "chat_llm_fallback": "AWAZ_LLM_FALLBACK",
    "cpu_threads": "AWAZ_CPU_THREADS",
    "device": "AWAZ_DEVICE",
    "beam": "AWAZ_BEAM",
    "memory_saver": "AWAZ_VOICE_UNLOAD",
    "retrieval_mode": "AWAZ_RETRIEVAL",
    "temperature": "AWAZ_LLM_TEMP",
}


def load() -> dict:
    s = dict(DEFAULTS)
    try:
        with open(PATH, encoding="utf-8") as f:
            s.update(json.load(f))
    except Exception:
        pass
    return s


def apply_to_env(s: dict | None = None) -> None:
    s = s or load()
    for k, env in ENV_MAP.items():
        if k in s and s[k] is not None:
            os.environ[env] = str(s[k]).lower() if isinstance(s[k], bool) else str(s[k])
    # translation engine drives both subtitle MT and chat MT
    os.environ["AWAZ_MT"] = s.get("translate_engine", "nllb")
    os.environ["AWAZ_CHAT_MT"] = s.get("translate_engine", "nllb")


def save(patch: dict) -> dict:
    s = load()
    for k, v in patch.items():
        if k in DEFAULTS:
            s[k] = v
    with open(PATH, "w", encoding="utf-8") as f:
        json.dump(s, f, ensure_ascii=False, indent=1)
    apply_to_env(s)
    return s


# ---------------- availability / status (read-only, offline) ----------------
def _hf_hub_dir() -> str:
    base = (os.environ.get("HF_HOME")
            or os.path.join(os.path.dirname(HERE), "models", "hf-cache"))
    if not os.path.isdir(os.path.join(base, "hub")):
        base = os.environ.get("HF_HOME") or os.path.expanduser("~/.cache/huggingface")
    return os.path.join(base, "hub")


WEIGHT_EXT = (".bin", ".safetensors", ".pt", ".ct2", ".onnx", ".model")


def _hub(name: str) -> bool:
    """True only when the repo has real WEIGHTS on disk.

    A failed gated download still leaves a folder containing refs/ and a README,
    so a bare "directory is non-empty" test reports a model as installed when it
    is a 17 KB stub. That false positive surfaces later as a runtime crash.
    """
    p = os.path.join(_hf_hub_dir(), name)
    if not os.path.isdir(p):
        return False
    for root, _dirs, files in os.walk(os.path.join(p, "snapshots")):
        for f in files:
            if f.endswith(WEIGHT_EXT):
                try:
                    if os.path.getsize(os.path.join(root, f)) > 1_000_000:
                        return True
                except OSError:
                    continue
    return False


def whisper_installed() -> list[str]:
    return [s for s in ("tiny", "base", "small", "medium", "large-v3")
            if _hub(f"models--Systran--faster-whisper-{s}")]


def ollama_exe() -> str:
    """Locate the ollama binary portably (PATH first, then the standard per-user
    install dir via LOCALAPPDATA / HOME — no hardcoded username)."""
    import shutil
    found = shutil.which("ollama")
    if found:
        return found
    cands = []
    la = os.environ.get("LOCALAPPDATA")
    if la:
        cands.append(os.path.join(la, "Programs", "Ollama", "ollama.exe"))
    cands += [os.path.expanduser("~/.ollama/bin/ollama"), "/usr/local/bin/ollama"]
    for c in cands:
        if os.path.exists(c):
            return c
    return "ollama"


def ollama_models() -> list[str]:
    import subprocess
    try:
        out = subprocess.run([ollama_exe(), "list"], capture_output=True, text=True, timeout=10)
        return [ln.split()[0] for ln in out.stdout.splitlines()[1:] if ln.strip()]
    except Exception:
        return []


def free_ram_mb() -> int | None:
    try:
        import ctypes

        class MS(ctypes.Structure):
            _fields_ = [("dwLength", ctypes.c_ulong), ("dwMemoryLoad", ctypes.c_ulong),
                        ("ullTotalPhys", ctypes.c_ulonglong), ("ullAvailPhys", ctypes.c_ulonglong),
                        ("ullTotalPageFile", ctypes.c_ulonglong), ("ullAvailPageFile", ctypes.c_ulonglong),
                        ("ullTotalVirtual", ctypes.c_ulonglong), ("ullAvailVirtual", ctypes.c_ulonglong),
                        ("ullAvailExtendedVirtual", ctypes.c_ulonglong)]
        m = MS()
        m.dwLength = ctypes.sizeof(MS)
        ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(m))
        return int(m.ullAvailPhys / (1024 * 1024))
    except Exception:
        return None


def models_dir() -> str:
    """Repo-level models/ folder (app/ is one level below the repo root)."""
    return os.environ.get("AWAZ_MODELS_DIR") or os.path.join(
        os.path.dirname(HERE), "models")


def nllb_dir() -> str:
    # Fallback must point at the REPO-level models/, not app/models/ — otherwise the
    # Settings status panel reports NLLB missing whenever run.py has not set the env.
    return os.environ.get("AWAZ_NLLB_CT2_DIR") or os.path.join(models_dir(), "nllb-int8")


def indictrans2_directions() -> dict:
    """Which IndicTrans2 direction models are actually present on disk.

    en-indic is separately gated on Hugging Face, so a partial install is normal:
    indic-en + indic-indic alone still improve Marathi/Hindi -> English noticeably.
    """
    return {
        "indic-en": _hub("models--ai4bharat--indictrans2-indic-en-dist-200M"),
        "en-indic": _hub("models--ai4bharat--indictrans2-en-indic-dist-200M"),
        "indic-indic": _hub("models--ai4bharat--indictrans2-indic-indic-dist-320M"),
    }


def translate_engines() -> dict:
    """Availability is decided by WEIGHTS ON DISK, not by whether a token file exists —
    once downloaded the models work offline with no login."""
    nllb = os.path.exists(os.path.join(nllb_dir(), "model.bin"))
    d = indictrans2_directions()
    return {"nllb": nllb, "indictrans2": bool(d["indic-en"])}


def mms_voices() -> list[str]:
    return [L for L, r in (("hi", "hin"), ("mr", "mar"), ("en", "eng"))
            if _hub(f"models--facebook--mms-tts-{r}")]


def status() -> dict:
    import urllib.request
    try:
        urllib.request.urlopen("http://127.0.0.1:11434/api/tags", timeout=3)
        ollama_up = True
    except Exception:
        ollama_up = False
    return {
        "free_ram_mb": free_ram_mb(),
        "ollama_up": ollama_up,
        "ollama_models": ollama_models(),
        "whisper_installed": whisper_installed(),
        "translate_engines": translate_engines(),
        "mms_voices": mms_voices(),
        "offline": True,
        "guide": MODEL_GUIDE,
        "it2_directions": indictrans2_directions(),
    }


# ---------------- model guidance (shown on the Settings page) ----------------
# Ratings are measured on BAIF Marathi field video where marked "measured",
# otherwise they reflect published model behaviour. 5 = best, 1 = unusable.
MODEL_GUIDE = {
    "asr": {
        "tiny":     {"en": 2, "hi": 1, "mr": 1, "speed": 5, "ram_mb": 150,
                     "note": "Fastest. Latin-script only in practice — do not use for Indic."},
        "base":     {"en": 3, "hi": 2, "mr": 1, "speed": 5, "ram_mb": 250,
                     "note": "Measured: transcribed Hindi speech in Urdu script. Avoid for Indic."},
        "small":    {"en": 4, "hi": 3, "mr": 2, "speed": 4, "ram_mb": 600,
                     "note": "Measured: Marathi output was garbled and unusable. OK for English and live mic."},
        "medium":   {"en": 5, "hi": 4, "mr": 4, "speed": 3, "ram_mb": 1600,
                     "note": "RECOMMENDED. Measured RTF 0.32 on GPU; produced meaningful Marathi."},
        "large-v3": {"en": 5, "hi": 5, "mr": 5, "speed": 1, "ram_mb": 3200,
                     "note": "Best accuracy, but CUDA-OOMs on a 4 GB GPU and is very slow on CPU."},
    },
    "mt": {
        "nllb":        {"en": 4, "hi": 4, "mr": 3, "speed": 4, "ram_mb": 700,
                        "note": "DEFAULT. Ungated, no login, covers every hi/mr/en direction."},
        "indictrans2": {"en": 5, "hi": 5, "mr": 5, "speed": 3, "ram_mb": 1200,
                        "note": "Best Indic quality, but HF-gated — needs huggingface-cli login."},
    },
    "llm": {
        "qwen2.5:1.5b": {"en": 3, "hi": 2, "mr": 2, "speed": 5, "ram_mb": 1400,
                         "note": "Fallback for tight RAM. Weaker reasoning; keep answers short."},
        "qwen2.5:3b":   {"en": 4, "hi": 3, "mr": 3, "speed": 3, "ram_mb": 3200,
                         "note": "RECOMMENDED. Reasons in English, then the answer is translated."},
    },
}


def model_guide() -> dict:
    return MODEL_GUIDE
