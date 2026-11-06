"""Client side: verify signature and nonce, return (midpoint, radius) in seconds."""
import os
import struct

from cryptography.exceptions import InvalidSignature

from .mock_server import CONTEXT, RESP


class TimeRejected(Exception):
    pass


def new_nonce() -> bytes:
    return os.urandom(32)


def verify_response(public_key, nonce: bytes, body: bytes, sig: bytes) -> tuple[float, float]:
    try:
        public_key.verify(sig, CONTEXT + body)
    except InvalidSignature:
        raise TimeRejected("bad signature (forged time)")
    got_nonce, mid_us, rad_us = struct.unpack(RESP, body)
    if got_nonce != nonce:
        raise TimeRejected("nonce mismatch (replayed time)")
    return mid_us / 1e6, rad_us / 1e6


def query(server, true_time: float, rtt: float = 0.05) -> tuple[float, float]:
    """Ask the server; the extra rtt/2 widens the radius as in the draft."""
    nonce = new_nonce()
    body, sig = server.respond(nonce, true_time)
    mid, rad = verify_response(server.public_key, nonce, body, sig)
    return mid, rad + rtt / 2
