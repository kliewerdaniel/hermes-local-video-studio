"""Qwen-Image-2.1-Turbo adapter (qwen-image-studio, MLX, Apple Silicon).

Talks to the local studio's HTTP API. Standard library only.

Facts encoded here, all discovered the hard way and documented in the skill:
  * the upload field is `images`, not `images[]`
  * `edit`/`inpaint` require at least one upload; the first is the edit source
  * dimensions must be positive multiples of 32
  * outputs land in the studio's own `outputs/` dir — always read `result.path`
  * generation is serialised; one job at a time
"""
from __future__ import annotations

import json
import mimetypes
import os
import time
import urllib.error
import urllib.request
import uuid
from typing import Any, Dict, List, Optional

BASE = "http://127.0.0.1:8787"


class QwenError(RuntimeError):
    pass


def _encode_multipart(fields: Dict[str, Any], files: List[str]) -> (bytes, str):
    boundary = "----hlvs" + uuid.uuid4().hex
    out = bytearray()
    for key, value in fields.items():
        if value is None:
            continue
        out += ("--%s\r\nContent-Disposition: form-data; name=\"%s\"\r\n\r\n%s\r\n"
                % (boundary, key, value)).encode("utf-8")
    for path in files:
        name = os.path.basename(path)
        ctype = mimetypes.guess_type(name)[0] or "application/octet-stream"
        out += ("--%s\r\nContent-Disposition: form-data; name=\"images\"; filename=\"%s\"\r\n"
                "Content-Type: %s\r\n\r\n" % (boundary, name, ctype)).encode("utf-8")
        with open(path, "rb") as fh:
            out += fh.read()
        out += b"\r\n"
    out += ("--%s--\r\n" % boundary).encode("utf-8")
    return bytes(out), "multipart/form-data; boundary=%s" % boundary


class QwenAdapter:
    def __init__(self, base: str = BASE, timeout: int = 1800):
        self.base = base.rstrip("/")
        self.timeout = timeout

    def status(self) -> Dict[str, Any]:
        try:
            with urllib.request.urlopen(self.base + "/api/status", timeout=5) as r:
                return json.loads(r.read().decode("utf-8"))
        except Exception as exc:                       # noqa: BLE001
            raise QwenError("studio not reachable at %s: %s" % (self.base, exc))

    def generate(self, prompt: str, mode: str = "t2i", width: int = 1024,
                 height: int = 576, seed: Optional[int] = None,
                 images: Optional[List[str]] = None, steps: int = 8,
                 guidance: Optional[float] = None,
                 poll_seconds: float = 3.0) -> Dict[str, Any]:
        if width % 32 or height % 32:
            raise QwenError("dimensions must be multiples of 32 (got %dx%d)" % (width, height))
        if mode in ("edit", "img2img", "inpaint") and not images:
            raise QwenError("mode=%s requires at least one reference image" % mode)

        fields: Dict[str, Any] = {"mode": mode, "prompt": prompt, "steps": steps,
                                  "width": width, "height": height}
        if seed is not None:
            fields["seed"] = seed
        if guidance is not None:
            fields["guidance"] = guidance

        body, ctype = _encode_multipart(fields, images or [])
        req = urllib.request.Request(self.base + "/api/generate", data=body,
                                     headers={"Content-Type": ctype}, method="POST")
        started = time.time()
        try:
            with urllib.request.urlopen(req, timeout=120) as r:
                job = json.loads(r.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            raise QwenError("submit failed: %s %s" % (exc.code, exc.read()[:400]))
        job_id = job.get("job_id")
        if not job_id:
            raise QwenError("no job_id in response: %r" % job)

        while time.time() - started < self.timeout:
            time.sleep(poll_seconds)
            with urllib.request.urlopen("%s/api/jobs/%s" % (self.base, job_id), timeout=30) as r:
                st = json.loads(r.read().decode("utf-8"))
            state = st.get("state")
            if state == "done":
                path = (st.get("result") or {}).get("path")
                if not path or not os.path.isfile(path):
                    raise QwenError("job %s reported done but %r is not a file" % (job_id, path))
                return {"job_id": job_id, "path": path, "seconds": round(time.time() - started, 1),
                        "mode": mode, "seed": seed, "width": width, "height": height}
            if state == "error":
                raise QwenError("job %s failed: %s" % (job_id, st.get("error")))
        raise QwenError("job %s timed out after %ss" % (job_id, self.timeout))
