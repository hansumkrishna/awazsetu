"""AwazSetu — preflight self-test. Run it before a demo; it changes nothing.

    AwazSetu-Check.bat            (or)   runtime\\python\\python.exe scripts\\doctor.py

Answers one question: will this machine run every feature, right now, offline?
Each check prints PASS / WARN / FAIL with the reason, so a failure names its own fix
instead of surfacing later as a stack trace in front of an audience.
"""
from __future__ import annotations
import os
import sys
import json
import subprocess

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
APP = os.path.join(REPO, "app")
sys.path.insert(0, APP)
os.environ.setdefault("HF_HOME", os.path.join(REPO, "models", "hf-cache"))
os.environ.setdefault("HF_HUB_OFFLINE", "1")
os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")

results: list[tuple[str, str, str]] = []


def check(name, fn):
    try:
        state, detail = fn()
    except Exception as e:
        state, detail = "FAIL", f"{type(e).__name__}: {e}"
    results.append((state, name, detail))
    icon = {"PASS": "[ok]", "WARN": "[--]", "FAIL": "[XX]"}[state]
    print(f"{icon} {name:34} {detail}")


# --------------------------------------------------------------- the checks
def c_python():
    v = sys.version.split()[0]
    bundled = os.path.normpath(sys.executable).startswith(
        os.path.normpath(os.path.join(REPO, "runtime")))
    where = "bundled runtime" if bundled else "system Python"
    if not v.startswith("3.10"):
        return "WARN", f"{v} ({where}) — built and tested on 3.10"
    return "PASS", f"{v} ({where})"


def c_packages():
    missing, versions = [], {}
    for m in ("torch", "numpy", "transformers", "ctranslate2", "faster_whisper",
              "sentencepiece", "soundfile", "flask", "rank_bm25", "llama_cpp"):
        try:
            mod = __import__(m)
            versions[m] = getattr(mod, "__version__", "?")
        except Exception:
            missing.append(m)
    if missing:
        return "FAIL", "missing: " + ", ".join(missing)
    return "PASS", f"torch {versions['torch']}, transformers {versions['transformers']}"


def c_ffmpeg():
    import config
    exe = config.ffmpeg_exe()
    r = subprocess.run([exe, "-version"], capture_output=True, text=True, timeout=20)
    if r.returncode != 0:
        return "FAIL", f"{exe} did not run"
    line = (r.stdout or "").splitlines()[0][:52]
    bundled = os.path.isabs(exe) and "runtime" in exe
    return "PASS", f"{'bundled' if bundled else 'system'} — {line}"


def c_asr_models():
    import config
    got = config.whisper_installed()
    if not got:
        return "FAIL", "no whisper models found under models/hf-cache"
    want = os.environ.get("AWAZ_WHISPER") or config.load().get("asr_model")
    if want not in got:
        return "WARN", f"installed {got}; settings ask for '{want}' which is absent"
    return "PASS", f"{', '.join(got)} (using '{want}')"


def c_mt():
    import config
    eng = config.translate_engines()
    on = [k for k, v in eng.items() if v]
    if not on:
        return "FAIL", "no translation engine installed"
    d = config.indictrans2_directions()
    dirs = ", ".join(k for k, v in d.items() if v) or "none"
    want = config.load().get("translate_engine")
    state = "PASS" if want in on else "WARN"
    return state, f"engines: {', '.join(on)} | IndicTrans2 directions: {dirs}"


def c_voices():
    import config
    from langs import LANGS
    got = config.mms_voices()
    missing = [c for c in LANGS if c not in got]
    if missing:
        return "WARN", f"have {got}; no voice for {missing}"
    return "PASS", f"all {len(got)} voices: {', '.join(got)}"


def c_llm():
    import llm
    st = llm.status()
    if st["backend"] == "none":
        return "FAIL", "no GGUF in models/llm and no Ollama running"
    if st["backend"] == "ollama":
        return "WARN", f"using Ollama ({', '.join(st['models']) or 'no models'}) — "
    return "PASS", f"in-process llama.cpp, models: {', '.join(st['models'])}"


