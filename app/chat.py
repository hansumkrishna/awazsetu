"""AwazSetu — chat with the video.

RAG grounded strictly in the transcript: BM25 retrieval (zero-download, RAM-light)
+ a small local LLM via Ollama (qwen2.5:3b). The LLM is only reached in chat mode,
so its memory is never co-resident with ASR/MT (staged loading).

    from chat import answer
    answer(manifest, "which crop is discussed?", lang="hi")
    -> {"answer": "...", "sources": [{"start": 12.3, "text": "..."}]}
"""
from __future__ import annotations
import os
import re
import json
import urllib.request

OLLAMA = os.environ.get("OLLAMA_URL", "http://127.0.0.1:11434")
MODEL = os.environ.get("AWAZ_LLM", "qwen2.5:3b")               # primary (better quality)
FALLBACK = os.environ.get("AWAZ_LLM_FALLBACK", "qwen2.5:1.5b")  # auto-degrade if 3B can't fit RAM
LANG_FULL = {"hi": "Hindi", "mr": "Marathi", "en": "English"}

_bm25_cache: dict[str, tuple] = {}


def _tok(s: str) -> list[str]:
    return re.findall(r"\w+", s.lower(), flags=re.UNICODE)


def _retrieve(m: dict, q: str, k: int = 5) -> list[dict]:
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
    hits = [i for i in order if scores[i] > 0] or order
    return [segs[i] for i in sorted(hits)]  # chronological


def _ollama_call(model: str, system: str, user: str) -> str:
    body = json.dumps({
        "model": model, "stream": False,
        "messages": [{"role": "system", "content": system},
                     {"role": "user", "content": user}],
        "options": {"temperature": float(os.environ.get("AWAZ_LLM_TEMP", "0.2")),
                    "num_ctx": 8192,
                    "num_gpu": int(os.environ.get("AWAZ_LLM_GPU", "0"))},
    }).encode()
    req = urllib.request.Request(OLLAMA + "/api/chat", data=body,
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=180) as r:
        j = json.loads(r.read())
    if "message" not in j:
        raise RuntimeError(j.get("error", "ollama: no message"))
    return j["message"]["content"].strip()


def _ollama_chat(system: str, user: str) -> str:
    try:
        return _ollama_call(MODEL, system, user)
    except Exception:
        # 3B didn't fit the available RAM -> degrade to the smaller model, so chat never fully breaks
        return _ollama_call(FALLBACK, system, user)


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
    """Translate one string out-of-process. Try IndicTrans2 (best for Indic, esp. the
    question direction), then fall back to NLLB — which is ungated and covers en->indic
    (IndicTrans2's en-indic model is separately gated and may be unavailable)."""
    if src == tgt or not text.strip():
        return text
    # NLLB (ungated, all directions) is the default; IndicTrans2 only if opted in + logged in.
    engines = dict.fromkeys([os.environ.get("AWAZ_CHAT_MT", "nllb").lower(), "nllb"])
    for engine in engines:
        r = _mt_run(text, src, tgt, engine)
        if r:
            return r
    return None


def answer(m: dict, q: str, lang: str = "hi", history: list | None = None) -> dict:
    segs = m["segments"]
    src_name = LANG_FULL.get(m.get("src_lang", "hi"), "the source language")
    # Short video (<=~1500 words) -> feed the WHOLE transcript. Far more robust than
    # snippet retrieval: no retrieval-miss hallucinations. Else fall back to BM25.
    def fmt_segs(ss):
        return "\n".join(
            f"[{int(h['start'])//60}:{int(h['start']) % 60:02d}] {h['text']}" for h in ss)
    total_words = sum(len(s["text"].split()) for s in segs)
    # Foreground the most relevant segments (BM25) so a small LLM doesn't lose the fact
    # in a long transcript ("lost in the middle"); include the full transcript for short
    # videos as backup, else just the retrieved set.
    key = _retrieve(m, q, k=6)
    mode = os.environ.get("AWAZ_RETRIEVAL", "foreground")
    if mode != "retrieval" and total_words <= 1500:
        ctx = ("MOST RELEVANT LINES:\n" + fmt_segs(key)
               + "\n\nFULL TRANSCRIPT:\n" + fmt_segs(segs))
    else:
        ctx = fmt_segs(key)
    # Reason in English (qwen's strongest, most consistent language): translate the
    # question to English, answer grounded in the transcript, then translate the answer
    # to the requested language. en<->hi/mr all work via NLLB (ungated).
    q_en = q if lang == "en" else (_mt(q, lang, "en") or q)
    system = (f"You are AwazSetu. Answer the user's SPECIFIC question using ONLY the transcript "
              f"below (it is in {src_name}) — quote the exact numbers, names and facts it "
              f"contains, translated into English. Do NOT summarize the whole video; answer only "
              f"what is asked, in 1-2 sentences. If the fact truly isn't in the transcript, say "
              f"you don't know. Reply in English.")
    convo = ""
    if history:
        convo = "EARLIER Q&A (for follow-up context):\n" + "\n".join(
            f"Q: {h.get('q', '')}  A: {h.get('a', '')}" for h in history[-3:]) + "\n\n"
    user = (f"VIDEO TRANSCRIPT (with [mm:ss] timings):\n{ctx}\n\n{convo}"
            f"QUESTION: {q_en}\n\nDirect answer in English (only what is asked):")
    try:
        ans_en = _ollama_chat(system, user)
    except Exception as e:
        ans_en = f"[LLM error: {e}]"
    ans = ans_en if lang == "en" else (_mt(ans_en, "en", lang) or ans_en)
    src = _retrieve(m, q, k=3)  # BM25 top-3 power the jump-to-timestamp chips
    return {"answer": ans, "sources": [{"start": h["start"], "text": h["text"]} for h in src]}


if __name__ == "__main__":
    import sys
    base = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "work")
    ids = sorted(d for d in os.listdir(base)
                 if os.path.exists(os.path.join(base, d, "manifest.json")))
    work = os.path.join(base, sys.argv[3] if len(sys.argv) > 3 else ids[0])
    m = json.load(open(os.path.join(work, "manifest.json"), encoding="utf-8"))
    q = sys.argv[1] if len(sys.argv) > 1 else "इस वीडियो में किस फसल की बात हो रही है?"
    lang = sys.argv[2] if len(sys.argv) > 2 else "hi"
    print(json.dumps(answer(m, q, lang), ensure_ascii=False, indent=1))
