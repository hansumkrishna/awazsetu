"""AwazSetu — the Model Garden: every model, scored on every axis that matters offline.

The Settings page could already switch models, but it could not answer the question an
operator actually has: *which* model should I pick, for *which* language, on *this*
laptop? This module holds one catalogue that answers it, plus the hardware probe and
the presets the Garden page applies.

Scoring rules:
  * `q` is per-language quality, 1-5, and **None means the model cannot do that
    language at all** — which is very different from "does it badly". Whisper has no
    Odia token, so every ASR row scores `None` for `or`; Odia reaches the user through
    translation and voiceover instead.
  * `measured: True` marks a number observed on this project's own media. Everything
    else is published/expected behaviour and is labelled as such in the UI, so a
    reviewer can tell evidence from estimate.
  * `ram_mb` is resident size while running, used for the RAM-budget arithmetic. It is
    what decides whether a preset fits a 16 GB machine, so it is deliberately
    conservative.

Sizes are the real on-disk footprints of this repo's models/ tree, not download sizes.
"""
from __future__ import annotations
import os
import shutil

from langs import LANGS

TASKS = {
    "asr": "Speech → text",
    "mt":  "Translation",
    "tts": "Voiceover",
    "llm": "Chat & voice assistant",
}

# Hardware tiers. `baseline` is the BAIF-specified target machine
# (Intel i5 11th gen+ / Ryzen 5, 6+ cores, 16 GB RAM, Windows 11, no discrete GPU).
TIERS = {
    "lean":        {"label": "Lean",        "ram_gb": 8,  "cores": 4,
                    "note": "8 GB RAM. Everything still runs, but one model at a time."},
    "baseline":    {"label": "Baseline",    "ram_gb": 16, "cores": 6,
                    "note": "The BAIF target machine: i5 11th gen+ / Ryzen 5, 16 GB, no GPU."},
    "workstation": {"label": "Workstation", "ram_gb": 32, "cores": 8,
                    "note": "32 GB or a CUDA GPU. Highest quality with no compromise."},
}

