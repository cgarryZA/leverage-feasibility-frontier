from __future__ import annotations

import os
import argparse
import yaml
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

# ---------- PATH HARDENING ----------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ASSUMPTIONS_PATH = os.path.join(BASE_DIR, "..", "data", "assumptions.yaml")
RESULTS_DIR = os.path.join(BASE_DIR, "..", "results")
# ----------------------------------


def load_assumptions(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--preset", type=str, default=None, help="Preset name (must match what you simulated)")
    args = parser.parse_args()

    assumptions = load_assumptions(ASSUMPTIONS_PATH)
    default_preset = assumptions.get("calibration", {}).get("default_preset", None)
    preset = args.preset if args.preset is not None else default_preset
    if preset is None:
        raise ValueError("No preset provided and calibration.default_preset is missing.")

    csv_path = os.path.join(RESULTS_DIR, f"feasibility_frontier__{preset}.csv")
    if not os.path.exists(csv_path):
        raise FileNotFoundError(f"Missing results CSV: {csv_path}. Run src/simulate.py first.")

    df = pd.read_csv(csv_path)

    max_fail_prob = float(df["max_failure_probability"].iloc[0])
    stress_shock_bp = float(df["stress_shock_bp"].iloc[0])

    os.makedirs(RESULTS_DIR, exist_ok=True)

    # -----------------------
    # Plot 1: Feasibility frontier
    # LTV vs max shock tolerated (DSCR=1) at the stress occupancy
    # -----------------------
    plt.figure(figsize=(9, 5))
    plt.plot(df["ltv"], df["max_shock_bp_at_stress_occ_dscr1"], linewidth=2)

    # Mark the repo's chosen stress point
    plt.axhline(stress_shock_bp, linestyle="--", linewidth=1)
    plt.text(df["ltv"].min(), stress_shock_bp, f"  stress shock = {int(stress_shock_bp)}bp", va="bottom")

    plt.xlabel("LTV")
    plt.ylabel("Max tolerable shock at stress occupancy (bp)")
    plt.title(f"Leverage Feasibility Frontier — {preset}")
    plt.tight_layout()

    out1 = os.path.join(RESULTS_DIR, f"frontier__{preset}.png")
    plt.savefig(out1)
    plt.close()

    # -----------------------
    # Plot 2: Failure probability vs LTV
    # -----------------------
    plt.figure(figsize=(9, 5))
    plt.plot(df["ltv"], df["failure_probability"], linewidth=2)
    plt.axhline(max_fail_prob, linestyle="--", linewidth=1)
    plt.text(df["ltv"].min(), max_fail_prob, f"  max allowed p(fail) = {max_fail_prob:.2f}", va="bottom")

    # Optional: mark admissible points
    admissible = df["admissible"].astype(bool).values
    plt.scatter(df["ltv"][admissible], df["failure_probability"][admissible], s=20)

    plt.xlabel("LTV")
    plt.ylabel("Failure probability over scenario distribution")
    plt.title(f"Constraint Check: p(failure) vs LTV — {preset}")
    plt.tight_layout()

    out2 = os.path.join(RESULTS_DIR, f"failure_probability__{preset}.png")
    plt.savefig(out2)
    plt.close()

    print(f"Saved plots:\n- {out1}\n- {out2}")


if __name__ == "__main__":
    main()
