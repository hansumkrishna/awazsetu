"""AwazSetu — dub worker (MMS-TTS VITS, offline, CPU). Subprocess-isolated.

    python dub_worker.py <manifest.json> <lang> <out.wav>

Synthesises each segment's translated text and places it at the segment's start
timestamp. Isochronic fit: if a segment's speech would spill well past the next
segment's start, it is gently compressed to stay aligned with the video.
"""
import os
import sys
import json
import numpy as np
import soundfile as sf

os.environ.setdefault("CUDA_VISIBLE_DEVICES", "")  # CPU-only; safe when spawned from a torch parent
import torch
from transformers import VitsModel, AutoTokenizer

MMS = {"hi": "facebook/mms-tts-hin", "mr": "facebook/mms-tts-mar",
       "en": "facebook/mms-tts-eng"}


def _resample(wav: np.ndarray, new_len: int) -> np.ndarray:
    """Linear-interp resample to new_len samples (mild pitch change on compression)."""
    if new_len <= 0 or new_len == len(wav) or len(wav) < 2:
        return wav
    x_old = np.linspace(0.0, 1.0, len(wav), dtype=np.float32)
    x_new = np.linspace(0.0, 1.0, new_len, dtype=np.float32)
    return np.interp(x_new, x_old, wav).astype(np.float32)


def main():
    manifest_path, lang, out_wav = sys.argv[1], sys.argv[2], sys.argv[3]
    m = json.load(open(manifest_path, encoding="utf-8"))
    segs = sorted(m["segments"], key=lambda s: s["start"])

    model = VitsModel.from_pretrained(MMS[lang])
    tok = AutoTokenizer.from_pretrained(MMS[lang])
    sr = model.config.sampling_rate

    total = float(m.get("duration") or segs[-1]["end"]) + 1.0
    track = np.zeros(int(total * sr) + sr, dtype=np.float32)

    done = 0
    for i, s in enumerate(segs):
        text = (s.get("t", {}).get(lang) or s["text"]).strip()
        if not text:
            continue
        try:
            inputs = tok(text, return_tensors="pt")
            with torch.no_grad():
                wav = model(**inputs).waveform.squeeze().cpu().numpy().astype(np.float32)
        except Exception as e:
            print("skip seg:", repr(e), file=sys.stderr)
            continue
        # isochronic fit: keep speech from spilling far past the next segment
        nxt = segs[i + 1]["start"] if i + 1 < len(segs) else s["end"]
        avail = max(0.0, nxt - s["start"])
        if avail > 0.3 and len(wav) / sr > avail * 1.25:
            wav = _resample(wav, int(avail * 1.15 * sr))  # compress to ~slot
        off = int(s["start"] * sr)
        end = min(off + len(wav), len(track))
        if end > off:
            track[off:end] += wav[:end - off]
            done += 1

    peak = float(np.max(np.abs(track))) or 1.0
    track = (track / peak * 0.95).astype(np.float32)
    sf.write(out_wav, track, sr)
    print(f"wrote {out_wav}  segs={done}  dur={len(track)/sr:.1f}s  sr={sr}")


if __name__ == "__main__":
    main()
