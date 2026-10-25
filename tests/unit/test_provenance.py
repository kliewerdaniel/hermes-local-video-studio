import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from hlvs.provenance import (FAILED, REQUESTED_ONLY, VERIFIED, Manifest,
                             StepResult, sha256_file)


class TestProvenance(unittest.TestCase):
    def test_step_defaults_to_requested_only(self):
        s = StepResult(step="x", requested={"a": 1})
        self.assertEqual(s.status, REQUESTED_ONLY)

    def test_verify_requires_measurement(self):
        s = StepResult(step="x")
        with self.assertRaises(ValueError):
            s.verify()

    def test_verify_sets_status_and_evidence(self):
        s = StepResult(step="x").verify(peak=0.82)
        self.assertEqual(s.status, VERIFIED)
        self.assertEqual(s.verified["peak"], 0.82)

    def test_fail(self):
        s = StepResult(step="x").fail("boom")
        self.assertEqual(s.status, FAILED)
        self.assertEqual(s.error, "boom")

    def test_hash_is_stable_and_changes_with_content(self):
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "f.bin")
            with open(p, "wb") as fh:
                fh.write(b"hello")
            h1 = sha256_file(p)
            h2 = sha256_file(p)
            self.assertEqual(h1, h2)
            with open(p, "wb") as fh:
                fh.write(b"hello!")
            self.assertNotEqual(h1, sha256_file(p))

    def test_hash_of_missing_file_is_none(self):
        self.assertIsNone(sha256_file("/nonexistent/nope"))

    def test_manifest_summary_counts_statuses(self):
        with tempfile.TemporaryDirectory() as d:
            m = Manifest("p", d)
            m.add(StepResult(step="a").verify(x=1))
            m.add(StepResult(step="b"))
            m.add(StepResult(step="c").fail("e"))
            counts = m.summary()
            self.assertEqual(counts[VERIFIED], 1)
            self.assertEqual(counts[REQUESTED_ONLY], 1)
            self.assertEqual(counts[FAILED], 1)
            path = m.save()
            with open(path) as fh:
                data = json.load(fh)
            self.assertEqual(len(data["steps"]), 3)
            self.assertIn("summary", data)


if __name__ == "__main__":
    unittest.main()
