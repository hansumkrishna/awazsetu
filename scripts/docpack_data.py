"""Live data collection + page assets for the BAIF Documentation Pack.

Rendering lives in build_docpack.py; this module only gathers facts from the running
system so that every figure in the pack is read from the repository, never typed in.

ORIGINAL NOTE:

    python scripts/build_docpack.py
    python scripts/build_docpack.py --team 4 --pdf

Every number in the pack — segment counts, confidence scores, model footprints,
measured speeds, test results — is read from the repository at build time rather than
typed in. Re-running it after a change produces a pack that is still true, and a
reviewer can regenerate it themselves.

PDF rendering uses WeasyPrint, which is a pure-Python + Pango stack; nothing is sent
anywhere. If WeasyPrint is unavailable the HTML is still written and can be printed
from a browser with Ctrl+P.
"""
from __future__ import annotations
import os
import sys
import json
import html
import statistics
import subprocess
from datetime import datetime

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
APP = os.path.join(REPO, "app")
WORK = os.path.join(APP, "data", "work")
sys.path.insert(0, APP)
os.environ.setdefault("HF_HOME", os.path.join(REPO, "models", "hf-cache"))
os.environ.setdefault("HF_HUB_OFFLINE", "1")
os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")

TEAM = "Fluent Fusion"
TEAM_NO = os.environ.get("AWAZ_TEAM_NO", "")
OWNERS = os.environ.get("AWAZ_OWNERS", "Hansum Krishna (technical owner)")


def e(s):
    return html.escape(str(s))


# --------------------------------------------------------------- live data
def library():
    rows = []
    if not os.path.isdir(WORK):
        return rows
    for d in sorted(os.listdir(WORK)):
        mf = os.path.join(WORK, d, "manifest.json")
        if not os.path.exists(mf):
            continue
        m = json.load(open(mf, encoding="utf-8"))
        fs = os.listdir(os.path.join(WORK, d))
        subs = sorted({f.split(".")[1] for f in fs if f.startswith("subs.") and f.endswith(".vtt")})
        dubs = sorted({f.split(".")[1] for f in fs if f.startswith("dub.") and f.endswith(".wav")
                       and os.path.getsize(os.path.join(WORK, d, f)) > 10000})
        rows.append({
            "id": d, "title": m.get("video", d), "kind": m.get("kind", "video"),
            "src": m.get("src_lang"), "segs": len(m.get("segments", [])),
            "dur": m.get("duration", 0), "asr": m.get("asr_model", "?"),
            "mt": m.get("mt_engine", "?"), "subs": subs, "dubs": dubs,
            "conf": (m.get("asr_confidence") or {}).get("mean_logprob"),
            "complete": set(m.get("langs", [])) <= set(subs) and set(m.get("langs", [])) <= set(dubs),
        })
    return rows


def asr_timings():
    """Measured ASR runs, parsed from the reprocess log (real evidence, not claims)."""
    p = os.path.join(REPO, "dist", "reprocess.log")
    out = []
    if not os.path.exists(p):
        return out
    for ln in open(p, encoding="utf-8", errors="replace"):
        if "ASR_OK" in ln or ("rtf=" in ln and "model=" in ln):
            try:
                d = {}
                for tokn in ln.split():
                    if "=" in tokn:
                        k, v = tokn.split("=", 1)
                        d[k] = v
                if "rtf" in d and "dur" in d:
                    out.append({"model": d.get("model", "?"), "dev": d.get("dev", "?"),
                                "dur": float(d["dur"].rstrip("s")),
                                "time": float(d.get("time", "0").rstrip("s")),
                                "rtf": float(d["rtf"]), "segs": int(d.get("segs", 0)),
                                "logprob": float(d.get("logprob", 0))})
            except Exception:
                continue
    return out


