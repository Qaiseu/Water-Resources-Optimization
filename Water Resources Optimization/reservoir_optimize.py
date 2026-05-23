"""
reservoir_dispatch_7day.py
Solve a 7-day reservoir dispatch optimisation with scipy.optimize.minimize.

Maximises hydropower revenue by choosing daily releases subject to
storage continuity, storage bounds, and release limits.
"""

import numpy as np
import pandas as pd
from scipy.optimize import minimize, Bounds, NonlinearConstraint

# ============================================================================
# PHYSICAL CONSTANTS & RESERVOIR PARAMETERS
# ============================================================================

SEC_PER_DAY = 86400          # seconds in one day
N = 7                        # optimisation horizon (days)

# --- Reservoir storage limits (m³) ---
S0 = 500_000.0               # initial storage
S_MIN = 100_000.0            # dead storage (minimum)
S_MAX = 1_000_000.0          # full capacity

# --- Release limits (m³/s) ---
R_MIN = 10.0                 # minimum environmental flow
R_MAX = 100.0                # maximum discharge capacity

# --- Inflow forecast (m³/s) for days 1..7 ---
INFLOW = np.array([15.0, 12.0, 10.0, 8.0, 12.0, 15.0, 18.0])

# --- Electricity price forecast ($/MWh) ---
PRICE = np.array([0.08, 0.08, 0.08, 0.08, 0.10, 0.12, 0.10])

# --- Hydropower conversion parameters ---
ETA = 0.9                    # turbine–generator efficiency
RHO = 1000.0                 # water density (kg/m³)
G = 9.81                     # gravitational acceleration (m/s²)
HEAD_BASE = 10.0             # head at dead storage (m)
HEAD_RANGE = 40.0            # additional head when full (m)


# ============================================================================
# STORAGE TRAJECTORY  (derived state from decision variables)
# ============================================================================

def storage_trajectory(releases):
    """
    Return storage at start of each day S[0..N] (length N+1).

    Parameters
    ----------
    releases : ndarray of shape (N,)
        Daily average release in m³/s.

    Returns
    -------
    S : ndarray of shape (N+1,)
        Storage at the beginning of each day; S[0] = S0.
    """
    S = np.empty(N + 1)
    S[0] = S0
    for t in range(N):
        # Continuity: ΔS = (inflow - release) × seconds per day
        S[t + 1] = S[t] + (INFLOW[t] - releases[t]) * SEC_PER_DAY
    return S


# ============================================================================
# OBJECTIVE FUNCTION  (maximise hydropower revenue → minimise negative revenue)
# ============================================================================

def objective(releases):
    """
    Negative total hydropower revenue over the 7-day horizon.

    Revenue per day:
        P [MW]  = η ρ g Q H / 1e6
        E [MWh] = P × 24 h
        $       = E × price ($/MWh)

    Head H is a linear function of the average daily storage:
        H = HEAD_BASE + (S_avg - S_MIN) / (S_MAX - S_MIN) × HEAD_RANGE
    """
    S = storage_trajectory(releases)
    revenue = 0.0

    for t in range(N):
        # --- Effective head (proportional to average storage) ---
        S_avg = 0.5 * (S[t] + S[t + 1])
        head = HEAD_BASE + (S_avg - S_MIN) / (S_MAX - S_MIN) * HEAD_RANGE

        # --- Power (MW) and energy (MWh) ---
        power_mw = ETA * RHO * G * releases[t] * head / 1.0e6
        energy_mwh = power_mw * 24.0

        # --- Revenue contribution for this day ---
        revenue += energy_mwh * PRICE[t]

    return -revenue                       # minimiser sees negative revenue


# ============================================================================
# NONLINEAR STORAGE CONSTRAINTS
# ============================================================================

def storage_lower(releases):
    """Return S[t] - S_MIN >= 0 for all interior days t = 1..N."""
    return storage_trajectory(releases)[1:] - S_MIN


def storage_upper(releases):
    """Return S_MAX - S[t] >= 0 for all interior days t = 1..N."""
    return S_MAX - storage_trajectory(releases)[1:]


# ============================================================================
# REUSABLE OPTIMISATION FUNCTION
# ============================================================================

