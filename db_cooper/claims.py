"""Proposed-evidence claim records.

A claim record is a narrow statement tied to one source locator and a verbatim
quote, with a separate, explicit inference field. Nothing is a fact until an
independent review accepts it, and no record may rank, score or accuse a person.

Records are plain dicts so they serialise deterministically. Every function
returns a new record; the input is never mutated. Corrections and status
changes append to ``history``; earlier entries are never rewritten.
"""

import copy
import json

MAX_CLAIM_CHARS = 400

STATUSES = ("unreviewed", "accepted", "changes_requested", "rejected", "disputed")

REVIEW_VERDICTS = ("accept", "request_changes", "reject")

_VERDICT_STATUS = {
    "accept": "accepted",
    "request_changes": "changes_requested",
    "reject": "rejected",
}

REQUIRED_FIELDS = ("claim", "source_id", "locator", "quote", "inference",
                   "proposer_member_id", "status", "history")
OPTIONAL_FIELDS = ("positions",)

# Fragments that mark a field as ranking or accusing a person.
_FORBIDDEN_FRAGMENTS = ("suspect", "rank", "guilt", "accus", "culprit", "perpetrator")
_FORBIDDEN_EXACT = ("score", "likelihood", "probability")

CORRECTABLE_FIELDS = ("claim", "source_id", "locator", "quote", "inference")


class ClaimError(ValueError):
    """A claim record or a change to one breaks a rule."""


def _forbidden_key(key):
    norm = str(key).strip().lower().replace("-", "_").replace(" ", "_")
    if norm in _FORBIDDEN_EXACT or norm.endswith("_score"):
        return True
    return any(fragment in norm for fragment in _FORBIDDEN_FRAGMENTS)


def _check_forbidden(mapping, where):
    for key in mapping:
        if _forbidden_key(key):
            raise ClaimError("field %r in %s is forbidden: records never rank or accuse a person"
                             % (key, where))


def _nonempty_str(value, name):
    if not isinstance(value, str) or not value.strip():
        raise ClaimError("%s is required and must be a non-empty string" % name)


def validate_claim(record):
    """Raise ClaimError if ``record`` breaks any rule; return it unchanged otherwise."""
    if not isinstance(record, dict):
        raise ClaimError("a claim record must be a dict")
    _check_forbidden(record, "record")
    unknown = set(record) - set(REQUIRED_FIELDS) - set(OPTIONAL_FIELDS)
    if unknown:
        raise ClaimError("unknown fields: %s" % ", ".join(sorted(unknown)))
    missing = [f for f in REQUIRED_FIELDS if f not in record]
    if missing:
        raise ClaimError("missing fields: %s" % ", ".join(missing))

    _nonempty_str(record["claim"], "claim")
    if len(record["claim"]) > MAX_CLAIM_CHARS:
        raise ClaimError("claim is %d characters; the limit is %d"
                         % (len(record["claim"]), MAX_CLAIM_CHARS))
    _nonempty_str(record["source_id"], "source_id")
    _nonempty_str(record["locator"], "locator")
    _nonempty_str(record["quote"], "quote")
    if not isinstance(record["inference"], str):
        raise ClaimError("inference must be a string (it may be empty, but must be explicit)")
    _nonempty_str(record["proposer_member_id"], "proposer_member_id")

    status = record["status"]
    if status not in STATUSES:
        raise ClaimError("status %r is not one of %s" % (status, ", ".join(STATUSES)))
    history = record["history"]
    if not isinstance(history, list) or not all(isinstance(h, dict) for h in history):
        raise ClaimError("history must be a list of dicts")
    for entry in history:
        _check_forbidden(entry, "history entry")
        if isinstance(entry.get("review"), dict):
            _check_forbidden(entry["review"], "review")

    if status == "accepted":
        last_status_entry = _last_status_entry(history)
        if (last_status_entry is None or last_status_entry.get("to_status") != "accepted"
                or not isinstance(last_status_entry.get("review"), dict)):
            raise ClaimError("status accepted requires an accepting review record in history")
        validate_review(last_status_entry["review"], record)

    if status == "disputed":
        _validate_positions(record.get("positions"))
    elif "positions" in record:
        raise ClaimError("positions are only kept on a disputed claim")
    return record


def _last_status_entry(history):
    for entry in reversed(history):
        if "to_status" in entry:
            return entry
    return None


def make_claim(claim, source_id, locator, quote, inference, proposer_member_id):
    """Construct a new, unreviewed claim record. ``inference`` may be '' but must be given."""
    record = {
        "claim": claim,
        "source_id": source_id,
        "locator": locator,
        "quote": quote,
        "inference": inference,
        "proposer_member_id": proposer_member_id,
        "status": "unreviewed",
        "history": [{"event": "proposed", "member_id": proposer_member_id,
                     "to_status": "unreviewed"}],
    }
    return validate_claim(record)


