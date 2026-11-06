"""Simple circular-Keplerian constellations and a receiver near Delhi.

Modelled, not precise: circular orbits, no perturbations, GMST = 0 at t = 0.
"""
from dataclasses import dataclass

import numpy as np

MU = 3.986004418e14
OMEGA_E = 7.2921151467e-5
C = 299_792_458.0
WGS_A, WGS_F = 6378137.0, 1 / 298.257223563
WGS_E2 = WGS_F * (2 - WGS_F)
GEO_A = 42_164_000.0

DELHI_IGI = (28.5562, 77.1000, 230.0)  # Indira Gandhi International Airport


@dataclass(frozen=True)
class Orbit:
    a: float      # semi-major axis, m
    inc: float    # rad
    raan: float   # rad
    m0: float     # argument of latitude at t=0, rad

    def ecef(self, t: float) -> np.ndarray:
        u = self.m0 + np.sqrt(MU / self.a**3) * t
        x, y = self.a * np.cos(u), self.a * np.sin(u)
        ci, si, co, so = np.cos(self.inc), np.sin(self.inc), np.cos(self.raan), np.sin(self.raan)
        eci = np.array([x * co - y * ci * so, x * so + y * ci * co, y * si])
        th = OMEGA_E * t
        return np.array([eci[0] * np.cos(th) + eci[1] * np.sin(th),
                         -eci[0] * np.sin(th) + eci[1] * np.cos(th), eci[2]])


@dataclass(frozen=True)
class Satellite:
    system: str
    prn: int
    name: str
    orbit: Orbit


def lla_to_ecef(lat, lon, h):
    lat, lon = np.radians(lat), np.radians(lon)
    n = WGS_A / np.sqrt(1 - WGS_E2 * np.sin(lat) ** 2)
    return np.array([(n + h) * np.cos(lat) * np.cos(lon),
                     (n + h) * np.cos(lat) * np.sin(lon),
                     (n * (1 - WGS_E2) + h) * np.sin(lat)])


def ecef_to_lla(p):
    x, y, z = p
    lon = np.arctan2(y, x)
    r = np.hypot(x, y)
    lat = np.arctan2(z, r * (1 - WGS_E2))
    for _ in range(6):
        n = WGS_A / np.sqrt(1 - WGS_E2 * np.sin(lat) ** 2)
        h = r / np.cos(lat) - n
        lat = np.arctan2(z, r * (1 - WGS_E2 * n / (n + h)))
    return np.degrees(lat), np.degrees(lon), h


def elevation(sat, rx):
    lat, lon, _ = ecef_to_lla(rx)
    lat, lon = np.radians(lat), np.radians(lon)
    up = np.array([np.cos(lat) * np.cos(lon), np.cos(lat) * np.sin(lon), np.sin(lat)])
    d = sat - rx
    return np.degrees(np.arcsin(d @ up / np.linalg.norm(d)))


def navic_satellites():
    """The three working NavIC satellites (July 2026)."""
    d = np.radians
    return [
        Satellite("NAVIC", 2, "IRNSS-1B", Orbit(GEO_A, d(29), d(35), d(20))),
        Satellite("NAVIC", 9, "IRNSS-1I", Orbit(GEO_A, d(29), d(-145), d(200))),
        Satellite("NAVIC", 10, "NVS-01", Orbit(GEO_A, 0.0, 0.0, d(129.5))),
    ]


def walker(system, a, inc_deg, planes, per_plane, prn0, raan0=0.0, phase=1):
    sats, d = [], np.radians
    for p in range(planes):
        for s in range(per_plane):
            raan = d(raan0 + 360 * p / planes)
            m0 = d(360 * s / per_plane + 360 * phase * p / (planes * per_plane))
            prn = prn0 + p * per_plane + s
            sats.append(Satellite(system, prn, f"{system[0]}{prn:02d}", Orbit(a, d(inc_deg), raan, m0)))
    return sats


def galileo_satellites():
    return walker("GALILEO", 29_600_000.0, 56, 3, 8, 1, raan0=0)


def gps_satellites():
    return walker("GPS", 26_560_000.0, 55, 6, 4, 1, raan0=10)


def visible(sats, rx, t0=0.0, t1=0.0, mask=10.0):
    return [s for s in sats if min(elevation(s.orbit.ecef(t), rx) for t in (t0, t1)) > mask]