def optimize_reservoir(inflow=None):
    """
    Run the 7-day reservoir dispatch optimisation with a given inflow.

    Parameters
    ----------
    inflow : array-like of shape (N,), optional
        Daily inflow (m3/s).  Defaults to module-level INFLOW constant.

    Returns
    -------
    releases : ndarray of shape (N,)
        Optimal daily releases (m3/s).
    storage : ndarray of shape (N+1,)
        Storage trajectory (m3); storage[0] = S0.
    revenue : float
        Total hydropower revenue ($).
    result : OptimizeResult
        The full result from ``scipy.optimize.minimize``.
    """
    if inflow is None:
        inflow = INFLOW
    inflow = np.asarray(inflow, dtype=float)

    # Local closures capture the caller's inflow instead of module-level INFLOW
    def _traj(rels):
        S = np.empty(N + 1)
        S[0] = S0
        for t in range(N):
            S[t + 1] = S[t] + (inflow[t] - rels[t]) * SEC_PER_DAY
        return S

    def _obj(rels):
        S = _traj(rels)
        rev = 0.0
        for t in range(N):
            S_avg = 0.5 * (S[t] + S[t + 1])
            head = HEAD_BASE + (S_avg - S_MIN) / (S_MAX - S_MIN) * HEAD_RANGE
            power_mw = ETA * RHO * G * rels[t] * head / 1.0e6
            rev += power_mw * 24.0 * PRICE[t]
        return -rev

    def _lower(rels):
        return _traj(rels)[1:] - S_MIN

    def _upper(rels):
        return S_MAX - _traj(rels)[1:]

    guess = np.clip(inflow, R_MIN, R_MAX)
    bnds = Bounds([R_MIN] * N, [R_MAX] * N)
    cons = [
        NonlinearConstraint(_lower, 0, np.inf),
        NonlinearConstraint(_upper, 0, np.inf),
    ]
    res = minimize(
        _obj, guess, method="SLSQP", bounds=bnds, constraints=cons,
        options={"maxiter": 2000, "ftol": 1e-12},
    )
    rels = res.x
    S = _traj(rels)
    rev = -res.fun
    return rels, S, rev, res


# ============================================================================
# VALIDATION FUNCTION
# ============================================================================

def run_validation(releases, storage, revenue, inflow=None, price=None):
    """
    Check storage bounds, release bounds, mass balance, and revenue for a
    candidate solution.  Writes ``validation_report.txt`` and returns the
    report text.

    Parameters
    ----------
    releases : ndarray of shape (N,)
        Daily releases (m3/s).
    storage : ndarray of shape (N+1,)
        Storage trajectory (m3); storage[0] = initial.
    revenue : float
        Total revenue ($) reported by the optimiser.
    inflow : array-like of shape (N,), optional
        Inflows used.  Defaults to module-level INFLOW.
    price : array-like of shape (N,), optional
        Prices used.  Defaults to module-level PRICE.
    """
    if inflow is None:
        inflow = INFLOW
    if price is None:
        price = PRICE
    inflow = np.asarray(inflow, dtype=float)
    price = np.asarray(price, dtype=float)

    violations = []
    all_pass = True

    storage_ok = True
    for t in range(1, N + 1):
        if storage[t] < S_MIN - 1e-6:
            violations.append(f"  Storage[{t}] = {storage[t]:.2f} < S_MIN ({S_MIN})")
            storage_ok = False
        if storage[t] > S_MAX + 1e-6:
            violations.append(f"  Storage[{t}] = {storage[t]:.2f} > S_MAX ({S_MAX})")
            storage_ok = False

    release_ok = True
    for t in range(N):
        if releases[t] < R_MIN - 1e-6:
            violations.append(f"  Release[{t+1}] = {releases[t]:.2f} < R_MIN ({R_MIN})")
            release_ok = False
        if releases[t] > R_MAX + 1e-6:
            violations.append(f"  Release[{t+1}] = {releases[t]:.2f} > R_MAX ({R_MAX})")
            release_ok = False

    mb_ok = True
    mb_max_error = 0.0
    for t in range(N):
        expected = storage[t] + (inflow[t] - releases[t]) * SEC_PER_DAY
        error = abs(storage[t + 1] - expected)
        mb_max_error = max(mb_max_error, error)
        if error > 1e-6:
            violations.append(
                f"  Mass balance error at day {t+1}: "
                f"S[{t+1}] = {storage[t+1]:.6f}, expected {expected:.6f}, "
                f"error = {error:.2e}"
            )
            mb_ok = False

    rev_independent = 0.0
    for t in range(N):
        S_avg = 0.5 * (storage[t] + storage[t + 1])
        head = HEAD_BASE + (S_avg - S_MIN) / (S_MAX - S_MIN) * HEAD_RANGE
        power_mw = ETA * RHO * G * releases[t] * head / 1.0e6
        rev_independent += power_mw * 24.0 * price[t]

    rev_ok = abs(rev_independent - revenue) < 1e-6
    feasible = storage_ok and release_ok and mb_ok and rev_ok

    lines = []
    lines.append("-" * 50)
    lines.append("VALIDATION REPORT")
    lines.append("-" * 50)
    lines.append("")
    lines.append(f"  Storage Bounds Check  :  {'PASS' if storage_ok else 'FAIL'}")
    lines.append(f"  Release Bounds Check  :  {'PASS' if release_ok else 'FAIL'}")
    lines.append(f"  Mass Balance Check    :  {'PASS' if mb_ok else 'FAIL'}")
    lines.append(f"  Revenue Verification  :  {'PASS' if rev_ok else 'FAIL'}")
    lines.append("")
    lines.append(f"  Final Solution Feasible  :  {'YES' if feasible else 'NO'}")
    lines.append("")
    if violations:
        lines.append("  Violations found:")
        lines.append("")
        for v in violations:
            lines.append(v)
        lines.append("")
    else:
        lines.append("  No violations found.")
        lines.append("")
    lines.append("-" * 50)

    report_text = "\n".join(lines)
    with open("validation_report.txt", "w") as f:
        f.write(report_text)
    return report_text


