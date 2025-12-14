from __future__ import annotations

from dataclasses import dataclass
from typing import Tuple
import numpy as np


@dataclass(frozen=True)
class CashflowModel:
    operating_cost_ratio: float  # c
    interest_only: bool = True

    def noi(self, gross_rent: float, occupancy: float) -> float:
        """Net operating income: (1-c) * R * occ."""
        c = float(self.operating_cost_ratio)
        return (1.0 - c) * float(gross_rent) * float(occupancy)

    def interest(self, rate: float, debt: float) -> float:
        """Interest-only debt service: r * D (annual)."""
        return float(rate) * float(debt)

    def net_cashflow(self, gross_rent: float, occupancy: float, rate: float, debt: float) -> float:
        return self.noi(gross_rent, occupancy) - self.interest(rate, debt)

    def dscr(self, gross_rent: float, occupancy: float, rate: float, debt: float) -> float:
        """
        DSCR = NOI / interest. If occupancy=0 => NOI=0; define DSCR=0.
        """
        noi = self.noi(gross_rent, occupancy)
        intr = self.interest(rate, debt)
        if intr <= 0:
            raise ValueError("Interest must be > 0 (check rate/debt).")
        return 0.0 if noi <= 0 else (noi / intr)


def ltv_grid(start: float, stop: float, step: float) -> np.ndarray:
    if step <= 0:
        raise ValueError("step must be > 0")
    n = int(np.floor((stop - start) / step + 1e-12)) + 1  # inclusive stop (tolerant)
    grid = start + step * np.arange(n, dtype=float)
    return np.round(grid, 10)


def implied_gross_yield(preset: dict) -> float:
    """
    Preset may contain:
      - gross_yield directly, OR
      - purchase_price_gbp + annual_rent_gbp
    """
    if "gross_yield" in preset and preset["gross_yield"] is not None:
        gy = float(preset["gross_yield"])
        if gy <= 0:
            raise ValueError("gross_yield must be > 0")
        return gy

    if "purchase_price_gbp" in preset and "annual_rent_gbp" in preset:
        price = float(preset["purchase_price_gbp"])
        rent = float(preset["annual_rent_gbp"])
        if price <= 0 or rent <= 0:
            raise ValueError("purchase_price_gbp and annual_rent_gbp must be > 0")
        return rent / price

    raise ValueError("Preset must define gross_yield or (purchase_price_gbp, annual_rent_gbp).")


def normalised_rent_from_yield(gross_yield: float, price: float = 1.0) -> float:
    """Normalize price=1 by default, so rent = yield."""
    return float(gross_yield) * float(price)


def normalised_debt_from_ltv(ltv: float, price: float = 1.0) -> float:
    """Normalize price=1 by default, so debt = LTV."""
    if ltv <= 0 or ltv >= 1.0:
        raise ValueError("ltv must be in (0, 1)")
    return float(ltv) * float(price)


def analytical_max_rate_for_dscr(
    operating_cost_ratio: float,
    gross_yield: float,
    ltv: float,
    occupancy: float,
    min_dscr: float = 1.0,
) -> float:
    """
    DSCR = NOI / (r*D) >= min_dscr
    NOI = (1-c)*R*occ, with R=gross_yield (price=1), D=ltv (price=1)
    => r <= (1-c)*R*occ / (min_dscr*D)
    """
    c = float(operating_cost_ratio)
    R = float(gross_yield)
    D = float(ltv)
    occ = float(occupancy)
    m = float(min_dscr)

    if D <= 0:
        raise ValueError("ltv must be > 0")
    if m <= 0:
        raise ValueError("min_dscr must be > 0")
    return (1.0 - c) * R * occ / (m * D)


def analytical_break_even_shock_bp(
    base_rate: float,
    max_rate: float,
) -> float:
    """
    Convert max permissible rate to max permissible shock (bp) above base_rate.
    Returns negative if already infeasible at base_rate.
    """
    return 10_000.0 * (float(max_rate) - float(base_rate))


def normalise_weights(values: np.ndarray, weights: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
    values = np.asarray(values, dtype=float)
    weights = np.asarray(weights, dtype=float)
    if values.ndim != 1 or weights.ndim != 1 or values.size != weights.size:
        raise ValueError("values and weights must be 1D arrays of equal length")
    if np.any(weights < 0):
        raise ValueError("weights must be non-negative")
    s = float(np.sum(weights))
    if s <= 0:
        raise ValueError("sum(weights) must be > 0")
    return values, (weights / s)
