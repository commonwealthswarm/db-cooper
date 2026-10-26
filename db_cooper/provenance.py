"""Source provenance records for db-cooper.

Every real source this project uses is described by a record that says where it came from, under what terms, whether
it may be republished and whether anyone has actually verified it. A record built from a description alone is
'unverified' and carries no hash. Nothing here reads the network.
"""

import hashlib
import re

REQUIRED = ("id", "title", "url", "license", "attribution", "redistribution", "status")
REDISTRIBUTION = ("open", "attribution-required", "restricted", "unresolved")
STATUS = ("verified", "unverified")
_SHA256 = re.compile(r"^[0-9a-f]{64}$")


def sha256_bytes(data):
    return hashlib.sha256(data).hexdigest()


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def validate_source_record(rec):
    """Return a list of problems; an empty list means the record is well formed."""
    if not isinstance(rec, dict):
        return ["record must be an object"]
    problems = []
    for key in REQUIRED:
        if rec.get(key) in (None, ""):
            problems.append("missing field: " + key)
    if rec.get("redistribution") not in (None, "") and rec["redistribution"] not in REDISTRIBUTION:
        problems.append("redistribution must be one of " + ", ".join(REDISTRIBUTION))
    if rec.get("status") not in (None, "") and rec["status"] not in STATUS:
        problems.append("status must be one of " + ", ".join(STATUS))
    sha = rec.get("sha256")
    if sha is not None and not (isinstance(sha, str) and _SHA256.match(sha)):
        problems.append("sha256 must be 64 lowercase hex characters")
    if rec.get("status") == "verified":
        if sha is None:
            problems.append("a verified record needs sha256")
        if not rec.get("retrieved"):
            problems.append("a verified record needs retrieved (date)")
    if rec.get("publishable") is True and rec.get("redistribution") in ("restricted", "unresolved"):
        problems.append("a restricted or unresolved source cannot be publishable")
    return problems
