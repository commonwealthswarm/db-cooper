"""Tests for db_cooper.claims on invented documents.

SYNTHETIC: every fixture below is invented (a made-up memo from a made-up office).
None of it is research evidence and nothing here is a finding.
"""

import json
import unittest

from db_cooper import claims
from db_cooper.claims import ClaimError

SYNTHETIC_SOURCE = "synthetic-memo-001"
SYNTHETIC_QUOTE = "SYNTHETIC: The courier left the depot at nine with two sealed crates."


def _claim(**overrides):
    args = dict(
        claim="SYNTHETIC: The invented memo says the courier left the depot at nine.",
        source_id=SYNTHETIC_SOURCE,
        locator="para 2",
        quote=SYNTHETIC_QUOTE,
        inference="",
        proposer_member_id="m_alpha",
    )
    args.update(overrides)
    return claims.make_claim(**args)


def _review(verdict="accept", reviewer="m_beta", **overrides):
    review = {"reviewer_member_id": reviewer, "verdict": verdict,
              "reason": "SYNTHETIC: quote found at para 2 of the invented memo.",
              "source_opened": True}
    review.update(overrides)
    return review


class ConstructionTests(unittest.TestCase):
    def test_new_claim_is_unreviewed_with_history(self):
        rec = _claim()
        self.assertEqual(rec["status"], "unreviewed")
        self.assertEqual(len(rec["history"]), 1)
        self.assertEqual(rec["history"][0]["event"], "proposed")

    def test_quote_required(self):
        with self.assertRaises(ClaimError):
            _claim(quote="")
        with self.assertRaises(ClaimError):
            _claim(quote="   ")

    def test_locator_required(self):
        with self.assertRaises(ClaimError):
            _claim(locator="")

    def test_source_id_required(self):
        with self.assertRaises(ClaimError):
            _claim(source_id=None)

    def test_claim_over_400_chars_rejected(self):
        with self.assertRaises(ClaimError):
            _claim(claim="S" * 401)
        self.assertEqual(len(_claim(claim="S" * 400)["claim"]), 400)

    def test_inference_explicit_may_be_empty(self):
        self.assertEqual(_claim(inference="")["inference"], "")
        rec = _claim(inference="SYNTHETIC: the crates were probably heavy.")
        self.assertNotEqual(rec["inference"], rec["quote"])
        bad = dict(rec)
        del bad["inference"]
        with self.assertRaises(ClaimError):
            claims.validate_claim(bad)
        bad["inference"] = None
        with self.assertRaises(ClaimError):
            claims.validate_claim(bad)

    def test_unknown_status_rejected(self):
        rec = _claim()
        rec["status"] = "confirmed"
        with self.assertRaises(ClaimError):
            claims.validate_claim(rec)


class ForbiddenFieldTests(unittest.TestCase):
    def test_suspect_rank_fields_rejected(self):
        for key in ("suspect", "suspect_score", "rank", "Suspect-Rank", "ranking",
                    "guilt", "score", "likelihood", "match_score", "accused"):
            rec = _claim()
            rec[key] = "x"
            with self.assertRaises(ClaimError, msg=key):
                claims.validate_claim(rec)

    def test_forbidden_field_in_review_rejected(self):
        rec = _claim()
        with self.assertRaises(ClaimError):
            claims.apply_review(rec, _review(suspect_score=0.9))


