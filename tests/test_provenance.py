import unittest

from db_cooper.provenance import sha256_bytes, validate_source_record

GOOD = {
    "id": "example", "title": "SYNTHETIC example source", "url": "https://example.invalid/x", "license": "none (test fixture)",
    "attribution": "SYNTHETIC", "redistribution": "open", "status": "unverified",
}


class ProvenanceTests(unittest.TestCase):
    def test_sha256_of_known_bytes(self):
        self.assertEqual(sha256_bytes(b"abc"), "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad")

    def test_unverified_record_without_hash_is_valid(self):
        self.assertEqual(validate_source_record(GOOD), [])

    def test_verified_record_needs_hash_and_date(self):
        problems = validate_source_record({**GOOD, "status": "verified"})
        self.assertTrue(any("sha256" in p for p in problems))
        self.assertTrue(any("retrieved" in p for p in problems))

    def test_bad_hash_is_reported(self):
        self.assertTrue(any("sha256" in p for p in validate_source_record({**GOOD, "sha256": "XYZ"})))

    def test_missing_field_is_reported(self):
        rec = dict(GOOD)
        del rec["license"]
        self.assertIn("missing field: license", validate_source_record(rec))

    def test_restricted_source_cannot_be_publishable(self):
        for redistribution in ("restricted", "unresolved"):
            problems = validate_source_record({**GOOD, "redistribution": redistribution, "publishable": True})
            self.assertTrue(any("publishable" in p for p in problems), redistribution)


if __name__ == "__main__":
    unittest.main()
