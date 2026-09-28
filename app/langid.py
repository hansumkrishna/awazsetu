"""AwazSetu — telling Hindi from Marathi.

Unicode settles most language questions here: Oriya script means Odia, Latin
means English. It cannot settle the one that matters most, because Hindi and
Marathi share Devanagari completely. A script check therefore passed a Marathi
answer off as Hindi, which is the bug a user reported as "it still responds in
different languages".

No model is used. The two languages differ in exactly the words that appear in
every sentence -- the copula, the postpositions, the conjunctions -- so a short
closed-class word list separates them reliably and instantly:

    Hindi    है   में   और   का/की/के   नहीं   को   था
    Marathi  आहे  मध्ये  आणि  चा/ची/चे   नाही   ला   होता

Two orthographic tells help further: the letter ळ (LLA) is ordinary in Marathi
and essentially absent from standard Hindi, and the eyelash ra ऱ is Marathi-only.

Measured on this project's own 460 segments, each of which exists in both
languages -- 920 labelled sentences of real field material. See `benchmark()`.
"""
from __future__ import annotations
import re

# Closed-class words. Chosen for frequency, not for coverage: every one of these
# appears in ordinary prose constantly, so even a one-sentence answer contains
# several. Open-class vocabulary is deliberately excluded -- the two languages
# share far too much of it for a noun to be evidence of anything.
HI_WORDS = frozenset("""
है हैं हूँ हूं था थी थे होगा होगी होंगे हुआ हुई हुए
में और या का की के को से पर तक ने भी ही तो
नहीं क्या कैसे कौन कहाँ कब क्यों जो वह यह इस उस इन उन
लिए साथ बाद पहले अगर लेकिन इसलिए चाहिए सकता सकती सकते
करना करने किया गया गई गए रहा रही रहे अपने अपनी उनके उनकी
""".split())

MR_WORDS = frozenset("""
आहे आहेत आहोत होतील असेल असतील
मध्ये आणि किंवा चा ची चे च्या ला ने ही हे तो ती ते त्या या
नाही नाहीत काय कसे कोण कुठे केव्हा का जो ज्या
साठी सोबत नंतर आधी जर पण म्हणून पाहिजे शकते शकतो शकतात
करणे करावे केली केले गेला गेली गेले आपल्या त्यांच्या त्यांना यांना
असे अशा तसेच त्यामुळे वर खाली सुद्धा देखील
""".split())

# Orthography. ळ is common in Marathi (शेळी, वेळ, मूळ, जवळ) and does not occur
# in standard Hindi; ऱ (eyelash ra) is Marathi-only.
_MR_LETTERS = re.compile(r"[ळऱ]")          # ळ, ऱ
# The danda (U+0964) and double danda (U+0965) live inside the Devanagari
# block, so a naive [ऀ-ॿ]+ class swallows them and turns the
# commonest marker in the language, sentence-final "है।", into a token that
# matches nothing. Excluded explicitly.
_DEVA_WORD = re.compile(r"[ऀ-ॣ०-ॿ]+")

# Suffix evidence, used only to break a tie. Weaker than the word lists because
# a suffix can fall out of an unrelated word, so it never outvotes them.
MR_SUFFIXES = ("च्या", "ांनी", "ांना", "ावे", "ेल", "ला", "ची", "चे", "चा")
HI_SUFFIXES = ("ों", "ाएँ", "ियाँ", "ेगा", "ेगी", "ूंगा", "कर")


def _score(text: str) -> tuple[int, int]:
    words = _DEVA_WORD.findall(text or "")
    hi = sum(1 for w in words if w in HI_WORDS)
    mr = sum(1 for w in words if w in MR_WORDS)
    mr += 2 * len(_MR_LETTERS.findall(text or ""))
    return hi, mr


def devanagari_lang(text: str) -> str | None:
    """'hi', 'mr', or None when the text gives no usable evidence.

    None is a real answer, not a failure: a three-word fragment, a bare number
    or a proper noun genuinely does not identify a language, and guessing would
    be worse than saying so.
    """
    if not text:
        return None
    hi, mr = _score(text)
    if hi != mr:
        return "hi" if hi > mr else "mr"
    words = _DEVA_WORD.findall(text)
    h = sum(1 for w in words if w.endswith(HI_SUFFIXES))
    m = sum(1 for w in words if w.endswith(MR_SUFFIXES))
    if h != m:
        return "hi" if h > m else "mr"
    return None


def is_lang(text: str, lang: str) -> bool:
    """Is this text plausibly in `lang`? Unsure counts as yes.

    Asymmetric on purpose. This gates whether an answer is shown or re-translated,
    and refusing to show a correct answer because a six-word sentence carried no
    function words would be a worse failure than the one it prevents.
    """
    if lang not in ("hi", "mr"):
        return True
    got = devanagari_lang(text)
    return got is None or got == lang


def confident(text: str, min_hits: int = 2) -> bool:
    """True when there is enough evidence to act on `devanagari_lang`."""
    hi, mr = _score(text)
    return max(hi, mr) >= min_hits and hi != mr


def benchmark() -> dict:
    """Accuracy over this project's own translated segments.

    Every segment carries both a Hindi and a Marathi rendering of the same
    sentence, so the corpus is labelled, in-domain and free -- and it is the
    exact text this discriminator has to judge in production.
    """
    import os
    import json
    base = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "work")
    tot = {"hi": 0, "mr": 0}
    right = {"hi": 0, "mr": 0}
    unsure = {"hi": 0, "mr": 0}
    wrong_samples = []
    for d in sorted(os.listdir(base)):
        mp = os.path.join(base, d, "manifest.json")
        if not os.path.exists(mp):
            continue
        with open(mp, encoding="utf-8") as f:
            m = json.load(f)
        for s in m["segments"]:
            t = s.get("t") or {}
            for lang in ("hi", "mr"):
                txt = t.get(lang)
                if not txt:
                    continue
                tot[lang] += 1
                got = devanagari_lang(txt)
                if got is None:
                    unsure[lang] += 1
                elif got == lang:
                    right[lang] += 1
                elif len(wrong_samples) < 8:
                    wrong_samples.append((lang, got, txt[:80]))
    n = tot["hi"] + tot["mr"]
    r = right["hi"] + right["mr"]
    u = unsure["hi"] + unsure["mr"]
    return {"total": n, "correct": r, "unsure": u, "wrong": n - r - u,
            "accuracy": round(r / n, 4) if n else 0.0,
            "per_lang": {L: {"n": tot[L], "correct": right[L], "unsure": unsure[L]}
                         for L in ("hi", "mr")},
            "wrong_samples": wrong_samples}


if __name__ == "__main__":
    import json
    print(json.dumps(benchmark(), ensure_ascii=False, indent=1))
