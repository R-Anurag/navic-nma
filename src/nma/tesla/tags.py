"""Truncated HMAC-SHA-256 tags and tag accumulation."""
import hashlib
import hmac


def hmac_trunc(key: bytes, data: bytes, bits: int) -> int:
    mac = hmac.new(key, data, hashlib.sha256).digest()
    return int.from_bytes(mac, "big") >> (256 - bits)


def tag_input(message: bytes, prn: int, interval: int) -> bytes:
    return message + prn.to_bytes(2, "big") + interval.to_bytes(4, "big")


def make_tag(key: bytes, message: bytes, prn: int, interval: int, bits: int = 32) -> int:
    return hmac_trunc(key, tag_input(message, prn, interval), bits)


def check_tag(key, message, prn, interval, tag: int, bits: int = 32) -> bool:
    return make_tag(key, message, prn, interval, bits) == tag


class TagAccumulator:
    """A satellite counts as authenticated once verified tag bits reach `target`.
    Any failed tag resets the count (OSNMA does the same)."""

    def __init__(self, target_bits: int):
        self.target = target_bits
        self.bits = 0

    def add(self, ok: bool, bits: int) -> bool:
        self.bits = self.bits + bits if ok else 0
        return self.authenticated

    @property
    def authenticated(self) -> bool:
        return self.bits >= self.target
