# Phase 2: broadcast simulator
Built: circular-Keplerian constellations (IRNSS-1B/1I IGSO at 55°E, NVS-01 GEO 129.5°E, 24-sat Galileo Walker -> 8 in view from IGI), nav data per interval, modelled message 10 (tag + delayed key), `World.broadcast()` + plan API `broadcast(t0, duration)`.
Timing: NavIC 48 s key period, 2-interval (96 s) delay -> 144 s TTFAF, matching ISRO. Galileo 30 s, 1-interval delay, 40-bit tags to 80 bits.
Failed first: IRNSS-1I placed on the far side of Earth (RAAN wrong); PRN collision between NavIC and Galileo (both use 2, 9, 10) broke A3 until keyed by (system, prn).
Root key repeats every 6 intervals (modelled; real systems spread it over minutes) so cold start costs something.
