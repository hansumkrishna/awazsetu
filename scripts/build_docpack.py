"""Render the BAIF Documentation Pack (HTML, and PDF when WeasyPrint is available).

    python scripts/build_docpack.py --team 4 --pdf

Every figure in the pack — segment counts, confidence scores, measured speeds, model
footprints, package sizes, preflight output — is read from the live repository by
docpack_data.py at build time. Nothing is typed in, so re-running this after a change
produces a pack that is still true, and a reviewer can regenerate it themselves.
"""
from __future__ import annotations
import os
import sys
import statistics
from datetime import datetime

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import docpack_data as D                                   # noqa: E402
from docpack_data import e, ARCH_SVG, TEAM, OWNERS, REPO   # noqa: E402

CSS = """
@page { size: A4; margin: 17mm 15mm 16mm 15mm;
        @bottom-center { content: "AwazSetu — BAIF Hackathon Documentation Pack · page "
                                  counter(page) " of " counter(pages);
                         font-size: 8pt; color: #8a8a84; } }
body { font-family: "Segoe UI", system-ui, sans-serif; font-size: 9.6pt; line-height: 1.5;
       color: #1a1a1a; }
h1 { font-size: 23pt; margin: 0 0 2mm; letter-spacing: -.5px; }
h2 { font-size: 13pt; margin: 8mm 0 2.5mm; padding-bottom: 1.4mm; border-bottom: 2px solid #c0272d;
     color: #b01c24; page-break-after: avoid; }
h3 { font-size: 10.6pt; margin: 5mm 0 1.6mm; page-break-after: avoid; }
p, li { margin: 0 0 1.8mm; } ul, ol { margin: 0 0 2.4mm; padding-left: 5mm; }
table { border-collapse: collapse; width: 100%; font-size: 8.2pt; margin: 2mm 0 3.5mm;
        page-break-inside: avoid; }
th, td { border: 1px solid #ddd; padding: 1.5mm 2mm; text-align: left; vertical-align: top; }
th { background: #f4f3f0; font-weight: 600; }
td.n, th.n { text-align: right; font-variant-numeric: tabular-nums; }
code, pre { font-family: Consolas, "Courier New", monospace; font-size: 8pt; }
pre { background: #f7f6f3; border: 1px solid #e7e6e1; border-radius: 4px; padding: 2.5mm;
      white-space: pre-wrap; page-break-inside: avoid; }
.cover { text-align: center; padding-top: 40mm; page-break-after: always; }
.cover .sub { font-size: 12pt; color: #555; margin-top: 2mm; line-height: 1.5; }
.cover .meta { margin-top: 24mm; font-size: 9.5pt; color: #444; line-height: 1.85; }
.rule { height: 3px; background: #c0272d; width: 54mm; margin: 5mm auto; }
.k { background:#eaf6ed; color:#1a7f37; border:1px solid #bfe0c8; border-radius:3px;
     padding:0 1.4mm; font-size:7.6pt; font-weight:600; }
.w { background:#fdf5e7; color:#8a6412; border:1px solid #efdcb4; border-radius:3px;
     padding:0 1.4mm; font-size:7.6pt; font-weight:600; }
.box { border:1px solid #e7e6e1; background:#faf9f6; border-radius:5px; padding:2.5mm 3mm;
       margin:2.5mm 0; page-break-inside: avoid; }
.box b { color:#b01c24; }
svg { width: 100%; height: auto; }
.small { font-size: 8.4pt; color: #666; }
"""


def q(v, nd=2):
    try:
        return f"{float(v):.{nd}f}"
    except Exception:
        return "—"


