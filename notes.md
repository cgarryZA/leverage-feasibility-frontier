# Notes — Leverage Feasibility Frontier

## What this repo is (and isn’t)
This repo is a **constraint-based feasibility analysis**:
- it does not forecast rates or occupancy,
- it does not optimise ROI,
- it maps “what breaks” as leverage increases.

## Why the frontier is analytic
With proportional opex and interest-only debt, DSCR takes a separable form:

NOI = (1 − c) · R · occ  
interest = r · D

DSCR = NOI / interest  
     = (1 − c) · R · occ / (r · D)

So for a required minimum DSCR (typically 1.0),

DSCR ≥ DSCR_min  ⇒  r ≤ (1 − c) · R · occ / (DSCR_min · D)

With normalised price = 1:
- R = gross_yield
- D = LTV

So:

r_max(LTV, occ) = (1 − c) · gross_yield · occ / (DSCR_min · LTV)

Converting to a base-rate shock:

shock_max_bp = 10,000 · (r_max − base_rate)

This is the plotted “frontier”: for each LTV, how much shock is tolerable at the stress occupancy.

## Probabilistic feasibility
We also impose an ex-ante constraint:

p(failure) ≤ α

where failure means:
- CF < 0 OR DSCR < 1

and p(failure) is computed over a weighted grid of (shock, occupancy) scenarios.
Weights are modelling choices to represent “stress likelihood”, not empirical frequencies.

## Why CF=0 and DSCR=1 coincide here
Under proportional opex:
CF = NOI − rD
DSCR = NOI / (rD)

CF = 0  ⇔ NOI = rD  ⇔ DSCR = 1

So feasibility boundaries overlap. They diverge if you add:
- fixed annual costs (insurance, council tax for HMOs, compliance costs),
- amortisation,
- taxes, void re-letting costs, etc.

Those are intentionally excluded here to keep the feasibility geometry transparent.