class AcceptanceTests(unittest.TestCase):
    def test_accept_requires_review(self):
        rec = _claim()
        with self.assertRaises(ClaimError):
            claims.set_status(rec, "accepted", "m_beta")
        forged = dict(rec)
        forged["status"] = "accepted"
        with self.assertRaises(ClaimError):
            claims.validate_claim(forged)

    def test_accept_with_valid_review(self):
        rec = claims.apply_review(_claim(), _review())
        self.assertEqual(rec["status"], "accepted")
        self.assertEqual(rec["history"][-1]["review"]["reviewer_member_id"], "m_beta")

    def test_self_review_cannot_accept(self):
        with self.assertRaises(ClaimError):
            claims.apply_review(_claim(), _review(reviewer="m_alpha"))

    def test_review_needs_reason_and_opened_source(self):
        with self.assertRaises(ClaimError):
            claims.apply_review(_claim(), _review(reason=""))
        with self.assertRaises(ClaimError):
            claims.apply_review(_claim(), _review(source_opened=False))

    def test_reject_and_request_changes(self):
        self.assertEqual(claims.apply_review(_claim(), _review("reject"))["status"], "rejected")
        self.assertEqual(claims.apply_review(_claim(), _review("request_changes"))["status"],
                         "changes_requested")

    def test_input_not_mutated(self):
        rec = _claim()
        before = claims.to_json(rec)
        claims.apply_review(rec, _review())
        self.assertEqual(claims.to_json(rec), before)


class HistoryTests(unittest.TestCase):
    def test_correction_appends_history_and_resets_status(self):
        rec = claims.apply_review(_claim(), _review())
        fixed = claims.correct(rec, "m_alpha", "SYNTHETIC: fix locator",
                               locator="para 3")
        self.assertEqual(fixed["locator"], "para 3")
        self.assertEqual(fixed["status"], "unreviewed")
        self.assertEqual(fixed["history"][:len(rec["history"])], rec["history"])
        self.assertEqual(fixed["history"][-1]["previous"], {"locator": "para 2"})

    def test_correction_cannot_touch_status_or_proposer(self):
        with self.assertRaises(ClaimError):
            claims.correct(_claim(), "m_alpha", "note", status="accepted")
        with self.assertRaises(ClaimError):
            claims.correct(_claim(), "m_alpha", "note", proposer_member_id="m_x")


class DisputeTests(unittest.TestCase):
    def test_disputed_keeps_both_positions(self):
        rec = claims.apply_review(_claim(), _review())
        positions = [
            {"member_id": "m_beta", "position": "SYNTHETIC: quote is at para 2."},
            {"member_id": "m_gamma", "position": "SYNTHETIC: para 2 says ten, not nine."},
        ]
        disputed = claims.mark_disputed(rec, positions, "m_gamma")
        self.assertEqual(disputed["status"], "disputed")
        self.assertEqual(disputed["positions"], positions)
        self.assertEqual(disputed["history"][-1]["positions"], positions)
        round_trip = claims.from_json(claims.to_json(disputed))
        self.assertEqual([p["position"] for p in round_trip["positions"]],
                         [p["position"] for p in positions])

    def test_dispute_needs_two_members(self):
        one_sided = [{"member_id": "m_beta", "position": "a"},
                     {"member_id": "m_beta", "position": "b"}]
        with self.assertRaises(ClaimError):
            claims.mark_disputed(_claim(), one_sided, "m_beta")
        with self.assertRaises(ClaimError):
            claims.set_status(_claim(), "disputed", "m_beta")

    def test_disputed_claim_cannot_be_accepted_by_one_review(self):
        positions = [{"member_id": "m_beta", "position": "a"},
                     {"member_id": "m_gamma", "position": "b"}]
        disputed = claims.mark_disputed(_claim(), positions, "m_gamma")
        with self.assertRaises(ClaimError):
            claims.apply_review(disputed, _review(reviewer="m_delta"))


class SerialisationTests(unittest.TestCase):
    def test_deterministic_json(self):
        a = claims.apply_review(_claim(), _review())
        b = claims.apply_review(_claim(), _review())
        self.assertEqual(claims.to_json(a), claims.to_json(b))
        reordered = json.loads(json.dumps(a), object_pairs_hook=lambda p: dict(reversed(p)))
        self.assertEqual(claims.to_json(reordered), claims.to_json(a))
        self.assertEqual(claims.from_json(claims.to_json(a)), a)


if __name__ == "__main__":
    unittest.main()