CATALOG = [
    # ---------------------------------------------------------------- ASR
    {"id": "tiny", "task": "asr", "licence": "MIT", "load_s": 1.2, "name": "Whisper tiny", "engine": "faster-whisper INT8",
     "q": {"en": 2, "hi": 1, "mr": 1, "or": None}, "speed": 5, "ram_mb": 150, "disk_mb": 75,
     "min_ram_gb": 4, "measured": False,
     "note": "Fastest by far, but Latin-script only in practice. Do not use for Indic."},
    {"id": "base", "task": "asr", "licence": "MIT", "load_s": 1.8, "name": "Whisper base", "engine": "faster-whisper INT8",
     "q": {"en": 3, "hi": 2, "mr": 1, "or": None}, "speed": 5, "ram_mb": 250, "disk_mb": 142,
     "min_ram_gb": 4, "measured": True,
     "note": "Measured: transcribed Hindi speech into Urdu script. Avoid for Indic."},
    {"id": "small", "task": "asr", "licence": "MIT", "load_s": 3.0, "name": "Whisper small", "engine": "faster-whisper INT8",
     "q": {"en": 4, "hi": 3, "mr": 2, "or": None}, "speed": 4, "ram_mb": 600, "disk_mb": 464,
     "min_ram_gb": 8, "measured": True,
     "note": "Measured: Marathi output was garbled. Fine for English and for the live mic, "
             "where latency matters more than the last word."},
    {"id": "medium", "task": "asr", "licence": "MIT", "load_s": 5.0, "name": "Whisper medium", "engine": "faster-whisper INT8",
     "q": {"en": 5, "hi": 4, "mr": 4, "or": None}, "speed": 3, "ram_mb": 1600, "disk_mb": 1460,
     "min_ram_gb": 8, "measured": True,
     "note": "The best quality-per-second on a CPU-only machine. Produced meaningful Marathi."},
    {"id": "large-v3", "task": "asr", "licence": "MIT", "load_s": 6.9, "name": "Whisper large-v3", "engine": "faster-whisper INT8",
     "q": {"en": 5, "hi": 5, "mr": 5, "or": None}, "speed": 2, "ram_mb": 3200, "disk_mb": 2948,
     "min_ram_gb": 16, "measured": True,
     "note": "Best accuracy available offline. Measured on a 4 GB laptop GPU at "
             "int8_float16: loads in 6.9 s, RTF 0.34 — it does NOT OOM, contrary to the "
             "earlier note. On CPU it is roughly 3× slower than medium, which is fine for "
             "one-time processing but not for the live mic."},

    # ----------------------------------------------------------------- MT
    {"id": "indictrans2", "task": "mt", "licence": "MIT", "load_s": 22.0, "name": "IndicTrans2 (distilled)",
     "engine": "AI4Bharat 200M/320M",
     "q": {"en": 5, "hi": 5, "mr": 5, "or": 5}, "speed": 3, "ram_mb": 1200, "disk_mb": 6317,
     "min_ram_gb": 8, "measured": True,
     "note": "DEFAULT. Purpose-built for Indian languages; hi↔mr and hi↔or go direct with "
             "no English pivot, which is where NLLB loses the meaning. Ships as three "
             "direction checkpoints (indic→en, en→indic, indic→indic)."},
    {"id": "nllb", "task": "mt", "licence": "CC-BY-NC 4.0", "load_s": 6.0, "name": "NLLB-200 distilled 600M",
     "engine": "CTranslate2 INT8",
     "q": {"en": 4, "hi": 3, "mr": 2, "or": 2}, "speed": 4, "ram_mb": 700, "disk_mb": 640,
     "min_ram_gb": 4, "measured": True,
     "note": "Fallback. Smaller and faster, but measured to mistranslate domain terms: "
             "it rendered 'tubers' as a fungus in Marathi, as pots in Hindi, and as a bush "
             "in Odia. Use only when disk is tight."},

    # ---------------------------------------------------------------- TTS
    {"id": "mms-hin", "task": "tts", "licence": "CC-BY-NC 4.0", "load_s": 4.0, "name": "MMS-TTS Hindi", "engine": "VITS", "lang": "hi",
     "q": {"en": None, "hi": 4, "mr": None, "or": None}, "speed": 4, "ram_mb": 400,
     "disk_mb": 278, "min_ram_gb": 4, "measured": True, "note": "Clear Hindi voiceover."},
    {"id": "mms-mar", "task": "tts", "licence": "CC-BY-NC 4.0", "load_s": 4.0, "name": "MMS-TTS Marathi", "engine": "VITS", "lang": "mr",
     "q": {"en": None, "hi": None, "mr": 4, "or": None}, "speed": 4, "ram_mb": 400,
     "disk_mb": 278, "min_ram_gb": 4, "measured": True,
     "note": "Ships with phonemize=True, which would demand espeak-ng. Its vocabulary is "
             "in fact 60 Devanagari tokens, so the flag is forced off and Marathi speech "
             "works with no extra system dependency."},
    {"id": "mms-eng", "task": "tts", "licence": "CC-BY-NC 4.0", "load_s": 3.0, "name": "MMS-TTS English", "engine": "VITS", "lang": "en",
     "q": {"en": 4, "hi": None, "mr": None, "or": None}, "speed": 5, "ram_mb": 300,
     "disk_mb": 139, "min_ram_gb": 4, "measured": True, "note": "Fastest voice; smallest file."},
    {"id": "mms-ory", "task": "tts", "licence": "CC-BY-NC 4.0", "load_s": 4.0, "name": "MMS-TTS Odia", "engine": "VITS", "lang": "or",
     "q": {"en": None, "hi": None, "mr": None, "or": 4}, "speed": 4, "ram_mb": 400,
     "disk_mb": 278, "min_ram_gb": 4, "measured": True,
     "note": "Gives Odia a voice even though no ASR model can transcribe Odia — the route "
             "is Marathi/Hindi speech → IndicTrans2 → Odia voiceover."},

    # ---------------------------------------------------------------- LLM
    {"id": "qwen2.5:3b", "task": "llm", "licence": "Apache 2.0", "load_s": 2.4, "name": "Qwen 2.5 3B Instruct", "engine": "GGUF Q4_K_M",
     "q": {"en": 4, "hi": 3, "mr": 3, "or": 2}, "speed": 3, "ram_mb": 2600, "disk_mb": 1930,
     "min_ram_gb": 8, "measured": True,
     "note": "RECOMMENDED. Reasons in English over the transcript, then the answer is "
             "translated by IndicTrans2 — markedly better than asking a 3B model to "
             "compose directly in Marathi or Odia."},
    {"id": "qwen2.5:1.5b", "task": "llm", "licence": "Apache 2.0", "load_s": 1.1, "name": "Qwen 2.5 1.5B Instruct", "engine": "GGUF Q4_K_M",
     "q": {"en": 3, "hi": 2, "mr": 2, "or": 2}, "speed": 5, "ram_mb": 1400, "disk_mb": 986,
     "min_ram_gb": 4, "measured": True,
     "note": "Automatic fallback when the 3B will not fit. Measured at 0.6 s for a short "
             "grounded answer. Weaker reasoning, so it is held to short replies."},
]

