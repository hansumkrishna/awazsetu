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
    "asr_model": "small",               # video transcription (whisper size)
    "mic_model": "small",               # voice-input STT (whisper size)
    "translate_engine": "nllb",         # nllb (ungated) | indictrans2 (needs login)
    "chat_llm": "qwen2.5:3b",           # Ollama model
    "chat_llm_fallback": "qwen2.5:1.5b",
    "langs": ["hi", "mr", "en"],        # target languages to generate
    "cpu_threads": 4,
    "device": "cpu",                    # cpu | cuda
    "beam": 1,                          # ASR/MT beam (1=fast, >1=quality)
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
    base = os.environ.get("HF_HOME") or os.path.expanduser("~/.cache/huggingface")
    return os.path.join(base, "hub")


def _hub(name: str) -> bool:
    p = os.path.join(_hf_hub_dir(), name)
    return os.path.isdir(p) and any(os.scandir(p))


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


def nllb_dir() -> str:
    return os.environ.get("AWAZ_NLLB_CT2_DIR") or os.path.join(HERE, "models", "nllb-int8")


def translate_engines() -> dict:
    nllb = os.path.exists(os.path.join(nllb_dir(), "model.bin"))
    it2 = _hub("models--ai4bharat--indictrans2-indic-en-dist-200M")
    tok_base = os.environ.get("HF_HOME") or os.path.expanduser("~/.cache/huggingface")
    token = os.path.exists(os.path.join(tok_base, "token")) or bool(os.environ.get("HF_TOKEN"))
    return {"nllb": nllb, "indictrans2": bool(it2 and token)}


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
    }
