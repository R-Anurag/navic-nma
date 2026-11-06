"""Local Roughtime-style server that signs (nonce, midpoint, radius) with Ed25519.

Follows draft-ietf-ntp-roughtime in spirit: the client sends a random nonce,
the server signs it together with its time and an uncertainty radius, using the
draft's signature context string. Skipped: delegation certificates, Merkle
batching and the tag/value wire encoding.
"""
import random
import struct

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

CONTEXT = b"RoughTime v1 response signature\x00"
RESP = ">32sqI"  # nonce, midpoint (microseconds), radius (microseconds)


class MockRoughtimeServer:
    def __init__(self, seed=0, radius=0.5, error=None):
        rng = random.Random(seed)
        self.sk = Ed25519PrivateKey.from_private_bytes(rng.randbytes(32))
        self.public_key = self.sk.public_key()
        self.radius = radius
        # the server's own error, always inside its stated radius
        self.error = rng.uniform(-0.8 * radius, 0.8 * radius) if error is None else error

    def respond(self, nonce: bytes, true_time: float) -> tuple[bytes, bytes]:
        body = struct.pack(RESP, nonce, int((true_time + self.error) * 1e6), int(self.radius * 1e6))
        return body, self.sk.sign(CONTEXT + body)
