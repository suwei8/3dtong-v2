"""Pre-registered, label-blind, reproducible control for the next 3-digit issue.

No true draws, model outputs, timestamps or secrets enter this algorithm.
Version and deterministic scoring are permanent after first future freeze.
"""
import hashlib
import re

NAME = "random-control-v1"
VERSION = "sha256-rank-v1"


def control_digits(known_issue, target_issue):
    """Choose 3 distinct digits from SHA256 ranks, without Python PRNG variance.

    Domain separation prevents accidental reuse of application hashes. This is
    a reproducible pseudo-random control, not cryptographically secret: anyone
    can reproduce it from the publicly frozen issue IDs. Under iid uniform
    lottery digits, its theoretical probability to hit any digit is 65.7%.
    """
    if not all(isinstance(s, str) and re.fullmatch(r"[0-9]{7}", s)
               for s in (known_issue, target_issue)):
        raise ValueError("both issue IDs must be 7-digit strings")
    if int(target_issue) <= int(known_issue):
        raise ValueError("control cannot target an existing draw")
    # Sorting by independent SHA256-like digest gives symmetric, deterministic
    # selection among 0..9. Output order does NOT represent digit positions.
    domain = f"3dtong-v2|random-control-v1|{known_issue}|{target_issue}|"
    ranked = sorted(range(10), key=lambda digit: (
        hashlib.sha256((domain + str(digit)).encode("ascii")).digest(), digit
    ))
    return ranked[:3]
