"""Meaconing check: the time the signal claims vs. signed (Roughtime) local time."""


def replay_suspected(local_time: float, signal_time: float, threshold: float) -> bool:
    return abs(local_time - signal_time) > threshold