def doctor_output():
    exe = os.path.join(REPO, "runtime", "python", "python.exe")
    if not os.path.exists(exe):
        exe = sys.executable
    env = dict(os.environ)
    env.update({"AWAZ_MODELS_DIR": os.path.join(REPO, "models"),
                "AWAZ_BIN_DIR": os.path.join(REPO, "runtime", "bin"),
                "AWAZ_LLM_DIR": os.path.join(REPO, "models", "llm"),
                "PYTHONIOENCODING": "utf-8"})
    try:
        r = subprocess.run([exe, os.path.join(REPO, "scripts", "doctor.py")],
                           capture_output=True, text=True, encoding="utf-8",
                           errors="replace", timeout=900, env=env, cwd=REPO)
        return (r.stdout or "") + (r.stderr or "")
    except Exception as ex:
        return f"(doctor did not run: {ex})"


def git_log(n=12):
    try:
        r = subprocess.run(["git", "-C", REPO, "log", f"-{n}", "--pretty=%h  %ad  %s",
                            "--date=short"], capture_output=True, text=True, timeout=30)
        return r.stdout.strip()
    except Exception:
        return ""


def pkg_sizes():
    out = {}
    for k in ("lite", "full"):
        p = os.path.join(REPO, "dist", f"awazsetu-{k}")
        if os.path.isdir(p):
            tot = sum(os.path.getsize(os.path.join(r, f))
                      for r, _d, fs in os.walk(p) for f in fs
                      if os.path.exists(os.path.join(r, f)))
            out[k] = tot
    return out


