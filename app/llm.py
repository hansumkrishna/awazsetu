"""AwazSetu — the local chat LLM, with no installed service behind it.

Two interchangeable backends:

  * **llamacpp** (default) — loads a GGUF file in-process via `llama_cpp`. Nothing to
    install, nothing to start, no second server, no `%USERPROFILE%` state.
  * **ollama** — the original HTTP backend, kept because a machine that already runs
    Ollama should keep using it rather than loading a second copy of the weights.

`AWAZ_LLM_BACKEND` = auto (default) | llamacpp | ollama.
Under `auto` a bundled GGUF wins; otherwise a live Ollama is used; otherwise the
caller gets a clean "no backend" error instead of a connection traceback.

Why this exists: Ollama was the single largest obstacle to "directly executable".
It meant a 1.5 GB installer, an `xcopy` of blobs into `%USERPROFILE%\\.ollama`, and a
`ollama serve` process running alongside the app. The blobs Ollama stores are already
GGUF (magic `47 47 55 46`), so the very same weights load here from a 7.1 MB wheel —
the install step buys nothing.

Logical model names ("qwen2.5:3b") are preserved across both backends so settings.json
and the Settings page stay backend-agnostic.
"""
from __future__ import annotations
import os
import json
import glob
import threading
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
OLLAMA = os.environ.get("OLLAMA_URL", "http://127.0.0.1:11434")

# Logical name -> the GGUF basename shipped in models/llm/. Both files come straight
# from the Ollama blob store, so quality is bit-identical to the Ollama path.
GGUF_FILES = {
    "qwen2.5:3b":   "qwen2.5-3b-instruct-q4_k_m.gguf",
    "qwen2.5:1.5b": "qwen2.5-1.5b-instruct-q4_k_m.gguf",
}
# Approximate resident size once loaded, for the Model Garden's RAM budget.
GGUF_RAM_MB = {"qwen2.5:3b": 2600, "qwen2.5:1.5b": 1400}

_lock = threading.Lock()
_loaded: dict = {"name": None, "llm": None}


# ----------------------------------------------------------------- discovery
def llm_dir() -> str:
    return os.environ.get("AWAZ_LLM_DIR") or os.path.join(
        os.path.dirname(HERE), "models", "llm")


def gguf_path(name: str) -> str | None:
    """Resolve a logical model name to a GGUF on disk, tolerating extra files."""
    d = llm_dir()
    fn = GGUF_FILES.get(name)
    if fn:
        p = os.path.join(d, fn)
        if os.path.exists(p):
            return p
    # A GGUF dropped in by hand still counts, matched loosely on the family name.
    stem = name.replace(":", "-").replace(".", "")
    for p in glob.glob(os.path.join(d, "*.gguf")):
        if stem in os.path.basename(p).replace(".", "").lower():
            return p
    return None


def gguf_models() -> list[str]:
    """Logical names whose weights are actually present."""
    return [n for n in GGUF_FILES if gguf_path(n)]


def ollama_up() -> bool:
    try:
        urllib.request.urlopen(OLLAMA + "/api/tags", timeout=2)
        return True
    except Exception:
        return False


def ollama_models() -> list[str]:
    try:
        with urllib.request.urlopen(OLLAMA + "/api/tags", timeout=3) as r:
            return [m["name"] for m in json.loads(r.read()).get("models", [])]
    except Exception:
        return []


def backend() -> str:
    """Which backend will actually serve the next call."""
    want = (os.environ.get("AWAZ_LLM_BACKEND") or "auto").lower()
    if want == "llamacpp":
        return "llamacpp"
    if want == "ollama":
        return "ollama"
    if gguf_models():
        try:
            import llama_cpp  # noqa: F401
            return "llamacpp"
        except Exception:
            pass
    return "ollama" if ollama_up() else "none"


def available_models() -> list[str]:
    b = backend()
    if b == "llamacpp":
        return gguf_models()
    if b == "ollama":
        return ollama_models()
    return []


# ------------------------------------------------------------ llama.cpp path
def _ctx() -> int:
    return int(os.environ.get("AWAZ_LLM_CTX", "8192"))


def _threads() -> int:
    n = int(os.environ.get("AWAZ_CPU_THREADS", "0"))
    return n or max(4, (os.cpu_count() or 8) // 2)


def _get_llama(name: str):
    """Load and cache one model. Swapping models frees the previous one first —
    two 3B models resident at once would breach the 16 GB budget on the target box."""
    from llama_cpp import Llama
    with _lock:
        if _loaded["name"] == name and _loaded["llm"] is not None:
            return _loaded["llm"]
        unload()
        path = gguf_path(name)
        if not path:
            raise RuntimeError(f"no GGUF on disk for {name} (looked in {llm_dir()})")
        _loaded["llm"] = Llama(
            model_path=path, n_ctx=_ctx(), n_threads=_threads(),
            n_gpu_layers=int(os.environ.get("AWAZ_LLM_GPU", "0")), verbose=False)
        _loaded["name"] = name
        return _loaded["llm"]


def unload() -> None:
    """Release the model. Called before mic STT when memory_saver is on."""
    if _loaded.get("llm") is not None:
        try:
            _loaded["llm"].close()
        except Exception:
            pass
    _loaded["llm"] = None
    _loaded["name"] = None


def _llamacpp_call(model: str, system: str, user: str) -> str:
    llm = _get_llama(model)
    r = llm.create_chat_completion(
        messages=[{"role": "system", "content": system},
                  {"role": "user", "content": user}],
        temperature=float(os.environ.get("AWAZ_LLM_TEMP", "0.2")),
        max_tokens=int(os.environ.get("AWAZ_LLM_MAX_TOKENS", "512")))
    return (r["choices"][0]["message"]["content"] or "").strip()


# --------------------------------------------------------------- ollama path
def _ollama_call(model: str, system: str, user: str) -> str:
    body = json.dumps({
        "model": model, "stream": False,
        "messages": [{"role": "system", "content": system},
                     {"role": "user", "content": user}],
        "options": {"temperature": float(os.environ.get("AWAZ_LLM_TEMP", "0.2")),
                    "num_ctx": _ctx(),
                    "num_gpu": int(os.environ.get("AWAZ_LLM_GPU", "0"))},
    }).encode()
    req = urllib.request.Request(OLLAMA + "/api/chat", data=body,
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=180) as r:
        j = json.loads(r.read())
    if "message" not in j:
        raise RuntimeError(str(j.get("error") or "ollama returned no message"))
    return j["message"]["content"].strip()


# -------------------------------------------------------------------- public
def call(model: str, system: str, user: str) -> str:
    b = backend()
    if b == "llamacpp":
        return _llamacpp_call(model, system, user)
    if b == "ollama":
        return _ollama_call(model, system, user)
    raise RuntimeError(
        "no LLM backend: no GGUF in models/llm and no Ollama on 127.0.0.1:11434")


def status() -> dict:
    b = backend()
    return {"backend": b, "models": available_models(), "loaded": _loaded["name"],
            "gguf_dir": llm_dir(), "gguf": gguf_models(),
            "ollama_up": ollama_up() if b != "llamacpp" else False}
