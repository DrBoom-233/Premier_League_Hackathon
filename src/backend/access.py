"""High-entropy judge codes authorize bounded analyses; only hashes are configured."""
import hashlib
import json
import os


def configured_codes():
    codes = json.loads(os.environ.get('PITCHGUARD_ANALYSIS_CODES', '{}'))
    if not isinstance(codes, dict) or any(
        len(key) != 64 or any(c not in '0123456789abcdef' for c in key)
        or type(limit) is not int or not 1 <= limit <= 10 for key, limit in codes.items()
    ):
        raise ValueError('Analysis codes must map SHA-256 digests to limits of 1–10')
    return codes


def code_digest(code):
    return hashlib.sha256(code.encode()).hexdigest()
