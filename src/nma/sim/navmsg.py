"""Navigation data per satellite per interval: time of week + broadcast ephemeris.

Modelled layout (not an ICD): the ephemeris is the circular orbit itself.
"""
import struct
from dataclasses import dataclass

from .constellation import Orbit

_FMT = ">8sHIdddd"  # system, prn, interval, a, inc, raan, m0


@dataclass(frozen=True)
class NavData:
    system: str
    prn: int
    interval: int
    orbit: Orbit

    def to_bytes(self) -> bytes:
        o = self.orbit
        return struct.pack(_FMT, self.system.encode(), self.prn, self.interval, o.a, o.inc, o.raan, o.m0)

    @classmethod
    def from_bytes(cls, b: bytes) -> "NavData":
        sysname, prn, interval, a, inc, raan, m0 = struct.unpack(_FMT, b)
        return cls(sysname.rstrip(b"\0").decode(), prn, interval, Orbit(a, inc, raan, m0))

    @property
    def bits(self) -> int:
        return struct.calcsize(_FMT) * 8
