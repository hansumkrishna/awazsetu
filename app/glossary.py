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
