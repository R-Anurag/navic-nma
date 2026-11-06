"""Modelled NavIC NMA secondary message (subframe 4, message ID 10).

ISRO's interface spec is not public. Field sizes follow the published 2023
parameters (32-bit tag, 128-bit key); the rest of the layout is modelled.
"""
import json
import struct
from dataclasses import dataclass

MSG_ID = 10
KEY_BYTES = 16


@dataclass(frozen=True)
class NmaMessage:
    prn: int
    interval: int
    tag: int | None          # tag over this interval's nav data (None = key-only)
    tag_bits: int
    key_index: int | None    # delayed key disclosure
    key: bytes | None

    def to_bytes(self) -> bytes:
        tb = (self.tag_bits + 7) // 8
        tag = (self.tag or 0).to_bytes(tb, "big")
        flags = (self.tag is not None) | ((self.key is not None) << 1)
        return (struct.pack(">BBHIBI", MSG_ID, flags, self.prn, self.interval, self.tag_bits,
                            self.key_index or 0) + tag + (self.key or bytes(KEY_BYTES)))

    @classmethod
    def from_bytes(cls, b: bytes) -> "NmaMessage":
        msg_id, flags, prn, interval, tag_bits, key_index = struct.unpack(">BBHIBI", b[:13])
        assert msg_id == MSG_ID
        tb = (tag_bits + 7) // 8
        tag = int.from_bytes(b[13:13 + tb], "big") if flags & 1 else None
        key = b[13 + tb:13 + tb + KEY_BYTES] if flags & 2 else None
        return cls(prn, interval, tag, tag_bits, key_index if key else None, key)

    @property
    def auth_bits(self) -> int:
        """Bits that exist only for authentication (tag + key)."""
        return (self.tag_bits if self.tag is not None else 0) + (128 if self.key else 0)


@dataclass(frozen=True)
class RootKeyMessage:
    system: str
    root: bytes
    params: dict
    signature: bytes

    def to_bytes(self) -> bytes:
        return self.system.encode().ljust(8, b"\0") + self.root + self.signature + json.dumps(self.params, sort_keys=True).encode()
