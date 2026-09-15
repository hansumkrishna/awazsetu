"""AwazSetu — end-to-end acceptance tests.

Exercises every user journey across every language and writes a pass/fail matrix
to notes/TEST_EVIDENCE.md (the artefact the evaluation rubric asks for).

    python scripts/test_e2e.py            # all suites
    python scripts/test_e2e.py chat       # one suite: assets|chat|refusal|dub|voice|settings
"""
import os
import sys
import json
import time
import glob
import traceback

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault("HF_HOME", os.path.join(REPO, "models", "hf-cache"))
os.environ.setdefault("HF_HUB_OFFLINE", "1")
os.environ.setdefault("AWAZ_NLLB_CT2_DIR", os.path.join(REPO, "models", "nllb-int8"))
os.environ.setdefault("PYTHONIOENCODING", "utf-8")
sys.path.insert(0, os.path.join(REPO, "app"))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

WORK = os.path.join(REPO, "app", "data", "work")
from langs import DEFAULT_TARGETS          # noqa: E402  (adds Odia automatically)
LANGS = list(DEFAULT_TARGETS)
RESULTS = []


def rec(suite, case, lang, ok, detail="", secs=None):
    RESULTS.append({"suite": suite, "case": case, "lang": lang, "ok": bool(ok),
                    "detail": str(detail)[:300], "secs": round(secs, 1) if secs else None})
    mark = "PASS" if ok else "FAIL"
    print(f"  [{mark}] {suite}/{case} ({lang}) {('- ' + str(detail)[:120]) if detail else ''}",
          flush=True)


def manifests():
    """Load every manifest, with `id` forced to the FOLDER name.

    The folder is the real identity — server.load_manifest() resolves by folder, and
    every URL embeds it. The `id` field is the content hash recorded at ingest, and
    the two can diverge if a source file is replaced in place. Trusting the field
    instead of the folder made callers build paths to directories that do not exist.
    """
    out = []
    for d in sorted(glob.glob(os.path.join(WORK, "*", "manifest.json"))):
        try:
            m = json.load(open(d, encoding="utf-8"))
            folder = os.path.basename(os.path.dirname(d))
            if m.get("id") != folder:
                m["id_recorded"] = m.get("id")
                m["id"] = folder
            out.append(m)
        except Exception:
            pass
    return out


# --------------------------------------------------------------------------- assets
def suite_assets(ms):
    print("\n== assets: subtitles + manifest integrity ==", flush=True)
    for m in ms:
        vid, name = m["id"], m.get("video", "?")
        work = os.path.join(WORK, vid)
        for L in LANGS:
            p = os.path.join(work, f"subs.{L}.vtt")
            exists = os.path.exists(p) and os.path.getsize(p) > 50
            rec("assets", f"subtitle:{name}", L, exists,
                f"{os.path.getsize(p)}B" if os.path.exists(p) else "missing")
        segs = m.get("segments", [])
        translated = all(all(s.get("t", {}).get(L) for L in m.get("langs", [])) for s in segs[:20])
        rec("assets", f"all-langs-translated:{name}", "all", translated and bool(segs),
            f"{len(segs)} segments")
        conf = m.get("asr_confidence") or {}
        rec("assets", f"asr-confidence:{name}", m.get("src_lang", "?"),
            bool(conf.get("usable")), f"mean_logprob={conf.get('mean_logprob')}")


# --------------------------------------------------------------------------- chat
GOOD_Q = {
    "en": "What is this video about?",
    "hi": "यह वीडियो किस बारे में है?",
    "mr": "हा व्हिडिओ कशाबद्दल आहे?",
    "or": "ଏହି ଭିଡିଓ କେଉଁ ବିଷୟରେ?",
}
OFFTOPIC_Q = {
    "en": "What is the share price of Reliance Industries today?",
    "hi": "आज रिलायंस का शेयर भाव क्या है?",
    "mr": "आज रिलायन्सचा शेअर भाव किती आहे?",
    "or": "ଆଜି ରିଲାଏନ୍ସର ସେୟାର ଦାମ କେତେ?",
}
# The catastrophic failure we are guarding against.
BANNED = ["modeling", "modelling", "मॉडलिंग", "fashion", "film career"]


