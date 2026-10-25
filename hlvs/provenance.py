"""Provenance manifests and content hashes.

Every step writes what it *requested* and what it *verified*. The distinction is
the whole point: a manifest that only records requests is a log of intentions.
"""
from __future__ import annotations

import hashlib
import json
import os
import time
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional

VERIFIED = "verified"
REQUESTED_ONLY = "requested_only"
FAILED = "failed"
SKIPPED = "skipped"


def sha256_file(path: str, chunk: int = 1 << 20) -> Optional[str]:
    if not os.path.isfile(path):
        return None
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for block in iter(lambda: fh.read(chunk), b""):
            h.update(block)
    return h.hexdigest()


@dataclass
class StepResult:
    """One unit of work, with request and evidence kept apart."""

    step: str
    status: str = REQUESTED_ONLY
    requested: Dict[str, Any] = field(default_factory=dict)
    verified: Dict[str, Any] = field(default_factory=dict)
    evidence: List[str] = field(default_factory=list)
    error: Optional[str] = None
    seconds: float = 0.0

    def verify(self, **measured: Any) -> "StepResult":
        """Mark verified, but only if the caller supplied a measurement."""
        if not measured:
            raise ValueError("verify() requires measured evidence; "
                             "a step with no measurement stays requested_only")
        self.verified.update(measured)
        self.status = VERIFIED
        return self

    def fail(self, error: str) -> "StepResult":
        self.status = FAILED
        self.error = error
        return self

    def as_dict(self) -> Dict[str, Any]:
        return asdict(self)


class Manifest:
    def __init__(self, project_name: str, root: str):
        self.root = root
        self.data: Dict[str, Any] = {
            "project": project_name,
            "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "root": root,
            "steps": [],
        }

    def add(self, result: StepResult) -> StepResult:
        self.data["steps"].append(result.as_dict())
        return result

    def record_artifact(self, name: str, path: str) -> Dict[str, Any]:
        entry = {"name": name, "path": path, "bytes": None, "sha256": None}
        if os.path.isfile(path):
            entry["bytes"] = os.path.getsize(path)
            entry["sha256"] = sha256_file(path)
        self.data.setdefault("artifacts", []).append(entry)
        return entry

    def summary(self) -> Dict[str, int]:
        counts = {VERIFIED: 0, REQUESTED_ONLY: 0, FAILED: 0, SKIPPED: 0}
        for s in self.data["steps"]:
            counts[s["status"]] = counts.get(s["status"], 0) + 1
        return counts

    def save(self, path: Optional[str] = None) -> str:
        path = path or os.path.join(self.root, "manifest.json")
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
        self.data["summary"] = self.summary()
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(self.data, fh, indent=2)
        return path
