"""Media inspection — the only module allowed to say something is verified.

Every function here measures a file on disk. Nothing trusts a renderer's own
report.
"""
from __future__ import annotations

import json
import os
import subprocess
from typing import Any, Dict, Optional, Tuple


def _run(cmd, timeout: int = 300) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)


def probe(path: str) -> Dict[str, Any]:
    if not os.path.isfile(path):
        return {"exists": False, "path": path}
    r = _run(["ffprobe", "-v", "error", "-show_format", "-show_streams", "-of", "json", path])
    if r.returncode != 0:
        return {"exists": True, "decodable": False, "error": r.stderr[:400]}
    data = json.loads(r.stdout)
    streams = data.get("streams", [])
    return {
        "exists": True,
        "decodable": True,
        "duration": float(data.get("format", {}).get("duration") or 0.0),
        "bytes": int(data.get("format", {}).get("size") or 0),
        "video": next((s for s in streams if s.get("codec_type") == "video"), None),
        "audio": next((s for s in streams if s.get("codec_type") == "audio"), None),
        "stream_count": len(streams),
    }


def decodes_cleanly(path: str) -> Tuple[bool, str]:
    r = _run(["ffmpeg", "-v", "error", "-i", path, "-f", "null", "-"])
    return (r.returncode == 0 and not r.stderr.strip(), r.stderr.strip()[:400])


def frame_at(path: str, seconds: float, out_png: str) -> Optional[str]:
    r = _run(["ffmpeg", "-y", "-v", "error", "-ss", "%.3f" % seconds, "-i", path,
              "-frames:v", "1", out_png])
    return out_png if r.returncode == 0 and os.path.isfile(out_png) else None


def _gray(path: str) -> Any:
    import numpy as np
    from PIL import Image
    return np.asarray(Image.open(path).convert("L"), dtype=float)


def mean_abs_diff(path: str, t0: float, t1: float, tmpdir: str) -> Optional[float]:
    """Frame difference between two times — the motion measurement.

    Sample well inside the clip: a window overlapping a transition measures the
    transition, not the animation.
    """
    import numpy as np
    a_p = frame_at(path, t0, os.path.join(tmpdir, "_m0.png"))
    b_p = frame_at(path, t1, os.path.join(tmpdir, "_m1.png"))
    if not a_p or not b_p:
        return None
    return float(np.abs(_gray(a_p) - _gray(b_p)).mean())


def structure(path: str, t: float, tmpdir: str) -> Optional[Dict[str, float]]:
    """Luma mean and std of a frame — catches empty shots and flat regions."""
    import numpy as np
    p = frame_at(path, t, os.path.join(tmpdir, "_s.png"))
    if not p:
        return None
    g = _gray(p)
    return {"mean": float(g.mean()), "std": float(g.std())}


def loudness(path: str) -> Optional[Dict[str, float]]:
    """Integrated loudness and true peak of the first audio stream."""
    r = _run(["ffmpeg", "-hide_banner", "-i", path, "-af",
              "loudnorm=print_format=json", "-f", "null", "-"])
    txt = r.stderr
    start = txt.rfind("{")
    end = txt.rfind("}")
    if start == -1 or end == -1:
        return None
    try:
        data = json.loads(txt[start:end + 1])
    except json.JSONDecodeError:
        return None
    return {"input_i": float(data.get("input_i", 0)),
            "input_tp": float(data.get("input_tp", 0)),
            "input_lra": float(data.get("input_lra", 0))}


def decoded_peak(path: str) -> Optional[float]:
    """Peak of the decoded samples. > 1.0 means the delivered file clips."""
    import numpy as np
    r = subprocess.run(["ffmpeg", "-v", "error", "-i", path, "-ac", "1",
                        "-f", "f32le", "-"], capture_output=True)
    if not r.stdout:
        return None
    a = np.frombuffer(r.stdout, dtype=np.float32)
    return float(abs(a).max()) if a.size else None