# Presets. Each names one model per task; the Garden shows the resulting RAM budget
# before it is applied, so nothing is chosen that the machine cannot hold.
PRESETS = {
    "max_quality": {
        "label": "Maximum quality",
        "for": "workstation",
        "why": "Every best-in-class model. Processing is slower, playback is not — all "
               "assets are built once, up front.",
        "settings": {"asr_model": "large-v3", "mic_model": "small",
                     "translate_engine": "indictrans2", "chat_llm": "qwen2.5:3b",
                     "chat_llm_fallback": "qwen2.5:1.5b", "beam": 5, "memory_saver": False},
    },
    "balanced": {
        "label": "Balanced",
        "for": "baseline",
        "why": "The recommended setting for the 16 GB target machine: near-best Indic "
               "accuracy at roughly a third of large-v3's processing time.",
        "settings": {"asr_model": "medium", "mic_model": "small",
                     "translate_engine": "indictrans2", "chat_llm": "qwen2.5:3b",
                     "chat_llm_fallback": "qwen2.5:1.5b", "beam": 5, "memory_saver": True},
    },
    "fast_low_ram": {
        "label": "Fast & low RAM",
        "for": "lean",
        "why": "For an 8 GB machine or when other applications must stay open. Indic "
               "transcription quality drops noticeably — prefer it only for English.",
        "settings": {"asr_model": "small", "mic_model": "tiny",
                     "translate_engine": "nllb", "chat_llm": "qwen2.5:1.5b",
                     "chat_llm_fallback": "qwen2.5:1.5b", "beam": 1, "memory_saver": True},
    },
    "demo_safe": {
        "label": "Demo-safe",
        "for": "baseline",
        "why": "Nothing heavy loads during a live demo. Everything on screen is already "
               "precomputed, so this only governs the chat assistant and any new upload.",
        "settings": {"asr_model": "medium", "mic_model": "small",
                     "translate_engine": "indictrans2", "chat_llm": "qwen2.5:1.5b",
                     "chat_llm_fallback": "qwen2.5:1.5b", "beam": 5, "memory_saver": True},
    },
}


# ------------------------------------------------------------------ hardware
def hardware() -> dict:
    """Probe this machine. Everything degrades gracefully if a probe is unavailable."""
    import config as _c
    total_gb = cores = None
    try:
        import psutil
        total_gb = round(psutil.virtual_memory().total / (1024 ** 3), 1)
        cores = psutil.cpu_count(logical=True)
    except Exception:
        cores = os.cpu_count()
    gpu = None
    try:
        import torch
        if torch.cuda.is_available():
            p = torch.cuda.get_device_properties(0)
            gpu = {"name": p.name, "vram_gb": round(p.total_memory / (1024 ** 3), 1)}
    except Exception:
        pass
    free_disk_gb = None
    try:
        free_disk_gb = round(shutil.disk_usage(_c.models_dir()).free / (1024 ** 3), 1)
    except Exception:
        pass
    free_ram = _c.free_ram_mb()
    if total_gb is None and free_ram:
        total_gb = round(free_ram / 1024, 1)

    tier = "lean"
    if (total_gb or 0) >= 28 or gpu:
        tier = "workstation"
    elif (total_gb or 0) >= 14:
        tier = "baseline"
    return {"total_ram_gb": total_gb, "free_ram_mb": free_ram, "cores": cores,
            "gpu": gpu, "free_disk_gb": free_disk_gb, "tier": tier,
            "tier_label": TIERS[tier]["label"], "tier_note": TIERS[tier]["note"]}


# ------------------------------------------------------------- installed set
def installed_ids() -> set:
    """Which catalogue entries have real weights on this machine right now."""
    import config as _c
    import llm as _llm
    out = set(_c.whisper_installed())
    for k, v in _c.translate_engines().items():
        if v:
            out.add(k)
    for code in _c.mms_voices():
        out.add("mms-" + LANGS[code]["mms"].split("-")[-1])
    out |= set(_llm.available_models())
    return out


def fits(entry: dict, hw: dict) -> bool:
    """Does this model fit the machine?

    The 5 % tolerance is not slack: Windows reports usable RAM, so a genuine 16 GB
    laptop — the BAIF target — reports about 15.4 GB. A strict `>= 16` comparison
    marked large-v3 as not fitting the very machine it is specified for.
    """
    ram = hw.get("total_ram_gb")
    return ram is None or ram >= entry.get("min_ram_gb", 0) * 0.95