# ============================================================================
# TRADE-OFF ANALYSIS FUNCTION
# ============================================================================

def run_tradeoff_analysis(inflow=None, price=None):
    """
    Run a weighted-objective trade-off study (revenue vs. ecological deficit)
    and save the Pareto frontier as ``tradeoff_analysis.png``.

    Parameters
    ----------
    inflow : array-like of shape (N,), optional
        Daily inflows used for every weight combination.
    price : array-like of shape (N,), optional
        Electricity prices.
    """
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    if inflow is None:
        inflow = INFLOW
    if price is None:
        price = PRICE
    inflow = np.asarray(inflow, dtype=float)
    price = np.asarray(price, dtype=float)

    ECO_TARGET = 25.0

    def _trade_rev(rels):
        S = storage_trajectory(rels)
        r = 0.0
        for t in range(N):
            S_avg = 0.5 * (S[t] + S[t + 1])
            head = HEAD_BASE + (S_avg - S_MIN) / (S_MAX - S_MIN) * HEAD_RANGE
            power_mw = ETA * RHO * G * rels[t] * head / 1.0e6
            r += power_mw * 24.0 * price[t]
        return r

    def _trade_eco(rels):
        return np.sum(np.maximum(0.0, ECO_TARGET - rels))

    weight_pairs = [(round(i * 0.1, 1), round(1.0 - i * 0.1, 1))
                    for i in range(11)]

    eco_vals = []
    rev_vals = []

    for w_rev, w_eco in weight_pairs:
        def _obj(rels, wr=w_rev, we=w_eco):
            return -(wr * _trade_rev(rels)) + (we * _trade_eco(rels))
        guess = np.clip(inflow, R_MIN, R_MAX)
        bnds = Bounds([R_MIN] * N, [R_MAX] * N)

        def _lower(rels):
            return storage_trajectory(rels)[1:] - S_MIN
        def _upper(rels):
            return S_MAX - storage_trajectory(rels)[1:]

        cons = [
            NonlinearConstraint(_lower, 0, np.inf),
            NonlinearConstraint(_upper, 0, np.inf),
        ]
        res = minimize(_obj, guess, method="SLSQP", bounds=bnds,
                       constraints=cons, options={"maxiter": 2000, "ftol": 1e-12})
        r = res.x
        eco_vals.append(_trade_eco(r))
        rev_vals.append(_trade_rev(r))

    sorted_idx = np.argsort(eco_vals)
    eco_sorted = np.array(eco_vals)[sorted_idx]
    rev_sorted = np.array(rev_vals)[sorted_idx]
    labels_sorted = np.array(
        [f"{weight_pairs[i][0]:.1f}/{weight_pairs[i][1]:.1f}"
         for i in sorted_idx]
    )

    fig, ax = plt.subplots(figsize=(8, 5))
    ax.plot(eco_sorted, rev_sorted, "bo-", markersize=6, linewidth=1.5,
            label="Pareto frontier")
    for i, lbl in enumerate(labels_sorted):
        ax.annotate(lbl, (eco_sorted[i], rev_sorted[i]),
                    textcoords="offset points", xytext=(0, 10), fontsize=7,
                    ha="center")
    ax.set_xlabel("Total Ecological Deficit  (m3/s)")
    ax.set_ylabel("Total Hydropower Revenue  ($)")
    ax.set_title("Trade-off:  Hydropower Revenue vs. Ecological Protection")
    ax.grid(True, alpha=0.3)
    ax.legend()
    plt.tight_layout()
    plt.savefig("tradeoff_analysis.png", dpi=150)
    plt.close(fig)


