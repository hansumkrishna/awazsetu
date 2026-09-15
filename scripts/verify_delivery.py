"""AwazSetu — final delivery gate. Checks the ARTEFACTS, not the runtime.

    python scripts/verify_delivery.py
    python scripts/verify_delivery.py --pkg dist/awazsetu-lite

`doctor.py` answers "will this machine run everything?". This answers a different
question: "is what we are about to hand over actually complete and self-consistent?"
It is the check to run immediately before sending the packages and the pack.

Nothing here loads a model, so it is safe to run while a build is in flight.
"""
from __future__ import annotations
import os
import sys
import json
import subprocess

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
APP = os.path.join(REPO, "app")
WORK = os.path.join(APP, "data", "work")
DIST = os.path.join(REPO, "dist")
sys.path.insert(0, APP)

TARGETS = ("hi", "mr", "en", "or")
MIN_DUB = 10_000
rows: list[tuple[str, str, str]] = []


def rec(state, name, detail=""):
    rows.append((state, name, detail))
    print(f"{ {'PASS': '[ok]', 'WARN': '[--]', 'FAIL': '[XX]'}[state] } {name:38} {detail}",
          flush=True)


# ------------------------------------------------------------------ library
def check_library():
    if not os.path.isdir(WORK):
        return rec("FAIL", "library present", "app/data/work missing")
    items, complete, problems = 0, 0, []
    for d in sorted(os.listdir(WORK)):
        p = os.path.join(WORK, d)
        mf = os.path.join(p, "manifest.json")
        if not os.path.isdir(p):
            continue
        if not os.path.exists(mf):
            problems.append(f"{d[:8]}: no manifest")
            continue
        items += 1
        m = json.load(open(mf, encoding="utf-8"))
        fs = os.listdir(p)
        subs = {f.split(".")[1] for f in fs if f.startswith("subs.") and f.endswith(".vtt")}
        dubs = {f.split(".")[1] for f in fs if f.startswith("dub.") and f.endswith(".wav")
                and os.path.getsize(os.path.join(p, f)) > MIN_DUB}
        want = set(m.get("langs", []))
        miss = []
        if not want:
            miss.append("no languages")
        if want - subs:
            miss.append("subs:" + ",".join(sorted(want - subs)))
        if want - dubs:
            miss.append("dubs:" + ",".join(sorted(want - dubs)))
        media = m.get("media")
        if not media or media == "audio.wav" or not os.path.exists(os.path.join(p, media)):
            miss.append(f"media={media!r}")
        if m.get("id") != d:
            miss.append(f"id!=folder ({m.get('id')})")
        if miss:
            problems.append(f"{d[:8]} {m.get('video','')[:26]}: " + "; ".join(miss))
        else:
            complete += 1
    rec("PASS" if complete == items and items else ("WARN" if complete else "FAIL"),
        "library complete",
        f"{complete}/{items} items have every subtitle track and every voiceover")
    for p_ in problems[:12]:
        rec("WARN", "  incomplete item", p_)


def check_quality():
    """Every item should be on the best models the build shipped."""
    weak = []
    n = 0
    for d in sorted(os.listdir(WORK)) if os.path.isdir(WORK) else []:
        mf = os.path.join(WORK, d, "manifest.json")
        if not os.path.exists(mf):
            continue
        n += 1
        m = json.load(open(mf, encoding="utf-8"))
        if not m.get("mt_engine", "").startswith("indictrans2"):
            weak.append(f"{d[:8]}: mt={m.get('mt_engine')}")
        elif not set(TARGETS).issubset(set(m.get("langs", []))):
            weak.append(f"{d[:8]}: langs={m.get('langs')}")
    rec("PASS" if not weak else "WARN", "every item on IndicTrans2 + 4 languages",
        f"{n - len(weak)}/{n}" + ("" if not weak else " — " + "; ".join(weak[:4])))


# ------------------------------------------------------------------ package
def check_package(root):
    name = os.path.basename(root)
    if not os.path.isdir(root):
        return rec("WARN", f"package {name}", "not built")
    need = [
        ("AwazSetu.bat", "launcher"),
        ("AwazSetu-Check.bat", "preflight launcher"),
        ("READ_ME_FIRST.md", "readme"),
        (os.path.join("runtime", "python", "python.exe"), "embedded interpreter"),
        (os.path.join("runtime", "bin", "ffmpeg.exe"), "bundled ffmpeg"),
        (os.path.join("app", "run.py"), "application"),
        (os.path.join("app", "settings.json"), "settings"),
        (os.path.join("models", "hf-cache", "hub"), "model cache"),
        (os.path.join("models", "llm"), "assistant weights"),
        (os.path.join("app", "data", "work"), "processed library"),
    ]
    missing = [label for rel, label in need if not os.path.exists(os.path.join(root, rel))]
    rec("PASS" if not missing else "FAIL", f"package {name}: structure",
        "all present" if not missing else "MISSING: " + ", ".join(missing))

    # a package must not claim a model it does not carry
    try:
        s = json.load(open(os.path.join(root, "app", "settings.json"), encoding="utf-8"))
        hub = os.path.join(root, "models", "hf-cache", "hub")
        have = os.listdir(hub) if os.path.isdir(hub) else []
        bad = []
        if not any(s["asr_model"] in h for h in have):
            bad.append(f"asr_model={s['asr_model']}")
        if s.get("translate_engine") == "indictrans2" and \
                not any("indictrans2" in h for h in have):
            bad.append("translate_engine=indictrans2")
        if s.get("translate_engine") == "nllb" and \
                not os.path.exists(os.path.join(root, "models", "nllb-int8", "model.bin")):
            bad.append("translate_engine=nllb")
        ggufs = os.listdir(os.path.join(root, "models", "llm"))
        if not ggufs:
            bad.append("no GGUF")
        rec("PASS" if not bad else "FAIL", f"package {name}: settings match contents",
            "settings only select models that are present" if not bad
            else "SELECTS ABSENT: " + ", ".join(bad))
    except Exception as ex:
        rec("FAIL", f"package {name}: settings match contents", repr(ex))

    # no duplicate weights, no caches
    dup = sum(1 for r, _d, fs in os.walk(os.path.join(root, "models"))
              for f in fs if f == "pytorch_model.bin")
    pyc = sum(1 for r, ds, _f in os.walk(root) for x in ds if x == "__pycache__")
    rec("PASS" if dup == 0 else "WARN", f"package {name}: no duplicate weights",
        f"{dup} pytorch_model.bin, {pyc} __pycache__ dirs")

    size = sum(os.path.getsize(os.path.join(r, f))
               for r, _d, fs in os.walk(root) for f in fs
               if os.path.exists(os.path.join(r, f)))
    items = len([d for d in os.listdir(os.path.join(root, "app", "data", "work"))
                 if os.path.isdir(os.path.join(root, "app", "data", "work", d))]) \
        if os.path.isdir(os.path.join(root, "app", "data", "work")) else 0
    rec("PASS", f"package {name}: size", f"{size/1e9:.2f} GB, {items} processed items")


