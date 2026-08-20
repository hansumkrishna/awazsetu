"""AwazSetu — rebuild the pitch deck (reflects the BUILT app + voice/literacy slide).

    python generate_deck.py    ->    AwazSetu_Deck.pptx  (6 slides, 16:9)
"""
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.enum.shapes import MSO_SHAPE

RED = RGBColor(0xB0, 0x1C, 0x24)
INK = RGBColor(0x1A, 0x1A, 0x1A)
MUT = RGBColor(0x6B, 0x6B, 0x6B)
LINE = RGBColor(0xE2, 0xE2, 0xE0)
DARK = RGBColor(0x1A, 0x1A, 0x1A)
WHITE = RGBColor(0xFF, 0xFF, 0xFF)
CARD = RGBColor(0xFA, 0xFA, 0xF8)
CHIP = RGBColor(0xF6, 0xEC, 0xED)
SERIF, BODY = "Georgia", "Calibri"

prs = Presentation()
prs.slide_width, prs.slide_height = Inches(13.333), Inches(7.5)
BL = prs.slide_layouts[6]


def slide():
    s = prs.slides.add_slide(BL)
    bg = s.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, prs.slide_width, prs.slide_height)
    bg.fill.solid(); bg.fill.fore_color.rgb = WHITE; bg.line.fill.background()
    bg.shadow.inherit = False
    return s


def box(s, x, y, w, h, fill=CARD, line=LINE, rad=True):
    shp = s.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE if rad else MSO_SHAPE.RECTANGLE,
                             Inches(x), Inches(y), Inches(w), Inches(h))
    if fill is None:
        shp.fill.background()
    else:
        shp.fill.solid(); shp.fill.fore_color.rgb = fill
    if line is None:
        shp.line.fill.background()
    else:
        shp.line.color.rgb = line; shp.line.width = Pt(0.75)
    shp.shadow.inherit = False
    return shp


def text(s, x, y, w, h, runs, align=PP_ALIGN.LEFT, anchor=MSO_ANCHOR.TOP, space=2):
    """runs: list of paragraphs; each paragraph is a list of (txt,size,bold,color,font)."""
    tb = s.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    tf = tb.text_frame; tf.word_wrap = True; tf.vertical_anchor = anchor
    for m in (tf.margin_left, ):
        pass
    tf.margin_left = tf.margin_right = Inches(0.05); tf.margin_top = tf.margin_bottom = Inches(0.02)
    for i, para in enumerate(runs):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.alignment = align; p.space_after = Pt(space); p.space_before = Pt(0)
        for (t, sz, b, col, fn) in para:
            r = p.add_run(); r.text = t
            r.font.size = Pt(sz); r.font.bold = b; r.font.color.rgb = col; r.font.name = fn
    return tb


def R(t, sz, b=False, col=INK, fn=BODY):
    return (t, sz, b, col, fn)


def header(s, kicker, title, sub):
    box(s, 0, 0, 13.333, 0.12, fill=RED, line=None, rad=False)
    text(s, 0.6, 0.42, 12, 0.6, [[R(title, 30, True, RED, SERIF)]])
    text(s, 0.62, 1.15, 9.5, 0.5, [[R(sub, 18, False, INK, SERIF)]])
    text(s, 10.2, 0.5, 2.6, 0.5, [[R(kicker, 12, True, MUT, BODY)]], align=PP_ALIGN.RIGHT)


def icon_card(s, x, y, w, h, title, body, fill=CARD, tcol=INK, bcol=MUT):
    box(s, x, y, w, h, fill=fill)
    text(s, x + 0.25, y + 0.18, w - 0.5, 0.4, [[R(title, 15, True, tcol, BODY)]])
    text(s, x + 0.25, y + 0.62, w - 0.5, h - 0.7, [[R(body, 12, False, bcol, BODY)]])


def chips(s, x, y, items, w=1.9, h=0.42, gap=0.15):
    for i, it in enumerate(items):
        cx = x + i * (w + gap)
        box(s, cx, y, w, h, fill=CHIP, line=None)
        text(s, cx, y + 0.06, w, 0.32, [[R(it, 11.5, True, RED, BODY)]], align=PP_ALIGN.CENTER)


