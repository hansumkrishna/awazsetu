"""
AwazSetu — Machine Translation layer (hi / mr / en), swappable engine.

    from mt import get_mt
    mt = get_mt()                       # env AWAZ_MT or default "nllb"
    mt.translate(["...hindi..."], src="hi", tgt="mr")  -> ["...marathi..."]

Engines (same interface):
  * nllb        facebook/nllb-200-distilled-600M   — UNGATED, works out of the box,
                any-to-any incl. hi<->mr DIRECT (no English pivot).
  * indictrans2 ai4bharat/indictrans2-*-dist        — higher Indic quality, but GATED
                on HuggingFace (needs `huggingface-cli login` + terms acceptance).

Both lazy-load and run fp16 on CUDA (dev) / fp32 on CPU (target i5). hi<->mr is
always a direct pair on both engines, matching the deck's requirement.
"""
from __future__ import annotations
import os
import json
import torch
from transformers import AutoModelForSeq2SeqLM, AutoTokenizer

from langs import FLORES  # single source of truth for language codes

# IndicTrans2 direction routing, mirroring indictrans_worker.route(). Kept here so
# callers can group targets that share a checkpoint into one worker process.
_INDIC = {k for k in FLORES if k != "en"}


def _route(src: str, tgt: str) -> str:
    if src in _INDIC and tgt == "en":
        return "indic-en"
    if src == "en" and tgt in _INDIC:
        return "en-indic"
    if src in _INDIC and tgt in _INDIC:
        return "indic-indic"
    raise ValueError(f"unsupported {src}->{tgt}")
INDIC = {"hi", "mr"}


def _device(d: str | None) -> str:
    return (d or os.environ.get("AWAZ_DEVICE")
            or ("cuda" if torch.cuda.is_available() else "cpu"))


class NLLBMT:
    NAME = "nllb-200-distilled-600M"
    REPO = "facebook/nllb-200-distilled-600M"

    def __init__(self, device: str | None = None):
        self.device = _device(device)
        self.dtype = torch.float16 if self.device == "cuda" else torch.float32
        self.tok = AutoTokenizer.from_pretrained(self.REPO)
        self.model = AutoModelForSeq2SeqLM.from_pretrained(
            self.REPO, torch_dtype=self.dtype, low_cpu_mem_usage=True
        ).to(self.device).eval()

    def translate(self, sentences: list[str], src: str, tgt: str,
                  beams: int = 3, batch_size: int = 16) -> list[str]:
        if src == tgt:
            return list(sentences)
        self.tok.src_lang = FLORES[src]
        bos = self.tok.convert_tokens_to_ids(FLORES[tgt])
        out: list[str] = []
        for i in range(0, len(sentences), batch_size):
            chunk = sentences[i:i + batch_size]
            enc = self.tok(chunk, truncation=True, padding=True, max_length=256,
                           return_tensors="pt").to(self.device)
            with torch.no_grad():
                gen = self.model.generate(**enc, forced_bos_token_id=bos,
                                          max_length=256, num_beams=beams)
            out.extend(self.tok.batch_decode(gen, skip_special_tokens=True))
        return out


class NLLBCt2MT:
    """NLLB-200 distilled, CTranslate2 INT8 — ~700 MB RAM, fast on CPU (the deck's
    INT8 path, same engine family as faster-whisper). One-time export via
    ct2-transformers-converter into app/models/nllb-600M-ct2-int8."""
    NAME = "nllb-600M-ct2-int8"
    HF = "facebook/nllb-200-distilled-600M"

    def __init__(self, model_dir: str | None = None, device: str | None = None):
        import ctranslate2
        from transformers import AutoTokenizer
        dev = _device(device)
        self.device = "cuda" if dev == "cuda" else "cpu"
        model_dir = (model_dir or os.environ.get("AWAZ_NLLB_CT2_DIR")
                     or os.path.join(os.path.dirname(__file__), "models",
                                     "nllb-600M-ct2-int8"))
        threads = int(os.environ.get("AWAZ_CPU_THREADS", "4"))
        # Load the HF tokenizer (initialises torch/OpenMP) BEFORE the CT2
        # Translator — reverse order triggers a dual-OpenMP native crash on CPU.
        self.tok = AutoTokenizer.from_pretrained(self.HF)
        self.translator = ctranslate2.Translator(
            model_dir, device=self.device, compute_type="int8",
            intra_threads=threads)

    def translate(self, sentences: list[str], src: str, tgt: str,
                  beams: int = 1, batch_size: int = 16) -> list[str]:
        if src == tgt:
            return list(sentences)
        self.tok.src_lang = FLORES[src]
        tgt_tok = FLORES[tgt]
        out: list[str] = []
        for i in range(0, len(sentences), batch_size):
            chunk = sentences[i:i + batch_size]
            srcs = [self.tok.convert_ids_to_tokens(self.tok.encode(s)) for s in chunk]
            results = self.translator.translate_batch(
                srcs, target_prefix=[[tgt_tok]] * len(srcs), beam_size=beams)
            for r in results:
                hyp = r.hypotheses[0]
                if hyp and hyp[0] == tgt_tok:
                    hyp = hyp[1:]
                out.append(self.tok.decode(
                    self.tok.convert_tokens_to_ids(hyp), skip_special_tokens=True))
        return out


