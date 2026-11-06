"""The TESLA security condition.

A tag for interval i is only useful if, when it arrived, nobody could yet know
K(i). With worst-case clock error `uncertainty`, require
    local_rx_time + uncertainty < disclosure_time(i).
"""


def disclosure_time(interval: int, period: float, delay_intervals: int) -> float:
    return (interval + delay_intervals) * period


def key_not_yet_disclosed(local_rx_time: float, uncertainty: float, disclosure: float) -> bool:
    return local_rx_time + uncertainty < disclosure