def foot(s, txt):
    box(s, 0.6, 6.72, 11.3, 0.52, fill=DARK, line=None)
    text(s, 0.85, 6.79, 10.8, 0.4, [[R(txt, 12, False, WHITE, BODY)]], anchor=MSO_ANCHOR.MIDDLE)


def pageno(s, n):
    text(s, 12.05, 6.85, 1.1, 0.3, [[R(f"{n:02d} / 06", 10, True, MUT, BODY)]], align=PP_ALIGN.RIGHT)


# ---------------- Slide 1 — Title / Problem ----------------
s = slide()
box(s, 0, 0, 13.333, 0.12, fill=RED, line=None, rad=False)
box(s, 0.6, 0.5, 0.32, 0.32, fill=RED, line=None)
text(s, 1.0, 0.46, 6, 0.45, [[R("AwazSetu", 24, True, INK, SERIF), R("   Built for BAIF", 13, False, MUT, BODY)]])
box(s, 5.0, 0.5, 1.7, 0.42, fill=CHIP, line=None)
text(s, 5.0, 0.56, 1.7, 0.32, [[R("Tech for Good", 11.5, True, RED, BODY)]], align=PP_ALIGN.CENTER)
text(s, 0.6, 1.35, 12, 0.6, [[R("The video is in Hindi.", 30, False, INK, SERIF)]])
text(s, 0.6, 2.0, 12.2, 0.7, [[R("The farmer speaks Marathi.  ", 30, True, INK, SERIF),
                               R("The internet isn’t there.", 30, True, RED, SERIF)]])
text(s, 0.6, 2.95, 12.1, 1.0, [[R("An offline desktop app that transcribes, translates and dubs audio, video or text across "
      "Hindi · Marathi · English — with switchable subtitles and on-demand voiceover, and now "
      "chat & voice: ask the video a question and hear the answer, entirely on-device.", 15, False, INK, BODY)]])
for i, (big, sub) in enumerate([
        ("83M", "native Marathi speakers (2011 Census) — most agri material is English or Hindi"),
        ("~85%", "of Indians don’t use English even as a second language"),
        ("0", "Mbps internet needed — the app runs fully on-device")]):
    x = 0.6 + i * 4.05
    box(s, x, 4.15, 3.8, 1.55, fill=(RED if i == 2 else CARD))
    text(s, x + 0.25, 4.3, 3.4, 0.7, [[R(big, 40, True, (WHITE if i == 2 else RED), SERIF)]])
    text(s, x + 0.25, 5.05, 3.4, 0.6, [[R(sub, 11.5, False, (WHITE if i == 2 else MUT), BODY)]])
foot(s, "Watch it in your language — and ask it anything, out loud.   Hindi · Marathi · English   —   audio · video · text")
pageno(s, 1)

# ---------------- Slide 2 — User Journey ----------------
s = slide()
header(s, "USER JOURNEY", "USER JOURNEY & REQUEST LIFECYCLE", "What the user does, and what runs underneath")
text(s, 0.6, 1.75, 5, 0.35, [[R("THE USER  (village-centre laptop)", 12, True, RED, BODY)]])
for i, (t, b) in enumerate([
        ("Uploads a file", "Drops in an audio clip or a Hindi agri video; picks the languages."),
        ("Watches in their language", "Plays it and flips subtitles / voiceover between Hindi · Marathi · English on the fly."),
        ("Asks the video", "Types or 🎙 speaks a question → a grounded answer in their language, spoken aloud, with jump-to-timestamp.")]):
    y = 2.2 + i * 1.35
    box(s, 0.6, y, 0.55, 0.55, fill=RED, line=None)
    text(s, 0.6, y + 0.08, 0.55, 0.4, [[R(str(i + 1), 18, True, WHITE, SERIF)]], align=PP_ALIGN.CENTER)
    text(s, 1.35, y - 0.02, 4.4, 0.4, [[R(t, 15, True, INK, BODY)]])
    text(s, 1.35, y + 0.42, 4.5, 0.8, [[R(b, 12, False, MUT, BODY)]])
