"""AwazSetu — chat with the video.

RAG grounded strictly in the transcript: BM25 retrieval (zero-download, RAM-light)
+ a small local LLM via Ollama. The LLM is only reached in chat mode, so its memory
is never co-resident with ASR/MT (staged loading).

    from chat import answer
    answer(manifest, "which breed is discussed?", lang="mr")
    -> {"answer": "...", "sources": [...], "grounded": True}

Design rules learned the hard way:
  * NEVER machine-translate an error or refusal string — that produced the
    "[LLM त्रुटिः ]" screen. UI strings are pre-written per language.
  * A confident wrong answer is worse than an honest "not covered". The model must
    emit NOT_IN_TRANSCRIPT when the fact is absent, and we surface the closest lines.
  * Retrieval that scores 0 everywhere means "no keyword match", NOT "take the first
    three segments" — the old fallback made every answer cite 0:04/0:35/0:43.
"""
from __future__ import annotations
import os
import re
import json
import urllib.request

OLLAMA = os.environ.get("OLLAMA_URL", "http://127.0.0.1:11434")
# Read at CALL time (not import time) so the Settings page actually switches models
# without restarting the server.
def _model() -> str:
    return os.environ.get("AWAZ_LLM", "qwen2.5:3b")


def _fallback() -> str:
    return os.environ.get("AWAZ_LLM_FALLBACK", "qwen2.5:1.5b")
LANG_FULL = {"hi": "Hindi", "mr": "Marathi", "en": "English"}
SENTINEL = "NOT_IN_TRANSCRIPT"

# Pre-written UI strings. Never machine-translated (that is how an error message
# once reached the user as "[LLM त्रुटिः ]" with no diagnostic at all).
STR_NOT_COVERED = {
    "en": "This video does not cover that. The closest lines I found are below.",
    "hi": "इस वीडियो में इसकी जानकारी नहीं है। सबसे नज़दीकी पंक्तियाँ नीचे दी गई हैं।",
    "mr": "या व्हिडिओमध्ये याची माहिती नाही. सर्वात जवळच्या ओळी खाली दिल्या आहेत.",
}
STR_LLM_DOWN = {
    "en": ("The local AI model could not be loaded — not enough free memory. "
           "Close other applications, or pick a smaller chat model in Settings."),
    "hi": ("स्थानीय AI मॉडल लोड नहीं हो सका — पर्याप्त मेमोरी नहीं है। "
           "कृपया अन्य ऐप बंद करें, या सेटिंग्स में छोटा मॉडल चुनें।"),
    "mr": ("स्थानिक AI मॉडेल लोड होऊ शकले नाही — पुरेशी मेमरी नाही. "
           "कृपया इतर अ‍ॅप्स बंद करा, किंवा सेटिंग्जमध्ये लहान मॉडेल निवडा."),
}
STR_LOW_ASR = {
    "en": "Note: the audio was hard to transcribe, so this answer may be imprecise.",
    "hi": "सूचना: ऑडियो स्पष्ट न होने के कारण यह उत्तर अनुमानित हो सकता है।",
    "mr": "सूचना: ऑडिओ स्पष्ट नसल्याने हे उत्तर अचूक नसू शकते.",
}

_bm25_cache: dict[str, tuple] = {}


def _tok(s: str) -> list[str]:
    return re.findall(r"\w+", s.lower(), flags=re.UNICODE)


def _retrieve(m: dict, q: str, k: int = 5) -> tuple[list[dict], float]:
    """Return (chronological hits, best_score). best_score == 0 means NO keyword match."""
    from rank_bm25 import BM25Okapi
    vid = m["id"]
    if vid not in _bm25_cache:
        segs = m["segments"]
        # index every language version of each segment -> cross-lingual retrieval
        corpus = [_tok(" ".join((s.get("t") or {}).values()) + " " + s["text"]) for s in segs]
        _bm25_cache[vid] = (BM25Okapi(corpus), segs)
    bm25, segs = _bm25_cache[vid]
    scores = bm25.get_scores(_tok(q))
    order = sorted(range(len(segs)), key=lambda i: scores[i], reverse=True)[:k]
    best = float(scores[order[0]]) if order else 0.0
    hits = [i for i in order if scores[i] > 0]
    if not hits:
        # No lexical match. Return the head of the video as *context only* — the caller
        # must not present these as citations for a specific factual question.
        hits = order
    return [segs[i] for i in sorted(hits)], best


