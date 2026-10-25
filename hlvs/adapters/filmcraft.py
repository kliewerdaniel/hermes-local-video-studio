"""FilmCraft adapter — the NLE.

Three things this adapter refuses to let the caller get wrong:

1. `--project` requires an existing file; a new project is created with
   `--save-as`.
2. `timeline.place` takes ITEM ids; transitions and selection take SEQUENCE
   CLIP ids. They are different namespaces.
3. A transition acts on the edit point under the playhead, so the playhead must
   be moved first — and the export still succeeds if you forget.
"""
from __future__ import annotations

import json
import os
import subprocess
from typing import Any, Dict, List, Optional

TICKS_PER_SECOND = 254_016_000_000


def seconds_to_ticks(seconds: float) -> int:
    return int(round(seconds * TICKS_PER_SECOND))


class FilmCraftError(RuntimeError):
    pass


class FilmCraft:
    def __init__(self, binary: str, project_path: str):
        self.binary = binary
        self.project_path = project_path
        self._created = False

    # -- plumbing ---------------------------------------------------------
    def _call(self, args: List[str], save: bool = True, timeout: int = 900) -> str:
        cmd = [self.binary]
        if self._created:
            cmd += ["--project", self.project_path]
            if save:
                cmd += ["--save"]
        cmd += args
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        if r.returncode != 0:
            raise FilmCraftError("%s failed (%s): %s" % (args[:2], r.returncode,
                                                         (r.stderr or r.stdout)[:500]))
        return r.stdout

    @staticmethod
    def _last_json(text: str) -> Dict[str, Any]:
        """Return the last complete JSON document in the output.

        `import` and `inspect` print PRETTY-PRINTED, multi-line JSON. A
        line-by-line scan finds only `}` and returns nothing; a naive
        last-brace-to-last-brace scan finds a NESTED object and silently returns
        a fragment (which made `inspect sequence` look like an empty timeline).
        Decode from each `{` and keep the object that ends at the final brace.
        """
        decoder = json.JSONDecoder()
        final = text.rfind("}")
        if final == -1:
            return {}
        idx = text.find("{")
        while idx != -1:
            try:
                obj, consumed = decoder.raw_decode(text, idx)
            except json.JSONDecodeError:
                idx = text.find("{", idx + 1)
                continue
            if idx + consumed - 1 == final:
                return obj if isinstance(obj, dict) else {}
            idx = text.find("{", idx + 1)
        return {}

    # -- session ----------------------------------------------------------
    def create(self, name: str, width: int, height: int, fps: int,
               sample_rate: int = 48000) -> None:
        cmd = [self.binary, "--save-as", self.project_path, "exec", "file.newProject",
               json.dumps({"name": name})]
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        if r.returncode != 0 or not os.path.isfile(self.project_path):
            raise FilmCraftError("could not create project: %s" % (r.stderr or r.stdout)[:400])
        self._created = True
        # The command id is `file.newSequence`. `sequence.new` does not exist —
        # discovered by reading the catalogue after it failed, which is the
        # discipline this repo is about: discover, do not assume.
        self._call(["exec", "file.newSequence",
                    json.dumps({"name": "S", "width": width, "height": height,
                                "fps": fps, "sampleRate": sample_rate})])

    def open(self) -> None:
        if not os.path.isfile(self.project_path):
            raise FilmCraftError("no project at %s" % self.project_path)
        self._created = True

    # -- media ------------------------------------------------------------
    def import_media(self, path: str) -> int:
        out = self._call(["import", os.path.abspath(path)])
        data = self._last_json(out)
        items = data.get("items") or []
        if not items:
            raise FilmCraftError("import returned no item id for %s: %r" % (path, out[:200]))
        return int(items[0])

    def place(self, item: int, track: str, seconds: float,
              duration: Optional[float] = None) -> None:
        payload: Dict[str, Any] = {"item": item, "track": track, "seconds": seconds}
        if duration is not None:
            payload["duration"] = seconds_to_ticks(duration)
        self._call(["exec", "timeline.place", json.dumps(payload)])

    def sequence(self) -> Dict[str, Any]:
        return self._last_json(self._call(["inspect", "sequence"], save=False))

    def placed_clips(self, track_index: int = 0) -> List[Dict[str, Any]]:
        """Sequence CLIP ids in timeline order — not the item ids you placed."""
        seq = self.sequence()
        video = seq.get("video") or []
        if track_index >= len(video):
            return []
        return sorted(video[track_index].get("items", []), key=lambda i: i.get("start", 0))

    # -- edit -------------------------------------------------------------
    def set_playhead(self, seconds: float) -> None:
        self._call(["exec", "playhead.set", json.dumps({"seconds": seconds})])

    def dissolve(self, clip_id: int, seconds: float, frames: int = 12) -> None:
        self.set_playhead(seconds)
        self._call(["exec", "sequence.applyVideoTransition",
                    json.dumps({"clip": clip_id, "effect": "cross_dissolve",
                                "frames": frames, "edge": "in"})])

    def motion(self, clip_id: int, start: float, end: float,
               scale_from: float, scale_to: float,
               width: int, height: int) -> None:
        """Ken Burns. `time` is SEQUENCE-absolute — a time before the clip's
        start clamps onto the first keyframe and the clip never moves."""
        # `keyframe: true` is REQUIRED to animate. The catalogue says it plainly:
        # "a parameter that is not animated gets a new static value whatever the
        # time". Without the flag this writes two static values, the second wins,
        # the clip never moves, and nothing errors.
        self._call(["exec", "effects.setParam",
                    json.dumps({"clip": clip_id, "effect": "motion", "param": "scale",
                                "value": scale_from, "time": seconds_to_ticks(start),
                                "keyframe": True})])
        self._call(["exec", "effects.setParam",
                    json.dumps({"clip": clip_id, "effect": "motion", "param": "scale",
                                "value": scale_to, "time": seconds_to_ticks(end),
                                "keyframe": True})])

    def transitions_count(self) -> int:
        seq = self.sequence()
        total = 0
        for tr in seq.get("video") or []:
            total += len(tr.get("transitions") or [])
        return total

    # -- output -----------------------------------------------------------
    def export(self, out_path: str, bitrate_kbps: int = 4000,
               loudness: bool = False) -> Dict[str, Any]:
        settings = {"bitrateKbps": bitrate_kbps, "bitrateMode": "vbr1Pass",
                    "effects": {"loudness": {"enabled": loudness}}}
        out = self._call(["export", os.path.abspath(out_path), "--format", "h264",
                          "--settings", json.dumps(settings)], save=False, timeout=1800)
        return self._last_json(out)