text(s, 6.5, 1.75, 6, 0.35, [[R("WHAT RUNS PER REQUEST  (all on-device)", 12, True, RED, BODY)]])
steps = [("Detect & demux", "route by type; FFmpeg → 16 kHz mono audio"),
         ("Cache check", "SHA-256 the source; if seen, reuse — skip all models"),
         ("Segment (VAD)", "split on voice activity — one short chunk in memory"),
         ("ASR → MT → subs/dub", "transcribe, translate, switchable subtitles + on-demand voice"),
         ("Index for chat", "embed the transcript into the local knowledge base"),
         ("Answer", "retrieve top lines + local LLM → grounded reply, spoken back")]
for i, (t, b) in enumerate(steps):
    y = 2.15 + i * 0.72
    box(s, 6.5, y, 6.23, 0.64, fill=CARD)
    text(s, 6.7, y + 0.1, 0.4, 0.45, [[R(str(i + 1), 15, True, RED, SERIF)]])
    text(s, 7.15, y + 0.06, 5.5, 0.3, [[R(t + "  ", 12.5, True, INK, BODY), R(b, 11, False, MUT, BODY)]])
foot(s, "Zero-config for the farmer: one action per screen · large icon-led buttons · local-language labels · no login.   Operators get an advanced Settings page.")
pageno(s, 2)

# ---------------- Slide 3 — Architecture ----------------
s = slide()
header(s, "ARCHITECTURE", "SOLUTION ARCHITECTURE & TECH STACK", "Low-level design — offline & open-source")
def layer(y, label):
    text(s, 0.6, y + 0.12, 1.6, 0.4, [[R(label, 11, True, MUT, BODY)]])
layer(1.75, "CLIENT")
box(s, 2.2, 1.72, 10.5, 0.62, fill=CARD)
text(s, 2.4, 1.83, 10.2, 0.4, [[R("Desktop UI (Flask + HTML5, localhost)", 13, True, INK, BODY),
     R("  — upload · live language switch · chat & voice pane · progress", 12, False, MUT, BODY)]])
layer(2.55, "ORCHESTRATION")
box(s, 2.2, 2.52, 10.5, 0.62, fill=DARK, line=None)
text(s, 2.4, 2.63, 10.2, 0.4, [[R("Request Orchestrator (Python)", 13, True, WHITE, BODY),
     R("   routes by input type · checks cache first · staged model loading", 12, False, RGBColor(0xD9,0xD9,0xD9), BODY)]])
procs = [("ASR", "faster-whisper INT8", "audio → text"),
         ("Translate", "NLLB-200 INT8 (default)\nIndicTrans2 (optional)", "hi ↔ en ↔ mr"),
         ("Chat", "BM25 + qwen2.5 (Ollama)", "grounded RAG"),
         ("Speak", "MMS-TTS", "text → speech"),
         ("Compose", "FFmpeg", "switchable subs + dub")]
for i, (t, m, r) in enumerate(procs):
    x = 0.6 + i * 2.44
    box(s, x, 3.35, 2.28, 1.35, fill=CARD)
    text(s, x + 0.18, 3.48, 2.0, 0.35, [[R(t, 14, True, INK, BODY)]])
    text(s, x + 0.18, 3.86, 2.0, 0.6, [[R(m, 10.5, False, INK, BODY)]])
    text(s, x + 0.18, 4.42, 2.0, 0.25, [[R(r, 10, True, RED, BODY)]])
layer(4.95, "PERSISTENCE")
box(s, 2.2, 4.92, 10.5, 0.6, fill=DARK, line=None)
text(s, 2.4, 5.02, 10.2, 0.4, [[R("Searchable Knowledge Library (SQLite / local)", 13, True, WHITE, BODY),
     R("   source-hash cache · transcript chunks & embeddings · local media", 12, False, RGBColor(0xD9,0xD9,0xD9), BODY)]])