def _ollama_call(model: str, system: str, user: str) -> str:
    body = json.dumps({
        "model": model, "stream": False,
        "messages": [{"role": "system", "content": system},
                     {"role": "user", "content": user}],
        "options": {"temperature": float(os.environ.get("AWAZ_LLM_TEMP", "0.2")),
                    "num_ctx": int(os.environ.get("AWAZ_LLM_CTX", "8192")),
                    "num_gpu": int(os.environ.get("AWAZ_LLM_GPU", "0"))},
    }).encode()
    req = urllib.request.Request(OLLAMA + "/api/chat", data=body,
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=180) as r:
        j = json.loads(r.read())
    if "message" not in j:
        raise RuntimeError(str(j.get("error") or "ollama returned no message"))
    return j["message"]["content"].strip()


def _describe(e: Exception) -> str:
    """Exceptions with an empty str() produced the infamous '[LLM error: ]'."""
    return f"{type(e).__name__}: {e}" if str(e).strip() else type(e).__name__


def _ollama_chat(system: str, user: str) -> str:
    """Try the primary model, then the smaller fallback. Raise with BOTH reasons."""
    try:
        primary = _model()
        return _ollama_call(primary, system, user)
    except Exception as e1:
        try:
            fb = _fallback()
            return _ollama_call(fb, system, user)
        except Exception as e2:
            raise RuntimeError(
                f"{_model()} -> {_describe(e1)} | {_fallback()} -> {_describe(e2)}") from e2


def _mt_run(text: str, src: str, tgt: str, engine: str) -> str | None:
    import subprocess
    import tempfile
    import sys
    if engine in ("indictrans2", "it2", "indic"):
        worker, job = "indictrans_worker.py", {
            "src": src, "targets": [tgt], "sentences": [text], "threads": 4}
    else:
        model_dir = os.environ.get("AWAZ_NLLB_CT2_DIR")
        if not model_dir:
            return None
        worker, job = "translate_worker.py", {
            "model_dir": model_dir, "src": src, "targets": [tgt],
            "sentences": [text], "threads": 4}
    wpath = os.path.join(os.path.dirname(__file__), worker)
    try:
        with tempfile.TemporaryDirectory() as d:
            jf, of = os.path.join(d, "j.json"), os.path.join(d, "o.json")
            with open(jf, "w", encoding="utf-8") as f:
                json.dump(job, f, ensure_ascii=False)
            subprocess.run([sys.executable, wpath, jf, of], check=True, timeout=180)
            with open(of, encoding="utf-8") as f:
                out = json.load(f).get(tgt) or []
            return out[0] if out else None
    except Exception:
        return None


def _mt(text: str, src: str, tgt: str) -> str | None:
    """Translate one string out-of-process. Prefers the configured engine, then NLLB
    (ungated, covers every hi/mr/en direction)."""
    if src == tgt or not text.strip():
        return text
    engines = dict.fromkeys([os.environ.get("AWAZ_CHAT_MT", "nllb").lower(), "nllb"])
    for engine in engines:
        r = _mt_run(text, src, tgt, engine)
        if r:
            return r
    return None


def _fmt_segs(ss, prefer: str = "en") -> str:
    """Render segments for the LLM, preferring the English translation.

    The source is usually Devanagari, which costs roughly three times the tokens of
    the same sentence in English. Sending Marathi overflowed num_ctx, so the model
    silently saw only a fragment - which made it answer NOT_IN_TRANSCRIPT even for
    "what is this video about?".
    """
    out = []
    for h in ss:
        txt = (h.get("t") or {}).get(prefer) or h["text"]
        out.append(f"[{int(h['start'])//60}:{int(h['start']) % 60:02d}] {txt}")
    return "\n".join(out)


