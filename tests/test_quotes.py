"""Tests for db_cooper.quotes on invented page text.

SYNTHETIC: every page below is invented. None of it is research evidence.
"""

import unittest

from db_cooper.quotes import check_quote, normalise

PAGE = ("SYNTHETIC MEMO, invented office.\n"
        "The agent filed the re-\n"
        "port on Tuesday. The  van   stopped at\n"
        "   the ferry landing. A well-\n"
        "known clerk said “nothing unusual” about it.\n")


class QuoteCheckTests(unittest.TestCase):
    def test_hyphenated_line_break_joined(self):
        r = check_quote("filed the report on Tuesday", PAGE)
        self.assertEqual(r["status"], "found")
        self.assertIn("re-\nport", r["matched"][0])

    def test_real_hyphen_across_line_kept(self):
        r = check_quote("A well-known clerk", PAGE)
        self.assertEqual(r["status"], "found")

    def test_double_spaces(self):
        r = check_quote("The van stopped", PAGE)
        self.assertEqual(r["status"], "found")

    def test_curly_quotes_in_page(self):
        r = check_quote('said "nothing unusual" about', PAGE)
        self.assertEqual(r["status"], "found")

    def test_curly_quotes_in_quote(self):
        page = "SYNTHETIC: the note read 'hold the parcel' twice over."
        r = check_quote("read ‘hold the parcel’", page)
        self.assertEqual(r["status"], "found")

    def test_quote_split_across_lines(self):
        r = check_quote("van stopped at the ferry landing", PAGE)
        self.assertEqual(r["status"], "found")
        self.assertIn("\n", r["matched"][0])

    def test_quote_absent(self):
        r = check_quote("an entirely different sentence about weather balloons", PAGE)
        self.assertEqual(r["status"], "not_found")
        self.assertEqual(r["spans"], [])

    def test_quote_twice_is_ambiguous(self):
        page = "SYNTHETIC: the bell rang. Later, the bell rang. Then silence."
        r = check_quote("the bell rang", page)
        self.assertEqual(r["status"], "ambiguous")
        self.assertEqual(len(r["spans"]), 2)
        self.assertEqual(r["matched"], ["the bell rang", "the bell rang"])

    def test_near_match_not_found(self):
        page = "SYNTHETIC: the parcel was handed over at the north gate at dusk."
        r = check_quote("the parcel was handed over at the south gate", page)
        self.assertEqual(r["status"], "near_match")
        self.assertNotEqual(r["status"], "found")
        self.assertTrue(r["differences"])
        joined_page = "".join(d["page"] for d in r["differences"])
        joined_quote = "".join(d["quote"] for d in r["differences"])
        self.assertNotEqual(joined_page, joined_quote)

    def test_span_offsets_point_into_original(self):
        page = "SYNTHETIC:   alpha  beta gamma"
        r = check_quote("alpha beta", page)
        s, e = r["spans"][0]
        self.assertEqual(page[s:e], "alpha  beta")

    def test_empty_quote_rejected(self):
        with self.assertRaises(ValueError):
            check_quote("   \n ", PAGE)

    def test_deterministic_and_normalise_map(self):
        self.assertEqual(check_quote("the ferry", PAGE), check_quote("the ferry", PAGE))
        text, index = normalise("a  b“")
        self.assertEqual(text, 'a b"')
        self.assertEqual(len(text), len(index))


if __name__ == "__main__":
    unittest.main()