def validate_review(review, record):
    """Minimal review-record check: a different member, an opened source, a stated reason.

    The full review rules live in their own task; this is the gate the claim record needs.
    """
    if not isinstance(review, dict):
        raise ClaimError("a review record must be a dict")
    _check_forbidden(review, "review")
    _nonempty_str(review.get("reviewer_member_id"), "reviewer_member_id")
    if review["reviewer_member_id"] == record["proposer_member_id"]:
        raise ClaimError("a reviewer must be a different member from the proposer")
    if review.get("verdict") not in REVIEW_VERDICTS:
        raise ClaimError("review verdict must be one of %s" % ", ".join(REVIEW_VERDICTS))
    _nonempty_str(review.get("reason"), "reason")
    if review.get("source_opened") is not True:
        raise ClaimError("the reviewer must have opened the cited source")
    return review


def apply_review(record, review):
    """Return a new record with the review applied. Only an accept review can accept."""
    validate_claim(record)
    validate_review(review, record)
    if record["status"] == "disputed":
        raise ClaimError("a disputed claim keeps its positions; resolve the dispute first")
    new = copy.deepcopy(record)
    to_status = _VERDICT_STATUS[review["verdict"]]
    new["history"].append({
        "event": "reviewed",
        "member_id": review["reviewer_member_id"],
        "from_status": record["status"],
        "to_status": to_status,
        "review": copy.deepcopy(review),
    })
    new["status"] = to_status
    return validate_claim(new)


def set_status(record, status, member_id, note=""):
    """Change status without a review. Never allowed to reach 'accepted' this way."""
    if status == "accepted":
        raise ClaimError("status moves to accepted only through an accepting review record")
    if status == "disputed":
        raise ClaimError("use mark_disputed, which keeps both positions")
    if status not in STATUSES:
        raise ClaimError("status %r is not one of %s" % (status, ", ".join(STATUSES)))
    validate_claim(record)
    _nonempty_str(member_id, "member_id")
    new = copy.deepcopy(record)
    new["history"].append({"event": "status_changed", "member_id": member_id,
                           "from_status": record["status"], "to_status": status, "note": note})
    new["status"] = status
    return validate_claim(new)


def correct(record, member_id, note, **changes):
    """Correct claim fields. The old values stay in history; the claim returns to unreviewed."""
    validate_claim(record)
    _nonempty_str(member_id, "member_id")
    _nonempty_str(note, "note")
    if not changes:
        raise ClaimError("a correction must change at least one field")
    bad = set(changes) - set(CORRECTABLE_FIELDS)
    if bad:
        raise ClaimError("cannot correct fields: %s" % ", ".join(sorted(bad)))
    new = copy.deepcopy(record)
    previous = {k: record[k] for k in sorted(changes)}
    new.update(changes)
    new.pop("positions", None)
    new["history"].append({"event": "corrected", "member_id": member_id, "note": note,
                           "previous": previous, "from_status": record["status"],
                           "to_status": "unreviewed"})
    new["status"] = "unreviewed"
    return validate_claim(new)


def _validate_positions(positions):
    if not isinstance(positions, list) or len(positions) < 2:
        raise ClaimError("a disputed claim must keep at least two positions")
    members = set()
    for pos in positions:
        if not isinstance(pos, dict):
            raise ClaimError("each position must be a dict")
        _check_forbidden(pos, "position")
        _nonempty_str(pos.get("member_id"), "position member_id")
        _nonempty_str(pos.get("position"), "position text")
        members.add(pos["member_id"])
    if len(members) < 2:
        raise ClaimError("a dispute needs positions from at least two different members")


def mark_disputed(record, positions, member_id):
    """Mark a claim disputed, keeping every position side by side."""
    validate_claim(record)
    _nonempty_str(member_id, "member_id")
    positions = copy.deepcopy(positions)
    _validate_positions(positions)
    new = copy.deepcopy(record)
    new["positions"] = positions
    new["history"].append({"event": "disputed", "member_id": member_id,
                           "from_status": record["status"], "to_status": "disputed",
                           "positions": copy.deepcopy(positions)})
    new["status"] = "disputed"
    return validate_claim(new)


def to_json(record):
    """Deterministic serialisation: sorted keys, fixed separators, UTF-8 text."""
    validate_claim(record)
    return json.dumps(record, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def from_json(text):
    """Parse and validate a serialised claim record."""
    return validate_claim(json.loads(text))
