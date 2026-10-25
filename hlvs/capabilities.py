"""Environment discovery — the `doctor` report.

Read-only. Never installs, never writes outside the repo, never prints secrets.
Each entry says whether a capability was FOUND, and separately whether it was
PROBED (i.e. actually answered a request). A binary on disk that cannot run is
not a capability.
"""
from __future__ import annotations

import json
import os
import platform
import shutil
import subprocess
from typing import Any, Dict, List, Optional

RUST_APPS = ["effectcraft", "filmcraft", "lightcraft", "photocraft",
             "vectorcraft", "designcraft", "pdfcraft"]

QWEN_STATUS = "http://127.0.0.1:8787/api/status"


def _run(cmd: List[str], timeout: int = 15) -> str:
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return (r.stdout or r.stderr).strip()
    except Exception as exc:            # noqa: BLE001 - discovery must not raise
        return "ERROR %s" % exc


def _first_line(cmd: List[str]) -> str:
    return (_run(cmd).splitlines() or [""])[0]


def find_binary(app: str) -> Optional[str]:
    """Prefer a release build, fall back to debug, then PATH."""
    for profile in ("release", "debug"):
        p = os.path.expanduser("~/Projects/%s/target/%s/%s-cli" % (app, profile, app))
        if os.path.isfile(p) and os.access(p, os.X_OK):
            return p
    return shutil.which("%s-cli" % app)


def probe_binary(path: str) -> Dict[str, Any]:
    """A binary that cannot list its commands is not usable."""
    out = _run([path, "commands"], timeout=25)
    ok = bool(out) and "ERROR" not in out[:10]
    return {"runs": ok, "command_catalogue_chars": len(out)}


def probe_qwen() -> Dict[str, Any]:
    try:
        import urllib.request
        with urllib.request.urlopen(QWEN_STATUS, timeout=3) as r:
            body = json.loads(r.read().decode("utf-8"))
        return {"reachable": True, "status": body}
    except Exception as exc:            # noqa: BLE001
        return {"reachable": False, "error": str(exc)}


def discover(probe: bool = True) -> Dict[str, Any]:
    import sys

    info: Dict[str, Any] = {
        "os": "%s %s" % (platform.system(), platform.release()),
        "os_version": _run(["sw_vers", "-productVersion"]) if platform.system() == "Darwin" else "",
        "arch": platform.machine(),
        "cpu": _run(["sysctl", "-n", "machdep.cpu.brand_string"]) if platform.system() == "Darwin" else platform.processor(),
        "cpu_cores": os.cpu_count(),
        "python": platform.python_version(),
        "python_executable": sys.executable,
        "ffmpeg": _first_line(["ffmpeg", "-version"]),
        "ffprobe": _first_line(["ffprobe", "-version"]),
        "text_filters": has_text_filters(),
        "rust_apps": {},
        "qwen": {},
    }

    for app in RUST_APPS:
        path = find_binary(app)
        entry: Dict[str, Any] = {"path": path, "found": bool(path)}
        if path and probe:
            entry.update(probe_binary(path))
        info["rust_apps"][app] = entry

    info["qwen"] = probe_qwen() if probe else {"probed": False}
    return info


def has_text_filters() -> bool:
    """Whether this ffmpeg can draw text at all.

    Worth checking before planning subtitles: many builds ship without libass,
    and a filter chain naming `subtitles` then fails outright.
    """
    out = _run(["ffmpeg", "-hide_banner", "-filters"])
    names = set()
    for line in out.splitlines():
        parts = line.split()
        if len(parts) >= 2 and not line.startswith("Filters:"):
            names.add(parts[1])
    return bool({"subtitles", "ass", "drawtext"} & names)


def summarise(info: Dict[str, Any]) -> str:
    lines = []
    lines.append("host      : %s (%s) %s x%d" % (info["os"], info["arch"], info["cpu"], info["cpu_cores"] or 0))
    lines.append("python    : %s" % info["python"])
    lines.append("ffmpeg    : %s" % (info["ffmpeg"][:60] or "NOT FOUND"))
    lines.append("text filt : %s" % ("yes" if info["text_filters"] else "no — burn captions via title graphics, not drawtext"))
    for app, e in info["rust_apps"].items():
        state = "ok" if e.get("runs") else ("found, not probed" if e["found"] else "missing")
        lines.append("%-10s: %-22s %s" % (app, state, e.get("path") or ""))
    q = info["qwen"]
    if q.get("reachable"):
        lines.append("qwen      : reachable on :8787")
    elif not q.get("probed", True):
        lines.append("qwen      : not probed")
    else:
        lines.append("qwen      : not running (%s)" % str(q.get("error"))[:50])
    return "\n".join(lines)
