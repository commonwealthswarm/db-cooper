"""Repository guard: this repository holds code, synthetic fixtures generated in tests, and small text records.
It must not hold source data files (see SOURCES.md for each source's redistribution terms)."""

import os
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BLOCKED_EXTENSIONS = (".wav", ".mp3", ".flac", ".fits", ".fil", ".h5", ".hdf5", ".tif", ".tiff", ".png", ".jpg", ".jpeg", ".pdf", ".zip", ".gz", ".bed", ".bam", ".npy", ".pkl",)
MAX_BYTES = 1000000


def repo_files():
    for base, dirs, files in os.walk(ROOT):
        dirs[:] = [d for d in dirs if d not in (".git", "__pycache__")]
        for name in files:
            yield os.path.join(base, name)


class RepoGuardTests(unittest.TestCase):
    def test_no_source_data_files(self):
        found = [p for p in repo_files() if os.path.splitext(p)[1].lower() in BLOCKED_EXTENSIONS]
        self.assertEqual(found, [], "data/media files must not be committed")

    def test_no_oversized_files(self):
        big = [p for p in repo_files() if os.path.getsize(p) > MAX_BYTES]
        self.assertEqual(big, [], "files over the size limit must not be committed")


if __name__ == "__main__":
    unittest.main()
