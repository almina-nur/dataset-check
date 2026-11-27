import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent
EXAMPLES = ROOT / "examples"


def run_check(dataset, schema=EXAMPLES / "schema.json"):
    return subprocess.run(
        [sys.executable, str(ROOT / "dataset_check.py"), str(dataset), "--schema", str(schema)],
        capture_output=True,
        text=True,
        check=False,
    )


class DatasetCheckTests(unittest.TestCase):
    def test_valid_dataset(self):
        result = run_check(EXAMPLES / "orders_valid.csv")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout), {
            "status": "pass", "rows_checked": 3, "issue_counts": {}, "issues": [],
        })

    def test_invalid_dataset(self):
        result = run_check(EXAMPLES / "orders_invalid.csv")
        self.assertEqual(result.returncode, 1, result.stderr)
        report = json.loads(result.stdout)
        self.assertEqual(report["rows_checked"], 5)
        self.assertEqual(report["issue_counts"], {
            "duplicate": 1, "missing": 1, "invalid_type": 2,
            "unknown_category": 1, "wrong_field_count": 1,
        })
        self.assertIn({"row": 4, "column": "unit_price", "issue": "invalid_type"}, report["issues"])

    def test_header_only_dataset(self):
        with tempfile.TemporaryDirectory() as directory:
            dataset = Path(directory) / "empty.csv"
            dataset.write_text("order_id,quantity,unit_price,channel\n", encoding="utf-8")
            result = run_check(dataset)
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertEqual(json.loads(result.stdout)["issue_counts"], {"empty_dataset": 1})

    def test_header_mismatch(self):
        with tempfile.TemporaryDirectory() as directory:
            dataset = Path(directory) / "mismatched.csv"
            dataset.write_text("order_id,order_id\n101,102\n", encoding="utf-8")
            result = run_check(dataset)
        self.assertEqual(result.returncode, 2)
        self.assertIn("Duplicate: ['order_id']", result.stderr)
        self.assertEqual(result.stdout, "")

    def test_invalid_schema(self):
        with tempfile.TemporaryDirectory() as directory:
            schema = Path(directory) / "bad.json"
            schema.write_text('{"order_id": {"type": "integer", "unique": "false"}}', encoding="utf-8")
            result = run_check(EXAMPLES / "orders_valid.csv", schema)
        self.assertEqual(result.returncode, 2)
        self.assertIn("unique must be true or false", result.stderr)

    def test_duplicate_schema_keys(self):
        cases = {
            "order_id": '{"order_id": {"type": "integer"}, "order_id": {"type": "text"}}',
            "unique": '{"order_id": {"type": "integer", "unique": true, "unique": false}}',
        }
        with tempfile.TemporaryDirectory() as directory:
            schema = Path(directory) / "duplicate.json"
            for key, contents in cases.items():
                with self.subTest(key=key):
                    schema.write_text(contents, encoding="utf-8")
                    result = run_check(EXAMPLES / "orders_valid.csv", schema)
                    self.assertEqual(result.returncode, 2)
                    self.assertIn(f"Duplicate schema key: {key!r}", result.stderr)
                    self.assertEqual(result.stdout, "")


if __name__ == "__main__":
    unittest.main()
