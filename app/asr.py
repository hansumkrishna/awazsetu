"""AwazSetu — ASR (faster-whisper) + audio extraction (FFmpeg)."""
from __future__ import annotations
import os
import subprocess
import torch
from faster_whisper import WhisperModel


def extract_audio(video_path: str, out_wav: str, sr: int = 16000) -> str:
    os.makedirs(os.path.dirname(out_wav), exist_ok=True)
    subprocess.run(
        ["ffmpeg", "-y", "-i", video_path, "-vn", "-ac", "1", "-ar", str(sr),
         "-c:a", "pcm_s16le", out_wav],
        check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return out_wav


class WhisperASR:
    def __init__(self, size: str | None = None, device: str | None = None):
        size = size or os.environ.get("AWAZ_WHISPER", "small")
        self.device = (device or os.environ.get("AWAZ_DEVICE")
                       or ("cuda" if torch.cuda.is_available() else "cpu"))
        # int8 keeps it inside the i5/16GB budget on the target machine
        compute = "float16" if self.device == "cuda" else "int8"
        threads = int(os.environ.get("AWAZ_CPU_THREADS", "4"))
        self.model = WhisperModel(size, device=self.device, compute_type=compute,
                                  cpu_threads=threads, num_workers=1)
        self.size = size

    def transcribe(self, audio_path: str, language: str | None = None):
        # vad_filter uses Silero VAD -> only short voiced chunks decoded (deck's design)
        beam = int(os.environ.get("AWAZ_BEAM", "1" if self.device == "cpu" else "5"))
        segments, info = self.model.transcribe(
            audio_path, language=language, vad_filter=True, beam_size=beam)
        segs = [{"start": float(s.start), "end": float(s.end), "text": s.text.strip()}
                for s in segments if s.text.strip()]
        return segs, info.language