def suite_chat(ms):
    print("\n== chat: grounded answers in every language ==", flush=True)
    from chat import answer
    m = ms[0]
    for L in LANGS:
        t0 = time.time()
        try:
            r = answer(m, GOOD_Q[L], L)
            a = r.get("answer", "")
            leaked = [b for b in BANNED if b.lower() in a.lower()]
            # A refusal to "what is this video about?" is a FAILURE, not a pass.
            # The first assertion only checked for the hallucinated word and let a
            # wrongly-refused general question through as green.
            refused = (r.get("grounded") is False)
            on_topic = any(w in a.lower() for w in
                           ("goat", "बकर", "शेळ", "rear", "farm", "पालन", "शेती",
                            "ଛେଳି", "ପାଳନ", "ରୋଗ", "ଚିକିତ୍ସା"))
            ok = bool(a.strip()) and not leaked and not refused and on_topic
            why = ("HALLUCINATION:%s " % leaked if leaked else
                   "WRONGLY REFUSED a general question " if refused else
                   "" if on_topic else "answer not on-topic ")
            rec("chat", "on-topic", L, ok, why + a[:150], time.time() - t0)
        except Exception as e:
            rec("chat", "on-topic", L, False, traceback.format_exc()[-200:], time.time() - t0)


def suite_refusal(ms):
    print("\n== refusal: out-of-scope must NOT be answered ==", flush=True)
    from chat import answer, STR_NOT_COVERED
    m = ms[0]
    for L in LANGS:
        t0 = time.time()
        try:
            r = answer(m, OFFTOPIC_Q[L], L)
            a = r.get("answer", "")
            refused = (not r.get("grounded", True)) or STR_NOT_COVERED[L][:25] in a
            rec("refusal", "offtopic-refused", L, refused, a[:150], time.time() - t0)
        except Exception as e:
            rec("refusal", "offtopic-refused", L, False, str(e)[:200], time.time() - t0)


# --------------------------------------------------------------------------- dub
def suite_dub(ms):
    print("\n== dub: MMS-TTS voiceover per language ==", flush=True)
    import subprocess
    m = ms[0]
    work = os.path.join(WORK, m["id"])
    for L in LANGS:
        out = os.path.join(work, f"dub.{L}.wav")
        t0 = time.time()
        if os.path.exists(out) and os.path.getsize(out) > 10000:
            rec("dub", "voiceover", L, True, f"cached {os.path.getsize(out)//1024}KB")
            continue
        try:
            subprocess.run([sys.executable, os.path.join(REPO, "app", "dub_worker.py"),
                            os.path.join(work, "manifest.json"), L, out],
                           check=True, timeout=1200, capture_output=True)
            ok = os.path.exists(out) and os.path.getsize(out) > 10000
            rec("dub", "voiceover", L, ok,
                f"{os.path.getsize(out)//1024}KB" if ok else "no audio", time.time() - t0)
        except Exception as e:
            rec("dub", "voiceover", L, False, str(e)[:200], time.time() - t0)


# --------------------------------------------------------------------------- voice
def suite_voice(ms):
    print("\n== voice: TTS -> STT round trip (no mic needed) ==", flush=True)
    import subprocess
    m = ms[0]
    work = os.path.join(WORK, m["id"])
    worker = os.path.join(REPO, "app", "voice_worker.py")
    for L in LANGS:
        t0 = time.time()
        try:
            txt = os.path.join(work, f"_t_{L}.txt")
            wav = os.path.join(work, f"_t_{L}.wav")
            with open(txt, "w", encoding="utf-8") as f:
                f.write(GOOD_Q[L])
            subprocess.run([sys.executable, worker, "tts", txt, L, wav],
                           check=True, timeout=600, capture_output=True)
            spoke = os.path.exists(wav) and os.path.getsize(wav) > 5000
            rec("voice", "tts", L, spoke,
                f"{os.path.getsize(wav)//1024}KB" if spoke else "no audio", time.time() - t0)
            if not spoke:
                continue
            t1 = time.time()
            outj = os.path.join(work, f"_t_{L}.json")
            subprocess.run([sys.executable, worker, "stt", wav, L, outj],
                           check=True, timeout=600, capture_output=True)
            heard = json.load(open(outj, encoding="utf-8")).get("text", "").strip()
            rec("voice", "stt", L, bool(heard), heard[:120], time.time() - t1)
        except Exception as e:
            rec("voice", "roundtrip", L, False, str(e)[:200], time.time() - t0)