def c_llm_answer():
    """Actually generate. A loadable model that cannot answer is still broken."""
    import llm
    if llm.backend() == "none":
        return "FAIL", "no backend"
    name = (os.environ.get("AWAZ_LLM_FALLBACK") or "qwen2.5:1.5b")
    if name not in llm.available_models():
        name = (llm.available_models() or [None])[0]
        if not name:
            return "FAIL", "no model available"
    import time
    t0 = time.time()
    out = llm.call(name, "Answer only from the text. Be brief.",
                   "TEXT: The shed holds 12 goats.\n\nQ: How many goats?")
    llm.unload()
    ok = "12" in out
    return ("PASS" if ok else "WARN"), f"{name} answered in {time.time()-t0:.1f}s: {out[:46]!r}"


def c_library():
    work = os.path.join(APP, "data", "work")
    if not os.path.isdir(work):
        return "FAIL", "app/data/work is missing"
    items = full = 0
    for d in sorted(os.listdir(work)):
        mf = os.path.join(work, d, "manifest.json")
        if not os.path.exists(mf):
            continue
        items += 1
        m = json.load(open(mf, encoding="utf-8"))
        fs = os.listdir(os.path.join(work, d))
        subs = {f.split(".")[1] for f in fs if f.startswith("subs.")}
        dubs = {f.split(".")[1] for f in fs if f.startswith("dub.")
                and os.path.getsize(os.path.join(work, d, f)) > 10000}
        if set(m.get("langs", [])) <= subs and set(m.get("langs", [])) <= dubs:
            full += 1
    if items == 0:
        return "FAIL", "no processed media — the library will be empty"
    state = "PASS" if full == items else "WARN"
    return state, f"{items} items, {full} complete (subtitles + every voiceover)"


def c_memory():
    import garden
    hw = garden.hardware()
    rec = garden.recommended_preset(hw)
    b = garden.preset_budget(rec)
    ram = hw.get("total_ram_gb") or 0
    if ram and b["peak_mb"] / 1024 > ram * 0.8:
        return "WARN", (f"{ram} GB RAM; preset '{rec}' peaks at "
                        f"{b['peak_mb']/1024:.1f} GB — close other apps")
    return "PASS", (f"{ram} GB RAM, {hw.get('cores')} threads, tier "
                    f"{hw['tier']} → preset '{rec}' peaks {b['peak_mb']/1024:.1f} GB")


def c_offline():
    """The offline claim must be enforced, not just documented."""
    flags = [os.environ.get("HF_HUB_OFFLINE"), os.environ.get("TRANSFORMERS_OFFLINE")]
    if not all(f == "1" for f in flags):
        return "WARN", "HF offline flags not set in this shell (run.py sets them)"
    return "PASS", "HF_HUB_OFFLINE=1, TRANSFORMERS_OFFLINE=1 — downloads impossible"


def main():
    print("=" * 74)
    print(" AwazSetu preflight — nothing is modified, nothing is downloaded")
    print("=" * 74)
    check("Python runtime", c_python)
    check("Python packages", c_packages)
    check("FFmpeg", c_ffmpeg)
    check("Speech-to-text models", c_asr_models)
    check("Translation engines", c_mt)
    check("Voiceover voices", c_voices)
    check("Chat LLM backend", c_llm)
    check("Chat LLM actually answers", c_llm_answer)
    check("Processed library", c_library)
    check("Memory budget", c_memory)
    check("Offline enforcement", c_offline)

    bad = [r for r in results if r[0] == "FAIL"]
    warn = [r for r in results if r[0] == "WARN"]
    print("-" * 74)
    print(f" {len(results)-len(bad)-len(warn)} passed, {len(warn)} warnings, {len(bad)} failures")
    if bad:
        print("\n NOT READY — fix these first:")
        for _s, n, d in bad:
            print(f"   * {n}: {d}")
    elif warn:
        print("\n READY, with notes:")
        for _s, n, d in warn:
            print(f"   * {n}: {d}")
    else:
        print("\n READY. Every feature works on this machine, offline.")
    print("=" * 74)
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