class IndicMT:
    """Higher Indic quality — gated. Routes across 3 distilled checkpoints."""
    NAME = "indictrans2-dist"
    _REPOS = {
        "indic-en": "ai4bharat/indictrans2-indic-en-dist-200M",
        "en-indic": "ai4bharat/indictrans2-en-indic-dist-200M",
        "indic-indic": "ai4bharat/indictrans2-indic-indic-dist-320M",
    }

    def __init__(self, device: str | None = None):
        try:
            from IndicTransToolkit.processor import IndicProcessor
        except Exception:
            from IndicTransToolkit import IndicProcessor  # type: ignore
        self.device = _device(device)
        self.dtype = torch.float16 if self.device == "cuda" else torch.float32
        self.ip = IndicProcessor(inference=True)
        self._cache: dict[str, tuple] = {}

    @staticmethod
    def _route(src: str, tgt: str) -> str:
        if src in INDIC and tgt == "en":
            return "indic-en"
        if src == "en" and tgt in INDIC:
            return "en-indic"
        if src in INDIC and tgt in INDIC:
            return "indic-indic"
        raise ValueError(f"Unsupported {src}->{tgt}")

    def _load(self, route: str):
        if route not in self._cache:
            repo = self._REPOS[route]
            tok = AutoTokenizer.from_pretrained(repo, trust_remote_code=True)
            model = AutoModelForSeq2SeqLM.from_pretrained(
                repo, trust_remote_code=True, torch_dtype=self.dtype
            ).to(self.device).eval()
            self._cache[route] = (tok, model)
        return self._cache[route]

    def translate(self, sentences: list[str], src: str, tgt: str,
                  beams: int = 3, batch_size: int = 16) -> list[str]:
        if src == tgt:
            return list(sentences)
        tok, model = self._load(self._route(src, tgt))
        sl, tl = FLORES[src], FLORES[tgt]
        out: list[str] = []
        for i in range(0, len(sentences), batch_size):
            chunk = sentences[i:i + batch_size]
            pre = self.ip.preprocess_batch(chunk, src_lang=sl, tgt_lang=tl)
            enc = tok(pre, truncation=True, padding="longest",
                      return_tensors="pt", return_attention_mask=True).to(self.device)
            with torch.no_grad():
                gen = model.generate(**enc, use_cache=True, min_length=0,
                                     max_length=256, num_beams=beams,
                                     num_return_sequences=1)
            dec = tok.batch_decode(gen, skip_special_tokens=True,
                                   clean_up_tokenization_spaces=True)
            out.extend(self.ip.postprocess_batch(dec, lang=tl))
        return out


class NLLBWorkerMT:
    """Default engine: runs int8 NLLB in a subprocess (translate_worker.py) so
    ctranslate2 never has to co-exist with torch/faster-whisper in one process."""
    NAME = "nllb-600M-ct2-int8"

    def __init__(self, model_dir: str | None = None, device: str | None = None):
        self.model_dir = (model_dir or os.environ.get("AWAZ_NLLB_CT2_DIR")
                          or os.path.join(os.path.dirname(__file__), "models",
                                          "nllb-600M-ct2-int8"))
        self.threads = int(os.environ.get("AWAZ_CPU_THREADS", "4"))
        self.device = "cpu"

    def translate_multi(self, sentences: list[str], src: str,
                        targets: list[str]) -> dict:
        import subprocess
        import tempfile
        import sys
        tgts = [t for t in targets if t != src]
        if not tgts:
            return {}
        worker = os.path.join(os.path.dirname(__file__), "translate_worker.py")
        with tempfile.TemporaryDirectory() as d:
            jf, of = os.path.join(d, "job.json"), os.path.join(d, "out.json")
            with open(jf, "w", encoding="utf-8") as f:
                json.dump({"model_dir": self.model_dir, "src": src, "targets": tgts,
                           "sentences": list(sentences), "threads": self.threads},
                          f, ensure_ascii=False)
            subprocess.run([sys.executable, worker, jf, of], check=True)
            with open(of, encoding="utf-8") as f:
                return json.load(f)

    def translate(self, sentences: list[str], src: str, tgt: str,
                  beams: int = 1, batch_size: int = 16) -> list[str]:
        if src == tgt:
            return list(sentences)
        return self.translate_multi(sentences, src, [tgt]).get(tgt, [])