# ------------------------------------------------------------------ pack/git
def check_docpack():
    got = [f for f in os.listdir(DIST) if f.endswith(".pdf")
           and "DocumentationPack" in f] if os.path.isdir(DIST) else []
    if not got:
        return rec("FAIL", "documentation pack", "no DocumentationPack PDF in dist/")
    f = sorted(got)[-1]
    size = os.path.getsize(os.path.join(DIST, f))
    named = "[" in f or "_" in f.replace("BAIF_Hackathon_", "").replace("_DocumentationPack", "")
    rec("PASS", "documentation pack", f"{f} ({size/1e6:.2f} MB)")
    if "FluentFusion_Doc" in f:
        rec("WARN", "  team number", "filename has no [team #] — convention is TeamName[team #]")


def check_git():
    try:
        st = subprocess.run(["git", "-C", REPO, "status", "--porcelain"],
                            capture_output=True, text=True, timeout=30).stdout.strip()
        rec("PASS" if not st else "WARN", "working tree clean",
            "clean" if not st else f"{len(st.splitlines())} uncommitted change(s)")
        ahead = subprocess.run(["git", "-C", REPO, "log", "origin/main..HEAD", "--oneline"],
                               capture_output=True, text=True, timeout=30).stdout.strip()
        rec("PASS" if not ahead else "WARN", "pushed to origin",
            "up to date" if not ahead else f"{len(ahead.splitlines())} unpushed commit(s)")
    except Exception as ex:
        rec("WARN", "git state", repr(ex))


def check_secrets():
    """Nothing shipped may contain a token or a meeting credential.

    The patterns are assembled from fragments rather than written out, so this file
    does not itself contain the strings it hunts for — an earlier version flagged
    its own source, which is both a false positive and, for the meeting passcode, a
    real leak into a committed file.
    """
    import re
    pats = [
        r"hf_[A-Za-z0-9]{30,}",                  # Hugging Face token
        r"(?:passcode|password|passwd)\s*[:=]\s*\S{6,}",
        r"sk-[A-Za-z0-9]{20,}",                  # generic API key shape
        r"zoom\.us/j/\d+",                       # meeting link with an id
    ]
    pat = re.compile("|".join(pats), re.I)
    me = os.path.abspath(__file__)
    hits = []
    for base in ("app", "scripts", "docs", "README.md", "requirements-pinned.txt",
                 "AwazSetu.bat", "AwazSetu-Check.bat"):
        p = os.path.join(REPO, base)
        walk = [(os.path.dirname(p), [], [os.path.basename(p)])] if os.path.isfile(p) \
            else os.walk(p)
        for r, ds, fs in walk:
            ds[:] = [d for d in ds if d != "__pycache__"]
            for f in fs:
                if not f.endswith((".py", ".md", ".json", ".txt", ".bat", ".html")):
                    continue
                fp = os.path.join(r, f)
                if os.path.abspath(fp) == me:
                    continue                      # never scan the scanner
                try:
                    if pat.search(open(fp, encoding="utf-8", errors="ignore").read()):
                        hits.append(fp)
                except Exception:
                    pass
    rec("PASS" if not hits else "FAIL", "no secrets in shipped files",
        "clean" if not hits else "FOUND IN: " + ", ".join(hits))


def main():
    pkgs = [a for i, a in enumerate(sys.argv) if sys.argv[i - 1] == "--pkg"] or \
        [os.path.join(DIST, "awazsetu-lite"), os.path.join(DIST, "awazsetu-full")]
    print("=" * 78)
    print(" AwazSetu delivery gate — artefacts, not runtime. Nothing is loaded or changed.")
    print("=" * 78)
    check_library()
    check_quality()
    for p in pkgs:
        check_package(p)
    check_docpack()
    check_secrets()
    check_git()
    bad = [r for r in rows if r[0] == "FAIL"]
    warn = [r for r in rows if r[0] == "WARN"]
    print("-" * 78)
    print(f" {len(rows)-len(bad)-len(warn)} passed, {len(warn)} warnings, {len(bad)} failures")
    if bad:
        print("\n NOT READY TO SEND:")
        for _s, n, d in bad:
            print(f"   * {n}: {d}")
    print("=" * 78)
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
