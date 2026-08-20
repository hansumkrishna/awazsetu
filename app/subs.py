"""AwazSetu — WebVTT subtitle writer (switchable soft tracks for the HTML5 player)."""
from __future__ import annotations


def _ts(t: float) -> str:
    h = int(t // 3600)
    m = int((t % 3600) // 60)
    s = t % 60
    return f"{h:02d}:{m:02d}:{s:06.3f}"


def write_vtt(segments: list[dict], path: str, lang: str) -> str:
    lines = ["WEBVTT", ""]
    for i, seg in enumerate(segments, 1):
        text = (seg.get("t", {}).get(lang)) or seg["text"]
        lines += [str(i), f"{_ts(seg['start'])} --> {_ts(seg['end'])}", text, ""]
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    return path


def srt_string(segments: list[dict], lang: str) -> str:
    """SubRip (.srt) text for download."""
    def ts(t):
        return f"{_ts(t)}".replace(".", ",")
    out = []
    for i, seg in enumerate(segments, 1):
        text = (seg.get("t", {}).get(lang)) or seg["text"]
        out += [str(i), f"{ts(seg['start'])} --> {ts(seg['end'])}", text, ""]
    return "\n".join(out)