for i, (t, b) in enumerate([
        ("Fits 16 GB / i5", "INT8 weights + VAD chunks + staged loading — chat models never co-resident with ASR/MT/TTS; peak RAM stays flat."),
        ("Truly offline", "All model weights local; the app makes zero network calls at runtime."),
        ("Cheap to re-run", "SHA-256 of the source keys the library; exact & near-duplicate inputs skip the models.")]):
    x = 0.6 + i * 4.05
    text(s, x, 5.7, 3.85, 0.3, [[R(t, 13, True, RED, BODY)]])
    text(s, x, 6.05, 3.9, 1.0, [[R(b, 10.5, False, MUT, BODY)]])
pageno(s, 3)

# ---------------- Slide 4 — Voice & Chat (NEW capstone) ----------------
s = slide()
header(s, "CHAT & VOICE", "UNDERSTAND IT, DON’T JUST TRANSLATE IT", "Chat & voice — the accessibility capstone")
flow = ["transcript", "local index", "ask (type or 🎙 speak)", "grounded answer in your language", "🔊 heard aloud"]
for i, f in enumerate(flow):
    x = 0.6 + i * 2.47
    box(s, x, 1.7, 2.25, 0.7, fill=(RED if i in (2, 4) else CARD))
    text(s, x + 0.1, 1.83, 2.05, 0.5, [[R(f, 11.5, True, (WHITE if i in (2, 4) else INK), BODY)]],
         align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE)
    if i < 4:
        text(s, x + 2.18, 1.8, 0.35, 0.5, [[R("→", 16, True, RED, BODY)]])
# hero example
box(s, 0.6, 2.7, 6.0, 1.75, fill=CARD)
text(s, 0.85, 2.85, 5.5, 0.3, [[R("HERO EXAMPLE", 11, True, RED, BODY)]])
text(s, 0.85, 3.2, 5.5, 1.2, [[R("A Hindi PM-KISAN scheme video. A Marathi farmer "
     "speaks: “मला या योजनेचा लाभ मिळेल का?” → AwazSetu answers "
     "from the video, in Marathi, aloud — offline.", 14, False, INK, BODY)]])
# literacy insight
box(s, 6.75, 2.7, 5.98, 1.75, fill=DARK, line=None)
text(s, 7.0, 2.85, 5.5, 0.3, [[R("WHY IT MATTERS — LITERACY", 11, True, RGBColor(0xF0,0xB0,0xB4), BODY)]])
text(s, 7.0, 3.2, 5.5, 1.2, [[R("Text chat quietly needs literacy. Voice doesn’t. "
     "Speak-and-hear is what makes AwazSetu work for the farmer who can’t read "
     "or type — not a convenience, the whole point.", 14, False, WHITE, BODY)]])
# reuse note
box(s, 0.6, 4.65, 12.13, 0.72, fill=CHIP, line=None)
text(s, 0.85, 4.78, 11.6, 0.5, [[R("Zero new models.  ", 13, True, RED, BODY),
     R("The same Whisper that transcribes the video also hears you; the same MMS-TTS that dubs also "
       "speaks the answer; the same library grounds the chat.", 12.5, False, INK, BODY)]])
chips(s, 0.6, 5.6, ["Grounded — only from this video", "Fully offline — zero network", "Fits 16 GB — staged loading"], w=4.0, h=0.5, gap=0.06)
foot(s, "Type or talk · answers in Hindi · Marathi · English · with a jump-to-timestamp · no open-web, no hallucinated facts.")
pageno(s, 4)

# ---------------- Slide 5 — Dataset & Workflow ----------------
s = slide()
header(s, "DATA & TUNING", "DATASET & TRANSLATION WORKFLOW", "Domain-tuned for the field")
for i, (t, b) in enumerate([
        ("Collect", "Public, licence-clear agri corpora: ICAR / KVK material, farmer-helpline transcripts, open captions (hi / mr / en)."),
        ("Align & glossary  ·  shipped", "Curate a term glossary (crop, pest, irrigation) used as source-side post-correction so field terms win."),
        ("Domain-adapt  ·  roadmap", "LoRA fine-tune IndicTrans2 on aligned pairs; verify hi ↔ mr runs as a direct pair, not pivoted through English."),
        ("Evaluate", "Held-out agri set: chrF/BLEU + glossary-hit ≥ 90%; chat groundedness / refusal-when-unknown; native-speaker fluency.")]):
    y = 1.75 + i * 1.12
    box(s, 0.6, y, 7.4, 1.0, fill=CARD)
    text(s, 0.8, y + 0.14, 7.0, 0.35, [[R(t, 14, True, INK, BODY)]])
    text(s, 0.8, y + 0.52, 7.0, 0.5, [[R(b, 11.5, False, MUT, BODY)]])
