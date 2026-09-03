"""AwazSetu — the single place languages are defined.

Adding a language used to mean editing seven files. Everything now reads this table.

`asr` records whether Whisper can TRANSCRIBE the language. Odia is deliberately
False: faster-whisper has no `or` token, so Odia audio cannot be transcribed. It is
still a first-class TARGET — translation, subtitles, voiceover and chat answers all
work — which is the common BAIF case (Marathi source, Odia audience).
"""
from __future__ import annotations

LANGS = {
    "hi": {"name": "Hindi",   "native": "हिंदी",   "flores": "hin_Deva",
           "mms": "facebook/mms-tts-hin", "asr": True,  "script": "devanagari"},
    "mr": {"name": "Marathi", "native": "मराठी",   "flores": "mar_Deva",
           "mms": "facebook/mms-tts-mar", "asr": True,  "script": "devanagari"},
    "en": {"name": "English", "native": "English", "flores": "eng_Latn",
           "mms": "facebook/mms-tts-eng", "asr": True,  "script": None},
    "or": {"name": "Odia",    "native": "ଓଡ଼ିଆ",    "flores": "ory_Orya",
           "mms": "facebook/mms-tts-ory", "asr": False, "script": "oriya"},
}

DEFAULT_TARGETS = ("hi", "mr", "en", "or")

FLORES = {k: v["flores"] for k, v in LANGS.items()}
MMS = {k: v["mms"] for k, v in LANGS.items()}
LANG_NAMES = {k: v["native"] for k, v in LANGS.items()}
LANG_FULL = {k: v["name"] for k, v in LANGS.items()}
SCRIPT = {k: v["script"] for k, v in LANGS.items()}
# Languages Whisper can transcribe. Used to pick a source language and to decide
# what the microphone may be set to.
ASR_LANGS = [k for k, v in LANGS.items() if v["asr"]]


def is_supported(code: str) -> bool:
    return code in LANGS


def can_transcribe(code: str) -> bool:
    return bool(LANGS.get(code, {}).get("asr"))


def native(code: str) -> str:
    return LANG_NAMES.get(code, code)


def full_name(code: str) -> str:
    return LANG_FULL.get(code, code)
