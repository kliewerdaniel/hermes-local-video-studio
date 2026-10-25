"""Integration tests against the real ffmpeg/ffprobe on this machine."""
import os
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from hlvs.adapters import media

HAVE_FFMPEG = subprocess.run(["which", "ffmpeg"], capture_output=True).returncode == 0
HAVE_NUMPY = True
try:
    import numpy  # noqa: F401
    import PIL     # noqa: F401
except Exception:  # noqa: BLE001
    HAVE_NUMPY = False


@unittest.skipUnless(HAVE_FFMPEG, "ffmpeg not installed")
class TestMedia(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp()
        cls.clip = os.path.join(cls.tmp, "clip.mp4")
        # a real moving clip: testsrc2 animates, so motion is measurable
        subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "lavfi",
                        "-i", "testsrc2=size=320x180:rate=24:duration=3",
                        "-pix_fmt", "yuv420p", cls.clip], check=True)

    def test_probe_reads_streams(self):
        info = media.probe(self.clip)
        self.assertTrue(info["exists"])
        self.assertTrue(info["decodable"])
        self.assertEqual(info["video"]["codec_name"], "h264")
        self.assertAlmostEqual(info["duration"], 3.0, delta=0.2)

    def test_probe_missing_file(self):
        self.assertFalse(media.probe("/nope.mp4")["exists"])

    def test_clean_decode(self):
        ok, err = media.decodes_cleanly(self.clip)
        self.assertTrue(ok, err)

    @unittest.skipUnless(HAVE_NUMPY, "numpy/pillow not installed")
    def test_motion_is_measured(self):
        diff = media.mean_abs_diff(self.clip, 0.5, 2.5, self.tmp)
        self.assertIsNotNone(diff)
        self.assertGreater(diff, 0.3, "testsrc2 should animate")

    @unittest.skipUnless(HAVE_NUMPY, "numpy/pillow not installed")
    def test_structure_of_flat_frame(self):
        flat = os.path.join(self.tmp, "flat.mp4")
        subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "lavfi",
                        "-i", "color=c=black:size=320x180:rate=24:duration=1",
                        "-pix_fmt", "yuv420p", flat], check=True)
        s = media.structure(flat, 0.4, self.tmp)
        self.assertLess(s["std"], 3.0)


if __name__ == "__main__":
    unittest.main()
