"""AwazSetu — local Flask app: switchable-subtitle player + chat (offline).

    python server.py    ->    http://127.0.0.1:5000

Serves everything from app/data/work/<id>/. No network calls at runtime.
"""
from __future__ import annotations
import os
import json
import mimetypes

from flask import (Flask, send_from_directory, render_template, abort,
                   request, jsonify)

mimetypes.add_type("text/vtt", ".vtt")

APP_DIR = os.path.dirname(os.path.abspath(__file__))
WORK = os.path.join(APP_DIR, "data", "work")
from langs import LANG_NAMES

app = Flask(__name__,
            template_folder=os.path.join(APP_DIR, "templates"),
            static_folder=os.path.join(APP_DIR, "static"))


def _media_name(vid: str) -> str:
    """The source file as it was saved. Audio uploads keep their own extension —
    an .mp3 served as video.mp4 will not play in any browser."""
    work = os.path.join(WORK, vid)
    mp = os.path.join(work, "manifest.json")
    if os.path.exists(mp):
        try:
            with open(mp, encoding="utf-8") as f:
                n = json.load(f).get("media")
            if n and os.path.exists(os.path.join(work, n)):
                return n
        except Exception:
            pass
    if os.path.isdir(work):
        for f in sorted(os.listdir(work)):
            if f.startswith(("video.", "audio.")) and f != "audio.wav":
                return f
    return "video.mp4"


def load_manifest(vid: str) -> dict:
    """Load a manifest with `id` forced to the FOLDER it came from.

    The folder is the identity: every route resolves by it and every URL embeds it.
    The stored `id` is the content hash recorded at ingest, and the two diverge if a
    source file is ever replaced in place. player.html builds the media source, each
    subtitle track, the exports and the chat id from `m.id`, so a divergence renders
    a player whose every URL points at a directory that does not exist.
    """
    p = os.path.join(WORK, vid, "manifest.json")
    if not os.path.exists(p):
        abort(404)
    with open(p, encoding="utf-8") as f:
        m = json.load(f)
    if m.get("id") != vid:
        m["id_recorded"] = m.get("id")
        m["id"] = vid
    return m


@app.route("/")
def index():
    vids = []
    if os.path.isdir(WORK):
        for d in sorted(os.listdir(WORK)):
            mp = os.path.join(WORK, d, "manifest.json")
            if os.path.exists(mp):
                m = json.load(open(mp, encoding="utf-8"))
                vids.append({"id": d, "video": m.get("video"),
                             "kind": m.get("kind", "video"),
                             "langs": m.get("langs", [])})
    return render_template("index.html", videos=vids, lang_names=LANG_NAMES)


@app.route("/watch/<vid>")
def watch(vid: str):
    m = load_manifest(vid)
    tracks = [{"lang": L, "name": LANG_NAMES.get(L, L), "file": m["vtts"][L]}
              for L in m["langs"] if L in m.get("vtts", {})]
    import config
    return render_template("player.html", m=m, tracks=tracks,
                           auto_speak=config.load().get("auto_speak", True))


@app.route("/media/<vid>/<path:fn>")
def media(vid: str, fn: str):
    if fn in ("video", "media"):
        fn = _media_name(vid)
    return send_from_directory(os.path.join(WORK, vid), fn, conditional=True)


@app.route("/chat/<vid>", methods=["POST"])
def chat(vid: str):
    """Grounded RAG over the transcript (wired in Phase 3)."""
    try:
        from chat import answer  # lazy import so the LLM loads only in chat mode
    except Exception as e:
        import sys as _s
        print(f"[chat] engine import failed: {e}", file=_s.stderr, flush=True)
        from chat import STR_LLM_DOWN
        lg = (request.get_json(silent=True) or {}).get("lang", "en")
        return jsonify({"answer": STR_LLM_DOWN.get(lg, STR_LLM_DOWN["en"]),
                        "sources": [], "grounded": False})
    data = request.get_json(force=True)
    q = (data.get("q") or "").strip()
    lang = data.get("lang", "hi")
    if not q:
        return jsonify({"answer": "", "sources": []})
    m = load_manifest(vid)
    res = answer(m, q, lang, data.get("history"))
    return jsonify(res)


