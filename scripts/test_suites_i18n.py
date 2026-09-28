"""AwazSetu — acceptance suites for the language pack and the writable-data split.

Imported by test_e2e.py as the `i18n` and `paths` suites.

These exist because both features fail SILENTLY when they break. An untranslated
string still renders -- in English, on a Hindi page, looking deliberate. A
read-only install still starts -- and then loses every setting the moment
somebody presses Save. Neither shows up in a smoke test that only checks for
HTTP 200, so both are checked here by content.
"""
from __future__ import annotations
import os
import sys
import time

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _t():
    """Resolve test_e2e lazily; see the note in test_suites_platform."""
    main = sys.modules.get("__main__")
    if main is not None and hasattr(main, "RESULTS") and hasattr(main, "rec"):
        return main
    import test_e2e
    return test_e2e


# Pages, and the keys that must be visible on each of them. Chosen as the things
# a user has to be able to read to get anywhere: what this page is, what the
# buttons do, and how to leave.
PAGE_KEYS = {
    "/": ["home_add", "home_drop", "home_search", "home_processed",
          "lang_title", "lang_sub", "lang_continue"],
    "/settings": ["set_interface", "set_interface_lbl", "set_models", "set_langs",
                  "set_perf", "set_save", "set_status"],
    "/garden": ["gd_machine", "gd_bestfor", "gd_quality", "gd_presets",
                "gd_legend", "gd_odia_title"],
}
WATCH_KEYS = ["chat_title", "chat_answer_in", "chat_welcome", "chat_ask",
              "pl_subs", "pl_dub", "pl_download", "pl_original"]


def suite_i18n(ms):
    """The interface must be complete, and must actually reach the page."""
    T = _t()
    print("\n== i18n ==")
    import i18n

    # 1) catalogue completeness -- one test per language, so a gap names itself
    for lang, gaps in i18n.missing().items():
        T.rec("i18n", "catalogue-complete", lang, not gaps,
              f"{len(i18n.S)} keys, {len(gaps)} missing"
              + (f": {gaps[:5]}" if gaps else ""))

    # 2) no string may be left as its own key -- that is what pack() returns when
    #    a key is missing in every language, and on screen it reads as a bug
    #    report. Checked only for namespaced keys: the English value of a bare
    #    key like `yes` is legitimately the word "yes".
    for lang in i18n.UI_LANGS:
        p = i18n.pack(lang)
        echoed = [k for k, v in p.items() if v == k and "_" in k]
        T.rec("i18n", "no-key-echo", lang, not echoed,
              f"{len(p)} strings" + (f", echoed: {echoed[:5]}" if echoed else ""))

    # and the fallback itself must behave: an unknown key returns the key, not
    # an exception and not an empty label
    T.rec("i18n", "unknown-key", "-",
          i18n.t("no_such_key_at_all", "hi") == "no_such_key_at_all",
          "unknown keys fall through to the key name rather than raising")

    # 3) a non-English pack must actually differ from English. A pack that is
    #    100% English would pass every other check here.
    en = i18n.pack("en")
    for lang in i18n.UI_LANGS:
        if lang == "en":
            continue
        same = [k for k, v in i18n.pack(lang).items() if v == en[k]]
        # Some strings are legitimately identical: "RAM", "CPU", "GPU", ".mkv".
        T.rec("i18n", "differs-from-english", lang, len(same) <= 8,
              f"{len(same)} of {len(en)} strings identical to English: {same[:8]}")

    # 4) unknown, regional and empty language codes must all resolve, never raise
    cases = [("hi-IN", "hi"), ("MR", "mr"), ("or_IN", "or"), ("zz", "en"),
             ("", "en"), (None, "en")]
    bad = [(a, i18n.normalise(a)) for a, want in cases if i18n.normalise(a) != want]
    T.rec("i18n", "normalise", "-", not bad, f"{len(cases)} codes" + (f", wrong: {bad}" if bad else ""))

    # 5) every page, every language, by CONTENT -- a 200 that renders English is
    #    the exact failure this is here to catch
    sys.path.insert(0, os.path.join(REPO, "app"))
    import server
    vid = ms[0]["id"] if ms else None
    pages = dict(PAGE_KEYS)
    if vid:
        pages["/watch/" + vid] = WATCH_KEYS
    client = server.app.test_client()
    for path, keys in pages.items():
        for lang in i18n.UI_LANGS:
            t = time.time()
            try:
                client.set_cookie("awaz_ui_lang", lang, domain="localhost")
                r = client.get(path)
                html = r.get_data(as_text=True)
                miss = [k for k in keys if i18n.t(k, lang) not in html]
                ok = r.status_code == 200 and not miss
                detail = f"HTTP {r.status_code}, {len(keys)-len(miss)}/{len(keys)} strings"
                if miss:
                    detail += f", missing {miss[:3]}"
            except Exception as ex:
                ok, detail = False, f"{type(ex).__name__}: {ex}"
            T.rec("i18n", "page" + path.replace("/" + str(vid), "/<id>"), lang,
                  ok, detail, time.time() - t)

    # 6) switching the language must take effect and persist in the cookie
    t = time.time()
    try:
        c = server.app.test_client()
        r = c.post("/api/ui-lang", json={"lang": "mr", "remember": False})
        body = r.get_json()
        cookie_set = any("awaz_ui_lang=mr" in h[1]
                         for h in r.headers if h[0] == "Set-Cookie")
        after = c.get("/").get_data(as_text=True)
        ok = (body.get("lang") == "mr" and cookie_set
              and i18n.t("home_add", "mr") in after)
        T.rec("i18n", "switch-applies", "mr", ok,
              f"cookie={cookie_set}, strings={len(body.get('strings', {}))}",
              time.time() - t)
    except Exception as ex:
        T.rec("i18n", "switch-applies", "mr", False, f"{type(ex).__name__}: {ex}")

    # 7) the answer-language buttons must offer every language, and the one that
    #    is highlighted must be the one the chat will actually use. They were
    #    driven by two different values, which is what made a Marathi video show
    #    Hindi as selected and then answer in Marathi.
    if vid:
        for lang in i18n.UI_LANGS:
            c = server.app.test_client()
            c.set_cookie("awaz_ui_lang", lang, domain="localhost")
            html = c.get("/watch/" + vid).get_data(as_text=True)
            offered = all(f'data-alang="{L}"' in html for L in i18n.UI_LANGS)
            active = f'class="btn active" data-alang="{lang}"' in html
            initial = f'let alang = "{lang}"' in html
            T.rec("i18n", "answer-lang-consistent", lang,
                  offered and active and initial,
                  f"all four offered={offered}, highlighted={active}, used={initial}")


