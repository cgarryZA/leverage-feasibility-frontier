# Leverage Feasibility Frontier Under Rate and Occupancy Shocks

## Research Question
How much **leverage (LTV)** is admissible for a levered UK rental cashflow under explicit downside constraints:
- a **deterministic stress scenario** (rate shock × occupancy), and
- a **failure probability constraint** over a weighted scenario distribution?

This repo is **feasibility / constraints**, not return optimisation.

## Motivation (risk lens)
Two properties with identical “headline yields” can have very different robustness once leverage is introduced. The objective is to map:
- **safe vs unsafe leverage regions**,
- the **LTV frontier** implied by a required stress headroom,
- and how feasibility degrades under combined rate + vacancy pressure.

## Model & Assumptions
Annual, deterministic one-year cashflow:

- Revenue: `rev = R · occ`
- Opex: `opex = c · rev`
- NOI: `NOI = (1−c) · R · occ`
- Interest-only service: `int = r · D`
- Net cashflow: `CF = NOI − int`
- DSCR: `DSCR = NOI / int` (defined as 0 when `occ=0`)

**Failure rule**
A scenario fails if `CF < 0` or `DSCR < 1`.

**Scale-free calibration**
We normalise price to 1 and use `gross_yield` as `R/price`. For each LTV:
- `D = LTV`
- `R = gross_yield`
- `θ = R/D = gross_yield / LTV`

Presets live in `data/assumptions.yaml`:
- `durham_typical` (transferable heuristic yield)
- `rightmove_example` (frozen listing → implied yield)

## Method
1. Sweep `LTV ∈ [start, stop]`.
2. For each LTV:
   - Evaluate a **deterministic stress scenario** `(occ*, shock*)`.
   - Compute **p(failure)** over a weighted grid of shocks and occupancy regimes.
   - Compute the **analytic max shock** (bp) at stress occupancy where `DSCR=1`.

**Admissible LTV**
An LTV is admissible if it passes both:
- the deterministic stress test, and
- `p(failure) ≤ max_failure_probability`.

## Results
Outputs (saved to `results/`):
- `feasibility_frontier__<preset>.csv`
- `frontier__<preset>.png`
- `failure_probability__<preset>.png`

## Limitations
- Scenario weights are a modelling choice (stress distribution), not forecasts.
- Opex is proportional to realised rent (no fixed annual costs).
- One-year horizon only; refinancing dynamics are intentionally excluded (Project 4).
- Independence between occupancy and rate shocks is assumed for `p(failure)`.

## Reproducibility
```bash
python -m pip install -r requirements.txt

python src/simulate.py
python src/plots.py

python src/simulate.py --preset rightmove_example
python src/plots.py --preset rightmove_example

---

## `notes.md`

```md
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