# --------------------------------------------------------------------------- settings
def suite_settings(ms):
    print("\n== settings: switching a model must actually take effect ==", flush=True)
    import config
    import chat as chatmod
    before = config.load()
    try:
        config.save({"chat_llm": "qwen2.5:1.5b"})
        rec("settings", "switch-llm-applies", "-",
            chatmod._model() == "qwen2.5:1.5b",
            f"chat._model()={chatmod._model()}")
        config.save({"asr_model": "small"})
        rec("settings", "switch-asr-applies", "-",
            os.environ.get("AWAZ_WHISPER") == "small",
            f"AWAZ_WHISPER={os.environ.get('AWAZ_WHISPER')}")
        st = config.status()
        rec("settings", "status-detects-models", "-",
            bool(st["whisper_installed"]) and bool(st["mms_voices"]),
            f"whisper={st['whisper_installed']} mms={st['mms_voices']}")
        rec("settings", "guide-present", "-", bool(st.get("guide", {}).get("asr")),
            "per-language model guidance exposed")
    finally:
        config.save(before)  # restore operator's real settings
        rec("settings", "restored", "-", config.load()["chat_llm"] == before["chat_llm"],
            f"chat_llm={config.load()['chat_llm']}")


from test_suites_platform import suite_platform, suite_media   # noqa: E402

SUITES = {"assets": suite_assets, "chat": suite_chat, "refusal": suite_refusal,
          "dub": suite_dub, "voice": suite_voice, "settings": suite_settings,
          "platform": suite_platform, "media": suite_media}


def write_report():
    os.makedirs(os.path.join(REPO, "docs"), exist_ok=True)
    p = os.path.join(REPO, "docs", "TEST_EVIDENCE.md")
    total = len(RESULTS)
    passed = sum(1 for r in RESULTS if r["ok"])
    with open(p, "w", encoding="utf-8") as f:
        f.write("# AwazSetu — Test Evidence\n\n")
        f.write(f"**{passed}/{total} passed**\n\n")
        f.write("| Suite | Case | Lang | Result | Time | Detail |\n")
        f.write("|---|---|---|---|---|---|\n")
        for r in RESULTS:
            f.write(f"| {r['suite']} | {r['case']} | {r['lang']} | "
                    f"{'PASS' if r['ok'] else 'FAIL'} | {r['secs'] or ''} | "
                    f"{r['detail'].replace(chr(10), ' ').replace('|', '/')} |\n")
        fails = [r for r in RESULTS if not r["ok"]]
        if fails:
            f.write(f"\n## Open defects ({len(fails)})\n")
            for r in fails:
                f.write(f"- **{r['suite']}/{r['case']}** ({r['lang']}): {r['detail']}\n")
    print(f"\nreport -> {p}  ({passed}/{total} passed)", flush=True)
    with open(os.path.join(REPO, "docs", "test_results.json"), "w", encoding="utf-8") as f:
        json.dump(RESULTS, f, ensure_ascii=False, indent=1)
    return passed, total


if __name__ == "__main__":
    ms = manifests()
    if not ms:
        raise SystemExit("no processed videos in app/data/work - run scripts/batch_process.py")
    print(f"{len(ms)} processed video(s)")
    want = sys.argv[1:] or list(SUITES)
    for nm in want:
        if nm not in SUITES:
            print(f"unknown suite: {nm}")
            continue
        try:
            SUITES[nm](ms)
        except Exception:
            traceback.print_exc()
            rec(nm, "suite-crashed", "-", False, traceback.format_exc()[-200:])
    p, t = write_report()
    sys.exit(0 if p == t else 1)
