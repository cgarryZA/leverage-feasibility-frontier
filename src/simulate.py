from __future__ import annotations

import os
import argparse
import yaml
import numpy as np
import pandas as pd

from model import (
    CashflowModel,
    ltv_grid,
    implied_gross_yield,
    normalised_rent_from_yield,
    normalised_debt_from_ltv,
    analytical_max_rate_for_dscr,
    analytical_break_even_shock_bp,
    normalise_weights,
)

# ---------- PATH HARDENING ----------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ASSUMPTIONS_PATH = os.path.join(BASE_DIR, "..", "data", "assumptions.yaml")
RESULTS_DIR = os.path.join(BASE_DIR, "..", "results")
# ----------------------------------


def load_assumptions(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def select_preset(assumptions: dict, preset_name: str | None) -> tuple[str, dict]:
    calib = assumptions.get("calibration", {})
    presets = calib.get("presets", {})
    default_name = calib.get("default_preset", None)

    name = preset_name if preset_name is not None else default_name
    if name is None:
        raise ValueError("No preset provided and calibration.default_preset is missing.")

    if name not in presets:
        raise ValueError(f"Unknown preset '{name}'. Available: {list(presets.keys())}")

    return name, presets[name]


def failure_probability_over_distribution(
    model: CashflowModel,
    gross_rent: float,
    debt: float,
    base_rate: float,
    shock_bp_values: np.ndarray,
    shock_bp_weights: np.ndarray,
    occ_values: np.ndarray,
    occ_weights: np.ndarray,
    min_dscr: float,
    min_cashflow: float,
) -> float:
    # Normalize weights defensively
    shock_bp_values, shock_bp_weights = normalise_weights(shock_bp_values, shock_bp_weights)
    occ_values, occ_weights = normalise_weights(occ_values, occ_weights)

    # Joint weights (independence assumption)
    joint_w = np.outer(occ_weights, shock_bp_weights)  # [occ, shock]

    # Evaluate grid
    fail_w = 0.0
    for i, occ in enumerate(occ_values):
        for j, shock_bp in enumerate(shock_bp_values):
            rate = float(base_rate) + float(shock_bp) / 10_000.0
            cf = model.net_cashflow(gross_rent, occ, rate, debt)
            dscr = model.dscr(gross_rent, occ, rate, debt)
            failed = (dscr < float(min_dscr)) or (cf < float(min_cashflow))
            if failed:
                fail_w += float(joint_w[i, j])

    return float(fail_w)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--preset", type=str, default=None, help="Calibration preset name from assumptions.yaml")
    parser.add_argument("--base-rate", type=float, default=None, help="Override base interest rate (decimal, e.g. 0.05)")
    args = parser.parse_args()

    assumptions = load_assumptions(ASSUMPTIONS_PATH)

    # Base params
    c = float(assumptions["base_cashflow"]["operating_cost_ratio"])
    yaml_base_rate = float(assumptions.get("financing", {}).get("base_interest_rate_value", 0.05))
    base_rate = float(args.base_rate) if args.base_rate is not None else yaml_base_rate

    constraints = assumptions["risk_constraints"]
    min_dscr = float(constraints["min_dscr"])
    min_cf = float(constraints["min_cashflow"])
    max_fail_prob = float(constraints["max_failure_probability"])
    stress_occ = float(constraints["stress_test"]["occupancy"])
    stress_shock_bp = float(constraints["stress_test"]["rate_shock_bp"])

    # Preset (defines gross yield)
    preset_name, preset = select_preset(assumptions, args.preset)
    gross_yield = implied_gross_yield(preset)

    # Sweep grid
    sweep = assumptions["ltv_sweep"]
    ltvs = ltv_grid(float(sweep["start"]), float(sweep["stop"]), float(sweep["step"]))

    # Distribution
    dist = assumptions["stress_distribution"]
    shock_bp_values = np.array(dist["interest_rate_shock_bp"]["values"], dtype=float)
    shock_bp_weights = np.array(dist["interest_rate_shock_bp"]["weights"], dtype=float)
    occ_values = np.array(dist["occupancy_multiplier"]["values"], dtype=float)
    occ_weights = np.array(dist["occupancy_multiplier"]["weights"], dtype=float)

    model = CashflowModel(operating_cost_ratio=c, interest_only=True)

    rows = []
    for ltv in ltvs:
        R = normalised_rent_from_yield(gross_yield, price=1.0)
        D = normalised_debt_from_ltv(float(ltv), price=1.0)

        # Deterministic stress scenario check
        stress_rate = base_rate + stress_shock_bp / 10_000.0
        stress_cf = model.net_cashflow(R, stress_occ, stress_rate, D)
        stress_dscr = model.dscr(R, stress_occ, stress_rate, D)
        passes_stress = (stress_cf >= min_cf) and (stress_dscr >= min_dscr)

        # Probability of failure over the joint scenario distribution
        p_fail = failure_probability_over_distribution(
            model=model,
            gross_rent=R,
            debt=D,
            base_rate=base_rate,
            shock_bp_values=shock_bp_values,
            shock_bp_weights=shock_bp_weights,
            occ_values=occ_values,
            occ_weights=occ_weights,
            min_dscr=min_dscr,
            min_cashflow=min_cf,
        )
        passes_prob = p_fail <= max_fail_prob

        # Worst-case over distribution support (not weighted)
        worst_cf = np.inf
        worst_dscr = np.inf
        for occ in occ_values:
            for shock_bp in shock_bp_values:
                rate = base_rate + float(shock_bp) / 10_000.0
                cf = model.net_cashflow(R, occ, rate, D)
                ds = model.dscr(R, occ, rate, D)
                worst_cf = min(worst_cf, cf)
                worst_dscr = min(worst_dscr, ds)

        # "Max tolerable shock" at the stress occupancy (analytic)
        max_rate = analytical_max_rate_for_dscr(
            operating_cost_ratio=c,
            gross_yield=gross_yield,
            ltv=float(ltv),
            occupancy=stress_occ,
            min_dscr=min_dscr,
        )
        max_shock_bp = analytical_break_even_shock_bp(base_rate, max_rate)

        admissible = bool(passes_stress and passes_prob)

        rows.append(
            {
                "preset": preset_name,
                "gross_yield": gross_yield,
                "base_rate": base_rate,
                "ltv": float(ltv),
                "theta_rent_to_debt": (gross_yield / float(ltv)),
                "stress_occ": stress_occ,
                "stress_shock_bp": stress_shock_bp,
                "stress_rate": stress_rate,
                "stress_cashflow": float(stress_cf),
                "stress_dscr": float(stress_dscr),
                "worst_cashflow_on_support": float(worst_cf),
                "worst_dscr_on_support": float(worst_dscr),
                "failure_probability": float(p_fail),
                "max_failure_probability": max_fail_prob,
                "max_shock_bp_at_stress_occ_dscr1": float(max_shock_bp),
                "passes_stress": passes_stress,
                "passes_probability": passes_prob,
                "admissible": admissible,
            }
        )

    df = pd.DataFrame(rows)

    os.makedirs(RESULTS_DIR, exist_ok=True)
    out_csv = os.path.join(RESULTS_DIR, f"feasibility_frontier__{preset_name}.csv")
    df.to_csv(out_csv, index=False)

    # Helpful console snapshot
    print(df[["ltv", "failure_probability", "passes_stress", "passes_probability", "admissible"]].head())
    print(f"Saved: {out_csv}")


if __name__ == "__main__":
    main()
