# Phase 6: experiments
`make experiments` (~2 min): 1,890 runs -> results/attack_matrix.csv, a8_bruteforce.csv, performance.csv. `make figures` -> 7 PNGs.
Headline: hardened fooled 0% on A1-A7 at headline severity. TESLA-only fooled on A4 (clock >2 s off), A5 (drag >2 s) and A6 (replay <30 s).
Expected losses measured: A6 at 0.3 s fools everyone; detection is 45% at 1 s, 100% from 1.5 s. A7 partial jamming leaves >=4 authenticated satellites, so the fix stays correct (not "detected", not fooled).
Fooled = fraction of post-attack epochs where the receiver presents a fix (Authenticated or no checks) more than 100 m from truth.