# ============================================================================
# MODULE-LEVEL SOLVER SETUP & OUTPUT  (runs only when executed directly)
# ============================================================================

if __name__ == "__main__":

    # --- Initial guess: release follows inflow (clipped to feasible range) ---
    R_guess = np.clip(INFLOW, R_MIN, R_MAX)

    # --- Box bounds on decision variables (m³/s) ---
    bounds = Bounds([R_MIN] * N, [R_MAX] * N)

    # --- Nonlinear constraints (storage must stay within physical limits) ---
    nonlinear_constraints = [
        NonlinearConstraint(storage_lower, 0, np.inf),
        NonlinearConstraint(storage_upper, 0, np.inf),
    ]

    # --- Solve using SLSQP ---
    result = minimize(
        objective,
        R_guess,
        method="SLSQP",
        bounds=bounds,
        constraints=nonlinear_constraints,
        options={"maxiter": 2000, "ftol": 1e-12},
    )


    # ============================================================================
    # POST-PROCESS
    # ============================================================================

    R_opt = result.x                              # optimal releases (m³/s)
    S_opt = storage_trajectory(R_opt)             # resulting storage (m³)
    total_revenue = -result.fun                   # back to positive revenue ($)

    # Print header
    print("=" * 72)
    print("  7-DAY RESERVOIR DISPATCH OPTIMISATION  (scipy.optimize, SLSQP)")
    print("=" * 72)
    print(f"  Status          :  {result.message}")
    print(f"  Iterations      :  {result.nit}")
    print(f"  Function calls  :  {result.nfev}")
    print()

    # Print daily table
    print(f"  {'Day':>4}  {'Inflow':>8}  {'Release':>9}  {'Storage':>10}  "
          f"{'Price':>7}  {'Revenue':>9}")
    print(f"  {'----':>4}  {'------':>8}  {'-------':>9}  {'-------':>10}  "
          f"{'-----':>7}  {'-------':>9}")

    day_revenues = []
    csv_data = []
    for t in range(N):
        S_avg = 0.5 * (S_opt[t] + S_opt[t + 1])
        head = HEAD_BASE + (S_avg - S_MIN) / (S_MAX - S_MIN) * HEAD_RANGE
        power_mw = ETA * RHO * G * R_opt[t] * head / 1.0e6
        energy_mwh = power_mw * 24.0
        rev = energy_mwh * PRICE[t]
        day_revenues.append(rev)
        csv_data.append({
            "Day": t + 1,
            "Inflow": round(INFLOW[t], 2),
            "Optimal Release": round(R_opt[t], 2),
            "Storage": round(S_opt[t + 1], 2),
            "Energy Price": PRICE[t],
            "Daily Revenue": round(rev, 2),
        })
        print(f"  {t+1:>4d}  {INFLOW[t]:>8.1f}  {R_opt[t]:>9.2f}  "
              f"{S_opt[t+1]:>10.0f}  {PRICE[t]:>7.2f}  {rev:>9.2f}")

    print(f"  {'----':>4}  {'------':>8}  {'-------':>9}  {'-------':>10}  "
          f"{'-----':>7}  {'-------':>9}")

    # Print totals
    print(f"  {'TOTAL':>4}  {'':>8}  {'':>9}  {'':>10}  {'':>7}  "
          f"{sum(day_revenues):>9.2f}")
    print()

    # Extra summary lines
    print(f"  Initial storage       : {S0:>10.0f} m3")
    print(f"  Final storage         : {S_opt[-1]:>10.0f} m3")
    print(f"  Minimum storage       : {S_opt[1:].min():>10.0f} m3  "
          f"(limit {S_MIN:>10.0f})")
    print(f"  Maximum storage       : {S_opt[1:].max():>10.0f} m3  "
          f"(limit {S_MAX:>10.0f})")
    print(f"  Total revenue         : ${total_revenue:>9.2f}")
    print("=" * 72)

    # ========================================================================
    # EXPORT OPTIMAL SCHEDULE TO CSV
    # ========================================================================

    df = pd.DataFrame(csv_data)
    df.to_csv("optimal_schedule.csv", index=False)
    print(f"\n  >>  optimal_schedule.csv written ({len(df)} rows)")

    print()
    print(run_validation(R_opt, S_opt, total_revenue))
    print("\n  >>  validation_report.txt written")

    run_tradeoff_analysis()
    print("  >>  tradeoff_analysis.png saved")