"""Check disclosed keys by hashing down to the root or the nearest verified key."""
import hmac

from .keychain import hash_down


class KeyVerifier:
    def __init__(self, root: bytes, max_steps: int = 100_000):
        self.known = {0: root}
        self.max_steps = max_steps

    def verify(self, i: int, key: bytes) -> bool:
        if i in self.known:
            return hmac.compare_digest(self.known[i], key)
        lower = [j for j in self.known if j < i]
        if i <= 0 or not lower:
            return False
        j = max(lower)
        if i - j > self.max_steps:
            return False
        h = key
        for _ in range(i - j):
            h = hash_down(h)
        if hmac.compare_digest(h, self.known[j]):
            self.known[i] = key
            return True
        return False
