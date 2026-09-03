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

import sys as _s, os as _o
_s.path.insert(0, _o.path.dirname(_o.path.abspath(__file__)))
from langs import MMS


import re as _re

# VITS degrades (and can blow up) on long inputs. Field transcript segments are often
# a full sentence or three, so synthesise sentence-by-sentence and concatenate.
_SENT_END = _re.compile(r"(?<=[\u0964\u0965.!?])\s+")   # danda, double danda, ASCII


def split_for_tts(text: str, max_chars: int = 180) -> list[str]:
    text = (text or "").strip()
    if not text:
        return []
    parts, buf = [], ""
    for sent in _SENT_END.split(text):
        sent = sent.strip()
        if not sent:
            continue
        if len(sent) > max_chars:                 # still too long: split on commas
            for piece in _re.split(r"(?<=[,;\u003b])\s+", sent):
                piece = piece.strip()
                while len(piece) > max_chars:     # last resort: hard wrap on a space
                    cut = piece.rfind(" ", 0, max_chars)
                    cut = cut if cut > 40 else max_chars
                    parts.append(piece[:cut].strip())
                    piece = piece[cut:].strip()
                if piece:
                    parts.append(piece)
            continue
        if len(buf) + len(sent) + 1 <= max_chars:
            buf = (buf + " " + sent).strip()
        else:
            if buf:
                parts.append(buf)
            buf = sent
    if buf:
        parts.append(buf)
    return parts


def synth_text(model, tok, text, np, torch):
    """Synthesise possibly-long text as concatenated chunks. Returns float32 mono."""
    chunks = split_for_tts(text)
    if not chunks:
        return np.zeros(0, dtype=np.float32)
    outs = []
    for c in chunks:
        try:
            with torch.no_grad():
                w = model(**tok(c, return_tensors="pt")).waveform.squeeze().cpu().numpy()
            outs.append(w.astype(np.float32))
        except Exception:
            continue
    if not outs:
        return np.zeros(0, dtype=np.float32)
    return np.concatenate(outs) if len(outs) > 1 else outs[0]



def _load_tts(repo):
    """Load an MMS-TTS voice, working around the Marathi tokenizer config.

    facebook/mms-tts-mar ships `phonemize=True`, which makes the tokenizer demand the
    `phonemizer` package (and an espeak-ng system binary). Its vocabulary is in fact
    60 Devanagari tokens — the model consumes Devanagari directly, exactly like
    mms-tts-hin (phonemize=False). Forcing the flag off makes Marathi speech work with
    NO extra system dependency, which is what keeps the install fully offline.
    """
    from transformers import VitsModel, AutoTokenizer
    tok = AutoTokenizer.from_pretrained(repo)
    if getattr(tok, "phonemize", False):
        try:
            import phonemizer  # noqa: F401  (use the real phonemiser when present)
        except Exception:
            tok.phonemize = False
    return VitsModel.from_pretrained(repo), tok

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

    repo = MMS.get(lang, MMS["en"])
    model, tok = _load_tts(repo)
    sr = model.config.sampling_rate

    total = float(m.get("duration") or segs[-1]["end"]) + 1.0
    track = np.zeros(int(total * sr) + sr, dtype=np.float32)

    done = 0
    for i, s in enumerate(segs):
        text = (s.get("t", {}).get(lang) or s["text"]).strip()
        if not text:
            continue
        try:
            wav = synth_text(model, tok, text, np, torch)
            if wav.size == 0:
                continue
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
