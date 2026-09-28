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
import paths
# Kept for the many `paths.work_dir(vid)` call sites that only ever read the
# shipped library; anything that resolves an arbitrary id goes through
# paths.work_dir() so an MSIX install can still process new uploads.
WORK = paths.SHIPPED_WORK
from langs import LANG_NAMES
import i18n

app = Flask(__name__,
            template_folder=os.path.join(APP_DIR, "templates"),
            static_folder=os.path.join(APP_DIR, "static"))

UI_COOKIE = "awaz_ui_lang"


def ui_lang() -> str:
    """The interface language for THIS request.

    Cookie first, and that ordering matters: a field laptop is shared, so the
    person in front of it must be able to switch language without rewriting the
    operator's saved default. Then the saved default, then whatever the browser
    itself asks for, then English.
    """
    try:
        c = request.cookies.get(UI_COOKIE)
    except Exception:
        c = None
    if c:
        return i18n.normalise(c)
    try:
        import config
        saved = config.load().get("ui_lang")
    except Exception:
        saved = None
    if saved:
        return i18n.normalise(saved)
    try:
        return i18n.normalise(request.accept_languages.best_match(i18n.UI_LANGS))
    except Exception:
        return i18n.DEFAULT_UI


@app.context_processor
def _inject_i18n():
    """Every template gets T, UI and the picker rows without being asked.

    Done here rather than in each route because the failure mode of the manual
    approach is silent: one forgotten render_template and that page alone renders
    every label as an empty string.
    """
    L = ui_lang()
    return {"UI": L, "T": i18n.pack(L), "UI_CHOICES": i18n.choices(),
            "UI_NAMES": i18n.UI_NAMES}


@app.route("/api/ui-lang", methods=["POST"])
def api_ui_lang():
    """Switch the interface language: cookie for this browser, settings.json as
    the machine default so the next person sees the last choice pre-selected."""
    data = request.get_json(silent=True) or {}
    lang = i18n.normalise(data.get("lang"))
    resp = jsonify({"lang": lang, "strings": i18n.pack(lang)})
    resp.set_cookie(UI_COOKIE, lang, max_age=365 * 24 * 3600, samesite="Lax")
    if data.get("remember", True):
        try:
            import config
            config.save({"ui_lang": lang})
        except Exception:
            pass       # read-only install (MSIX): the cookie still carries the choice
    return resp


def _media_name(vid: str) -> str:
    """The source file as it was saved. Audio uploads keep their own extension —
    an .mp3 served as video.mp4 will not play in any browser."""
    work = paths.work_dir(vid)
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
    p = os.path.join(paths.work_dir(vid), "manifest.json")
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
    for d, folder in paths.list_work():
        m = json.load(open(os.path.join(folder, "manifest.json"), encoding="utf-8"))
        vids.append({"id": d, "video": m.get("video"),
                     "kind": m.get("kind", "video"),
                     "langs": m.get("langs", [])})
    import config
    return render_template("index.html", videos=vids, lang_names=LANG_NAMES,
                           lang_prompt=bool(config.load().get("lang_prompt", True)))


@app.route("/watch/<vid>")
def watch(vid: str):
    m = load_manifest(vid)
    tracks = [{"lang": L, "name": LANG_NAMES.get(L, L), "file": m["vtts"][L]}
              for L in m["langs"] if L in m.get("vtts", {})]
    import config
    from langs import ASR_LANGS
    return render_template("player.html", m=m, tracks=tracks,
                           asr_langs=ASR_LANGS,
                           auto_speak=config.load().get("auto_speak", True))


@app.route("/media/<vid>/<path:fn>")
def media(vid: str, fn: str):
    if fn in ("video", "media"):
        fn = _media_name(vid)
    return send_from_directory(paths.work_dir(vid), fn, conditional=True)


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
    work = paths.work_dir(vid)
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
    updir = paths.uploads_dir()
    safe = secure_filename(f.filename) or "video.mp4"
    if not os.path.splitext(safe)[1]:
        safe += ".mp4"
    path = os.path.join(updir, safe)
    f.save(path)
    vid = _content_id(path)
    # Dedup BEFORE creating anything, or re-uploading a shipped video leaves an
    # empty folder in the writable root that then shadows the real one.
    if os.path.exists(os.path.join(paths.work_dir(vid), "manifest.json")):
        return jsonify({"id": vid, "cached": True})
    work = os.path.join(paths.work_rw(), vid)
    os.makedirs(work, exist_ok=True)
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
    lang = i18n.normalise(request.form.get("lang", "hi"))
    # Odia has no speech-recognition model, so a microphone clip in Odia can only
    # produce nonsense. Say that, in Odia, instead of transcribing it to garbage
    # and answering the garbage -- which is what used to happen.
    from langs import can_transcribe
    if not can_transcribe(lang):
        return jsonify({"question": "", "answer": i18n.t("voice_no_asr", lang),
                        "sources": [], "audio": None, "grounded": False})
    try:
        history = json.loads(request.form.get("history") or "[]")
    except Exception:
        history = []
    work = paths.work_dir(vid)
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
        return jsonify({"question": "", "answer": i18n.t("voice_nohear", lang),
                        "sources": [], "audio": None, "grounded": False})

    # 2) grounded answer (reuses the text chat pipeline: Q->En, RAG, LLM, ->lang)
    m = load_manifest(vid)
    res = answer(m, q, lang, history)
    ans = res.get("answer", "")

    # 3) text -> speech, using a voice that matches the script actually produced.
    # An Indic voice handed Latin text mispronounces every word of it, so when the
    # answer could not be translated the English voice reads it instead. Decided
    # from the Unicode block rather than an ASCII ratio, which mis-fired on Odia
    # and on Hindi answers containing technical terms.
    tts_lang = lang
    try:
        from chat import is_target_language, script_of
        import langid
        if ans and not is_target_language(ans, lang):
            # Marathi read aloud by the Hindi voice is not merely accented, it
            # is wrong, so the voice follows the language actually produced
            # rather than the one that was requested.
            tts_lang = (langid.devanagari_lang(ans)
                        or {"latin": "en", "orya": "or"}.get(script_of(ans), "en"))
    except Exception:
        pass
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
    p = os.path.join(paths.work_dir(vid), "status.json")
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
    work = paths.work_dir(vid)
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
    from langs import LANGS
    # The target-language chips used to be hardcoded to hi/mr/en in the template,
    # so opening Settings and pressing Save silently dropped Odia from the saved
    # list. They are built from the language table now.
    content = [{"code": k, "native": v["native"], "name": v["name"],
                "asr": v["asr"]} for k, v in LANGS.items()]
    return render_template("settings.html", s=config.load(), st=config.status(),
                           defaults=config.DEFAULTS, content_langs=content)


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
    work = paths.work_dir(vid)
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
    if q:
        for d, folder in paths.list_work():
            m = json.load(open(os.path.join(folder, "manifest.json"),
                               encoding="utf-8"))
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