@app.route("/dub/<vid>/<lang>")
def dub(vid: str, lang: str):
    """Generate (once) an MMS-TTS voiceover for a language, then serve it. Cached."""
    import subprocess
    import sys
    work = os.path.join(WORK, vid)
    out = os.path.join(work, f"dub.{lang}.wav")
    if not os.path.exists(out) or os.path.getsize(out) < 10000:
        # Voiceovers are pre-built during processing so playback is instant. A missing
        # one means this video predates that language being selected -> Re-process.
        return jsonify({"error": "voiceover not generated for this language",
                        "hint": "use Re-process to rebuild with the current settings"}), 404
    return jsonify({"url": f"/media/{vid}/dub.{lang}.wav"})


def _content_id(path: str) -> str:
    import hashlib
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for c in iter(lambda: f.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()[:16]


@app.route("/upload", methods=["POST"])
def upload():
    """Save an uploaded video and kick off processing in a detached subprocess.
    The SHA-256 content id is the dedup key — the same video is served instantly."""
    from werkzeug.utils import secure_filename
    import subprocess
    import sys
    import shutil
    f = request.files.get("file")
    if not f or not f.filename:
        return jsonify({"error": "no file"}), 400
    updir = os.path.join(APP_DIR, "data", "uploads")
    os.makedirs(updir, exist_ok=True)
    safe = secure_filename(f.filename) or "video.mp4"
    if not os.path.splitext(safe)[1]:
        safe += ".mp4"
    path = os.path.join(updir, safe)
    f.save(path)
    vid = _content_id(path)
    work = os.path.join(WORK, vid)
    os.makedirs(work, exist_ok=True)
    if os.path.exists(os.path.join(work, "manifest.json")):
        return jsonify({"id": vid, "cached": True})   # dedup: already processed
    try:  # keep the original extension so audio stays audio
        ext = os.path.splitext(path)[1].lower() or ".mp4"
        from pipeline import AUDIO_EXT
        base = "audio" if ext in AUDIO_EXT else "video"
        shutil.copy(path, os.path.join(work, base + ext))
    except Exception:
        pass
    with open(os.path.join(work, "status.json"), "w", encoding="utf-8") as fp:
        json.dump({"stage": "Queued", "pct": 1}, fp)
    subprocess.Popen([sys.executable, os.path.join(APP_DIR, "run.py"), path],
                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return jsonify({"id": vid})


@app.route("/voice_chat/<vid>", methods=["POST"])
def voice_chat(vid: str):
    """Full offline voice loop: mic clip -> Whisper STT -> grounded chat ->
    MMS-TTS spoken answer. Returns the transcribed question, the answer text +
    timestamps, and a URL to the spoken-answer wav. STT and TTS run in the
    voice worker subprocess so the server stays torch-free."""
    import subprocess
    import sys
    from chat import answer
    f = request.files.get("audio")
    if not f:
        return jsonify({"error": "no audio"}), 400
    lang = request.form.get("lang", "hi")
    try:
        history = json.loads(request.form.get("history") or "[]")
    except Exception:
        history = []
    work = os.path.join(WORK, vid)
    os.makedirs(work, exist_ok=True)
    clip = os.path.join(work, "voice_in.webm")
    f.save(clip)
    worker = os.path.join(APP_DIR, "voice_worker.py")

    # Memory-saver: free RAM before the STT model loads (tight machines) by unloading
    # the resident LLM; chat.answer() reloads it a moment later. Toggle in Settings.
    if os.environ.get("AWAZ_VOICE_UNLOAD", "true").lower() == "true":
        try:
            import llm as _llm
            if _llm.backend() == "llamacpp":
                _llm.unload()          # in-process: just drop the reference
            else:
                import config as _c
                for m_ in (os.environ.get("AWAZ_LLM", "qwen2.5:3b"),
                           os.environ.get("AWAZ_LLM_FALLBACK", "qwen2.5:1.5b")):
                    subprocess.run([_c.ollama_exe(), "stop", m_], timeout=15,
                                   capture_output=True)
        except Exception:
            pass

    # 1) speech -> text
    stt_out = os.path.join(work, "voice_q.json")
    try:
        subprocess.run([sys.executable, worker, "stt", clip, lang, stt_out],
                       check=True, timeout=180)
        q = json.load(open(stt_out, encoding="utf-8")).get("text", "").strip()
    except Exception as e:
        return jsonify({"error": f"stt failed: {e}"}), 500
    if not q:
        NOHEAR = {"en": "I could not hear that clearly. Please try again.",
                  "hi": "आवाज़ स्पष्ट नहीं सुनाई दी। कृपया दोबारा बोलें।",
                  "mr": "आवाज स्पष्ट ऐकू आला नाही. कृपया पुन्हा बोला.",
                  "or": "ସ୍ୱର ସ୍ପଷ୍ଟ ଶୁଣାଗଲା ନାହିଁ। ଦୟାକରି ପୁଣି କୁହନ୍ତୁ।"}
        return jsonify({"question": "", "answer": NOHEAR.get(lang, NOHEAR["en"]),
                        "sources": [], "audio": None, "grounded": False})

    # 2) grounded answer (reuses the text chat pipeline: Q->En, RAG, LLM, ->lang)
    m = load_manifest(vid)
    res = answer(m, q, lang, history)
    ans = res.get("answer", "")

    # 3) text -> speech. If the answer couldn't be translated (stayed English),
    # speak it with the English voice rather than mispronouncing it in an Indic voice.
    tts_lang = lang
    if lang in ("hi", "mr") and ans:
        non_ascii = sum(1 for c in ans if ord(c) > 127)
        if non_ascii < len(ans) * 0.15:
            tts_lang = "en"
    audio_url = None
    try:
        tf = os.path.join(work, "voice_ans.txt")
        with open(tf, "w", encoding="utf-8") as fp:
            fp.write(ans)
        out_wav = os.path.join(work, "voice_ans.wav")
        subprocess.run([sys.executable, worker, "tts", tf, tts_lang, out_wav],
                       check=True, timeout=180)
        audio_url = f"/media/{vid}/voice_ans.wav?ts={os.path.getmtime(out_wav)}"
    except Exception:
        audio_url = None  # answer still returned as text

    return jsonify({"question": q, "answer": ans,
                    "sources": res.get("sources", []), "audio": audio_url})


@app.route("/status/<vid>")
def status(vid: str):
    p = os.path.join(WORK, vid, "status.json")
    if not os.path.exists(p):
        return jsonify({"stage": "starting", "pct": 0})
    with open(p, encoding="utf-8") as f:
        return jsonify(json.load(f))


@app.route("/export/<vid>/srt/<lang>")
def export_srt(vid: str, lang: str):
    from flask import Response
    from subs import srt_string
    m = load_manifest(vid)
    return Response(srt_string(m["segments"], lang), mimetype="application/x-subrip",
                    headers={"Content-Disposition": f'attachment; filename="{vid}.{lang}.srt"'})


@app.route("/export/<vid>/transcript")
def export_transcript(vid: str):
    from flask import Response
    m = load_manifest(vid)
    lines = []
    for s in m["segments"]:
        t = s.get("t", {})
        stamp = f"[{int(s['start'])//60}:{int(s['start']) % 60:02d}]"
        lines.append(stamp + "  " + "  |  ".join(f"{L}: {t.get(L, s['text'])}" for L in m["langs"]))
    return Response("\n".join(lines), mimetype="text/plain",
                    headers={"Content-Disposition": f'attachment; filename="{vid}.transcript.txt"'})


@app.route("/export/<vid>/mkv")
def export_mkv(vid: str):
    import subprocess
    import config as _c
    work = os.path.join(WORK, vid)
    m = load_manifest(vid)
    out = os.path.join(work, "bundle.mkv")
    if not os.path.exists(out):
        subs = [L for L in m["langs"] if os.path.exists(os.path.join(work, f"subs.{L}.vtt"))]
        dubs = [L for L in m["langs"] if os.path.exists(os.path.join(work, f"dub.{L}.wav"))]
        cmd = [_c.ffmpeg_exe(), "-y", "-i", os.path.join(work, _media_name(vid))]
        for L in subs:
            cmd += ["-i", os.path.join(work, f"subs.{L}.vtt")]
        for L in dubs:
            cmd += ["-i", os.path.join(work, f"dub.{L}.wav")]
        cmd += ["-map", "0:v:0", "-map", "0:a:0?"]
        for j in range(len(dubs)):
            cmd += ["-map", f"{1 + len(subs) + j}:a:0"]
        for j in range(len(subs)):
            cmd += ["-map", f"{1 + j}:0"]
        cmd += ["-c:v", "copy", "-c:a", "aac", "-c:s", "srt"]
        for j, L in enumerate(subs):
            cmd += [f"-metadata:s:s:{j}", f"language={L}"]
        cmd += [out]
        try:
            subprocess.run(cmd, check=True, timeout=600, capture_output=True)
        except Exception as e:
            return jsonify({"error": f"mkv mux failed: {e}"}), 500
    return send_from_directory(work, "bundle.mkv", as_attachment=True)


@app.route("/settings")
def settings_page():
    import config
    return render_template("settings.html", s=config.load(), st=config.status(),
                           defaults=config.DEFAULTS)


@app.route("/api/settings", methods=["GET", "POST"])
def api_settings():
    import config
    if request.method == "POST":
        patch = request.get_json(force=True)
        if isinstance(patch.get("langs"), str):
            patch["langs"] = [x for x in patch["langs"].split(",") if x]
        return jsonify(config.save(patch))
    return jsonify({"settings": config.load(), "status": config.status()})


@app.route("/garden")
def garden_page():
    """Model Garden — every model scored per language, per task, against THIS machine."""
    import garden
    import config
    return render_template("garden.html", g=garden.overview(), s=config.load())


@app.route("/api/garden")
def api_garden():
    import garden
    return jsonify(garden.overview())


@app.route("/api/garden/preset/<name>", methods=["POST"])
def api_garden_preset(name: str):
    """Apply a named preset. Refuses one whose models are not installed rather than
    writing a setting that would fail at the next upload."""
    import garden
    import config
    p = garden.PRESETS.get(name)
    if not p:
        abort(404)
    have = garden.installed_ids()
    need = set(p["settings"][k] for k in ("asr_model", "mic_model",
                                          "translate_engine", "chat_llm"))
    missing = sorted(need - have)
    if missing:
        return jsonify({"error": "preset needs models that are not installed",
                        "missing": missing}), 409
    return jsonify({"applied": name, "settings": config.save(dict(p["settings"]))})


@app.route("/reprocess/<vid>", methods=["POST"])
def reprocess(vid: str):
    """Re-run the pipeline for one video with the CURRENT settings. Clears cached
    transcript/subs/dubs so the new ASR/MT models actually apply; keeps video.mp4."""
    import subprocess
    import sys
    work = os.path.join(WORK, vid)
    src = os.path.join(work, _media_name(vid))
    if not os.path.exists(src):
        return jsonify({"error": "source video not found"}), 404
    for fn in os.listdir(work):
        if fn in ("transcript.raw.json", "manifest.json") or \
           fn.startswith(("subs.", "dub.", "bundle")):
            try:
                os.remove(os.path.join(work, fn))
            except Exception:
                pass
    # run.py rebuilds transcript, translations, subtitles AND every voiceover with the
    # current settings; the player polls /status/<vid> for the same multi-step bar.
    with open(os.path.join(work, "status.json"), "w", encoding="utf-8") as fp:
        json.dump({"stage": "Queued (re-process)", "pct": 1, "steps": []}, fp)
    subprocess.Popen([sys.executable, os.path.join(APP_DIR, "run.py"), src],
                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return jsonify({"id": vid, "reprocessing": True})


@app.route("/search")
def search():
    q = (request.args.get("q") or "").strip().lower()
    hits = []
    if q and os.path.isdir(WORK):
        for d in sorted(os.listdir(WORK)):
            mp = os.path.join(WORK, d, "manifest.json")
            if not os.path.exists(mp):
                continue
            m = json.load(open(mp, encoding="utf-8"))
            for s in m["segments"]:
                blob = (" ".join(str(v) for v in (s.get("t") or {}).values())
                        + " " + s["text"]).lower()
                if q in blob:
                    hits.append({"id": d, "video": m.get("video"),
                                 "start": s["start"], "text": s["text"]})
                    break  # one hit per video in the list
    return jsonify({"hits": hits})


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=int(os.environ.get("AWAZ_PORT", "5000")),
            debug=False, threaded=True)
