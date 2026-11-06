"""Least-squares position + clock bias (Gauss-Newton)."""
import numpy as np


def solve(sat_pos: np.ndarray, pr: np.ndarray, iters: int = 15):
    """Returns (ecef position, clock bias in metres, residual rms)."""
    x = np.zeros(4)
    for _ in range(iters):
        d = sat_pos - x[:3]
        r = np.linalg.norm(d, axis=1)
        res = pr - (r + x[3])
        h = np.hstack([-d / r[:, None], np.ones((len(r), 1))])
        dx = np.linalg.lstsq(h, res, rcond=None)[0]
        x += dx
        if np.linalg.norm(dx[:3]) < 1e-4:
            break
    d = sat_pos - x[:3]
    res = pr - (np.linalg.norm(d, axis=1) + x[3])
    return x[:3], x[3], float(np.sqrt(np.mean(res**2)))
