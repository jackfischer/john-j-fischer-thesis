"""Regression checks for scan accounting; no OCR correction is inferred here."""
import unittest

from audit_scan import furniture
from fidelity_text import canonical


class ScanAccountingTests(unittest.TestCase):
    def test_top_continuation_is_not_a_header(self):
        self.assertIsNone(furniture(26, 'rests exclusively on competition among the workers.', 65))
        self.assertIsNone(furniture(86, 'of the individual and his political freedom', 72))
        self.assertIsNone(furniture(106, '98. Marx and Engels, Selected Works', 74))

    def test_only_exact_expected_bottom_folio_is_furniture(self):
        self.assertEqual(furniture(26, '23', 730), 'recognized original folio')
        self.assertIsNone(furniture(26, '24', 730))
        self.assertIsNone(furniture(26, 'In 1923', 730))
        self.assertIsNone(furniture(26, '23', 200))

    def test_repeated_header_is_logged_as_unverified_exclusion(self):
        self.assertIn('image review still required', furniture(
            26, 'AN IDEOLOGICAL OFFENSIVE FOR THE FREE WORLD', 60))

    def test_mathematical_superscript_is_not_normalized_away(self):
        result = canonical([{'c':c} for c in 'a² + 1'])
        self.assertEqual(result['text'], 'a²+1')


if __name__ == '__main__':
    unittest.main()
