"""AwazSetu — voice worker (subprocess-isolated). Two modes:

    python voice_worker.py stt <audio_in> <lang> <out.json>   # mic -> text
    python voice_worker.py tts <text_file> <lang> <out.wav>   # answer -> speech

Runs CPU-only (CUDA hidden, per the IndicTrans2/dub segfault lesson) so it is
safe to spawn from the torch-free Flask server. Reuses the same Whisper (STT)
and MMS-TTS (TTS) that power video transcription and dubbing — voice chat adds
NO new model family, only glues existing ones into a spoken loop.
"""
import os
import sys
import json

os.environ.setdefault("CUDA_VISIBLE_DEVICES", "")  # CPU only; safe under a torch parent

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

def do_stt(audio_in: str, lang: str, out_json: str):
    """Decode the browser's webm/opus clip to 16 kHz wav (ffmpeg) and transcribe."""
    import subprocess
    from faster_whisper import WhisperModel
    wav = audio_in + ".wav"
    from config import ffmpeg_exe
    subprocess.run([ffmpeg_exe(), "-y", "-i", audio_in, "-vn", "-ac", "1", "-ar",
                    "16000", "-c:a", "pcm_s16le", wav],
                   check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    # Mic clips are short -> a LIGHT model is enough and, crucially, fits in RAM
    # alongside a resident qwen (medium OOMs under memory pressure).
    threads = int(os.environ.get("AWAZ_CPU_THREADS", "0")) or max(4, (os.cpu_count() or 8) // 2)
    model = None
    for size in (os.environ.get("AWAZ_MIC_WHISPER", "small"), "base", "tiny"):
        try:
            model = WhisperModel(size, device="cpu", compute_type="int8", cpu_threads=threads)
            break
        except Exception:
            continue
    if model is None:
        raise RuntimeError("no whisper model could be loaded for mic STT")
    lang = lang if lang in ("hi", "mr", "en") else None
    # Same anti-garbage settings as the video path: no self-conditioning (stops
    # drift), domain priming, and a modest beam. Clips are short so the cost is small.
    prompt = None
    try:
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        from glossary import asr_prompt
        prompt = asr_prompt(lang) if lang else None
    except Exception:
        pass
    segments, info = model.transcribe(
        wav, language=lang, vad_filter=True,
        beam_size=int(os.environ.get("AWAZ_MIC_BEAM", "3")),
        condition_on_previous_text=False, initial_prompt=prompt,
        temperature=[0.0, 0.2], no_speech_threshold=0.6)
    text = " ".join(s.text.strip() for s in segments if s.text.strip()).strip()
    try:
        from asr import _dedupe, _collapse_chars, is_degenerate
        text = _dedupe(_collapse_chars(text))
        if lang and is_degenerate(text, lang)[0]:
            text = ""
    except Exception:
        pass
    json.dump({"text": text, "lang": info.language},
              open(out_json, "w", encoding="utf-8"), ensure_ascii=False)


def do_tts(text_file: str, lang: str, out_wav: str):
    """Synthesise one short answer to speech with MMS-TTS."""
    import numpy as np
    import soundfile as sf
    import torch
    from transformers import VitsModel, AutoTokenizer
    text = open(text_file, encoding="utf-8").read().strip() or "…"
    model, tok = _load_tts(MMS.get(lang, MMS["en"]))
    wav = synth_text(model, tok, text, np, torch)
    if wav.size == 0:
        wav = np.zeros(int(0.2 * model.config.sampling_rate), dtype=np.float32)
    peak = float(np.max(np.abs(wav))) or 1.0
    sf.write(out_wav, (wav / peak * 0.95).astype(np.float32), model.config.sampling_rate)


if __name__ == "__main__":
    mode = sys.argv[1]
    if mode == "stt":
        do_stt(sys.argv[2], sys.argv[3], sys.argv[4])
    elif mode == "tts":
        do_tts(sys.argv[2], sys.argv[3], sys.argv[4])
    else:
        raise SystemExit("mode must be stt|tts")