def suite_paths(ms):
    """A read-only install must still show the library and still save settings."""
    T = _t()
    print("\n== paths ==")
    sys.path.insert(0, os.path.join(REPO, "app"))
    import importlib
    import tempfile
    import paths

    # normal install: nothing may have moved
    d = paths.describe()
    T.rec("paths", "writable-install", "-",
          not d["read_only_install"]
          and os.path.abspath(d["data_root"]) == os.path.abspath(paths.SHIPPED_DATA),
          f"data_root={d['data_root']}, items={d['items']}")
    T.rec("paths", "library-visible", "-", d["items"] > 0, f"{d['items']} processed items")

    # simulated read-only install: shipped library still served, writes redirected
    t = time.time()
    tmp = tempfile.mkdtemp(prefix="awaz-ro-")
    old = os.environ.get("AWAZ_DATA_DIR")
    try:
        os.environ["AWAZ_DATA_DIR"] = tmp
        importlib.reload(paths)
        ro = paths.describe()
        shipped_still_there = ro["items"] == d["items"]
        writes_redirected = os.path.abspath(paths.work_rw()).startswith(os.path.abspath(tmp))
        settings_redirected = os.path.abspath(paths.settings_path()).startswith(
            os.path.abspath(tmp))
        # and a write must actually succeed there
        probe = os.path.join(paths.work_rw(), "probe.txt")
        with open(probe, "w", encoding="utf-8") as f:
            f.write("ok")
        wrote = os.path.exists(probe)
        T.rec("paths", "readonly-install", "-",
              shipped_still_there and writes_redirected and settings_redirected and wrote,
              f"library kept={shipped_still_there}, work redirected={writes_redirected}, "
              f"settings redirected={settings_redirected}, write ok={wrote}",
              time.time() - t)
    except Exception as ex:
        T.rec("paths", "readonly-install", "-", False, f"{type(ex).__name__}: {ex}")
    finally:
        if old is None:
            os.environ.pop("AWAZ_DATA_DIR", None)
        else:
            os.environ["AWAZ_DATA_DIR"] = old
        importlib.reload(paths)
        import shutil
        shutil.rmtree(tmp, ignore_errors=True)

    # and the reload must have put everything back
    back = paths.describe()
    T.rec("paths", "restored", "-", not back["read_only_install"],
          f"data_root={back['data_root']}")


