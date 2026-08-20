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

MMS = {"hi": "facebook/mms-tts-hin", "mr": "facebook/mms-tts-mar",
       "en": "facebook/mms-tts-eng"}


def do_stt(audio_in: str, lang: str, out_json: str):
    """Decode the browser's webm/opus clip to 16 kHz wav (ffmpeg) and transcribe."""
    import subprocess
    from faster_whisper import WhisperModel
    wav = audio_in + ".wav"
    subprocess.run(["ffmpeg", "-y", "-i", audio_in, "-vn", "-ac", "1", "-ar",
                    "16000", "-c:a", "pcm_s16le", wav],
                   check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    # Mic clips are short -> a LIGHT model is enough and, crucially, fits in RAM
    # alongside a resident qwen (medium OOMs under memory pressure).
    threads = int(os.environ.get("AWAZ_CPU_THREADS", "4"))
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
    segments, info = model.transcribe(wav, language=lang, vad_filter=True, beam_size=1)
    text = " ".join(s.text.strip() for s in segments if s.text.strip()).strip()
    json.dump({"text": text, "lang": info.language},
              open(out_json, "w", encoding="utf-8"), ensure_ascii=False)


def do_tts(text_file: str, lang: str, out_wav: str):
    """Synthesise one short answer to speech with MMS-TTS."""
    import numpy as np
    import soundfile as sf
    import torch
    from transformers import VitsModel, AutoTokenizer
    text = open(text_file, encoding="utf-8").read().strip() or "…"
    model = VitsModel.from_pretrained(MMS.get(lang, MMS["en"]))
    tok = AutoTokenizer.from_pretrained(MMS.get(lang, MMS["en"]))
    with torch.no_grad():
        wav = model(**tok(text, return_tensors="pt")).waveform.squeeze().cpu().numpy()
    wav = wav.astype(np.float32)
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
