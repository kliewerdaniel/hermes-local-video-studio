"""Regression tests for the CLI output parser.

The bug these lock down: `import` prints pretty-printed JSON, and the first
implementation scanned line-by-line for a line starting with `{`. It found `}`
instead, returned {}, and the run reported "placed 3 clips but sequence reports
0" — a silent, plausible-looking failure. A second implementation scanned
last-brace to last-brace and returned a NESTED object, which made `inspect
sequence` look like an empty timeline.
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from hlvs.adapters.filmcraft import FilmCraft, seconds_to_ticks


class TestLastJson(unittest.TestCase):
    def test_pretty_printed_import_result(self):
        out = '{\n  "items": [\n    1\n  ]\n}\n'
        self.assertEqual(FilmCraft._last_json(out), {"items": [1]})

    def test_pretty_printed_sequence_with_nested_objects(self):
        out = ('{\n  "audio": [{"id": 4, "items": []}],\n'
               '  "video": [{"id": 1, "items": [{"clip": 9}]}]\n}\n')
        parsed = FilmCraft._last_json(out)
        self.assertEqual(parsed["video"][0]["items"][0]["clip"], 9)

    def test_nested_document_is_not_truncated(self):
        out = '{"a": {"b": 1}}'
        self.assertEqual(FilmCraft._last_json(out), {"a": {"b": 1}})

    def test_no_json_returns_empty(self):
        self.assertEqual(FilmCraft._last_json("nothing here"), {})

    def test_ticks_conversion(self):
        self.assertEqual(seconds_to_ticks(1.0), 254_016_000_000)
        self.assertEqual(seconds_to_ticks(0.0), 0)


if __name__ == "__main__":
    unittest.main()
