import pytest

from nma.attacks.toolkit import a8_bruteforce
from nma.scenario import run

# (attack, severity): hardened receiver must not present a wrong position
DEFENDED = [("A1", 50), ("A2", 1), ("A3", 10), ("A4", 5), ("A5", 10), ("A6", 5), ("A6", 30), ("A7", 1)]


@pytest.mark.parametrize("attack,sev", DEFENDED)
def test_hardened_holds(attack, sev):
    m = run(attack, sev, "hardened").metrics
    assert m["fooled_frac"] == 0 and m["detected"]


@pytest.mark.parametrize("attack,sev", [("A1", 50), ("A4", 5), ("A6", 5), ("A7", 1)])
def test_naive_is_fooled(attack, sev):
    assert run(attack, sev, "naive").metrics["fooled_frac"] > 0.5


def test_clock_drag_beats_tesla_alone():
    assert run("A5", 10, "tesla").metrics["fooled_frac"] > 0.5


def test_tiny_replay_is_an_honest_loss():
    assert run("A6", 0.2, "hardened").metrics["fooled_frac"] > 0.5


def test_bruteforce_rates():
    assert 2 <= a8_bruteforce(8, 2000, seed=1) <= 20          # ~2000/256 = 7.8
    assert a8_bruteforce(8, 2000, accumulate=2, seed=1) <= 2  # ~2000/65536