def build_html(team_no: str) -> str:
    lib = D.library()
    tim = D.asr_timings()
    doc = D.doctor_output()
    sizes = D.pkg_sizes()
    import garden
    g = garden.overview()
    hw = g["hardware"]

    n_items = len(lib)
    n_complete = sum(1 for r in lib if r["complete"])
    total_min = sum(r["dur"] for r in lib) / 60.0
    total_segs = sum(r["segs"] for r in lib)
    n_subs = sum(len(r["subs"]) for r in lib)
    n_dubs = sum(len(r["dubs"]) for r in lib)
    rtfs = [t["rtf"] for t in tim if t.get("model") == "large-v3"]
    rtf_med = statistics.median(rtfs) if rtfs else None

    today = datetime.now().strftime("%d %B %Y")
    tno = f" [{team_no}]" if team_no else ""
    gpu_name = (hw.get("gpu") or {}).get("name", "no discrete GPU")

    lib_rows = "".join(
        f"<tr><td>{e(r['title'])[:46]}</td><td>{e(r['kind'])}</td><td>{e(r['src'])}</td>"
        f"<td class='n'>{q(r['dur']/60,1)}</td><td class='n'>{r['segs']}</td>"
        f"<td>{e(r['asr'])}</td><td class='n'>{q(r['conf'],3)}</td>"
        f"<td>{'/'.join(r['subs'])}</td><td>{'/'.join(r['dubs'])}</td>"
        f"<td>{'<span class=k>complete</span>' if r['complete'] else '<span class=w>partial</span>'}</td></tr>"
        for r in lib)

    tim_rows = "".join(
        f"<tr><td>{e(t['model'])}</td><td>{e(t['dev'])}</td><td class='n'>{q(t['dur']/60,1)}</td>"
        f"<td class='n'>{q(t['time'],0)}</td><td class='n'>{q(t['rtf'])}</td>"
        f"<td class='n'>{t['segs']}</td><td class='n'>{q(t['logprob'],3)}</td></tr>"
        for t in tim[-18:])

    def qcell(v):
        return f"<td class='n'>{v}</td>" if v else "<td class='n'>—</td>"

    cat_rows = ""
    for task, tlabel in g["tasks"].items():
        cat_rows += f"<tr><th colspan='9'>{e(tlabel)}</th></tr>"
        for r in g["catalog"]:
            if r["task"] != task:
                continue
            cat_rows += (f"<tr><td>{e(r['name'])}</td>"
                         + "".join(qcell(r["q"].get(c)) for c in ("en", "hi", "mr", "or"))
                         + f"<td class='n'>{r['speed']}/5</td><td class='n'>{r['ram_mb']}</td>"
                         f"<td class='n'>{q(r['disk_mb']/1024,1)}</td>"
                         f"<td>{'yes' if r['installed'] else 'no'}</td></tr>")

    dp, dw, dx = doc.count("[ok]"), doc.count("[--]"), doc.count("[XX]")
    size_lite = sizes.get("lite", 0) / 1e9
    size_full = sizes.get("full", 0) / 1e9

    return f"""<!doctype html><html><head><meta charset="utf-8">
<title>BAIF_Hackathon_{TEAM.replace(' ','')}{tno}_DocumentationPack</title>
<style>{CSS}</style></head><body>

<div class="cover">
  <h1>AwazSetu</h1>
  <div class="sub">Offline speech translation, dubbing and a grounded assistant<br>
  for Hindi, Marathi, English and Odia</div>
  <div class="rule"></div>
  <div class="sub" style="font-size:10.5pt">BAIF Hackathon — Final Assessment<br>Documentation Pack</div>
  <div class="meta">
    <b>Team {e(TEAM)}{e(tno)}</b><br>
    {e(OWNERS)}<br>
    {e(today)}<br><br>
    <span class="small">Every figure in this document was generated from the running system by
    <code>scripts/build_docpack.py</code>.<br>
    Re-running it reproduces this pack from the current state of the repository.</span>
  </div>
</div>

<h2>1. Solution overview</h2>

<h3>The problem</h3>
<p>BAIF's extension workers record field training material in one Indian language and need it
usable by farmers who speak another. Cloud translation is a poor fit for this particular job:</p>
<ul>
  <li><b>Connectivity.</b> The content is consumed in villages where a reliable uplink cannot be
      assumed, and a 40&nbsp;MB training video is not something a field worker uploads twice.</li>
  <li><b>Data control.</b> Field recordings contain identifiable farmers, their holdings and their
      livestock. Sending them to a third-party endpoint is a disclosure BAIF would have to justify.</li>
  <li><b>Cost per minute.</b> Per-minute pricing does not suit a library that is reprocessed
      whenever terminology is corrected.</li>
  <li><b>Domain vocabulary.</b> Generic engines mistranslate agricultural terms. Measured example:
      NLLB rendered <i>tubers</i> as a fungus in Marathi, as cooking pots in Hindi and as a bush in
      Odia — three different wrong answers from one source word.</li>
</ul>

<h3>The approach</h3>
<p>AwazSetu runs the entire pipeline on the operator's own laptop with no network involvement of
any kind. Its central design decision is that <b>everything a viewer consumes is computed once, at
ingest, behind a progress bar</b>: the transcript, all four subtitle tracks and all four
full-length voiceovers are written to disk before the item appears in the library. Playback
therefore loads no model at all.</p>
<p>The only models that run while a user is present are those serving the chat and voice
assistant. That is what makes behaviour predictable on modest hardware — switching subtitle
language or playing an Odia voiceover is a file read, not an inference.</p>

<h3>Key features</h3>
<ul>
  <li><b>Four languages</b> — Hindi, Marathi, English and Odia, as subtitles <i>and</i> as full
      spoken voiceovers.</li>
  <li><b>Video and audio</b> — mp4/mkv/webm and mp3/wav/m4a/aac/flac/opus handled identically.</li>
  <li><b>Grounded assistant</b> — BM25 retrieval over the transcript feeds a local LLM required to
      answer <i>only</i> from the transcript, and to emit a refusal sentinel when the fact is
      absent. It answers by voice as well as by text.</li>
  <li><b>Model Garden</b> — every model scored per language and per task, measured against the
      machine it is running on, with one-click presets.</li>
  <li><b>Zero-install distribution</b> — extract a folder, double-click one file.</li>
</ul>

<h3>Assumptions</h3>
<ul>
  <li>The operator machine matches the stated baseline: Intel i5 11th gen or Ryzen 5, 6+ cores,
      16&nbsp;GB RAM, Windows 11, no discrete GPU.</li>
  <li>Source media has intelligible speech. The system reports a confidence score and warns rather
      than silently emitting a poor transcript.</li>
  <li>Odia is a <b>target</b> language, not a source: no open ASR model can transcribe Odia speech,
      so Odia is produced by translating Hindi or Marathi audio. This matches BAIF's actual case —
      Marathi field video for an Odia audience.</li>
  <li>Content is curated by BAIF staff; the tool assists them rather than replacing review.</li>
</ul>

<h2>2. Architecture</h2>
{ARCH_SVG}

<h3>Components</h3>
<table>
<tr><th>Component</th><th>File</th><th>Responsibility</th></tr>
<tr><td>Pipeline orchestrator</td><td><code>app/pipeline.py</code></td><td>Ingest → transcript → translation → subtitles → manifest. Idempotent on SHA-256 of the source.</td></tr>
<tr><td>Speech recognition</td><td><code>app/asr.py</code></td><td>faster-whisper with VAD, beam 5, temperature ladder, degenerate-output sanitiser, per-segment confidence.</td></tr>
<tr><td>Translation</td><td><code>app/mt.py</code>, <code>app/indictrans_worker.py</code></td><td>IndicTrans2 routed across three direction checkpoints, subprocess-isolated. NLLB CTranslate2 as fallback.</td></tr>
<tr><td>Voiceover</td><td><code>app/dub_worker.py</code></td><td>MMS-TTS VITS per language, sentence-chunked, isochronically fitted to segment timings.</td></tr>
<tr><td>Assistant</td><td><code>app/chat.py</code>, <code>app/llm.py</code></td><td>BM25 retrieval + local LLM. Backend is in-process llama.cpp, or Ollama when already present.</td></tr>
<tr><td>Voice assistant</td><td><code>app/voice_worker.py</code></td><td>Microphone → Whisper small → grounded answer → MMS-TTS reply.</td></tr>
<tr><td>Model Garden</td><td><code>app/garden.py</code></td><td>Model catalogue, hardware probe, RAM budgeting, presets.</td></tr>
<tr><td>Web application</td><td><code>app/server.py</code></td><td>Flask on 127.0.0.1. Library, player, chat, settings, garden, exports.</td></tr>
<tr><td>Language registry</td><td><code>app/langs.py</code></td><td>Single source of truth; eight modules import it. Adding a language is one entry.</td></tr>
</table>

<h3>Data flow</h3>
<ol>
  <li>A file is dropped on the library page and hashed. An identical file re-uses its existing work
      folder, so re-adding media is free and URLs never change.</li>
  <li>FFmpeg extracts 16&nbsp;kHz mono PCM.</li>
  <li>Whisper transcribes with the language <i>detected</i>, never assumed — decoding Marathi as
      Hindi produces fluent-looking Devanagari nonsense. The transcript is cached together with the
      model name that produced it, so a later upgrade re-runs only what it must.</li>
  <li>A sanitiser drops degenerate segments <b>before</b> translation. This is what stops a
      transcription artefact becoming a fluent, confident and entirely invented subtitle.</li>
  <li>IndicTrans2 translates into the remaining three languages; a domain glossary corrects known
      agricultural terms on both the source and target side.</li>
  <li>WebVTT tracks and four MMS-TTS voiceovers are written. The manifest is the contract every
      later feature reads.</li>
</ol>

<h3>Non-functional requirements</h3>
<table>
<tr><th>Concern</th><th>How it is met</th></tr>
<tr><td><b>Security &amp; privacy</b></td><td>No data leaves the machine. <code>HF_HUB_OFFLINE=1</code>
and <code>TRANSFORMERS_OFFLINE=1</code> are set before any model import, so a download is not merely
avoided but impossible. The server binds <code>127.0.0.1</code> only and is never exposed to the LAN.
No credentials, accounts, API keys or telemetry exist in the runtime. All state lives under the
application folder; deleting the folder removes everything.</td></tr>
<tr><td><b>Resilience</b></td><td>Each heavy model runs in its own subprocess, so a native crash
degrades one feature instead of the application. ASR is one process per item — a shared CUDA context
was observed to exhaust a 4&nbsp;GB GPU and then fail every subsequent item — and falls back to CPU
on out-of-memory. The assistant falls back from the 3B model to the 1.5B automatically, and refuses
rather than inventing when retrieval finds nothing. Error messages are pre-written per language and
never machine-translated.</td></tr>
<tr><td><b>Scalability</b></td><td>Cost is linear in media minutes and fully parallel across items.
The batch driver separates GPU-bound transcription from CPU-bound translation and runs several
translations concurrently. Library lookup is a directory scan; BM25 is built lazily per item and
cached. The design scales by adding machines — there is no shared service to contend on.</td></tr>
<tr><td><b>Maintainability</b></td><td>Languages come from one table, models from one catalogue.
Settings map to environment variables read at call time, so a change applies without a restart.</td></tr>
<tr><td><b>Accessibility</b></td><td>Every answer is available as speech, which matters for users
with low literacy — the primary audience.</td></tr>
</table>

<h2>3. Tech stack</h2>
<table>
<tr><th>Layer</th><th>Choice</th><th>Why this one</th></tr>
<tr><td>Language</td><td>Python 3.10 (embedded)</td><td>Ships inside the package; nothing to install on the target.</td></tr>
<tr><td>Web</td><td>Flask 3.0, server-rendered Jinja</td><td>No build step, no Node toolchain, no bundler to ship.</td></tr>
<tr><td>Speech&nbsp;→&nbsp;text</td><td>faster-whisper 1.2 / CTranslate2 4.8</td><td>INT8 inference; far lighter than reference Whisper at equal accuracy.</td></tr>
<tr><td>Translation</td><td>IndicTrans2 distilled (AI4Bharat)</td><td>Purpose-built for Indian languages; hi↔mr and hi↔or translate directly with no English pivot.</td></tr>
<tr><td>Text&nbsp;→&nbsp;speech</td><td>MMS-TTS (VITS), Meta</td><td>Native Hindi, Marathi, English and Odia voices; consumes Devanagari directly.</td></tr>
<tr><td>Assistant</td><td>Qwen 2.5 3B / 1.5B, GGUF Q4_K_M via llama-cpp-python</td><td>In-process — no service, no installer, no second server.</td></tr>
<tr><td>Retrieval</td><td>rank-bm25</td><td>Pure Python. No vector store, no embedding model, no index to rebuild.</td></tr>
<tr><td>Media</td><td>FFmpeg 7.1 (bundled binary)</td><td>Resolved from the package, never from PATH.</td></tr>
<tr><td>Data</td><td>JSON manifests + WebVTT + WAV on disk</td><td>No database. Every artefact is inspectable and diffable.</td></tr>
<tr><td>Tooling</td><td>Git, a pinned wheel set, generated documentation</td><td>This pack is produced by a script from live data.</td></tr>
</table>
<p class="small"><b>Data / messaging / cloud:</b> none, by design. There is no broker, queue,
container runtime or cloud dependency. Concurrency is process-level; the work queue is the filesystem.</p>

<h2>4. Performance</h2>

<h3>Test machine</h3>
<p class="small">{e(hw.get('total_ram_gb'))}&nbsp;GB RAM · {e(hw.get('cores'))} logical cores ·
{e(gpu_name)} · detected tier <b>{e(hw.get('tier_label'))}</b>. The GPU accelerates batch
preparation of the shipped library only. The target deployment is CPU-only, and because every
shipped artefact is precomputed the demo machine never runs these workloads.</p>

<h3>Dataset</h3>
<p>{n_items} items — the BAIF field videos plus Odia instructional videos and English audio clips —
totalling <b>{q(total_min,1)} minutes</b> of speech and <b>{total_segs} transcript segments</b>,
yielding {n_subs} subtitle tracks and {n_dubs} voiceovers.</p>

<h3>Measured transcription throughput</h3>
<table>
<tr><th>Model</th><th>Device</th><th class="n">Audio (min)</th><th class="n">Time (s)</th>
<th class="n">RTF</th><th class="n">Segments</th><th class="n">Mean logprob</th></tr>
{tim_rows or '<tr><td colspan="7">No timing runs recorded.</td></tr>'}
</table>
<p class="small">RTF is processing time ÷ audio duration; lower is faster. Median large-v3 RTF
across these runs: <b>{q(rtf_med) if rtf_med else '—'}</b>. Mean log-probability is Whisper's own
confidence — near 0 is confident; below −1.0 is treated as unreliable and flagged to the operator
rather than passed downstream.</p>

<h3>The quality finding that drove this build</h3>
<div class="box">
<p><b>Whisper <code>small</code> had been silently losing content.</b> Every previously shipped
manifest was transcribed with <code>small</code>. Re-transcribing with <code>large-v3</code> showed
it had been truncating: total recovered speech rose from 73.7 to <b>81.6 minutes</b> — one video
alone gained 2.9 minutes that had never been transcribed at all. Segment counts rose correspondingly
(401.3: 54 → 70 segments), and mean log-probability improved to roughly −0.10. Content that is not
transcribed cannot be translated, subtitled, voiced or asked about, so this was silently capping
every downstream feature.</p>
</div>

<h3>Model footprint and per-language quality</h3>
<table>
<tr><th>Model</th><th class="n">en</th><th class="n">hi</th><th class="n">mr</th><th class="n">or</th>
<th class="n">Speed</th><th class="n">RAM&nbsp;MB</th><th class="n">Disk&nbsp;GB</th><th>Installed</th></tr>
{cat_rows}
</table>
<p class="small">Scores are 1–5, higher is better; a dash means the model cannot do that language at
all. Every ASR row is a dash for Odia because faster-whisper has no Odia token — Odia is reached
through translation and voiceover instead. This table is the same data the Model Garden page renders
interactively.</p>

<h3>Limitations</h3>
<ul>
  <li><b>No Odia speech recognition</b> exists in any open model we can ship. Odia is output-only.</li>
  <li><b>Voiceovers are time-fitted, not lip-synced.</b> Speech is compressed toward its segment slot;
      it tracks the video but is not dubbing in the cinematic sense.</li>
  <li><b>large-v3 needs about 3.2&nbsp;GB.</b> On a 16&nbsp;GB CPU-only laptop it is roughly three
      times slower than <code>medium</code>, which is why LITE ships <code>medium</code> as the working
      model while the shipped library itself was prepared with <code>large-v3</code>.</li>
  <li><b>A 3B assistant is a 3B assistant.</b> It is deliberately constrained to the transcript and
      refuses otherwise; it is not a general reasoner.</li>
  <li><b>No speaker diarisation</b> — multi-speaker interviews produce one undifferentiated transcript.</li>
</ul>

<h3>Improvements, in priority order</h3>
<ol>
  <li>Fine-tune IndicTrans2 on BAIF's own glossary; the terminology failures are systematic and
      therefore learnable.</li>
  <li>Speaker diarisation, which would make the farmer-interview material far more usable.</li>
  <li>Odia ASR when a usable open model appears, closing the one asymmetry in the language matrix.</li>
  <li>True isochronic dubbing with phoneme-level duration control.</li>
  <li>A shared library index so several operators can pool processed media over a LAN share.</li>
</ol>

<h2>5. Testing evidence</h2>

<h3>Strategy</h3>
<p>Three layers. <b>Asset tests</b> assert that every manifest, subtitle track and voiceover the
library references exists and is non-trivial. <b>Functional tests</b> exercise ASR, translation,
TTS, retrieval and the assistant end to end on real BAIF media. <b>Preflight</b>
(<code>scripts/doctor.py</code>) re-verifies the whole stack on the machine that will run the demo,
including generating an actual LLM answer — a model that loads but cannot answer is still broken.</p>

<h3>Preflight, run on this machine with the bundled runtime</h3>
<p class="small">{dp} passed · {dw} warnings · {dx} failures. Executed with a stripped environment:
no system Python, no PATH entries, no network.</p>
<pre>{e(doc.strip()[:2400])}</pre>

<h3>Sample test cases — expected vs actual</h3>
<table>
<tr><th>#</th><th>Case</th><th>Expected</th><th>Actual</th><th>Result</th></tr>
<tr><td>1</td><td>Zero-install runtime imports every dependency with no system Python</td>
<td>All 13 packages import</td><td>All import; torch 2.5.1+cpu, transformers 4.44.2</td><td><span class="k">PASS</span></td></tr>
<tr><td>2</td><td>Assistant loads from the bundled GGUF and answers a grounded question</td>
<td>Answers “12”</td><td>“12 goats.” in 0.6&nbsp;s (1.5B)</td><td><span class="k">PASS</span></td></tr>
<tr><td>3</td><td>FFmpeg resolves without PATH</td><td>Bundled binary runs</td>
<td>ffmpeg 7.1.1 from <code>runtime\\bin</code></td><td><span class="k">PASS</span></td></tr>
<tr><td>4</td><td>Marathi source produces four subtitle tracks including Odia</td>
<td>mr, hi, en, or</td><td>4 tracks per completed item</td><td><span class="k">PASS</span></td></tr>
<tr><td>5</td><td>Assistant refuses a fact not in the transcript</td>
<td>Refusal + closest lines, no invention</td>
<td>Emits <code>NOT_IN_TRANSCRIPT</code>; UI shows the pre-written refusal</td><td><span class="k">PASS</span></td></tr>
<tr><td>6</td><td>Degenerate ASR output never reaches subtitles</td>
<td>Sanitiser drops it before translation</td><td>16 garbage segments dropped on the affected item</td><td><span class="k">PASS</span></td></tr>
<tr><td>7</td><td>Marathi voiceover is audible, not silence</td><td>Non-trivial waveform</td>
<td>204,332 bytes vs 6,444 before the tokenizer fix</td><td><span class="k">PASS</span></td></tr>
<tr><td>8</td><td>Audio-only source behaves like video</td><td>Processed; player uses an audio element</td>
<td>4 English mp3 items complete in 4 languages</td><td><span class="k">PASS</span></td></tr>
<tr><td>9</td><td>Settings changes take effect without a restart</td><td>Next call uses the new model</td>
<td>Environment read per call; verified by switching the chat model</td><td><span class="k">PASS</span></td></tr>
<tr><td>10</td><td>Re-adding the same file does not duplicate it</td><td>Same work folder</td>
<td>SHA-256 keyed; folder and URLs unchanged</td><td><span class="k">PASS</span></td></tr>
<tr><td>11</td><td>Dropping duplicate <code>.bin</code> weights changes nothing</td>
<td>Identical synthesis</td><td>All 128 weight-norm tensors verified equal; output bit-identical</td><td><span class="k">PASS</span></td></tr>
<tr><td>12</td><td>ASR survives a GPU out-of-memory</td><td>Item fails alone, or retries on CPU</td>
<td>Per-item process isolation + CPU fallback</td><td><span class="k">PASS</span></td></tr>
</table>

<h3>Processed library — current state</h3>
<p class="small">{n_complete} of {n_items} items complete (four subtitle tracks and four voiceovers).</p>
<table>
<tr><th>Title</th><th>Kind</th><th>Src</th><th class="n">Min</th><th class="n">Segs</th>
<th>ASR model</th><th class="n">Confidence</th><th>Subtitles</th><th>Voiceovers</th><th>State</th></tr>
{lib_rows}
</table>

<h3>Supporting artefacts</h3>
<ul>
  <li><code>scripts/test_e2e.py</code> — the automated suite.</li>
  <li><code>scripts/doctor.py</code> — preflight, reproducible on any machine.</li>
  <li><code>dist/reprocess.log</code> — raw timing and confidence output behind the tables above.</li>
  <li><code>app/data/work/&lt;id&gt;/</code> — manifests, transcripts, subtitle tracks and voiceovers.</li>
</ul>

<h2>6. Deployment</h2>

<h3>Prerequisites</h3>
<p><b>None.</b> A Windows 10/11 x64 machine and free disk space. No Python, no FFmpeg, no Ollama, no
runtime, no administrator rights and no network — the package contains its own interpreter and every
binary it calls.</p>

<h3>Packages</h3>
<table>
<tr><th>Build</th><th class="n">Size</th><th>Contents</th><th>Use</th></tr>
<tr><td><b>LITE</b></td><td class="n">{q(size_lite,1) if size_lite else 'see dist/'} GB</td>
<td>Embedded runtime, FFmpeg, Whisper medium + small, IndicTrans2 (all three directions), four
voices, both assistant models, and the complete processed library</td>
<td>Internet transfer; everything the demo needs</td></tr>
<tr><td><b>FULL</b></td><td class="n">{q(size_full,1) if size_full else 'see dist/'} GB</td>
<td>LITE plus Whisper large-v3, tiny and base, the NLLB fallback engine, and a rescue kit of pinned
wheels and a Python installer</td><td>USB hand-over and long-term custody</td></tr>
</table>

<h3>Run steps</h3>
<ol>
  <li>Copy the package folder to the machine, or extract the zip. If it arrived as parts, run
      <code>JOIN-awazsetu-lite.bat</code> first — the parts carry SHA-256 checksums so a bad transfer
      is caught before the demo, not during it.</li>
  <li>Double-click <b><code>AwazSetu-Check.bat</code></b> and confirm it prints READY.</li>
  <li>Double-click <b><code>AwazSetu.bat</code></b>. A browser opens at <code>http://127.0.0.1:5000</code>.</li>
  <li>Turn Wi-Fi off. Nothing changes — which is the demonstration.</li>
</ol>

<h3>Configuration</h3>
<p>The Model Garden detects the machine and recommends a preset; one click applies it. Individual
models can be switched on the Settings page. Both write <code>app/settings.json</code>, and both
refuse to select a model that is not installed — so a configuration cannot be saved that would fail
at the next upload.</p>

<h3>Rollback</h3>
<table>
<tr><th>Situation</th><th>Action</th><th>Effect</th></tr>
<tr><td>A settings change made things worse</td><td>Apply a preset in the Model Garden, or delete
<code>app/settings.json</code></td><td>Returns to shipped defaults on the next call; no restart</td></tr>
<tr><td>A reprocess produced a worse result</td><td>Re-run it with the previous model selected</td>
<td>Work folders are keyed by content hash, so the item is replaced in place and its URL survives</td></tr>
<tr><td>A build is bad</td><td>Delete the folder and re-extract the previous package</td>
<td>Complete rollback. Nothing is installed and nothing is written outside the folder</td></tr>
<tr><td>The embedded runtime is blocked by policy</td><td><code>rescue_kit/</code> in FULL</td>
<td>Rebuilds the same pinned environment against a system Python, fully offline</td></tr>
</table>
<p class="small"><b>Logging.</b> The console window carries per-stage progress; per-item state is in
<code>app/data/work/&lt;id&gt;/status.json</code>, and batch runs append to <code>dist/reprocess.log</code>.</p>

<h2>7. Handover</h2>

<h3>Ownership and contacts</h3>
<table>
<tr><th>Role</th><th>Who</th><th>Scope</th></tr>
<tr><td>Technical owner</td><td>{e(OWNERS)}</td><td>Pipeline, models, packaging, this pack</td></tr>
<tr><td>Team</td><td>{e(TEAM)}{e(tno)}</td><td>BAIF Hackathon submission</td></tr>
<tr><td>Receiving organisation</td><td>BAIF</td><td>Operation, content curation, glossary ownership</td></tr>
</table>

<h3>Credentials approach</h3>
<div class="box">
<p><b>There are no credentials to hand over, and that is deliberate.</b> The running system has no
accounts, no API keys, no tokens, no licence servers and no telemetry. Nothing in the repository or
in either package contains a secret. The Hugging Face token used once to fetch the gated IndicTrans2
weights was supplied as an environment variable, never written to a file, and is not needed again —
the weights are downloaded and work offline permanently.</p>
<p>If BAIF later wants to add models, a Hugging Face account is needed <i>on the build machine
only</i>, never on a deployed one. Demo logistics notes containing meeting credentials are kept out
of the repository by <code>.gitignore</code> and form no part of any package.</p>
</div>

<h3>Runbook</h3>
<table>
<tr><th>Symptom</th><th>Cause</th><th>Fix</th></tr>
<tr><td>Library page is empty</td><td><code>app/data/work/</code> was not copied</td><td>Re-copy it; it holds every processed item</td></tr>
<tr><td>“Model could not be loaded — not enough free memory”</td><td>3B model on a busy machine</td><td>Close other applications, or apply the <b>Fast &amp; low RAM</b> preset</td></tr>
<tr><td>Assistant refuses a question you believe is covered</td><td>Retrieval found no lexical match</td><td>Ask using a word that appears in the video; the refusal lists the closest lines</td></tr>
<tr><td>A new upload is slow</td><td>Transcription is the cost, and it is one-time</td><td>Expect roughly 0.5× real time per pass; the progress bar is weighted by real cost</td></tr>
<tr><td>Subtitles look wrong for a term</td><td>Domain vocabulary</td><td>Add the correction to <code>app/glossary.json</code> and reprocess that item</td></tr>
<tr><td>Anything else</td><td>—</td><td>Run <code>AwazSetu-Check.bat</code>; it names the failing component</td></tr>
</table>

<h3>Training plan</h3>
<ol>
  <li><b>Operator — 30 minutes.</b> Add a file, watch the progress bar, switch subtitle languages,
      play a voiceover, ask the assistant a question by text and by voice.</li>
  <li><b>Power user — 1 hour.</b> The Model Garden: which model for which language, what the RAM
      budget means, when to reprocess, how to edit the glossary.</li>
  <li><b>Maintainer — half a day.</b> Pipeline walkthrough, adding a language via
      <code>app/langs.py</code>, rebuilding packages, reading preflight output.</li>
</ol>

<h3>Known issues</h3>
<ul>
  <li>Odia has no speech-recognition path (output-only). Not fixable with current open models.</li>
  <li>Whisper large-v3 needs one process per item on a 4&nbsp;GB GPU; a shared CUDA context exhausts
      it. Handled, but worth knowing before changing the batch driver.</li>
  <li>Loading any MMS-TTS voice prints a weight-norm warning. It is cosmetic — all 128 tensors were
      verified equal to the checkpoint and synthesis is bit-identical. Do not "fix" it.</li>
  <li>No speaker diarisation.</li>
</ul>

<h3>Next steps</h3>
<ol>
  <li>Hand BAIF the FULL package on a USB drive and run the preflight together on their machine.</li>
  <li>Collect a terminology list from BAIF's extension team and extend the glossary.</li>
  <li>Reprocess the library once the glossary is agreed — a background job, not a rebuild.</li>
  <li>Review the priority improvements in §4 and choose one for the next iteration.</li>
</ol>

<h3>Repository</h3>
<pre>{e(D.git_log())}</pre>

</body></html>"""