class IndicWorkerMT:
    """IndicTrans2 distilled in a subprocess (indictrans_worker.py). Higher Indic
    quality than NLLB; hi<->mr direct. Isolated so torch stays out of the caller."""
    NAME = "indictrans2-dist"

    def __init__(self, device: str | None = None):
        # 0 ("auto" in settings) must not collapse to a single thread: leave one core
        # for the OS and give the rest to the translator, which is the slowest stage.
        n = int(os.environ.get("AWAZ_CPU_THREADS", "0"))
        self.threads = n or max(4, (os.cpu_count() or 8) - 4)
        self.batch = int(os.environ.get("AWAZ_MT_BATCH", "8"))
        self.device = "cpu"

    def translate_multi(self, sentences: list[str], src: str,
                        targets: list[str]) -> dict:
        import subprocess
        import tempfile
        import sys
        worker = os.path.join(os.path.dirname(__file__), "indictrans_worker.py")
        res: dict = {}
        # One subprocess per ROUTE, not per target. The constraint is that two
        # DIFFERENT trust_remote_code checkpoints cannot share a process (segfault) —
        # several targets served by the SAME checkpoint can, and the worker already
        # caches by route. mr->hi and mr->or are both indic-indic, so grouping loads
        # that 320M model once per item instead of once per language.
        groups: dict[str, list[str]] = {}
        for tgt in targets:
            if tgt == src:
                res[tgt] = list(sentences)
                continue
            groups.setdefault(_route(src, tgt), []).append(tgt)
        for _r, tgts in groups.items():
            with tempfile.TemporaryDirectory() as d:
                jf, of = os.path.join(d, "j.json"), os.path.join(d, "o.json")
                with open(jf, "w", encoding="utf-8") as f:
                    json.dump({"src": src, "targets": tgts, "sentences": list(sentences),
                               "threads": self.threads, "batch": self.batch},
                              f, ensure_ascii=False)
                subprocess.run([sys.executable, worker, jf, of], check=True)
                with open(of, encoding="utf-8") as f:
                    res.update(json.load(f))
        return res

    def translate(self, sentences: list[str], src: str, tgt: str,
                  beams: int = 5, batch_size: int = 16) -> list[str]:
        if src == tgt:
            return list(sentences)
        return self.translate_multi(sentences, src, [tgt]).get(tgt, [])


def get_mt(engine: str | None = None, device: str | None = None):
    engine = (engine or os.environ.get("AWAZ_MT", "nllb")).lower()
    if engine in ("indictrans2", "it2", "indic"):
        return IndicWorkerMT(device)
    if engine in ("indictrans2-inproc",):
        return IndicMT(device)
    if engine in ("nllb-hf", "hf"):
        return NLLBMT(device)
    if engine in ("nllb-inproc", "ct2-inproc"):
        return NLLBCt2MT(device=device)
    return NLLBWorkerMT(device=device)


if __name__ == "__main__":
    import time
    mt = get_mt()
    print(f"[mt] engine={mt.NAME} device={mt.device}")
    samples = [
        "मेरे खेत में इस साल कपास की फसल बहुत अच्छी हुई है।",
        "सिंचाई के लिए पानी की कमी सबसे बड़ी समस्या है।",
        "यह सरकारी योजना छोटे किसानों के लिए बनाई गई है।",
    ]
    for tgt in ("en", "mr"):
        t0 = time.time()
        res = mt.translate(samples, src="hi", tgt=tgt)
        dt = time.time() - t0
        print(f"\n=== hi -> {tgt}  ({dt:.1f}s, {len(samples)} sents) ===")
        for s, r in zip(samples, res):
            print(f"  HI: {s}\n  {tgt.upper()}: {r}\n")
