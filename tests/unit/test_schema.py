import json
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from hlvs import schema

HERE = os.path.dirname(os.path.abspath(__file__))
EXAMPLE = os.path.join(HERE, "..", "..", "examples", "minimal-project", "project.json")


def base():
    return {
        "schema_version": "1.0",
        "project": {"name": "t", "canvas": {"width": 1024, "height": 576}, "fps": 24},
        "assets": [{"id": "a", "source": {"kind": "generate", "prompt": "x"}}],
        "scenes": [{"id": "s1", "asset": "a", "duration": 3.0}],
    }


class TestSchema(unittest.TestCase):
    def test_example_is_valid(self):
        p = schema.load(EXAMPLE)
        self.assertEqual(schema.validate(p, os.path.dirname(EXAMPLE)), [])

    def test_baseline_valid(self):
        self.assertEqual(schema.validate(base()), [])

    def test_rejects_non_multiple_of_32(self):
        p = base()
        p["project"]["canvas"]["height"] = 720          # exact 16:9, but 720 % 32 == 16
        errors = schema.validate(p)
        self.assertTrue(any("multiple of 32" in e for e in errors), errors)

    def test_rejects_unknown_motion(self):
        p = base()
        p["scenes"][0]["motion"] = {"type": "orbit"}
        self.assertTrue(any("unsupported motion" in e for e in schema.validate(p)))

    def test_rejects_unknown_asset_reference(self):
        p = base()
        p["scenes"][0]["asset"] = "nope"
        self.assertTrue(any("not declared" in e for e in schema.validate(p)))

    def test_rejects_non_adjacent_transition(self):
        p = base()
        p["assets"].append({"id": "b", "source": {"kind": "generate", "prompt": "y"}})
        p["scenes"].append({"id": "s2", "asset": "b", "duration": 3.0})
        p["scenes"].append({"id": "s3", "asset": "b", "duration": 3.0})
        p["transitions"] = [{"between": ["s1", "s3"], "type": "cross_dissolve"}]
        self.assertTrue(any("not adjacent" in e for e in schema.validate(p)))

    def test_rejects_duplicate_ids(self):
        p = base()
        p["assets"].append({"id": "a", "source": {"kind": "generate", "prompt": "y"}})
        self.assertTrue(any("duplicate asset id" in e for e in schema.validate(p)))

    def test_rejects_missing_prompt(self):
        p = base()
        p["assets"][0]["source"]["prompt"] = "  "
        self.assertTrue(any("prompt is required" in e for e in schema.validate(p)))

    def test_load_validated_raises(self):
        p = base()
        p["project"]["fps"] = 0
        tmp = os.path.join(HERE, "_bad.json")
        with open(tmp, "w") as fh:
            json.dump(p, fh)
        try:
            with self.assertRaises(schema.ValidationError):
                schema.load_validated(tmp)
        finally:
            os.remove(tmp)


if __name__ == "__main__":
    unittest.main()
