# navic-nma

This project simulates a satellite-navigation receiver at Delhi airport. The receiver rejects spoofed positions. It uses three defences:

- TESLA authentication for NavIC (a model of the 2023 ISRO proposal) and for Galileo OSNMA.
- Signed time from a Roughtime-style server.
- A replay check.

The project then attacks the receiver in eight different ways and measures the results. All work is software only. The project does not transmit radio signals.

## Run

```
uv venv .venv && uv pip install --python .venv/bin/python -e '.[test]'
make test          # 37 tests
make experiments   # approximately 2 min -> results/*.csv
make figures       # -> figures/*.png
make demo          # 5-step demo in the terminal
make demo-html     # -> demo/demo.html (opens in any browser, works offline)
```

To show the slides, open `slides/index.html`. Use the arrow keys to move between slides.

To run one attack manually, use this command:

```
PYTHONPATH=src .venv/bin/python -m nma.attacks A6 --severity 5
```

## Results

Each attack ran with 5 random seeds. Attack A6 ran with 40 seeds. "Fooled" is the percentage of time after the attack starts that the receiver shows a wrong position (more than 100 m from the true position) as valid.

| Attack | Naive receiver | TESLA only | Hardened receiver |
|---|---|---|---|
| A1: change ephemeris by 50 km | fooled 92% | drops satellites, 0% | drops satellites, 0% |
| A2: send a false key | no effect | detects | detects |
| A3: send a false root key | fooled 93% | detects | detects |
| A4: reuse old keys, clock 5 s slow | fooled 92% | fooled 92% | 0% |
| A5: move the clock by 10 s | fooled 85% | fooled 85% | 0% |
| A6: replay with 5 s delay | fooled 100% | fooled 100% | 0% |
| A6: replay with 0.3 s delay | fooled 100% | fooled 100% | **fooled 100%** (expected loss) |
| A7: jam all authenticated satellites | fooled 100% | Untrusted, 0% | Untrusted, 0% |
| A8: guess tags at random | not applicable | 2^-32 per guess (NavIC) | 2^-80 per guess (Galileo, 2 tags) |

Costs:

- One tag check takes 1.8 µs.
- Authentication uses 3.3 bit/s for each NavIC satellite.
- The receiver authenticates NavIC satellites 144 s after it starts. This value agrees with the ISRO value.

## Layout

| Folder or file | Contents |
|---|---|
| `src/nma/tesla` | Cryptography core |
| `src/nma/sim` | Satellite orbits and broadcast stream |
| `src/nma/time` | Receiver clock and Roughtime client and server |
| `src/nma/receiver` | Satellite state, position solver, trust policy, replay check |
| `src/nma/attacks/toolkit.py` | Attacks A1 to A8 |
| `src/nma/scenario.py` | One scored scenario |
| `src/nma/demo.py` | Terminal demo and HTML demo |
| `experiments/` | Experiment matrix and figures |
| `notes/` | Notes for each project phase |

## Limits of the model

These parts are models, not real systems:

- The NavIC message layout. The ISRO specification is not public.
- The satellite orbits. The orbits are circular.
- The Roughtime server. It is a local mock server.

The project simulates Galileo with the same TESLA library. It does not use OSNMAlib.