def suite_script(ms):
    """Script detection -- the guard that stops English being returned as Hindi."""
    T = _t()
    print("\n== script ==")
    sys.path.insert(0, os.path.join(REPO, "app"))
    from chat import script_of, in_target_script

    cases = [
        ("This is an English sentence.", "latin"),
        ("यह हिंदी वाक्य है।", "deva"),
        ("हा मराठी वाक्य आहे.", "deva"),
        ("ଏହା ଓଡ଼ିଆ ବାକ୍ୟ ଅଟେ।", "orya"),
        # A Hindi answer with technical terms in it is still Hindi. An ASCII
        # ratio test got this wrong, which is why it counts characters instead.
        ("मापी गई RTF 0.32 है और GPU पर चली।", "deva"),
        ("12345 !!! ...", "none"),
        ("", "none"),
    ]
    bad = [(txt[:24], want, script_of(txt)) for txt, want in cases
           if script_of(txt) != want]
    T.rec("script", "detect", "-", not bad, f"{len(cases)} cases" + (f", wrong: {bad}" if bad else ""))

    # the actual guard: English text must not pass as any Indic language
    en = "The video explains goat housing."
    checks = [(in_target_script(en, "hi"), False), (in_target_script(en, "mr"), False),
              (in_target_script(en, "or"), False), (in_target_script(en, "en"), True),
              (in_target_script("बकरी के बाड़े की जानकारी।", "hi"), True),
              (in_target_script("ଛେଳି ଘର ବିଷୟରେ।", "or"), True)]
    T.rec("script", "guard", "-", all(got == want for got, want in checks),
          f"{sum(1 for g, w in checks if g == w)}/{len(checks)} correct")


def suite_langid(ms):
    """Hindi must be distinguishable from Marathi, or the guard is decorative."""
    T = _t()
    print("\n== langid ==")
    sys.path.insert(0, os.path.join(REPO, "app"))
    import langid
    from chat import is_target_language

    # hand-written pairs first: unambiguous, and independent of the corpus
    pairs = [
        ("इस वीडियो में बकरी पालन की जानकारी दी गई है।", "hi"),
        ("या व्हिडिओमध्ये शेळीपालनाची माहिती दिली आहे.", "mr"),
        ("बाड़े का आकार दस वर्ग फुट होना चाहिए।", "hi"),
        ("गोठ्याचा आकार दहा चौरस फूट असावा.", "mr"),
        ("यह नस्ल दूध के लिए अच्छी है और वजन भी बढ़ता है।", "hi"),
        ("ही जात दुधासाठी चांगली आहे आणि वजनही वाढते.", "mr"),
    ]
    wrong = [(t[:30], want, langid.devanagari_lang(t))
             for t, want in pairs if langid.devanagari_lang(t) != want]
    T.rec("langid", "hand-pairs", "-", not wrong,
          f"{len(pairs)-len(wrong)}/{len(pairs)} identified"
          + (f", wrong: {wrong}" if wrong else ""))

    # then the project's own corpus: every segment exists in BOTH languages, so
    # it is 900+ labelled sentences of the exact text this has to judge
    b = langid.benchmark()
    T.rec("langid", "corpus-accuracy", "-", b["accuracy"] >= 0.85,
          f"{b['correct']}/{b['total']} correct, {b['unsure']} unsure, "
          f"{b['wrong']} wrong ({b['accuracy']:.1%})")

    # the two rates that actually matter in production
    keep = caught = 0
    import json as _json
    base = os.path.join(REPO, "app", "data", "work")
    n = 0
    for d in sorted(os.listdir(base)):
        mp = os.path.join(base, d, "manifest.json")
        if not os.path.exists(mp):
            continue
        with open(mp, encoding="utf-8") as f:
            man = _json.load(f)
        for seg in man["segments"]:
            tr = seg.get("t") or {}
            for lang, other in (("hi", "mr"), ("mr", "hi")):
                if not tr.get(lang):
                    continue
                n += 1
                if is_target_language(tr[lang], lang):
                    keep += 1
                if not is_target_language(tr[lang], other):
                    caught += 1
    T.rec("langid", "keeps-correct-answers", "-", n and keep / n >= 0.97,
          f"{keep}/{n} correct answers accepted ({keep/n:.1%}) "
          f"-- a false rejection costs the user their answer")
    T.rec("langid", "catches-wrong-language", "-", n and caught / n >= 0.85,
          f"{caught}/{n} wrong-language answers caught ({caught/n:.1%}) "
          f"-- this is the reported bug")

    # and the end-to-end predicate must not be fooled by script alone
    hi = "इस वीडियो में बकरी पालन की जानकारी दी गई है।"
    mr = "या व्हिडिओमध्ये शेळीपालनाची माहिती दिली आहे."
    checks = [(is_target_language(hi, "hi"), True), (is_target_language(hi, "mr"), False),
              (is_target_language(mr, "mr"), True), (is_target_language(mr, "hi"), False),
              (is_target_language("Goat housing needs space.", "hi"), False)]
    T.rec("langid", "guard", "-", all(g == w for g, w in checks),
          f"{sum(1 for g, w in checks if g == w)}/{len(checks)} correct "
          f"-- Marathi must NOT pass as Hindi")
