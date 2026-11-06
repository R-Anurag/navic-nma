"""Receiver clock: offset + drift, plus a hook an attacker can use to shift it.

`oscillator()` is the free-running local oscillator; GNSS signals can drag the
steered clock (`now`) but not the oscillator, which is how jumps are spotted.
"""


class Clock:
    def __init__(self, offset=0.0, drift_ppm=0.5):
        self.offset = offset
        self.drift = drift_ppm * 1e-6
        self.attack = lambda t: 0.0   # attacker hook: extra shift at true time t

    def oscillator(self, t: float) -> float:
        return t * (1 + self.drift)

    def now(self, t: float) -> float:
        return self.oscillator(t) + self.offset + self.attack(t)

    def set_to(self, t: float, value: float):
        """Steer so that now(t) == value."""
        self.offset += value - self.now(t)
