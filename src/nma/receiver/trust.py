"""Trust policy: what the receiver tells the pilot about its own position.

Deviation from the plan: a failed tag drops that satellite and raises an alarm,
but does not by itself poison a fix computed from the remaining satellites.
"""
AUTHENTICATED, DEGRADED, UNTRUSTED, UNCHECKED = "Authenticated", "Degraded", "Untrusted", "Unchecked"


def trust_level(mode: str, n_auth: int, time_ok: bool) -> str:
    if mode == "naive":
        return UNCHECKED
    if (mode == "hardened" and not time_ok) or n_auth == 0:
        return UNTRUSTED
    return AUTHENTICATED if n_auth >= 4 else DEGRADED
