"""AwazSetu — ASR (faster-whisper) + audio extraction (FFmpeg).

Quality notes (these settings are what make Indic ASR usable, not cosmetic):
  * `condition_on_previous_text=False` — with it ON, Whisper feeds its own previous
    output back in and drifts into repetition/invention once it mishears one segment.
    This was the single largest source of garbled Marathi.
  * `initial_prompt` — primes the decoder with domain vocabulary in the SOURCE script
    so "शेळीपालन" is a candidate at all. Without it the decoder falls back to
    phonetically-similar but meaningless words.
  * language must be DETECTED, never assumed — decoding Marathi audio with
    `language="hi"` produces fluent-looking Devanagari nonsense.
  * per-segment `avg_logprob` is returned so callers can flag low-confidence
    transcripts instead of silently passing garbage downstream.
"""
from __future__ import annotations
import os
import subprocess
import torch
from faster_whisper import WhisperModel

# Segments below this mean-logprob are almost certainly mis-decoded.
LOW_CONF = float(os.environ.get("AWAZ_ASR_LOW_CONF", "-1.0"))


def extract_audio(video_path: str, out_wav: str, sr: int = 16000) -> str:
    os.makedirs(os.path.dirname(out_wav), exist_ok=True)
    subprocess.run(
        ["ffmpeg", "-y", "-i", video_path, "-vn", "-ac", "1", "-ar", str(sr),
         "-c:a", "pcm_s16le", out_wav],
        check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return out_wav


def _prompt_for(lang: str) -> str | None:
    """Domain vocabulary hint, in the source script, from glossary.json."""
    try:
        from glossary import asr_prompt
        return asr_prompt(lang)
    except Exception:
        return None



def _temps():
    """Temperature fallback ladder. Each extra level can re-decode a failing segment,
    so keep it short: 2 levels caught the garbage cases at ~1/3 the cost of 6."""
    raw = os.environ.get("AWAZ_ASR_TEMPS", "0.0,0.2")
    try:
        return [float(x) for x in raw.split(",") if x.strip()]
    except Exception:
        return [0.0, 0.2]



def _dedupe(text: str, max_ngram: int = 6) -> str:
    """Collapse degenerate n-gram loops, e.g. a phrase repeated 13 times.

    Whisper echoes its own `initial_prompt` or spirals on unclear audio, and the
    compression-ratio threshold does not always catch a loop *inside* one segment.
    Token-based rather than regex, so it behaves identically for Devanagari and Latin.
    """
    toks = text.split()
    if len(toks) < 4:
        return text.strip()
    for n in range(1, max_ngram + 1):
        out, i = [], 0
        while i < len(toks):
            gram = toks[i:i + n]
            if len(gram) < n:
                out.extend(toks[i:])
                break
            reps, j = 1, i + n
            while j + n <= len(toks) and toks[j:j + n] == gram:
                reps += 1
                j += n
            if reps >= 3:
                out.extend(gram)
                i = j
            else:
                out.append(toks[i])
                i += 1
        toks = out
    return " ".join(toks).strip()


class WhisperASR:
    def __init__(self, size: str | None = None, device: str | None = None):
        size = size or os.environ.get("AWAZ_WHISPER", "small")
        self.device = (device or os.environ.get("AWAZ_DEVICE")
                       or ("cuda" if torch.cuda.is_available() else "cpu"))
        # int8 keeps it inside the i5/16GB budget on the target machine
        compute = "float16" if self.device == "cuda" else "int8"
        threads = int(os.environ.get("AWAZ_CPU_THREADS", "0")) or max(4, (os.cpu_count() or 8) // 2)
        self.model = WhisperModel(size, device=self.device, compute_type=compute,
                                  cpu_threads=threads, num_workers=1)
        self.size = size

    def detect_language(self, audio_path: str) -> tuple[str, float]:
        """Detect the spoken language before decoding. Returns (code, probability)."""
        try:
            lang, prob, _ = self.model.detect_language(audio_path)
            return lang, float(prob)
        except Exception:
            # Older faster-whisper: fall back to a cheap 1-segment probe.
            _segs, info = self.model.transcribe(audio_path, vad_filter=True, beam_size=1)
            next(_segs, None)
            return info.language, float(getattr(info, "language_probability", 0.0) or 0.0)

    def transcribe(self, audio_path: str, language: str | None = None):
        """Transcribe. `language=None` (or "auto") auto-detects — never assume.

        Returns (segments, detected_language). Each segment carries `logprob` and a
        `low_conf` flag so downstream stages can refuse rather than hallucinate.
        """
        if language in (None, "", "auto"):
            language, _p = self.detect_language(audio_path)
        # Quality decoding: greedy is noticeably worse for Indic; beam 5 is worth the
        # extra CPU on a one-time offline pass. Mic/live path overrides via AWAZ_BEAM.
        beam = int(os.environ.get("AWAZ_BEAM", "5"))
        segments, info = self.model.transcribe(
            audio_path,
            language=language,
            beam_size=beam,
            vad_filter=True,
            vad_parameters={"min_silence_duration_ms": 500},
            condition_on_previous_text=False,   # stops drift/repetition loops
            initial_prompt=_prompt_for(language),
            temperature=_temps(),
            compression_ratio_threshold=2.4,    # reject degenerate repetition
            log_prob_threshold=-1.0,
            no_speech_threshold=0.6,
        )
        segs = []
        for s in segments:
            txt = _dedupe(s.text.strip())
            if not txt:
                continue
            lp = float(getattr(s, "avg_logprob", 0.0) or 0.0)
            segs.append({"start": float(s.start), "end": float(s.end), "text": txt,
                         "logprob": lp, "low_conf": lp < LOW_CONF})
        return segs, info.language



# --- Unicode blocks we care about. Marathi/Hindi MUST be Devanagari; Whisper
# --- sometimes emits a different Indic script entirely when it loses the audio.
_SCRIPTS = {
    "devanagari": (0x0900, 0x097F),
    "bengali":    (0x0980, 0x09FF),
    "gurmukhi":   (0x0A00, 0x0A7F),
    "gujarati":   (0x0A80, 0x0AFF),
    "oriya":      (0x0B00, 0x0B7F),
    "tamil":      (0x0B80, 0x0BFF),
    "telugu":     (0x0C00, 0x0C7F),
    "kannada":    (0x0C80, 0x0CFF),
    "malayalam":  (0x0D00, 0x0D7F),
    "arabic":     (0x0600, 0x06FF),
}
_EXPECTED = {"hi": "devanagari", "mr": "devanagari", "en": None}


def _script_of(ch: str) -> str | None:
    o = ord(ch)
    for name, (lo, hi) in _SCRIPTS.items():
        if lo <= o <= hi:
            return name
    return None


def _collapse_chars(text: str, run: int = 5) -> str:
    """Collapse a single character repeated `run`+ times ("बबबबबब..." -> "ब").

    Token-level dedupe cannot see this: the loop contains no whitespace at all.
    """
    out, i, n = [], 0, len(text)
    while i < n:
        j = i
        while j < n and text[j] == text[i]:
            j += 1
        out.append(text[i] if (j - i) >= run else text[i:j])
        i = j
    return "".join(out)


def is_degenerate(text: str, lang: str) -> tuple[bool, str]:
    """True when a segment is ASR garbage rather than speech."""
    t = text.strip()
    if len(t) < 2:
        return True, "empty"
    letters = [c for c in t if c.isalpha()]
    if not letters:
        return True, "no-letters"
    # 1) hardly any distinct characters -> degenerate loop
    if len(t) >= 20 and len(set(letters)) / max(1, len(letters)) < 0.12:
        return True, "low-diversity"
    # 2) wrong script for the language
    exp = _EXPECTED.get(lang)
    if exp:
        counts = {}
        for c in letters:
            s = _script_of(c)
            if s:
                counts[s] = counts.get(s, 0) + 1
        total = sum(counts.values())
        if total >= 8:
            wrong = sum(v for k, v in counts.items() if k != exp)
            if wrong / total > 0.4:
                bad = max((k for k in counts if k != exp), key=lambda k: counts[k])
                return True, f"wrong-script:{bad}"
    return False, ""



def strip_foreign_tokens(text: str, lang: str) -> str:
    """Remove individual wrong-script WORDS from an otherwise valid segment.

    `is_degenerate` rejects a whole segment only when most of it is the wrong script.
    A mostly-Marathi line containing a few stray Bengali tokens survives that check,
    so those tokens reach the subtitles and the translator. Strip them individually.
    """
    exp = _EXPECTED.get(lang)
    if not exp:
        return text
    out = []
    for w in text.split():
        letters = [c for c in w if c.isalpha()]
        if len(letters) >= 2:
            scripts = [_script_of(c) for c in letters]
            named = [s for s in scripts if s]
            if named and sum(1 for s in named if s != exp) / len(named) > 0.5:
                continue
        out.append(w)
    return " ".join(out).strip()


def sanitize_segments(segs: list[dict], lang: str) -> tuple[list[dict], list[dict]]:
    """Repair repetition loops and DROP garbage segments before translation.

    Returning the dropped list keeps this auditable — a silent filter is how bad
    data sneaks back in.
    """
    kept, dropped = [], []
    for s in segs:
        txt = _collapse_chars(s.get("text", ""))
        txt = _dedupe(txt)
        txt = strip_foreign_tokens(txt, lang)
        bad, why = is_degenerate(txt, lang)
        if bad:
            dropped.append({**s, "reason": why})
            continue
        s = dict(s)
        s["text"] = txt
        kept.append(s)
    return kept, dropped


def transcript_confidence(segs: list[dict]) -> dict:
    """Aggregate ASR health so the UI/chat can be honest about a bad transcript."""
    if not segs:
        return {"mean_logprob": 0.0, "low_conf_ratio": 1.0, "usable": False}
    lps = [s.get("logprob", 0.0) for s in segs]
    mean = sum(lps) / len(lps)
    ratio = sum(1 for s in segs if s.get("low_conf")) / len(segs)
    return {"mean_logprob": round(mean, 3), "low_conf_ratio": round(ratio, 3),
            "usable": mean >= LOW_CONF and ratio < 0.5}
