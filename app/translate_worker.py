"""Standalone NLLB CT2 int8 translation worker.

Run as its own process so ctranslate2 imports cleanly (before/without torch's
OpenMP runtime) — in-process co-existence with torch/faster-whisper crashes on
Windows CPU. Called by mt.NLLBWorkerMT.

    python translate_worker.py <job.json> <out.json>
    job: {"model_dir":..., "src":"hi", "targets":["mr","en"], "sentences":[...], "threads":4}
    out: {"mr":[...], "en":[...]}
"""
import sys
import json
import ctranslate2
from transformers import AutoTokenizer

FLORES = {"hi": "hin_Deva", "mr": "mar_Deva", "en": "eng_Latn"}


def main():
    job = json.load(open(sys.argv[1], encoding="utf-8"))
    tok = AutoTokenizer.from_pretrained("facebook/nllb-200-distilled-600M")
    tr = ctranslate2.Translator(job["model_dir"], device="cpu",
                                compute_type="int8", intra_threads=job.get("threads", 4))
    sents = job["sentences"]
    res = {}
    for tgt in job["targets"]:
        tok.src_lang = FLORES[job["src"]]
        tt = FLORES[tgt]
        out = []
        for i in range(0, len(sents), 16):
            chunk = sents[i:i + 16]
            srcs = [tok.convert_ids_to_tokens(tok.encode(s)) for s in chunk]
            r = tr.translate_batch(srcs, target_prefix=[[tt]] * len(srcs), beam_size=1)
            for h in r:
                hy = h.hypotheses[0]
                if hy and hy[0] == tt:
                    hy = hy[1:]
                out.append(tok.decode(tok.convert_tokens_to_ids(hy),
                                      skip_special_tokens=True))
        res[tgt] = out
    json.dump(res, open(sys.argv[2], "w", encoding="utf-8"), ensure_ascii=False)


if __name__ == "__main__":
    main()
