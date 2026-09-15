"""Full-quality re-run of every processed item: large-v3 ASR + IndicTrans2 + 4 languages.

    python scripts/reprocess_all.py            # phase 1: ASR + MT + subtitles
    python scripts/reprocess_all.py --list     # show what would run, change nothing

Every shipped manifest was transcribed with whisper `small` (see manifest.asr_model),
which is the weakest Indic model in the guide. This re-runs each item from its own
cached source media — the content hash is unchanged, so the work-folder id, the
library entry and every existing URL stay valid.

Three phases, because they want different hardware:
  1. ASR   - GPU, one subprocess per item (a shared CUDA context exhausts a 4 GB card)
  2. MT    - CPU, several items in parallel, grouped by direction checkpoint
  3. Dubs  - CPU, several voices in parallel (scripts/build_dubs_par.py)

`transcript.raw.json` short-circuits ASR in pipeline.process_video, so it is dropped when
it came from a weaker model — otherwise this would silently re-emit the same transcript.
It is KEPT when it already came from the target model, so an interrupted run resumes.
"""
from __future__ import annotations
import os
import sys
import json
import time
import shutil

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
APP = os.path.join(REPO, "app")
WORK = os.path.join(APP, "data", "work")
sys.path.insert(0, APP)

# Full quality, GPU where it helps. int8_float16 (not float16) is what fits large-v3
# on a 4 GB laptop GPU — see app/asr.py.
os.environ.setdefault("HF_HOME", os.path.join(REPO, "models", "hf-cache"))
os.environ.setdefault("HF_HUB_OFFLINE", "1")
os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")
os.environ["AWAZ_WHISPER"] = os.environ.get("AWAZ_WHISPER", "large-v3")
os.environ["AWAZ_DEVICE"] = os.environ.get("AWAZ_DEVICE", "cuda")
os.environ["AWAZ_COMPUTE"] = os.environ.get("AWAZ_COMPUTE", "int8_float16")
os.environ["AWAZ_MT"] = os.environ.get("AWAZ_MT", "indictrans2")
os.environ["AWAZ_BEAM"] = os.environ.get("AWAZ_BEAM", "5")
# MT is the slowest stage and is CPU-bound in a subprocess. Unset, IndicWorkerMT used
# to fall back to 4 threads on a 16-thread machine.
os.environ.setdefault("AWAZ_CPU_THREADS", str(max(4, (os.cpu_count() or 8) - 4)))
os.environ.setdefault("AWAZ_MT_BATCH", "8")
os.environ.setdefault("PYTHONIOENCODING", "utf-8")

TARGETS = ("hi", "mr", "en", "or")
LOG = os.path.join(REPO, "dist", "reprocess.log")


def is_done(p: str) -> bool:
    """True when this folder already carries a full-quality result.

    Lets the driver be restarted (to pick up a tuning change) without throwing away
    items it has already finished — the expensive ASR pass is never repeated.
    """
    mf = os.path.join(p, "manifest.json")
    if not os.path.exists(mf):
        return False
    try:
        m = json.load(open(mf, encoding="utf-8"))
    except Exception:
        return False
    return (m.get("asr_model") == os.environ["AWAZ_WHISPER"]
            and m.get("mt_engine", "").startswith("indictrans2")
            and set(TARGETS).issubset(set(m.get("langs", []))))


def items():
    """(id, media_path, src_lang, title) for every real work folder; junk reported."""
    out, junk = [], []
    for d in sorted(os.listdir(WORK)):
        p = os.path.join(WORK, d)
        if not os.path.isdir(p):
            continue
        mf = os.path.join(p, "manifest.json")
        if not os.path.exists(mf):
            junk.append(p)
            continue
        if is_done(p) and "--force" not in sys.argv:
            print(f"skip (already full quality): {d}")
            continue
        m = json.load(open(mf, encoding="utf-8"))
        media = m.get("media")
        if not media or not os.path.exists(os.path.join(p, media)):
            # fall back to whatever source container is present (never audio.wav,
            # which is the 16 kHz extraction, not the source)
            cands = [f for f in os.listdir(p)
                     if f.startswith(("video.", "audio.")) and f != "audio.wav"]
            if not cands:
                junk.append(p)
                continue
            media = sorted(cands)[0]
        out.append((d, os.path.join(p, media), m.get("src_lang"), m.get("video", d)))
    return out, junk


