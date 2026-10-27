"""Quote locator check: does a quote occur in the supplied page text?

A pure function. It normalises whitespace, line-end hyphenation and curly quotes,
and reports exactly what it found. It never fuzzy-matches silently: an approximate
match is reported as ``near_match`` with the differing characters, never as ``found``.
"""

import difflib

NEAR_MATCH_RATIO = 0.85

_QUOTE_MAP = {
    "‘": "'", "’": "'", "‚": "'", "‛": "'", "′": "'",
    "“": '"', "”": '"', "„": '"', "‟": '"', "″": '"',
}


def _line_end_hyphen(text, i):
    """If text[i] is a hyphen ending a line between two letters, return the index of the
    next letter; otherwise None."""
    n = len(text)
    j = i + 1
    while j < n and text[j] in " \t":
        j += 1
    if j >= n or text[j] not in "\r\n":
        return None
    k = j
    while k < n and text[k].isspace():
        k += 1
    if k < n and text[k].isalpha() and i > 0 and text[i - 1].isalpha():
        return k
    return None


def normalise(text, join_hyphens=True):
    """Return (normalised_text, index_map); index_map[p] is the original offset of
    normalised character p."""
    out = []
    index = []
    i = 0
    n = len(text)
    while i < n:
        c = text[i]
        if c == "-":
            k = _line_end_hyphen(text, i)
            if k is not None:
                if not join_hyphens:
                    out.append("-")
                    index.append(i)
                i = k
                continue
        if c.isspace():
            if out and out[-1] != " ":
                out.append(" ")
                index.append(i)
            i += 1
            continue
        out.append(_QUOTE_MAP.get(c, c))
        index.append(i)
        i += 1
    if out and out[-1] == " ":
        out.pop()
        index.pop()
    return "".join(out), index


def _find_all(needle, hay):
    found = []
    start = hay.find(needle)
    while start != -1:
        found.append(start)
        start = hay.find(needle, start + 1)
    return found


def _span(index, start, length):
    return (index[start], index[start + length - 1] + 1)


def check_quote(quote, page_text):
    """Check ``quote`` against ``page_text``.

    Returns a dict: status (found | ambiguous | near_match | not_found), spans (list of
    [start, end] offsets into the original page text), matched (the original text of
    each span), differences (for near_match: op, quote and page characters that differ).
    """
    if not isinstance(quote, str) or not isinstance(page_text, str):
        raise TypeError("quote and page_text must be strings")
    # Hyphens inside the quote are kept; the page is tried both ways.
    norm_quote, _ = normalise(quote, join_hyphens=False)
    if not norm_quote:
        raise ValueError("quote is empty after normalisation")

    spans = set()
    for join in (True, False):
        norm_page, index = normalise(page_text, join_hyphens=join)
        for start in _find_all(norm_quote, norm_page):
            spans.add(_span(index, start, len(norm_quote)))
    spans = sorted(spans)
    if spans:
        return {
            "status": "found" if len(spans) == 1 else "ambiguous",
            "spans": [list(s) for s in spans],
            "matched": [page_text[s:e] for s, e in spans],
            "differences": [],
        }

    norm_page, index = normalise(page_text, join_hyphens=True)
    best = None
    if norm_page:
        width = min(len(norm_quote), len(norm_page))
        for start in range(0, len(norm_page) - width + 1):
            window = norm_page[start:start + width]
            ratio = difflib.SequenceMatcher(None, norm_quote, window, autojunk=False).ratio()
            if best is None or ratio > best[0]:
                best = (ratio, start, window)
    if best is not None and best[0] >= NEAR_MATCH_RATIO:
        ratio, start, window = best
        matcher = difflib.SequenceMatcher(None, norm_quote, window, autojunk=False)
        differences = [
            {"op": tag, "quote": norm_quote[i1:i2], "page": window[j1:j2]}
            for tag, i1, i2, j1, j2 in matcher.get_opcodes() if tag != "equal"
        ]
        s, e = _span(index, start, len(window))
        return {
            "status": "near_match",
            "spans": [[s, e]],
            "matched": [page_text[s:e]],
            "differences": differences,
            "ratio": round(ratio, 4),
        }
    return {"status": "not_found", "spans": [], "matched": [], "differences": []}
