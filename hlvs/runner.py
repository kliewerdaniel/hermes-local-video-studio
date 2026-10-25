"""Execute a validated project and report what was requested vs verified.

The rule this module enforces: a step is only `verified` when a function measured
a property of an artifact on disk. If a tool accepted a command and nothing
measured the result, the step stays `requested_only` and the report says so.
That distinction is the difference between a build log and a quality report.
"""
from __future__ import annotations

import json
import os
import time
from typing import Any, Dict, List, Optional

from . import schema
from .adapters import filmcraft as fc
from .adapters import media
from .adapters.qwen import QwenAdapter, QwenError
from .capabilities import discover, find_binary
from .provenance import (FAILED, REQUESTED_ONLY, SKIPPED, VERIFIED, Manifest,
                         StepResult, sha256_file)


class Runner:
    def __init__(self, project: Dict[str, Any], project_path: str,
                 workdir: str, log=print):
        self.project = project
        self.project_path = os.path.abspath(project_path)
        self.base = os.path.dirname(self.project_path)
        self.workdir = os.path.abspath(workdir)
        self.log = log
        self.manifest = Manifest((project.get("project") or {}).get("name", "untitled"), self.workdir)
        self.assets: Dict[str, str] = {}
        self.scene_starts: Dict[str, Dict[str, float]] = {}
        os.makedirs(self.workdir, exist_ok=True)

    # -- helpers ----------------------------------------------------------
    def _step(self, name: str, requested: Dict[str, Any]) -> StepResult:
        return StepResult(step=name, requested=requested)

    def _finish(self, result: StepResult, started: float) -> StepResult:
        result.seconds = round(time.time() - started, 2)
        self.manifest.add(result)
        icon = {VERIFIED: "OK  ", REQUESTED_ONLY: "REQ ", FAILED: "FAIL", SKIPPED: "SKIP"}.get(result.status, "?   ")
        detail = result.verified or result.error or "no measurement"
        self.log("%s %-26s %s" % (icon, result.step, str(detail)[:110]))
        return result

    # -- stages -----------------------------------------------------------
    def check_capabilities(self) -> StepResult:
        started = time.time()
        r = self._step("capabilities", {"probe": True})
        info = discover(probe=True)
        self.caps = info
        # Only uncached generate assets need the model server. A resumed run whose
        # stills already exist must not be blocked by a studio that is not running.
        cache_path = os.path.join(self.workdir, "assets.json")
        cache = {}
        if os.path.isfile(cache_path):
            try:
                cache = json.load(open(cache_path))
            except json.JSONDecodeError:
                cache = {}
        need_qwen = any(
            (a.get("source") or {}).get("kind") == "generate"
            and not os.path.isfile((cache.get(a["id"]) or {}).get("path", ""))
            for a in self.project.get("assets", []))
        problems = []
        if need_qwen and not info["qwen"].get("reachable"):
            problems.append("qwen studio not reachable on :8787 (needed for generate assets)")
        if not find_binary("filmcraft"):
            problems.append("filmcraft-cli not found (needed for assembly)")
        if problems:
            r.requested["capabilities"] = "checked"
            return self._finish(r.fail("; ".join(problems)), started)
        r.verify(rust_apps_found=sum(1 for a in info["rust_apps"].values() if a.get("runs")),
                 qwen_reachable=bool(info["qwen"].get("reachable")),
                 text_filters=info["text_filters"])
        return self._finish(r, started)

    def generate_assets(self, resume: bool = True) -> List[StepResult]:
        results = []
        cache_path = os.path.join(self.workdir, "assets.json")
        cache = {}
        if resume and os.path.isfile(cache_path):
            cache = json.load(open(cache_path))
        adapter = QwenAdapter()

        for asset in self.project.get("assets", []):
            aid = asset["id"]
            src = asset.get("source") or {}
            started = time.time()

            if src.get("kind") == "file":
                path = src["path"]
                if not os.path.isabs(path):
                    path = os.path.join(self.base, path)
                self.assets[aid] = path
                r = self._step("asset:%s" % aid, {"kind": "file", "path": path})
                results.append(self._finish(r.verify(sha256=sha256_file(path),
                                                     bytes=os.path.getsize(path)), started))
                continue

            r = self._step("asset:%s" % aid, {
                "kind": "generate", "mode": src.get("mode", "t2i"),
                "prompt": (src.get("prompt") or "")[:120], "seed": src.get("seed")})

            cached = cache.get(aid)
            if resume and cached and os.path.isfile(cached.get("path", "")):
                self.assets[aid] = cached["path"]
                results.append(self._finish(
                    r.verify(path=cached["path"], sha256=cached.get("sha256"),
                             reused=True), started))
                continue

            try:
                out = adapter.generate(
                    prompt=src["prompt"], mode=src.get("mode", "t2i"),
                    width=src.get("width") or self.project["project"]["canvas"]["width"],
                    height=src.get("height") or self.project["project"]["canvas"]["height"],
                    seed=src.get("seed"))
            except QwenError as exc:
                results.append(self._finish(r.fail(str(exc)), started))
                continue

            digest = sha256_file(out["path"])
            self.assets[aid] = out["path"]
            cache[aid] = {"path": out["path"], "sha256": digest}
            json.dump(cache, open(cache_path, "w"), indent=2)
            self.manifest.record_artifact(aid, out["path"])
            results.append(self._finish(
                r.verify(path=out["path"], sha256=digest, job_id=out["job_id"],
                         generation_seconds=out["seconds"]), started))
        return results

    def assemble(self) -> List[StepResult]:
        results = []
        meta = self.project["project"]
        canvas, fps = meta["canvas"], meta["fps"]
        binary = find_binary("filmcraft")
        if not binary:
            r = self._step("assemble", {})
            return [self._finish(r.fail("filmcraft-cli not found"), time.time())]

        proj_path = os.path.join(self.workdir, "film.fcproj")
        nle = fc.FilmCraft(binary, proj_path)

        started = time.time()
        r = self._step("nle:create", {"path": proj_path, "canvas": canvas, "fps": fps})
        try:
            nle.create(meta["name"], canvas["width"], canvas["height"], fps)
            results.append(self._finish(r.verify(project_exists=os.path.isfile(proj_path)), started))
        except fc.FilmCraftError as exc:
            results.append(self._finish(r.fail(str(exc)), started))
            return results

        # place scenes in order, tracking the timeline position ourselves
        cursor = 0.0
        placed: List[Dict[str, Any]] = []
        for scene in self.project["scenes"]:
            started = time.time()
            asset_path = self.assets.get(scene["asset"])
            r = self._step("place:%s" % scene["id"],
                           {"asset": scene["asset"], "start": cursor,
                            "duration": scene["duration"]})
            if not asset_path or not os.path.isfile(asset_path):
                results.append(self._finish(r.fail("missing asset %r" % scene["asset"]), started))
                cursor += float(scene["duration"])
                continue
            try:
                item = nle.import_media(asset_path)
                nle.place(item, "V1", cursor, float(scene["duration"]))
            except fc.FilmCraftError as exc:
                results.append(self._finish(r.fail(str(exc)), started))
                cursor += float(scene["duration"])
                continue
            placed.append({"id": scene["id"], "start": cursor,
                           "duration": float(scene["duration"]), "item": item})
            self.scene_starts[scene["id"]] = {"start": cursor, "duration": float(scene["duration"])}
            results.append(self._finish(r.verify(item_id=item), started))
            cursor += float(scene["duration"])

        # map sequence clip ids by timeline order — never reuse item ids
        started = time.time()
        r = self._step("nle:map_clips", {"expected": len(placed)})
        clips = nle.placed_clips()
        if len(clips) != len(placed):
            results.append(self._finish(
                r.fail("placed %d clips but sequence reports %d" % (len(placed), len(clips))), started))
            return results
        for entry, clip in zip(placed, clips):
            entry["clip"] = clip["clip"]
        results.append(self._finish(r.verify(clip_ids=[c["clip"] for c in placed]), started))

        # motion
        for entry in placed:
            scene = next(s for s in self.project["scenes"] if s["id"] == entry["id"])
            motion = (scene.get("motion") or {}).get("type", "none")
            if motion == "none":
                continue
            started = time.time()
            scale_from, scale_to = _scale_for(motion, scene)
            r = self._step("motion:%s" % entry["id"],
                           {"type": motion, "scale_from": scale_from, "scale_to": scale_to,
                            "start": entry["start"], "end": entry["start"] + entry["duration"]})
            try:
                nle.motion(entry["clip"], entry["start"], entry["start"] + entry["duration"],
                           scale_from, scale_to, canvas["width"], canvas["height"])
            except fc.FilmCraftError as exc:
                results.append(self._finish(r.fail(str(exc)), started))
                continue
            results.append(self._finish(r, started))

        # transitions — count must equal the spec, not merely exceed zero
        wanted = [t for t in self.project.get("transitions", []) if t["type"] == "cross_dissolve"]
        # A transition whose source scene never got placed cannot be applied.
        # Fail it explicitly rather than raising KeyError out of the runner.
        wanted = [t for t in wanted if t["between"][0] in self.scene_starts]
        for t in wanted:
            started = time.time()
            a, b = t["between"]
            at = self.scene_starts[a]["start"] + self.scene_starts[a]["duration"]
            target = next((p for p in placed if p["id"] == b), None)
            r = self._step("transition:%s->%s" % (a, b),
                           {"type": t["type"], "at": at, "frames": t.get("frames", 12)})
            if not target:
                results.append(self._finish(r.fail("target scene not placed"), started))
                continue
            try:
                nle.dissolve(target["clip"], at, t.get("frames", 12))
            except fc.FilmCraftError as exc:
                results.append(self._finish(r.fail(str(exc)), started))
                continue
            results.append(self._finish(r, started))

        if wanted:
            started = time.time()
            r = self._step("verify:transitions", {"expected": len(wanted)})
            got = nle.transitions_count()
            if got == len(wanted):
                results.append(self._finish(r.verify(count=got), started))
            else:
                results.append(self._finish(
                    r.fail("expected %d dissolves, sequence has %d — refusing to export"
                           % (len(wanted), got)), started))
        return results

    def render(self, out_name: str = "output.mp4") -> StepResult:
        started = time.time()
        out_path = os.path.join(self.workdir, out_name)
        r = self._step("render", {"path": out_path,
                                  "bitrateKbps": (self.project.get("render") or {}).get("bitrateKbps", 4000)})
        binary = find_binary("filmcraft")
        nle = fc.FilmCraft(binary, os.path.join(self.workdir, "film.fcproj"))
        nle.open()
        try:
            nle.export(out_path, (self.project.get("render") or {}).get("bitrateKbps", 4000))
        except fc.FilmCraftError as exc:
            return self._finish(r.fail(str(exc)), started)
        if not os.path.isfile(out_path):
            return self._finish(r.fail("export returned success but no file exists"), started)
        info = media.probe(out_path)
        self.manifest.record_artifact("render", out_path)
        return self._finish(r.verify(bytes=info.get("bytes"),
                                     duration=round(info.get("duration", 0), 2),
                                     sha256=sha256_file(out_path)), started)

    def verify_output(self, out_name: str = "output.mp4") -> List[StepResult]:
        results = []
        out_path = os.path.join(self.workdir, out_name)
        meta = self.project["project"]

        started = time.time()
        r = self._step("verify:container", {"path": out_path})
        info = media.probe(out_path)
        if not info.get("exists") or not info.get("decodable"):
            results.append(self._finish(r.fail("file missing or undecodable"), started))
            return results
        problems = []
        if not info.get("video"):
            problems.append("no video stream")
        if info["video"] and info["video"].get("codec_name") != "h264":
            problems.append("codec is %s, expected h264" % info["video"].get("codec_name"))
        if problems:
            results.append(self._finish(r.fail("; ".join(problems)), started))
        else:
            results.append(self._finish(r.verify(
                codec=info["video"]["codec_name"],
                width=info["video"].get("width"), height=info["video"].get("height"),
                duration=round(info["duration"], 2)), started))

        started = time.time()
        r = self._step("verify:decode", {"path": out_path})
        ok, err = media.decodes_cleanly(out_path)
        results.append(self._finish(r.verify(clean=True) if ok else r.fail("decode errors: %s" % err), started))

        # duration: sum of holds minus dissolve overlaps
        started = time.time()
        r = self._step("verify:duration", {"rule": "sum(durations) - dissolve overlaps"})
        total = sum(float(s["duration"]) for s in self.project["scenes"])
        fps = meta["fps"]
        overlap = sum(t.get("frames", 12) for t in self.project.get("transitions", [])
                      if t["type"] == "cross_dissolve") / float(fps)
        # Whether a dissolve OVERLAPS (shortening the timeline) or sits inside the
        # existing edit is a property of the NLE, not of the spec. Measured on
        # FilmCraft: a cross dissolve does NOT shorten the sequence — a 3x4s film
        # with two 16-frame dissolves renders 12.01 s, not 10.67 s. Accept either
        # model and record which one matched, rather than encoding a guess.
        candidates = {"sum": total, "sum_minus_overlap": total - overlap}
        actual = info["duration"]
        tol = max(0.5, 2.5 / fps * max(1, len(self.project.get("transitions", []))))
        matched = [k for k, v in candidates.items() if abs(actual - v) <= tol]
        if matched:
            results.append(self._finish(r.verify(actual=round(actual, 2),
                                                 model=matched[0],
                                                 expected=round(candidates[matched[0]], 2),
                                                 tolerance=round(tol, 2)), started))
        else:
            results.append(self._finish(r.fail("duration %.2fs matches neither %s"
                                               % (actual, {k: round(v, 2) for k, v in candidates.items()})), started))

        # motion — sample well inside each clip
        started = time.time()
        r = self._step("verify:motion", {"rule": "frame diff inside each moving clip"})
        moving = [s for s in self.project["scenes"]
                  if (s.get("motion") or {}).get("type", "none") != "none"]
        measured = {}
        for scene in moving:
            w = self.scene_starts.get(scene["id"])
            if not w:
                continue
            t0 = w["start"] + min(1.2, w["duration"] * 0.2)
            t1 = w["start"] + w["duration"] - min(1.2, w["duration"] * 0.2)
            diff = media.mean_abs_diff(out_path, t0, t1, self.workdir)
            measured[scene["id"]] = round(diff, 3) if diff is not None else None
        static = [k for k, v in measured.items() if v is not None and v < 0.3]
        if not moving:
            results.append(self._finish(StepResult(step=r.step, status=SKIPPED,
                                                   requested=r.requested), started))
        elif static:
            results.append(self._finish(r.fail("static clips: %s (measured %s)" % (static, measured)), started))
        else:
            results.append(self._finish(r.verify(frame_diff=measured), started))

        # empty-shot check — at least one of three samples must carry structure
        started = time.time()
        r = self._step("verify:content", {"rule": ">=1 of 3 samples has luma std > 3"})
        per_scene = {}
        empty = []
        for scene in self.project["scenes"]:
            w = self.scene_starts.get(scene["id"])
            if not w:
                continue
            stds = []
            for frac in (0.25, 0.5, 0.75):
                s = media.structure(out_path, w["start"] + w["duration"] * frac, self.workdir)
                if s:
                    stds.append(round(s["std"], 1))
            per_scene[scene["id"]] = stds
            if stds and max(stds) <= 3.0:
                empty.append(scene["id"])
        if empty:
            results.append(self._finish(r.fail("empty shots: %s" % empty), started))
        else:
            results.append(self._finish(r.verify(luma_std=per_scene), started))
        return results

    # -- driver -----------------------------------------------------------
    def run(self, dry_run: bool = False, resume: bool = True) -> Dict[str, Any]:
        errors = schema.validate(self.project, base_dir=self.base)
        if errors:
            self.manifest.add(StepResult(step="validate", status=FAILED,
                                         error="; ".join(errors)))
            return self.manifest.data

        self.manifest.add(StepResult(step="validate", status=VERIFIED,
                                     verified={"scenes": len(self.project["scenes"]),
                                               "assets": len(self.project["assets"])}))
        caps = self.check_capabilities()
        if caps.status == FAILED:
            return self.manifest.data
        if dry_run:
            self.log("dry run: validation and capabilities only")
            self.manifest.data["summary"] = self.manifest.summary()
            return self.manifest.data

        gen = self.generate_assets(resume=resume)
        if any(s.status == FAILED for s in gen):
            self.manifest.data["summary"] = self.manifest.summary()
            return self.manifest.data

        assembled = self.assemble()
        if any(s.status == FAILED for s in assembled):
            self.manifest.data["summary"] = self.manifest.summary()
            return self.manifest.data

        rendered = self.render()
        if rendered.status != FAILED:
            self.verify_output()

        self.manifest.data["summary"] = self.manifest.summary()
        return self.manifest.data


def _scale_for(motion: str, scene: Dict[str, Any]):
    m = scene.get("motion") or {}
    lo = float(m.get("from", 100.0))
    hi = float(m.get("to", 108.0))
    if motion == "pull_out":
        return hi, lo
    return lo, hi
