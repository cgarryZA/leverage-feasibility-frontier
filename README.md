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