"""AwazSetu — chat with the video.

RAG grounded strictly in the transcript: BM25 retrieval (zero-download, RAM-light)
+ a small local LLM (llm.py: in-process llama.cpp, or Ollama if this machine
already runs it). The LLM is only reached in chat mode, so its memory
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
# Read at CALL time (not import time) so the Settings page actually switches models
# without restarting the server.
def _model() -> str:
    return os.environ.get("AWAZ_LLM", "qwen2.5:3b")


def _fallback() -> str:
    return os.environ.get("AWAZ_LLM_FALLBACK", "qwen2.5:1.5b")
from langs import LANG_FULL  # single source of truth for language codes
SENTINEL = "NOT_IN_TRANSCRIPT"

# Pre-written UI strings. Never machine-translated (that is how an error message
# once reached the user as "[LLM त्रुटिः ]" with no diagnostic at all).
STR_NOT_COVERED = {
    "en": "This video does not cover that. The closest lines I found are below.",
    "hi": "इस वीडियो में इसकी जानकारी नहीं है। सबसे नज़दीकी पंक्तियाँ नीचे दी गई हैं।",
    "mr": "या व्हिडिओमध्ये याची माहिती नाही. सर्वात जवळच्या ओळी खाली दिल्या आहेत.",
    "or": "ଏହି ଭିଡିଓରେ ସେ ବିଷୟରେ କିଛି ନାହିଁ। ନିକଟତମ ଧାଡ଼ିଗୁଡ଼ିକ ତଳେ ଦିଆଯାଇଛି।",
}
STR_LLM_DOWN = {
    "en": ("The local AI model could not be loaded — not enough free memory. "
           "Close other applications, or pick a smaller chat model in Settings."),
    "hi": ("स्थानीय AI मॉडल लोड नहीं हो सका — पर्याप्त मेमोरी नहीं है। "
           "कृपया अन्य ऐप बंद करें, या सेटिंग्स में छोटा मॉडल चुनें।"),
    "mr": ("स्थानिक AI मॉडेल लोड होऊ शकले नाही — पुरेशी मेमरी नाही. "
           "कृपया इतर अ‍ॅप्स बंद करा, किंवा सेटिंग्जमध्ये लहान मॉडेल निवडा."),
    "or": ("ସ୍ଥାନୀୟ AI ମଡେଲ ଲୋଡ ହୋଇପାରିଲା ନାହିଁ — ଯଥେଷ୍ଟ ମେମୋରୀ ନାହିଁ। "
           "ଅନ୍ୟ ଆପ୍ ବନ୍ଦ କରନ୍ତୁ, କିମ୍ବା ସେଟିଂସରେ ଛୋଟ ମଡେଲ ବାଛନ୍ତୁ।"),
}
STR_LOW_ASR = {
    "en": "Note: the audio was hard to transcribe, so this answer may be imprecise.",
    "hi": "सूचना: ऑडियो स्पष्ट न होने के कारण यह उत्तर अनुमानित हो सकता है।",
    "mr": "सूचना: ऑडिओ स्पष्ट नसल्याने हे उत्तर अचूक नसू शकते.",
    "or": "ଦ୍ରଷ୍ଟବ୍ୟ: ଅଡିଓ ସ୍ପଷ୍ଟ ନ ଥିବାରୁ ଏହି ଉତ୍ତର ଅନୁମାନିକ ହୋଇପାରେ।",
}

STR_UNTRANSLATED = {
    "en": "",
    "hi": "(अनुवाद उपलब्ध नहीं हो सका, इसलिए उत्तर अंग्रेज़ी में है।)",
    "mr": "(भाषांतर होऊ शकले नाही, त्यामुळे उत्तर इंग्रजीत आहे.)",
    "or": "(ଅନୁବାଦ ହୋଇପାରିଲା ନାହିଁ, ତେଣୁ ଉତ୍ତର ଇଂରାଜୀରେ ଅଛି।)",
}

# ---------------------------------------------------------------------------
# Script checking. The reported bug was "Hindi is selected but the answer comes
# back in English" — a SILENT failure, because a translation that returned None
# fell through to the English text and looked like a normal answer. Scripts are
# decidable from Unicode alone, with no model and no guessing, so the answer is
# now checked before it is returned.
#
# It cannot separate Hindi from Marathi (both Devanagari) and does not try to.
# That pair is kept correct by passing the right FLORES tag, which the interface
# now guarantees. What this catches is the failure that actually happened:
# untranslated Latin text presented as though it were Hindi.
# ---------------------------------------------------------------------------
_DEVA = re.compile(r"[\u0900-\u097F]")   # Devanagari: Hindi, Marathi
_ORYA = re.compile(r"[\u0B00-\u0B7F]")   # Oriya: Odia
_LATIN = re.compile(r"[A-Za-z]")
SCRIPT_OF = {"hi": "deva", "mr": "deva", "en": "latin", "or": "orya"}


def script_of(text: str) -> str:
    """The dominant script of a string: deva | orya | latin | none.

    Counted rather than merely detected, because a Hindi answer legitimately
    contains Latin characters — "RTF", "AI", a breed name — and a single one of
    those must not make the string look English.
    """
    if not text:
        return "none"
    d, o, l = len(_DEVA.findall(text)), len(_ORYA.findall(text)), len(_LATIN.findall(text))
    if d == o == l == 0:
        return "none"
    return {d: "deva", o: "orya", l: "latin"}[max(d, o, l)]


def in_target_script(text: str, lang: str) -> bool:
    want = SCRIPT_OF.get(lang)
    got = script_of(text)
    return got == "none" or want is None or got == want


def is_target_language(text: str, lang: str) -> bool:
    """The real check: right script AND, for Devanagari, the right language.

    Script alone passed Marathi off as Hindi, because they share Devanagari
    completely -- which is what "it still responds in different languages"
    meant. langid separates them on closed-class words; measured over this
    project's own 920 translated segments it keeps 99.0% of correct answers and
    catches 91.5% of wrong-language ones, and every case it misses is garbled
    ASR text that mixes both languages genuinely.
    """
    if not in_target_script(text, lang):
        return False
    try:
        import langid
        return langid.is_lang(text, lang)
    except Exception:
        return True          # never let a missing helper block a real answer


_bm25_cache: dict[str, tuple] = {}
# Chat re-asks the same things constantly ("what is this about?"), and every miss
# costs a subprocess that loads a 200M checkpoint. Bounded so a long session
# cannot grow it without limit.
_mt_cache: dict[tuple, str] = {}
_MT_CACHE_MAX = 512


def _tok(s: str) -> list[str]:
    return re.findall(r"\w+", s.lower(), flags=re.UNICODE)


# How far the best segment must stand above the average one before its lines are
# worth calling "most relevant". A bare score of zero is not the right test:
# Hindi and Marathi questions carry में / है / आहे, which occur in every segment, so
# EVERY segment scores and the best one stands barely above the crowd. Measured
# on this project's media, "यह वीडियो किस बारे में है?" scored best 12.3 against a
# mean of 8.1 -- a contrast of 1.5, which is noise -- while the same question in
# English scored 4.4 against 0.54, a contrast of 8.1. Below this the lines are
# not evidence of anything and must not be shown as though they were.
MIN_CONTRAST = 3.0


def _retrieve(m: dict, q: str, k: int = 5) -> tuple[list[dict], float]:
    """Return (chronological hits, contrast).

    `contrast` is the best score divided by the mean score, not the raw best.
    A raw score says how well a segment matched; the ratio says whether that
    match means anything, which is the question the caller is actually asking.
    """
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
    if not order:
        return [], 0.0
    best = float(scores[order[0]])
    mean = float(sum(scores)) / len(scores) if len(scores) else 0.0
    contrast = (best / mean) if mean > 0 else (float("inf") if best > 0 else 0.0)
    hits = [i for i in order if scores[i] > 0] or order
    return [segs[i] for i in sorted(hits)], contrast


def _describe(e: Exception) -> str:
    """Exceptions with an empty str() produced the infamous '[LLM error: ]'."""
    return f"{type(e).__name__}: {e}" if str(e).strip() else type(e).__name__


def _llm_chat(system: str, user: str) -> str:
    """Try the primary model, then the smaller fallback. Raise with BOTH reasons.

    The backend (in-process llama.cpp, or Ollama when this machine already runs it)
    is chosen in llm.py; nothing here depends on which one answered.
    """
    import llm
    try:
        primary = _model()
        return llm.call(primary, system, user)
    except Exception as e1:
        try:
            fb = _fallback()
            return llm.call(fb, system, user)
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
    """Translate one string out-of-process, and only accept a plausible result.

    Two changes over "call the engine and hope". First, a result in the wrong
    script is treated as a FAILURE and the next engine is tried: IndicTrans2 can
    return the input unchanged for a direction whose checkpoint is missing, and
    that echo previously became the answer. Second, every failure is logged, so
    an English answer where Hindi was asked for leaves a trace instead of being
    indistinguishable from a correct one.
    """
    if src == tgt or not text.strip():
        return text
    ck = (text, src, tgt)
    hit = _mt_cache.get(ck)
    if hit is not None:
        return hit
    engines = dict.fromkeys([os.environ.get("AWAZ_CHAT_MT", "nllb").lower(), "nllb"])
    for engine in engines:
        r = _mt_run(text, src, tgt, engine)
        if r and r.strip() and is_target_language(r, tgt):
            if len(_mt_cache) >= _MT_CACHE_MAX:
                _mt_cache.clear()
            _mt_cache[ck] = r
            return r
        if r:
            import langid
            got = langid.devanagari_lang(r) or script_of(r)
            _log(f"{engine} {src}->{tgt} produced {got}, rejected; trying the next engine")
        else:
            _log(f"{engine} {src}->{tgt} returned nothing")
    return None


def _log(msg: str) -> None:
    try:
        import sys
        print(f"[chat] {msg}", file=sys.stderr, flush=True)
    except Exception:
        pass


def _to_lang(text: str, lang: str, src_hint: str = "hi") -> tuple[str, bool]:
    """Render an answer in `lang`, returning (text, translated_cleanly).

    The model is asked to reason in English and usually does, but not always —
    a small model handed a Devanagari transcript sometimes answers in Devanagari.
    Feeding that to an en->hi engine as though it were English produced the worst
    output of all, so the script is established first and the text is routed
    accordingly:

      already in the target script, and unambiguous  -> use it as-is
      in some other Indic script                     -> normalise via English
      English                                        -> the ordinary path

    Odia is unambiguous because nothing else in this app uses the Oriya block.
    Devanagari is not — Hindi and Marathi share it — so Devanagari output is sent
    back through English rather than being assumed to be whichever was asked for.
    """
    text = (text or "").strip()
    if not text:
        return text, True
    got = script_of(text)
    if lang == "en":
        if got == "latin" or got == "none":
            return text, True
        out = _mt(text, src_hint, "en")
        return (out, True) if out else (text, False)

    if got == "orya" and lang == "or":
        return text, True                      # Oriya script implies Odia

    if got in ("deva", "orya"):
        # Normalise through English so Hindi and Marathi cannot be confused.
        # The source tag must be a language that actually writes this script: the
        # video's own language when it fits, and Hindi as the Devanagari default
        # otherwise. Passing "en" here would make the engine a no-op and send
        # Devanagari onward labelled as English, which is the mistake this whole
        # function exists to prevent.
        src = src_hint if SCRIPT_OF.get(src_hint) == got else (
            "hi" if got == "deva" else "or")
        via = _mt(text, src, "en")
        if not via:
            # Could not normalise. Keeping it was only safe when "right script"
            # meant "right language" -- it never did for Hindi and Marathi, so
            # this returned Marathi whenever Hindi was asked for and the
            # normalisation happened to fail. Now it has to be the right
            # language, not merely the right alphabet.
            _log(f"could not normalise {got} output via English for {lang}")
            return text, is_target_language(text, lang)
        text = via

    out = _mt(text, "en", lang)
    if out and is_target_language(out, lang):
        return out, True
    # Both engines were tried inside _mt and neither produced `lang`. Saying so
    # is the only honest option left: showing the other Indic language would be
    # exactly the bug, and showing nothing helps nobody.
    _log(f"could not render the answer in {lang}; returning English with a note")
    return text, False


def _question_to_en(q: str, lang: str, src_hint: str = "hi") -> str:
    """Whatever the person typed, in English, for the model to reason over."""
    sc = script_of(q)
    if sc in ("latin", "none"):
        return q                                  # already English, or just digits
    src = lang if SCRIPT_OF.get(lang) == sc else ("or" if sc == "orya" else src_hint)
    return _mt(q, src, "en") or q


def _fmt_segs(ss, prefer: str = "en") -> str:
    """Render segments for the LLM, preferring the English translation.

    The source is usually Devanagari, which costs roughly three times the tokens of
    the same sentence in English. Sending Marathi overflowed num_ctx, so the model
    silently saw only a fragment - which made it answer NOT_IN_TRANSCRIPT even for
    "what is this video about?".
    """
    try:
        from glossary import correct_target
    except Exception:
        def correct_target(t, _lang):
            return t
    out = []
    for h in ss:
        txt = (h.get("t") or {}).get(prefer) or h["text"]
        # Apply the glossary to what the model READS, not only to what it writes.
        # Correcting the answer afterwards cannot help when the mistake is in the
        # evidence: with "sheep" in the transcript the model reasons about sheep
        # and says so, and no amount of output correction makes that right.
        out.append(f"[{int(h['start'])//60}:{int(h['start']) % 60:02d}] "
                   + correct_target(txt, prefer))
    return "\n".join(out)


def answer(m: dict, q: str, lang: str = "hi", history: list | None = None) -> dict:
    segs = m["segments"]
    lang = lang if lang in LANG_FULL else "en"
    src_name = LANG_FULL.get(m.get("src_lang", "hi"), "the source language")
    total_words = sum(len(s["text"].split()) for s in segs)

    # Reason in English (the small model's strongest language), then translate out.
    # Routed by the script the question is WRITTEN in, not by the language chosen
    # for answers: someone running the app in Hindi still types English questions
    # half the time, and feeding English to an hi->en engine mangled them.
    q_en = _question_to_en(q, lang, m.get("src_lang", "hi"))

    # Retrieve with the ENGLISH question, not the one that was typed. The index
    # holds every language of every segment, so either finds material -- but an
    # Indic question drags its function words along, they match every segment,
    # and the real hits end up buried under noise. Measured on this media, the
    # same question retrieved at a contrast of 8.1 in English and 1.5 in Hindi,
    # and the Hindi path then refused questions the English path answered.
    key, contrast = _retrieve(m, q_en or q, k=6)
    matched = contrast >= MIN_CONTRAST
    # One line per question, on stderr. Enough to tell afterwards WHY an answer
    # came out as it did: what the question became, how well it matched, and
    # which branch of the context builder ran. Without it the only way to
    # diagnose a bad answer is to reproduce it by hand.
    _log(f"q={q[:40]!r} -> {q_en[:40]!r} lang={lang} "
         f"contrast={contrast:.1f} matched={matched}")
    mode = os.environ.get("AWAZ_RETRIEVAL", "foreground")
    limit = int(os.environ.get("AWAZ_CTX_SEGMENTS", "180"))
    whole = _fmt_segs(segs[:limit])
    if mode == "retrieval" and matched:
        ctx = _fmt_segs(key)
    elif matched:
        ctx = ("MOST RELEVANT LINES:\n" + _fmt_segs(key)
               + "\n\nFULL TRANSCRIPT:\n" + whole)
    else:
        # Nothing stood out -> almost always a general question ("what is this
        # about?"). Summarising needs the whole transcript, and labelling six
        # arbitrary lines "most relevant" actively misleads the model.
        ctx = "FULL TRANSCRIPT:\n" + whole

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
        f"5. Write the answer in ENGLISH, whatever language the transcript is in. "
        f"It is translated afterwards by a dedicated model; an answer written here "
        f"in another language gets translated twice and comes out wrong."
        + (f"\nDomain terms: {gloss}" if gloss else ""))

    convo = ""
    if history:
        convo = "EARLIER Q&A (for follow-up context):\n" + "\n".join(
            f"Q: {h.get('q', '')}  A: {h.get('a', '')}" for h in history[-3:]) + "\n\n"
    user = (f"VIDEO TRANSCRIPT (with [mm:ss] timings):\n{ctx}\n\n{convo}"
            f"QUESTION: {q_en}\n\nAnswer in English, or {SENTINEL}:")

    grounded, llm_ok = True, True
    try:
        ans_en = _llm_chat(system, user)
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
        _log(f"model declined: sentinel={SENTINEL in ans_en.upper()} "
             f"empty={not ans_en.strip()} len={len(ans_en)}")
        grounded = False
        near, _ = _retrieve(m, q_en or q, k=3)
        return {"answer": STR_NOT_COVERED.get(lang, STR_NOT_COVERED["en"]),
                "sources": [{"start": h["start"], "text": h["text"]} for h in near],
                "grounded": False}

    ans, translated = _to_lang(ans_en, lang, src_hint=m.get("src_lang", "hi"))
    try:  # enforce BAIF terminology in the answer too
        from glossary import correct_target
        ans = correct_target(ans, lang)
    except Exception:
        pass
    # Say so rather than passing English off as the requested language. The old
    # behaviour returned the English silently, which is exactly what made this
    # look like the model "sometimes answering in English".
    if not translated and STR_UNTRANSLATED.get(lang):
        ans = ans + "\n\n" + STR_UNTRANSLATED[lang]

    # Be upfront when the transcript itself was unreliable.
    conf = m.get("asr_confidence") or {}
    if conf and not conf.get("usable", True):
        ans = ans + "\n\n" + STR_LOW_ASR.get(lang, STR_LOW_ASR["en"])

    # Citations only when retrieval actually matched; otherwise the chips are noise.
    if matched:
        src, _ = _retrieve(m, q_en or q, k=3)
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
