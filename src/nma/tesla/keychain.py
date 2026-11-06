"""One-way TESLA key chain: K(i) = SHA-256(K(i+1)) truncated to 128 bits.

K(0) is the root key (signed and broadcast). K(i) authenticates interval i and
is disclosed later. Simplified vs OSNMA: no GST/alpha salt in the hash input.
"""
import hashlib
import random

KEY_BYTES = 16


def hash_down(key: bytes) -> bytes:
    return hashlib.sha256(key).digest()[:KEY_BYTES]


class KeyChain:
    def __init__(self, length: int, seed: int | bytes = 0):
        tip = seed if isinstance(seed, bytes) else random.Random(seed).randbytes(KEY_BYTES)
        keys = [tip[:KEY_BYTES]]
        for _ in range(length):
            keys.append(hash_down(keys[-1]))
        self.keys = keys[::-1]  # keys[0] is the root

    @property
    def root(self) -> bytes:
        return self.keys[0]

    def key(self, i: int) -> bytes:
        return self.keys[i]

    def __len__(self):
        return len(self.keys)