text(s, 8.4, 1.75, 4.3, 0.35, [[R("SUPPORTED INPUTS", 12, True, RED, BODY)]])
for i, (t, b) in enumerate([("Audio", "field recordings & training guides"),
                            ("Video", "agri demo videos — .mp4 / .mkv, 720p/1080p"),
                            ("Limits", "target ≤ 15 min · ≤ 200 MB per file")]):
    y = 2.2 + i * 0.95
    box(s, 8.4, y, 4.33, 0.82, fill=CARD)
    text(s, 8.6, y + 0.13, 4.0, 0.3, [[R(t + "   ", 13, True, RED, BODY), R(b, 11, False, MUT, BODY)]])
box(s, 8.4, 5.1, 4.33, 1.15, fill=DARK, line=None)
text(s, 8.6, 5.24, 4.0, 0.35, [[R("Searchable knowledge library", 13, True, WHITE, BODY)]])
text(s, 8.6, 5.62, 4.0, 0.6, [[R("Results kept & indexed; near-duplicate sources are served from the library — nothing is translated twice.", 10.5, False, RGBColor(0xD9,0xD9,0xD9), BODY)]])
pageno(s, 5)

# ---------------- Slide 6 — Execution & Status ----------------
s = slide()
header(s, "STATUS", "EXECUTION PLAN & WHAT’S WORKING", "From plan to a working demo")
weeks = [("Foundation", "offline ASR + translation on target spec", True),
         ("Core MVP", "text + audio path end-to-end; cache + glossary", True),
         ("Video + player", "switchable subtitles + on-demand voiceover", True),
         ("Chat + Voice", "grounded RAG + local LLM; speak & hear", True),
         ("Harden", "staged loading; NLLB self-sufficient; Settings", True),
         ("Ship", ".exe packaging · agri demo · handover", False)]
for i, (t, b, done) in enumerate(weeks):
    x = 0.6 + (i % 3) * 4.05
    y = 1.7 + (i // 3) * 1.35
    box(s, x, y, 3.85, 1.2, fill=(CARD if done else RED))
    mark = "✓ " if done else "→ "
    text(s, x + 0.2, y + 0.12, 3.5, 0.35, [[R(mark + t, 14, True, (RED if done else WHITE), BODY)]])
    text(s, x + 0.2, y + 0.55, 3.5, 0.55, [[R(b, 11, False, (MUT if done else WHITE), BODY)]])
text(s, 0.6, 4.55, 12, 0.35, [[R("TEAM OF 5", 12, True, RED, BODY),
     R("    ML / Translation  ·  App / Pipeline  ·  Media / QA + Docs", 12, False, INK, BODY)]])
text(s, 0.6, 5.05, 12.1, 1.0, [[R("Top risks (status):  ", 12, True, INK, BODY),
     R("small-LLM Indic answers → strict grounding + Sarvam-1 (roadmap)  ·  Marathi TTS → MMS voices shipped  ·  "
       "memory on i5 → INT8 + staged loading (solved)  ·  IndicTrans2 quality → optional after login (NLLB is the offline default)",
       11.5, False, MUT, BODY)]])
chips(s, 0.6, 6.05, ["100% offline", "100% open-source", "chat & voice", "Windows · i5 / 16 GB", "≤ 200 MB · .mp4/.mkv"],
      w=2.35, h=0.5, gap=0.08)
pageno(s, 6)

import os
out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "AwazSetu_Deck.pptx")
prs.save(out)
print("saved", out, "-", len(prs.slides._sldIdLst), "slides")