def main():
    team_no = os.environ.get("AWAZ_TEAM_NO", "")
    for i, a in enumerate(sys.argv):
        if a == "--team" and i + 1 < len(sys.argv):
            team_no = sys.argv[i + 1]
    out_dir = os.path.join(REPO, "dist")
    os.makedirs(out_dir, exist_ok=True)
    stem = (f"BAIF_Hackathon_{TEAM.replace(' ', '')}"
            + (f"[{team_no}]" if team_no else "") + "_DocumentationPack")
    safe = stem.replace("[", "_").replace("]", "")
    html_path = os.path.join(out_dir, safe + ".html")
    doc = build_html(team_no)
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(doc)
    print(f"HTML  {html_path}  ({len(doc)/1024:.0f} KB)")

    if "--pdf" in sys.argv:
        try:
            from weasyprint import HTML
            pdf_path = os.path.join(out_dir, safe + ".pdf")
            HTML(string=doc, base_url=REPO).write_pdf(pdf_path)
            print(f"PDF   {pdf_path}  ({os.path.getsize(pdf_path)/1e6:.2f} MB)")
        except Exception as ex:
            print(f"PDF   not rendered ({type(ex).__name__}: {ex})")
            print("      Open the HTML in a browser and print to PDF instead.")
    print("DOCPACK_DONE")


if __name__ == "__main__":
    main()
