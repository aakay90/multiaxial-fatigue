"""Power-law calibration using a damage-space shift that always stays well defined."""

from __future__ import annotations
import numpy as np


def fit_power_law_with_survival_std(Nf, DP, stdnum=0.0):
    """Fit DP = A*Nf**b while avoiding inversion of flat or shallow curves.

    STD is the scatter expressed in ln(N); it is undefined for fits that are
    flat or increasing. STD_ln_DP is always evaluated in ln(DP). When the
    slope is negative, shifting DP downwards is algebraically the same as the
    conventional life shift. Flat and positive slopes follow that same
    downward DP-space rule, and must not be read as a life survival
    probability.
    """
    Nf = np.asarray(Nf, dtype=float).ravel()
    DP = np.asarray(DP, dtype=float).ravel()
    if Nf.shape != DP.shape:
        raise ValueError("the life and damage arrays must have the same length")
    if not np.isfinite(stdnum) or stdnum < 0:
        raise ValueError("the number of standard deviations must be finite and nonnegative")
    keep = np.isfinite(Nf) & np.isfinite(DP) & (Nf > 0) & (DP > 0)
    Nf, DP = Nf[keep], DP[keep]
    degenerate = dict(
        A=np.nan,
        b=np.nan,
        STD=np.nan,
        A_surv=np.nan,
        STD_ln_DP=np.nan,
        n=int(Nf.size),
        R2_log=np.nan,
    )
    if Nf.size < 2 or np.ptp(np.log(Nf)) < 1e-12:
        return degenerate
    log_N, log_DP = np.log(Nf), np.log(DP)
    slope, intercept = np.polyfit(log_N, log_DP, 1)
    if abs(slope) < 1e-12:
        slope, intercept = 0.0, float(np.mean(log_DP))
    leftover = log_DP - (intercept + slope * log_N)
    sigma_dp = float(np.std(leftover, ddof=1))
    sigma_life = sigma_dp / abs(slope) if slope < 0 else np.nan
    ss_total = float(np.sum((log_DP - np.mean(log_DP)) ** 2))
    r2 = 1 - float(np.sum(leftover**2)) / ss_total if ss_total > 1e-24 else np.nan
    return dict(
        A=float(np.exp(intercept)),
        b=float(slope),
        STD=sigma_life,
        STD_ln_DP=sigma_dp,
        A_surv=float(np.exp(intercept - stdnum * sigma_dp)),
        n=int(Nf.size),
        R2_log=r2,
    )