def log(msg, fh=None):
    line = f"[{time.strftime('%H:%M:%S')}] {msg}"
    print(line, flush=True)
    if fh:
        fh.write(line + "\n")
        fh.flush()


def phase_asr(todo, fh):
    """GPU pass: transcribe every item with large-v3, ONE SUBPROCESS PER ITEM.

    Kept separate from translation because the two stages want different hardware —
    interleaving them left the GPU idle during the CPU-bound IndicTrans2 stage.

    Each item gets its own process because a single shared CUDA context ran the 4 GB
    card out of memory after two items and then failed every subsequent item with
    "invalid device ordinal". Per-item isolation costs ~7 s of model load and makes a
    failure local instead of fatal.
    """
    import json as _json
    import subprocess
    helper = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_asr_one.py")

    pend = []
    for vid, media, src, title in todo:
        raw = os.path.join(WORK, vid, "transcript.raw.json")
        if os.path.exists(raw):
            try:
                if _json.load(open(raw, encoding="utf-8")).get("asr_model") ==                         os.environ["AWAZ_WHISPER"]:
                    continue
            except Exception:
                pass
        pend.append((vid, media, src, title))
    if not pend:
        log("ASR: every transcript is already full quality", fh)
        return
    log(f"ASR: {len(pend)} item(s) with {os.environ['AWAZ_WHISPER']} "
        f"on {os.environ['AWAZ_DEVICE']}", fh)
    t_all = time.time()
    for i, (vid, media, src, title) in enumerate(pend, 1):
        t0 = time.time()
        r = subprocess.run([sys.executable, helper, vid, src or "auto"],
                           capture_output=True, text=True, encoding="utf-8",
                           errors="replace", timeout=5400)
        out = (r.stdout or "").strip().splitlines()
        ok = [l for l in out if l.startswith("ASR_OK")]
        if r.returncode == 0 and ok:
            log(f"  ASR [{i}/{len(pend)}] {title[:34]}: {ok[-1][7+len(vid):].strip()} "
                f"({time.time()-t0:.0f}s wall)", fh)
        else:
            tail = ((r.stdout or "") + (r.stderr or "")).strip()[-400:]
            log(f"  ASR [{i}/{len(pend)}] {vid[:8]} FAILED rc={r.returncode} :: {tail}", fh)
    log(f"ASR phase done in {(time.time()-t_all)/60:.1f} min", fh)


def _free_gb():
    try:
        import ctypes

        class MS(ctypes.Structure):
            _fields_ = [("dwLength", ctypes.c_ulong), ("dwMemoryLoad", ctypes.c_ulong),
                        ("ullTotalPhys", ctypes.c_ulonglong),
                        ("ullAvailPhys", ctypes.c_ulonglong),
                        ("ullTotalPageFile", ctypes.c_ulonglong),
                        ("ullAvailPageFile", ctypes.c_ulonglong),
                        ("ullTotalVirtual", ctypes.c_ulonglong),
                        ("ullAvailVirtual", ctypes.c_ulonglong),
                        ("ullAvailExtendedVirtual", ctypes.c_ulonglong)]
        m = MS()
        m.dwLength = ctypes.sizeof(MS)
        ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(m))
        return m.ullAvailPhys / (1024 ** 3)
    except Exception:
        return None


