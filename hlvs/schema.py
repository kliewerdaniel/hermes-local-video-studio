"""Project-specification validation.

Zero dependencies on purpose: the validator must run on a clean machine before
anything else is installed, so it uses only the standard library. A JSON Schema
copy lives in ``schemas/project.schema.json`` for editors and other tooling; this
module is the authority the runner actually consults.

Validation is deliberately strict and front-loaded. A malformed spec, an
unsupported operation, or a dimension the image model cannot produce is rejected
*before* an expensive generation starts.
"""
from __future__ import annotations

import json
import os
from typing import Any, Dict, List

SCHEMA_VERSION = "1.0"

# Qwen-Image-2.1 refuses dimensions that are not positive multiples of 32.
DIMENSION_MULTIPLE = 32

ALLOWED_MODES = {"t2i", "edit", "img2img", "inpaint"}
ALLOWED_MOTIONS = {"none", "push_in", "pull_out", "pan_left", "pan_right"}
ALLOWED_TRANSITIONS = {"cross_dissolve", "hard_cut"}
ALLOWED_FORMATS = {"h264"}
ALLOWED_ASSET_SOURCES = {"generate", "file"}


class ValidationError(Exception):
    """Raised when a project cannot be executed as written."""


def _err(errors: List[str], msg: str) -> None:
    errors.append(msg)


def validate(project: Dict[str, Any], base_dir: str = ".") -> List[str]:
    """Return a list of problems. Empty list means the project may run."""
    errors: List[str] = []

    if not isinstance(project, dict):
        return ["project root must be a JSON object"]

    if project.get("schema_version") != SCHEMA_VERSION:
        _err(errors, f"schema_version must be {SCHEMA_VERSION!r}, got {project.get('schema_version')!r}")

    meta = project.get("project") or {}
    if not isinstance(meta, dict):
        _err(errors, "project must be an object")
        meta = {}

    if not str(meta.get("name") or "").strip():
        _err(errors, "project.name is required")

    canvas = meta.get("canvas") or {}
    for axis in ("width", "height"):
        v = canvas.get(axis)
        if not isinstance(v, int) or v <= 0:
            _err(errors, f"project.canvas.{axis} must be a positive integer")
        elif v % DIMENSION_MULTIPLE:
            _err(errors, f"project.canvas.{axis}={v} is not a multiple of {DIMENSION_MULTIPLE}; "
                         f"Qwen-Image rejects it")

    fps = meta.get("fps")
    if not isinstance(fps, int) or fps <= 0:
        _err(errors, "project.fps must be a positive integer")

    assets = project.get("assets") or []
    if not isinstance(assets, list) or not assets:
        _err(errors, "assets must be a non-empty list")
        assets = []

    asset_ids = set()
    for i, a in enumerate(assets):
        if not isinstance(a, dict):
            _err(errors, f"assets[{i}] must be an object")
            continue
        aid = a.get("id")
        if not aid:
            _err(errors, f"assets[{i}].id is required")
            continue
        if aid in asset_ids:
            _err(errors, f"duplicate asset id {aid!r}")
        asset_ids.add(aid)

        src = a.get("source") or {}
        kind = src.get("kind")
        if kind not in ALLOWED_ASSET_SOURCES:
            _err(errors, f"asset {aid!r}: source.kind must be one of {sorted(ALLOWED_ASSET_SOURCES)}")
            continue
        if kind == "generate":
            if not str(src.get("prompt") or "").strip():
                _err(errors, f"asset {aid!r}: source.prompt is required for kind=generate")
            if src.get("mode", "t2i") not in ALLOWED_MODES:
                _err(errors, f"asset {aid!r}: unsupported mode {src.get('mode')!r}")
        elif kind == "file":
            p = src.get("path")
            if not p:
                _err(errors, f"asset {aid!r}: source.path is required for kind=file")
            elif not os.path.exists(p if os.path.isabs(p) else os.path.join(base_dir, p)):
                _err(errors, f"asset {aid!r}: file not found: {p}")

    scenes = project.get("scenes") or []
    if not isinstance(scenes, list) or not scenes:
        _err(errors, "scenes must be a non-empty list")
        scenes = []

    seen = set()
    for i, s in enumerate(scenes):
        if not isinstance(s, dict):
            _err(errors, f"scenes[{i}] must be an object")
            continue
        sid = s.get("id")
        if not sid:
            _err(errors, f"scenes[{i}].id is required")
            continue
        if sid in seen:
            _err(errors, f"duplicate scene id {sid!r}")
        seen.add(sid)

        ref = s.get("asset")
        if ref not in asset_ids:
            _err(errors, f"scene {sid!r}: asset {ref!r} is not declared")

        dur = s.get("duration")
        if not isinstance(dur, (int, float)) or dur <= 0:
            _err(errors, f"scene {sid!r}: duration must be > 0")

        motion = (s.get("motion") or {}).get("type", "none")
        if motion not in ALLOWED_MOTIONS:
            _err(errors, f"scene {sid!r}: unsupported motion {motion!r}; "
                         f"allowed {sorted(ALLOWED_MOTIONS)}")

    # transitions must join scenes that actually sit next to each other
    order = [s.get("id") for s in scenes if isinstance(s, dict)]
    for i, t in enumerate(project.get("transitions") or []):
        if not isinstance(t, dict):
            _err(errors, f"transitions[{i}] must be an object")
            continue
        a, b = t.get("between") or [None, None]
        if a not in order or b not in order:
            _err(errors, f"transitions[{i}]: between references unknown scenes {a!r},{b!r}")
            continue
        if order.index(b) != order.index(a) + 1:
            _err(errors, f"transitions[{i}]: {a!r} and {b!r} are not adjacent")
        if t.get("type") not in ALLOWED_TRANSITIONS:
            _err(errors, f"transitions[{i}]: unsupported type {t.get('type')!r}")
        frames = t.get("frames", 12)
        if not isinstance(frames, int) or frames < 0:
            _err(errors, f"transitions[{i}]: frames must be a non-negative integer")

    render = project.get("render") or {}
    if render.get("format", "h264") not in ALLOWED_FORMATS:
        _err(errors, f"render.format must be one of {sorted(ALLOWED_FORMATS)}")

    return errors


def load(path: str) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)


def load_validated(path: str) -> Dict[str, Any]:
    project = load(path)
    errors = validate(project, base_dir=os.path.dirname(os.path.abspath(path)))
    if errors:
        raise ValidationError("project is not executable:\n  - " + "\n  - ".join(errors))
    return project
