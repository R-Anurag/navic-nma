"""Per-satellite authentication state: no data -> key verified -> authenticated -> stale."""
from ..tesla.tags import TagAccumulator

NO_DATA, KEY_VERIFIED, AUTHENTICATED, STALE, FAILED = "no data", "key verified", "authenticated", "stale", "failed"


class SatAuth:
    def __init__(self, target_bits: int, max_age: float):
        self.acc = TagAccumulator(target_bits)
        self.max_age = max_age
        self.key_verified = False
        self.orbit = None        # last authenticated ephemeris
        self.last_auth = None
        self.failed = False

    def tag_ok(self, orbit, bits: int, t: float):
        if self.acc.add(True, bits):
            self.orbit, self.last_auth, self.failed = orbit, t, False

    def tag_failed(self):
        self.acc.add(False, 0)
        self.orbit, self.failed = None, True

    def state(self, t: float) -> str:
        if self.failed:
            return FAILED
        if self.orbit is not None:
            return AUTHENTICATED if t - self.last_auth <= self.max_age else STALE
        return KEY_VERIFIED if self.key_verified else NO_DATA

    def usable(self, t: float) -> bool:
        return self.state(t) == AUTHENTICATED
