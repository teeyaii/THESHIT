import unittest
from thai_title_diagnostics import nearest_substring_distance

class ThaiTitleDiagnosticTests(unittest.TestCase):
    def test_exact_and_whitespace(self):
        self.assertEqual(nearest_substring_distance("ภาษาไทย","prefix ภาษา ไทย suffix"),0)
    def test_missing_character(self):
        self.assertEqual(nearest_substring_distance("ภาษาไทย","prefix ภาษไทย suffix"),1)
        self.assertEqual(nearest_substring_distance("ภาษาไทย",""),7)
    def test_missing_sara_am_mark_not_silently_fixed(self):
        self.assertGreater(nearest_substring_distance("จำลอง","จ าลอง"),0)
    def test_empty_reference(self):
        with self.assertRaises(ValueError):nearest_substring_distance("","text")