def catalog(hw: dict | None = None) -> list:
    """The catalogue, annotated with install state and fit for THIS machine."""
    hw = hw or hardware()
    have = installed_ids()
    rows = []
    for e in CATALOG:
        r = dict(e)
        r["installed"] = e["id"] in have
        r["fits"] = fits(e, hw)
        r["task_label"] = TASKS[e["task"]]
        rows.append(r)
    return rows


def preset_budget(name: str) -> dict:
    """Peak RAM a preset needs. Stages are sequential, so the peak is the largest single
    stage plus the LLM, which is the only thing that can be resident during playback."""
    p = PRESETS[name]["settings"]
    by_id = {e["id"]: e for e in CATALOG}
    stage = max((by_id[p[k]]["ram_mb"] for k in ("asr_model",) if p.get(k) in by_id),
                default=0)
    mt = by_id.get(p.get("translate_engine"), {}).get("ram_mb", 0)
    llm_mb = by_id.get(p.get("chat_llm"), {}).get("ram_mb", 0)
    tts = max((e["ram_mb"] for e in CATALOG if e["task"] == "tts"), default=0)
    return {"processing_mb": max(stage, mt, tts), "chat_mb": llm_mb,
            "peak_mb": max(stage, mt, tts) + llm_mb}


def recommended_preset(hw: dict | None = None) -> str:
    hw = hw or hardware()
    for name, p in PRESETS.items():
        if p["for"] == hw["tier"] and name != "demo_safe":
            return name
    return "balanced"


def best_picks(hw: dict | None = None) -> dict:
    """The preference matrix: for each task × language, what to actually use here.

    This is the question the catalogue implies but never states outright. Ranking is
    quality first, then speed, then a smaller footprint — but only among models that
    are installed AND fit this machine's memory, so the answer is actionable rather
    than aspirational. `None` means no model can do that pair at all, which is a real
    answer (every ASR × Odia cell) and is shown as such rather than left blank.
    """
    hw = hw or hardware()
    have = installed_ids()
    out = {}
    for task in TASKS:
        row = {}
        for L in LANGS:
            cands = [e for e in CATALOG
                     if e["task"] == task and e["q"].get(L) and e["id"] in have
                     and fits(e, hw)]
            if not cands:
                # fall back to anything that CAN do it, so the UI can say
                # "possible, but not installed / does not fit" instead of "impossible"
                other = [e for e in CATALOG if e["task"] == task and e["q"].get(L)]
                row[L] = {"id": None, "why": ("not installed" if other
                                              else "no model supports this")}
                continue
            best = sorted(cands, key=lambda e: (-e["q"][L], -e["speed"], e["ram_mb"]))[0]
            alt = [e for e in cands if e["id"] != best["id"]]
            row[L] = {"id": best["id"], "name": best["name"], "q": best["q"][L],
                      "ram_mb": best["ram_mb"], "speed": best["speed"],
                      "why": _why(best, L, alt)}
        out[task] = row
    return out


def _why(best: dict, L: str, alt: list) -> str:
    """One sentence explaining the pick, in terms of the runner-up."""
    if not alt:
        return "the only installed model that covers this language"
    second = sorted(alt, key=lambda e: (-e["q"][L], -e["speed"], e["ram_mb"]))[0]
    if best["q"][L] > second["q"][L]:
        return (f"scores {best['q'][L]}/5 against {second['q'][L]}/5 for "
                f"{second['name']}")
    if best["speed"] > second["speed"]:
        return f"same quality as {second['name']} but faster"
    return f"same quality as {second['name']} in less memory"


def overview(hw: dict | None = None) -> dict:
    hw = hw or hardware()
    rows = catalog(hw)
    presets = {}
    for k, v in PRESETS.items():
        need = set(v["settings"][x] for x in ("asr_model", "mic_model",
                                              "translate_engine", "chat_llm"))
        have = installed_ids()
        presets[k] = dict(v, budget=preset_budget(k),
                          available=need.issubset(have),
                          missing=sorted(need - have))
    return {"hardware": hw, "tiers": TIERS, "tasks": TASKS, "catalog": rows,
            "best": best_picks(hw),
            "presets": presets, "recommended": recommended_preset(hw),
            "langs": {k: {"name": v["name"], "native": v["native"], "asr": v["asr"]}
                      for k, v in LANGS.items()},
            "total_disk_mb": sum(e["disk_mb"] for e in CATALOG if e["id"] in installed_ids())}
