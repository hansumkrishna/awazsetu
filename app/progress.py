"""AwazSetu — multi-step processing progress written to work/<id>/status.json.

Everything a viewer consumes (transcript, translations, subtitles, voiceovers) is
produced ONCE here, while the progress bar is on screen. At playback nothing is
synthesised: only the chat and voice assistant run in real time.

    p = Progress(work, langs=["mr", "hi", "en"], src="mr")
    p.start("asr"); ...; p.done("asr")
"""
from __future__ import annotations
import os
import json
import time

LANG_NAMES = {"hi": "हिंदी", "mr": "मराठी", "en": "English"}

# (key, label, relative cost) — cost drives the weighting of the overall bar so it
# advances at a believable rate instead of jumping.
BASE_STEPS = [
    ("extract", "Extracting audio", 1),
    ("asr", "Transcribing speech", 10),
    ("mt", "Translating", 5),
    ("subs", "Building subtitles", 1),
]
DUB_COST = 6


class Progress:
    def __init__(self, work: str, langs=None, src: str | None = None):
        self.work = work
        self.path = os.path.join(work, "status.json")
        self.t0 = time.time()
        self.steps = []
        for k, label, cost in BASE_STEPS:
            self.steps.append({"key": k, "label": label, "cost": cost, "state": "pending"})
        for L in (langs or []):
            self.steps.append({"key": f"dub:{L}", "cost": DUB_COST, "state": "pending",
                               "label": f"Voiceover — {LANG_NAMES.get(L, L)}"})
        self.total = sum(s["cost"] for s in self.steps) or 1
        self.stage = "Queued"
        self._write()

    # -- internals -------------------------------------------------------------
    def _pct(self) -> int:
        got = 0.0
        for s in self.steps:
            if s["state"] == "done":
                got += s["cost"]
            elif s["state"] == "running":
                got += s["cost"] * 0.5      # half credit while in flight
        return max(1, min(99, round(got / self.total * 100)))

    def _write(self, stage: str | None = None, pct: int | None = None):
        payload = {
            "stage": stage if stage is not None else self.stage,
            "pct": pct if pct is not None else self._pct(),
            "elapsed": round(time.time() - self.t0, 1),
            "steps": [{k: s[k] for k in ("key", "label", "state")} for s in self.steps],
        }
        try:
            tmp = self.path + ".tmp"
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(payload, f, ensure_ascii=False)
            os.replace(tmp, self.path)      # atomic: the poller never reads a half file
        except Exception:
            pass

    def _find(self, key: str):
        for s in self.steps:
            if s["key"] == key:
                return s
        return None

    # -- public ----------------------------------------------------------------
    def add_dubs(self, langs):
        """Register voiceover steps once the source language is actually known."""
        for L in langs:
            if not self._find(f"dub:{L}"):
                self.steps.append({"key": f"dub:{L}", "cost": DUB_COST, "state": "pending",
                                   "label": f"Voiceover — {LANG_NAMES.get(L, L)}"})
        self.total = sum(s["cost"] for s in self.steps) or 1
        self._write()

    def start(self, key: str, note: str = ""):
        s = self._find(key)
        if s:
            s["state"] = "running"
            self.stage = s["label"] + (f" {note}" if note else "")
        self._write()

    def done(self, key: str):
        s = self._find(key)
        if s:
            s["state"] = "done"
        self._write()

    def fail(self, key: str, why: str = ""):
        s = self._find(key)
        if s:
            s["state"] = "failed"
            if why:
                s["label"] += f" — {why[:60]}"
        self._write()

    def finish(self):
        for s in self.steps:
            if s["state"] in ("pending", "running"):
                s["state"] = "done"
        self.stage = "done"
        self._write("done", 100)

    def error(self, msg: str):
        self._write(f"error: {msg[:160]}", self._pct())
