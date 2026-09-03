"""AwazSetu — lightweight domain glossary.

Two jobs: (1) fix common source-language ASR mishears before translation, and
(2) surface key field terms to the chat prompt. This is the seed of the deck's
"domain-tuned" workflow (Tier 4 = curated agri corpora + constrained decoding).
"""
import os
import json

_G = None


def _load() -> dict:
    global _G
    if _G is None:
        try:
            with open(os.path.join(os.path.dirname(__file__), "glossary.json"),
                      encoding="utf-8") as f:
                _G = json.load(f)
        except Exception:
            _G = {"source_fixes": {}, "terms": []}
    return _G


def correct_source(text: str, lang: str) -> str:
    for wrong, right in _load().get("source_fixes", {}).get(lang, {}).items():
        text = text.replace(wrong, right)
    return text


def terms_hint() -> str:
    ts = [t.get("en", "") for t in _load().get("terms", []) if t.get("en")]
    return "; ".join(ts)


def asr_prompt(lang: str) -> str | None:
    """Domain vocabulary hint fed to Whisper's decoder as `initial_prompt`.

    Priming the decoder in the source script is what lets it produce शेळीपालन
    instead of a phonetically-close non-word.
    """
    p = _load().get("asr_prompts", {}).get(lang)
    return p or None


def terms_table(lang: str) -> str:
    """en <-> lang term pairs, for grounding translation and chat prompts."""
    rows = []
    for t in _load().get("terms", []):
        if t.get("en") and t.get(lang):
            rows.append(f"{t[lang]} = {t['en']}")
    return "; ".join(rows)


def correct_target(text: str, lang: str) -> str:
    """Enforce BAIF terminology in the TRANSLATED text.

    Generic MT renders "goat rearing" as the Hindi loan बकरीपालन even when the
    target is Marathi; the field term is शेळीपालन. Applied after translation to
    subtitles, dubs and chat answers alike.
    """
    for wrong, right in _load().get("target_fixes", {}).get(lang, {}).items():
        text = text.replace(wrong, right)
    return text
