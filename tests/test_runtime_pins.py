import tempfile
import unittest
from pathlib import Path
from check_runtime_pins import parse_pins,compare

class RuntimePinsTests(unittest.TestCase):
    def test_exact_names(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/"pins.txt"
            p.write_text("# example\nFoo_Bar==1.0\n",encoding="utf-8")
            self.assertEqual(parse_pins(p),{"foo-bar":"1.0"})
            p.write_text("Foo_Bar==1.0\nfoo-bar==2.0",encoding="utf-8")
            with self.assertRaises(ValueError):
                parse_pins(p)
    def test_detect_drift(self):
        self.assertFalse(any(compare({"a":"1"},{"a":"1"}).values()))
        d=compare({"a":"1","b":"2"},{"a":"2","c":"3"})
        self.assertEqual(d["missing"],["b"])
        self.assertEqual(d["unexpected"],["c"])
        self.assertEqual(d["mismatch"],[{"name":"a","expected":"1","actual":"2"}])