def answer(m: dict, q: str, lang: str = "hi", history: list | None = None) -> dict:
    segs = m["segments"]
    lang = lang if lang in LANG_FULL else "en"
    src_name = LANG_FULL.get(m.get("src_lang", "hi"), "the source language")
    total_words = sum(len(s["text"].split()) for s in segs)

    key, best = _retrieve(m, q, k=6)
    mode = os.environ.get("AWAZ_RETRIEVAL", "foreground")
    limit = int(os.environ.get("AWAZ_CTX_SEGMENTS", "180"))
    whole = _fmt_segs(segs[:limit])
    if mode == "retrieval" and best > 0:
        ctx = _fmt_segs(key)
    elif best > 0:
        ctx = ("MOST RELEVANT LINES:\n" + _fmt_segs(key)
               + "\n\nFULL TRANSCRIPT:\n" + whole)
    else:
        # No keyword hit -> almost always a general question ("what is this about?").
        # Summarising needs the whole transcript; the old head-only fallback made the
        # model answer NOT_IN_TRANSCRIPT for the most common question of all.
        ctx = "FULL TRANSCRIPT:\n" + whole

    # Reason in English (the small model's strongest language), then translate out.
    q_en = q if lang == "en" else (_mt(q, lang, "en") or q)

    try:
        from glossary import terms_table
        gloss = terms_table(m.get("src_lang", "hi"))
    except Exception:
        gloss = ""

    system = (
        f"You are AwazSetu, answering questions about ONE video. The transcript below "
        f"(in {src_name}) is your ONLY source of truth.\n"
        f"RULES:\n"
        f"1. Use ONLY facts present in the transcript. Never use outside knowledge.\n"
        f"2. If the transcript does not contain the answer, reply with EXACTLY the token "
        f"{SENTINEL} and nothing else. Do not guess. Do not invent a topic.\n"
        f"2b. EXCEPTION: a GENERAL question about the video as a whole (what is it "
        f"about, summarise it, who is it for, what does it teach) can always be "
        f"answered from the transcript overall - never reply {SENTINEL} to those.\n"
        f"3. The transcript may contain speech-recognition errors. If it is too garbled "
        f"to determine the answer, reply {SENTINEL}.\n"
        f"4. Answer only what is asked, in 1-2 sentences, quoting exact numbers and names.\n"
        f"5. Reply in English."
        + (f"\nDomain terms: {gloss}" if gloss else ""))

    convo = ""
    if history:
        convo = "EARLIER Q&A (for follow-up context):\n" + "\n".join(
            f"Q: {h.get('q', '')}  A: {h.get('a', '')}" for h in history[-3:]) + "\n\n"
    user = (f"VIDEO TRANSCRIPT (with [mm:ss] timings):\n{ctx}\n\n{convo}"
            f"QUESTION: {q_en}\n\nAnswer in English, or {SENTINEL}:")

    grounded, llm_ok = True, True
    try:
        ans_en = _ollama_chat(system, user)
    except Exception as e:
        llm_ok, grounded = False, False
        ans_en = ""
        err = _describe(e)
        try:
            import sys
            print(f"[chat] LLM unavailable -> {err}", file=sys.stderr, flush=True)
        except Exception:
            pass

    if not llm_ok:
        # Honest, readable, already in the user's language — never machine-translated.
        return {"answer": STR_LLM_DOWN.get(lang, STR_LLM_DOWN["en"]),
                "sources": [], "grounded": False, "error": err}

    if SENTINEL in ans_en.upper() or not ans_en.strip():
        grounded = False
        near, _ = _retrieve(m, q, k=3)
        return {"answer": STR_NOT_COVERED.get(lang, STR_NOT_COVERED["en"]),
                "sources": [{"start": h["start"], "text": h["text"]} for h in near],
                "grounded": False}

    ans = ans_en if lang == "en" else (_mt(ans_en, "en", lang) or ans_en)
    try:  # enforce BAIF terminology in the answer too
        from glossary import correct_target
        ans = correct_target(ans, lang)
    except Exception:
        pass

    # Be upfront when the transcript itself was unreliable.
    conf = m.get("asr_confidence") or {}
    if conf and not conf.get("usable", True):
        ans = ans + "\n\n" + STR_LOW_ASR.get(lang, STR_LOW_ASR["en"])

    # Citations only when retrieval actually matched; otherwise the chips are noise.
    if best > 0:
        src, _ = _retrieve(m, q, k=3)
        sources = [{"start": h["start"], "text": h["text"]} for h in src]
    else:
        sources = []
    return {"answer": ans, "sources": sources, "grounded": grounded}


if __name__ == "__main__":
    import sys
    base = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "work")
    ids = sorted(d for d in os.listdir(base)
                 if os.path.exists(os.path.join(base, d, "manifest.json")))
    work = os.path.join(base, sys.argv[3] if len(sys.argv) > 3 else ids[0])
    m = json.load(open(os.path.join(work, "manifest.json"), encoding="utf-8"))
    q = sys.argv[1] if len(sys.argv) > 1 else "What is this video about?"
    lang = sys.argv[2] if len(sys.argv) > 2 else "en"
    print(json.dumps(answer(m, q, lang), ensure_ascii=False, indent=1))
