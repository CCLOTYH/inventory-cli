"""Contract checks using isolated subprocesses and injected filesystem failures."""
import contextlib
import copy
import importlib.util
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

SCRIPT = Path(__file__).resolve().parents[1] / "products.py"
spec = importlib.util.spec_from_file_location("products", SCRIPT)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class InventoryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.cwd = Path(self.temp.name)
        self.path = self.cwd / "products.json"

    def run_cli(self, *args, code=0):
        before = self.path.read_bytes() if self.path.exists() else None
        result = subprocess.run([sys.executable, str(SCRIPT), *args], cwd=self.cwd,
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, code, result.stderr)
        self.assertNotIn("Traceback", result.stderr)
        if code:
            self.assertEqual(result.stdout, "")
            self.assertTrue(result.stderr)
            self.assertEqual(self.path.read_bytes() if self.path.exists() else None, before)
        return result

    def add(self, name="Notebook", price="4.5", quantity="10"):
        return json.loads(self.run_cli("add", "--name", name, "--price", price, "--quantity", quantity).stdout)

    def fixture(self):
        return {"next_id": 4, "products": [
            {"id": 3, "name": "Pen", "price": "1.00", "quantity": 5},
            {"id": 1, "name": "Book", "price": "0.00", "quantity": 0}]}

    def write(self, store):
        self.path.write_text(json.dumps(store), encoding="utf-8")

    def test_help(self):
        for args in [("--help",)] + [(c, "--help") for c in ("add", "list", "get", "update", "delete", "low-stock")]:
            self.assertIn("usage:", self.run_cli(*args).stdout)
            self.assertFalse(self.path.exists())
        self.write(self.fixture())
        before = self.path.read_bytes(), self.path.stat().st_mtime_ns
        self.run_cli("update", "--help")
        self.assertEqual((self.path.read_bytes(), self.path.stat().st_mtime_ns), before)

    def test_bad_syntax(self):
        for args in [(), ("wat",), ("list", "--wat"), ("list", "extra"), ("add",), ("get",),
                     ("delete", "1"), ("update", "1"), ("low-stock",), ("list", "--file", "x"),
                     ("add", "--na", "x", "--price", "1", "--quantity", "1")]:
            with self.subTest(args=args):
                self.run_cli(*args, code=2)

    def test_instructor_sequence(self):
        self.run_cli("--help")
        self.assertEqual(self.add(), {"id": 1, "name": "Notebook", "price": "4.50", "quantity": 10})
        self.assertEqual(self.add("Pencil", "1.25", "5")["id"], 2)
        self.assertEqual([p["id"] for p in json.loads(self.run_cli("list").stdout)], [1, 2])
        self.assertEqual(json.loads(self.run_cli("get", "1").stdout)["name"], "Notebook")
        expected = {"id": 1, "name": "Notebook", "price": "4.50", "quantity": 12}
        self.assertEqual(json.loads(self.run_cli("update", "1", "--quantity", "12").stdout), expected)
        self.assertEqual(json.loads(self.run_cli("delete", "2", "--yes").stdout), {"deleted_id": 2})
        self.assertEqual(json.loads(self.run_cli("list").stdout), [expected])
        self.assertEqual(json.loads(self.path.read_text())["next_id"], 3)
        self.assertEqual(self.add()["id"], 3)

    def test_update_all(self):
        self.add()
        result = self.run_cli("update", "1", "--name", " New  name ", "--price", "0004.50", "--quantity", "0")
        self.assertEqual(json.loads(result.stdout), {"id": 1, "name": "New  name", "price": "4.50", "quantity": 0})

    def test_valid_inputs(self):
        for value, expected in [("0", "0.00"), ("4", "4.00"), ("4.5", "4.50"), ("0004.50", "4.50")]:
            self.assertEqual(self.add(" Same  name ", value, "000")["price"], expected)
        self.assertEqual(len(json.loads(self.run_cli("list").stdout)), 4)

    def test_invalid_fields_are_atomic(self):
        self.add()
        cases = {
            "name": ["", " \t\n"],
            "price": ["-1", "+1", "$4.50", "1e3", "1.234", ".5", "4.", "NaN", "Infinity", "1 2", "", " ", "４", "١", "4\n"],
            "quantity": ["-1", "+1", "1.5", "1e3", "", " ", "１", "1\n"]}
        for field, values in cases.items():
            for value in values:
                with self.subTest(field=field, value=value):
                    args = {"name": "Fine", "price": "1", "quantity": "1"}
                    args[field] = value
                    self.run_cli("add", *[arg for k, v in args.items() for arg in ("--" + k, v)], code=2)
                    self.run_cli("update", "1", "--name", "Changed", "--" + field, value, code=2)
        self.assertEqual(self.add()["id"], 2)

    def test_invalid_ids(self):
        for value in ["0", "-1", "+1", "1.5", "x", "１", "", "1\n"]:
            for command in ("get", "update", "delete"):
                extra = ["--quantity", "1"] if command == "update" else ["--yes"] if command == "delete" else []
                self.run_cli(command, value, *extra, code=2)

    def test_missing_ids(self):
        for args in [("get", "91"), ("update", "91", "--price", "1"), ("delete", "91", "--yes")]:
            self.assertIn("91", self.run_cli(*args, code=1).stderr)
        self.assertFalse(self.path.exists())

    def test_read_only_missing(self):
        for args in [("list",), ("low-stock", "--threshold", "0")]:
            self.assertEqual(json.loads(self.run_cli(*args).stdout), [])
            self.assertFalse(self.path.exists())

    def test_read_only_and_sorting(self):
        self.write(self.fixture())
        before = self.path.read_bytes(), self.path.stat().st_mtime_ns
        for args in [("list",), ("low-stock", "--threshold", "5")]:
            self.assertEqual([p["id"] for p in json.loads(self.run_cli(*args).stdout)], [1, 3])
        self.run_cli("get", "3")
        self.assertEqual((self.path.read_bytes(), self.path.stat().st_mtime_ns), before)

    def test_low_stock(self):
        self.write(self.fixture())
        self.assertEqual([p["id"] for p in json.loads(self.run_cli("low-stock", "--threshold", "0").stdout)], [1])
        self.run_cli("update", "1", "--quantity", "10")
        self.assertEqual(json.loads(self.run_cli("low-stock", "--threshold", "0").stdout), [])
        for value in ["-1", "+1", "1.5", "１", "", "x"]:
            self.run_cli("low-stock", "--threshold", value, code=2)

    def test_alternate_paths(self):
        for filename in ["relative store.json", str(self.cwd / "absolute store.json")]:
            self.run_cli("--file", filename, "add", "--name", "X", "--price", "0", "--quantity", "0")
            self.assertEqual(len(json.loads(self.run_cli("--file", filename, "low-stock", "--threshold", "0").stdout)), 1)
        self.assertFalse(self.path.exists())

    def test_invalid_serialization(self):
        for content in [b"", b"{", b"\xff", b'{"next_id":1,"next_id":2,"products":[]}']:
            self.path.write_bytes(content)
            self.run_cli("list", code=1)

    def test_invalid_schema(self):
        cases = [None, [], {}, {"next_id": 1, "products": [], "extra": 1}]
        for value in [True, 0, -1, 1.0, "4", None]:
            item = self.fixture(); item["next_id"] = value; cases.append(item)
        item = self.fixture(); item["products"] = {}; cases.append(item)
        for field, values in {"id": [True, 0, -1, "1", 1.0, 4], "name": ["", " ", " x", "x ", 4],
                              "price": [1, "1", "01.00", "1.0", "-1.00", "NaN", "１.00"],
                              "quantity": [True, -1, 1.5, "1"]}.items():
            for value in values:
                item = self.fixture(); item["products"][0][field] = value; cases.append(item)
        item = self.fixture(); item["products"][0]["extra"] = 0; cases.append(item)
        item = self.fixture(); del item["products"][0]["name"]; cases.append(item)
        item = self.fixture(); item["products"].append(copy.deepcopy(item["products"][0])); cases.append(item)
        for i, item in enumerate(cases):
            with self.subTest(case=i):
                self.write(item)
                for args in [("list",), ("get", "1"), ("low-stock", "--threshold", "3"),
                             ("add", "--name", "X", "--price", "1", "--quantity", "1")]:
                    self.run_cli(*args, code=1)

    def test_retained_counter(self):
        self.write({"next_id": 12, "products": []})
        self.assertEqual(self.add()["id"], 12)

    def test_filesystem_errors(self):
        self.run_cli("--file", "missing/stock.json", "add", "--name", "X", "--price", "1", "--quantity", "1", code=1)
        self.assertFalse((self.cwd / "missing").exists())
        self.run_cli("--file", str(self.cwd), "list", code=1)

    def test_injected_write_failure(self):
        self.write(self.fixture())
        before = self.path.read_bytes()
        for target in ("os.replace", "os.fsync"):
            with patch.object(sys, "stdout", io.StringIO()) as stdout, contextlib.redirect_stderr(io.StringIO()) as stderr:
                with patch.object(module.os, target.split(".")[1], side_effect=PermissionError("injected failure")):
                    self.assertEqual(module.main(["--file", str(self.path), "add", "--name", "X", "--price", "1", "--quantity", "1"]), 1)
                self.assertEqual(stdout.getvalue(), "")
                self.assertIn("injected failure", stderr.getvalue())
            self.assertEqual(self.path.read_bytes(), before)
            self.assertEqual(list(self.cwd.glob(".inventory-*.tmp")), [])

    def test_serialization_failure_preserves_file(self):
        self.write(self.fixture())
        before = self.path.read_bytes()
        with self.assertRaises(TypeError):
            module.save_store(self.path, {"bad": object()})
        self.assertEqual(self.path.read_bytes(), before)
        self.assertEqual(list(self.cwd.glob(".inventory-*.tmp")), [])

    def test_large_values_without_arbitrary_limits(self):
        digits = "9" * 5000
        product = self.add(price=digits, quantity=digits)
        self.assertEqual(product["price"], digits + ".00")
        self.assertEqual(str(product["quantity"]), digits)
        self.run_cli("list")


if __name__ == "__main__":
    unittest.main()