# ------------------------------------------------------------------ the SVG
ARCH_SVG = """
<svg viewBox="0 0 980 560" xmlns="http://www.w3.org/2000/svg" font-family="Segoe UI,sans-serif">
  <defs>
    <marker id="a" markerWidth="9" markerHeight="7" refX="8" refY="3.5" orient="auto">
      <polygon points="0 0, 9 3.5, 0 7" fill="#8a8a84"/></marker>
    <style>
      .bx{fill:#fff;stroke:#d9d9d4;stroke-width:1.2;rx:7}
      .t{font-size:12.5px;fill:#1a1a1a}
      .s{font-size:10.5px;fill:#77776f}
      .ln{stroke:#8a8a84;stroke-width:1.2;fill:none;marker-end:url(#a)}
      .band{fill:#faf9f6;stroke:#e7e6e1;stroke-width:1;rx:9}
      .bl{font-size:11px;fill:#b01c24;font-weight:600;letter-spacing:.6px}
      .acc{fill:#fdf3f3;stroke:#e8c9ca}
    </style>
  </defs>

  <!-- ONE-TIME band -->
  <rect class="band" x="10" y="26" width="960" height="212"/>
  <text class="bl" x="24" y="46">ONE-TIME, BEHIND A PROGRESS BAR (nothing here runs during playback)</text>

  <rect class="bx" x="26"  y="62" width="126" height="52"/>
  <text class="t" x="38" y="84">Video / Audio</text><text class="s" x="38" y="100">mp4 · mp3 · wav · m4a</text>

  <rect class="bx" x="180" y="62" width="126" height="52"/>
  <text class="t" x="192" y="84">FFmpeg</text><text class="s" x="192" y="100">16 kHz mono PCM</text>

  <rect class="bx acc" x="334" y="62" width="150" height="52"/>
  <text class="t" x="346" y="84">faster-whisper</text><text class="s" x="346" y="100">large-v3 · INT8 · VAD</text>

  <rect class="bx" x="512" y="62" width="150" height="52"/>
  <text class="t" x="524" y="84">Sanitiser + glossary</text><text class="s" x="524" y="100">drops degenerate output</text>

  <rect class="bx acc" x="690" y="62" width="150" height="52"/>
  <text class="t" x="702" y="84">IndicTrans2</text><text class="s" x="702" y="100">hi · mr · en · or</text>

  <line class="ln" x1="152" y1="88" x2="178" y2="88"/>
  <line class="ln" x1="306" y1="88" x2="332" y2="88"/>
  <line class="ln" x1="484" y1="88" x2="510" y2="88"/>
  <line class="ln" x1="662" y1="88" x2="688" y2="88"/>

  <rect class="bx" x="334" y="160" width="150" height="52"/>
  <text class="t" x="346" y="182">WebVTT subtitles</text><text class="s" x="346" y="198">4 tracks per item</text>

  <rect class="bx acc" x="512" y="160" width="150" height="52"/>
  <text class="t" x="524" y="182">MMS-TTS (VITS)</text><text class="s" x="524" y="198">4 voiceovers, isochronic</text>

  <rect class="bx" x="690" y="160" width="150" height="52"/>
  <text class="t" x="702" y="182">work/&lt;sha256&gt;/</text><text class="s" x="702" y="198">manifest · vtt · wav</text>

  <path class="ln" d="M765 114 L765 134 L409 134 L409 158"/>
  <line class="ln" x1="484" y1="186" x2="510" y2="186"/>
  <line class="ln" x1="662" y1="186" x2="688" y2="186"/>

  <!-- REAL-TIME band -->
  <rect class="band" x="10" y="262" width="960" height="180"/>
  <text class="bl" x="24" y="282">REAL TIME (the only models loaded while a user is watching)</text>

  <rect class="bx" x="26"  y="298" width="126" height="52"/>
  <text class="t" x="38" y="320">Question</text><text class="s" x="38" y="336">typed or spoken</text>

  <rect class="bx" x="180" y="298" width="126" height="52"/>
  <text class="t" x="192" y="320">Whisper small</text><text class="s" x="192" y="336">microphone only</text>

  <rect class="bx" x="334" y="298" width="150" height="52"/>
  <text class="t" x="346" y="320">BM25 retrieval</text><text class="s" x="346" y="336">cross-lingual, in-process</text>

  <rect class="bx acc" x="512" y="298" width="150" height="52"/>
  <text class="t" x="524" y="320">llama.cpp · Qwen 2.5</text><text class="s" x="524" y="336">grounded, refuses if absent</text>

  <rect class="bx" x="690" y="298" width="150" height="52"/>
  <text class="t" x="702" y="320">Answer + citations</text><text class="s" x="702" y="336">user's language + voice</text>

  <line class="ln" x1="152" y1="324" x2="178" y2="324"/>
  <line class="ln" x1="306" y1="324" x2="332" y2="324"/>
  <line class="ln" x1="484" y1="324" x2="510" y2="324"/>
  <line class="ln" x1="662" y1="324" x2="688" y2="324"/>
  <path class="ln" d="M765 214 L765 240 L860 240 L860 290 L840 290 L840 300"/>
  <text class="s" x="796" y="236">transcript grounds the answer</text>

  <rect class="bx" x="334" y="372" width="328" height="46"/>
  <text class="t" x="346" y="392">Flask · 127.0.0.1:5000 · embedded Python 3.10 · no external service</text>
  <text class="s" x="346" y="408">HF_HUB_OFFLINE=1 — the process cannot reach a network even if one exists</text>

  <text class="s" x="24" y="470">Every box runs on the local CPU. Shaded boxes are neural models; all weights ship inside the package.</text>
  <text class="s" x="24" y="488">Work folders are keyed by SHA-256 of the source file, so re-adding the same media is idempotent and URLs stay stable.</text>
</svg>
"""


def test_results():
    """The last automated run, read from docs/test_results.json.

    The curated expected-vs-actual table in the pack is hand-written and covers
    history the suite cannot re-run. This is the complement: whatever the suite
    actually asserted the last time it ran, reported verbatim including failures.
    A pack that showed only the curated table would be making claims; this one shows
    its working.
    """
    p = os.path.join(REPO, "docs", "test_results.json")
    try:
        with open(p, encoding="utf-8") as f:
            rows = json.load(f)
    except Exception:
        return []
    return rows