def phase_mt(todo, fh, workers: int):
    """CPU pass: translate + subtitle, several items at a time.

    Worker count is capped by FREE memory, not by core count. Each IndicTrans2
    process resides at about 1.6 GB, and three of them alongside anything else on a
    16 GB machine crashed the native extension with 0xC0000005 rather than raising
    a clean MemoryError -- so the cap has to be applied before launching, not
    recovered from afterwards.
    """
    import subprocess
    helper = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_mt_one.py")
    free = _free_gb()
    if free:
        safe = max(1, int(free // 2.2))
        if safe < workers:
            log(f"MT: {free:.1f} GB free -> capping {workers} workers to {safe}", fh)
            workers = safe
    queue = list(todo)
    src_of = {t[0]: t[2] for t in todo}
    running: list = []
    done = fails = 0
    attempts: dict = {}
    t0 = time.time()
    log(f"MT: {len(queue)} item(s), {workers} parallel worker(s)", fh)
    env = dict(os.environ)
    # Split the cores across workers; oversubscribing makes every worker slower.
    env["AWAZ_CPU_THREADS"] = str(max(2, ((os.cpu_count() or 8) - 2) // max(1, workers)))
    while queue or running:
        while queue and len(running) < workers:
            vid, media, src, title = queue.pop(0)
            p = subprocess.Popen([sys.executable, helper, vid, src or "auto"],
                                 stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                 text=True, encoding="utf-8", errors="replace", env=env)
            running.append((p, vid, title, time.time()))
            log(f"  MT start {vid[:8]} {title[:40]}", fh)
        time.sleep(2)
        for rec in running[:]:
            p, vid, title, t_start = rec
            if p.poll() is None:
                continue
            running.remove(rec)
            out = (p.stdout.read() or "").strip() if p.stdout else ""
            if p.returncode == 0 and "MT_OK" in out:
                done += 1
                tail = [l for l in out.splitlines() if l.startswith("MT_OK")]
                log(f"  MT done  {vid[:8]} in {time.time()-t_start:.0f}s :: "
                    f"{tail[0] if tail else ''}", fh)
            else:
                n = attempts.get(vid, 0) + 1
                attempts[vid] = n
                if n == 1:
                    # One retry, alone. A native crash here is nearly always memory
                    # pressure from a neighbour, and it clears when run solo.
                    log(f"  MT retry {vid[:8]} (attempt 2, will run with fewer "
                        f"neighbours) rc={p.returncode}", fh)
                    queue.append((vid, None, src_of.get(vid), title))
                else:
                    fails += 1
                    log(f"  MT FAIL  {vid[:8]} rc={p.returncode} :: {out[-400:]}", fh)
    log(f"MT: {done} ok, {fails} failed in {(time.time()-t0)/60:.1f} min", fh)


def main():
    todo, junk = items()
    if "--list" in sys.argv:
        for i, (vid, media, src, title) in enumerate(todo, 1):
            print(f"{i:2}. {vid}  src={src}  {title}")
        print(f"\n{len(todo)} items to reprocess; {len(junk)} junk folder(s): "
              + ", ".join(os.path.basename(j) for j in junk))
        return

    for j in junk:                       # manifest-less folders are unusable dead weight
        shutil.rmtree(j, ignore_errors=True)
        print("removed junk folder:", os.path.basename(j))

    os.makedirs(os.path.dirname(LOG), exist_ok=True)
    fh = open(LOG, "a", encoding="utf-8")
    log(f"=== reprocess {len(todo)} items | whisper={os.environ['AWAZ_WHISPER']} "
        f"{os.environ['AWAZ_DEVICE']}/{os.environ['AWAZ_COMPUTE']} "
        f"mt={os.environ['AWAZ_MT']} targets={TARGETS} ===", fh)

    t_all = time.time()
    workers = 2
    for a in sys.argv:
        if a.startswith("--workers="):
            workers = int(a.split("=", 1)[1])

    if "--mt-only" not in sys.argv:
        phase_asr(todo, fh)
    if "--asr-only" not in sys.argv:
        phase_mt(todo, fh, workers)

    # Phase 3: voiceovers. Every existing one is stale after a re-transcription --
    # it still plays, so nothing looks broken, but it speaks the previous transcript.
    if "--no-dubs" not in sys.argv and "--asr-only" not in sys.argv:
        import subprocess
        helper = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                              "build_dubs_par.py")
        log("=== phase 3: voiceovers ===", fh)
        r = subprocess.run([sys.executable, "-u", helper, "--workers=4"],
                           capture_output=True, text=True, encoding="utf-8",
                           errors="replace", timeout=14400)
        for ln in (r.stdout or "").splitlines()[-40:]:
            log("  " + ln, fh)
        if r.returncode != 0:
            log(f"  voiceover phase rc={r.returncode} :: {(r.stderr or '')[-300:]}", fh)

    log(f"=== all phases done in {(time.time()-t_all)/60:.1f} min ===", fh)
    fh.close()
    print("REPROCESS_PHASE1_DONE")


if __name__ == "__main__":
    main()
