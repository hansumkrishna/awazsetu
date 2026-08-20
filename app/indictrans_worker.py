"""Standalone IndicTrans2 translation worker (subprocess-isolated).

    python indictrans_worker.py <job.json> <out.json>
    job: {"src":"hi","targets":["mr","en"],"sentences":[...],"threads":4}
    out: {"mr":[...],"en":[...]}

Routes across the 3 distilled checkpoints; hi<->mr is a DIRECT pair (no English pivot).
Higher Indic quality than NLLB. Runs on CPU fp32; models are small (200M/320M).
"""
import os
import sys
import json

# CPU-only: a CUDA torch worker spawned from a CUDA-initialised parent (pipeline/server)
# segfaults inside the custom IndicTrans2 attention code. Hiding CUDA avoids it.
os.environ.setdefault("CUDA_VISIBLE_DEVICES", "")
import torch
from transformers import AutoModelForSeq2SeqLM, AutoTokenizer

try:
    from IndicTransToolkit.processor import IndicProcessor
except Exception:
    from IndicTransToolkit import IndicProcessor  # type: ignore

FLORES = {"hi": "hin_Deva", "mr": "mar_Deva", "en": "eng_Latn"}
INDIC = {"hi", "mr"}
REPOS = {
    "indic-en": "ai4bharat/indictrans2-indic-en-dist-200M",
    "en-indic": "ai4bharat/indictrans2-en-indic-dist-200M",
    "indic-indic": "ai4bharat/indictrans2-indic-indic-dist-320M",
}


def route(src, tgt):
    if src in INDIC and tgt == "en":
        return "indic-en"
    if src == "en" and tgt in INDIC:
        return "en-indic"
    if src in INDIC and tgt in INDIC:
        return "indic-indic"
    raise ValueError(f"unsupported {src}->{tgt}")


def main():
    job = json.load(open(sys.argv[1], encoding="utf-8"))
    torch.set_num_threads(int(job.get("threads", 4)))
    ip = IndicProcessor(inference=True)
    sents, src = job["sentences"], job["src"]
    cache, res = {}, {}
    for tgt in job["targets"]:
        if tgt == src:
            res[tgt] = list(sents)
            continue
        r = route(src, tgt)
        if r not in cache:
            repo = REPOS[r]
            tok = AutoTokenizer.from_pretrained(repo, trust_remote_code=True)
            model = AutoModelForSeq2SeqLM.from_pretrained(
                repo, trust_remote_code=True, torch_dtype=torch.float32,
                attn_implementation="eager").eval()  # sdpa segfaults on torch 2.5
            cache[r] = (tok, model)
        tok, model = cache[r]
        sl, tl = FLORES[src], FLORES[tgt]
        bs = int(job.get("batch", 4))       # small batches: beam-search topk is memory-heavy
        beams = int(job.get("beams", 1))    # greedy: avoids the flaky beam-search code path
        out = []
        for i in range(0, len(sents), bs):
            chunk = sents[i:i + bs]
            pre = ip.preprocess_batch(chunk, src_lang=sl, tgt_lang=tl)
            enc = tok(pre, truncation=True, padding="longest",
                      return_tensors="pt", return_attention_mask=True)
            with torch.no_grad():
                gen = model.generate(**enc, use_cache=True, min_length=0,
                                     max_length=256, num_beams=beams, num_return_sequences=1)
            dec = tok.batch_decode(gen, skip_special_tokens=True,
                                   clean_up_tokenization_spaces=True)
            out.extend(ip.postprocess_batch(dec, lang=tl))
        res[tgt] = out
    json.dump(res, open(sys.argv[2], "w", encoding="utf-8"), ensure_ascii=False)


if __name__ == "__main__":
    main()
