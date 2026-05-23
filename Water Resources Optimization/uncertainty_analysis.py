"""
uncertainty_analysis.py
Monte Carlo uncertainty analysis for 7-day reservoir dispatch.

Imports :func:`optimize_reservoir` and constants from
``reservoir_optimize`` and runs 100 perturbed inflow scenarios
(Normal errors, 10 % std) to quantify how forecast uncertainty propagates
to revenue, storage, and release decisions.
"""

import numpy as np
import matplotlib.pyplot as plt
from reservoir_optimize import optimize_reservoir, N, INFLOW


# ============================================================================
# REUSABLE UNCERTAINTY ANALYSIS FUNCTION
# ============================================================================

def run_uncertainty_analysis(num_scenarios=100):
    """
    Perform Monte Carlo uncertainty analysis on inflow forecasts.

    Parameters
    ----------
    num_scenarios : int
        Number of perturbed inflow scenarios to generate and solve.

    Returns
    -------
    results : dict
        Contains keys: ``revenues``, ``final_storages``, ``avg_releases``,
        ``all_releases``, along with computed statistics.
    """
    rng = np.random.default_rng(42)
    error_mean = 0.0
    error_std = 0.10

    all_rev = np.empty(num_scenarios)
    all_final_S = np.empty(num_scenarios)
    all_avg_rel = np.empty(num_scenarios)
    all_rels = np.empty((num_scenarios, N))

    for i in range(num_scenarios):
        errors = 1.0 + rng.normal(error_mean, error_std, size=N)
        inflow_i = INFLOW * errors
        rels_i, S_i, rev_i, _ = optimize_reservoir(inflow=inflow_i)
        all_rev[i] = rev_i
        all_final_S[i] = S_i[-1]
        all_avg_rel[i] = np.mean(rels_i)
        all_rels[i] = rels_i

    # --- Deterministic reference ---
    det_rels, det_S, det_rev, _ = optimize_reservoir()

    # --- Statistics ---
    stats = {
        "num_scenarios":        num_scenarios,
        "mean_revenue":         np.mean(all_rev),
        "min_revenue":          np.min(all_rev),
        "max_revenue":          np.max(all_rev),
        "std_revenue":          np.std(all_rev),
        "cv_revenue":           np.std(all_rev) / np.mean(all_rev),
        "mean_final_storage":   np.mean(all_final_S),
        "det_revenue":          det_rev,
        "det_final_storage":    det_S[-1],
    }

    return {
        "revenues":       all_rev,
        "final_storages": all_final_S,
        "avg_releases":   all_avg_rel,
        "all_releases":   all_rels,
        "det_releases":   det_rels,
        "det_storage":    det_S,
        "stats":          stats,
    }


# ============================================================================
# REPORTING & VISUALISATION HELPERS
# ============================================================================

def print_statistics(results):
    """Print a statistical summary table to the console."""
    s = results["stats"]
    print()
    print(f"  {'Statistic':<30}  {'Value':>12}")
    print(f"  {'-'*30}  {'-'*12}")
    print(f"  {'Number of scenarios':<30}  {s['num_scenarios']:>12d}")
    print(f"  {'Mean revenue ($)':<30}  {s['mean_revenue']:>12.2f}")
    print(f"  {'Min revenue ($)':<30}  {s['min_revenue']:>12.2f}")
    print(f"  {'Max revenue ($)':<30}  {s['max_revenue']:>12.2f}")
    print(f"  {'Std dev revenue ($)':<30}  {s['std_revenue']:>12.2f}")
    print(f"  {'Coeff of variation':<30}  {s['cv_revenue']:>12.4f}")
    print(f"  {'Mean final storage (m3)':<30}  {s['mean_final_storage']:>12.0f}")
    print(f"  {'Deterministic revenue ($)':<30}  {s['det_revenue']:>12.2f}")


def save_histograms(results):
    """Save revenue and storage histograms."""
    s = results["stats"]

    fig, ax = plt.subplots(figsize=(8, 5))
    ax.hist(results["revenues"], bins=20, edgecolor="white",
            color="steelblue", alpha=0.85)
    ax.axvline(s["det_revenue"], color="red", ls="--", lw=1.5,
               label=f"Deterministic = ${s['det_revenue']:.2f}")
    ax.axvline(s["mean_revenue"], color="darkgreen", ls=":", lw=1.5,
               label=f"Mean = ${s['mean_revenue']:.2f}")
    ax.set_xlabel("Total Revenue ($)")
    ax.set_ylabel("Frequency")
    ax.set_title("Uncertainty in Hydropower Revenue  "
                 f"({s['num_scenarios']} Monte Carlo scenarios)")
    ax.legend()
    ax.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig("revenue_uncertainty.png", dpi=150)
    print("  >>  revenue_uncertainty.png saved")

    fig, ax = plt.subplots(figsize=(8, 5))
    ax.hist(results["final_storages"] / 1e6, bins=20, edgecolor="white",
            color="darkorange", alpha=0.85)
    ax.axvline(s["det_final_storage"] / 1e6, color="red", ls="--", lw=1.5,
               label=f"Deterministic = {s['det_final_storage']/1e6:.2f} M m3")
    ax.set_xlabel("Final Storage  (million m3)")
    ax.set_ylabel("Frequency")
    ax.set_title("Uncertainty in End-of-Horizon Storage  "
                 f"({s['num_scenarios']} Monte Carlo scenarios)")
    ax.legend()
    ax.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig("storage_uncertainty.png", dpi=150)
    print("  >>  storage_uncertainty.png saved")


def save_release_boxplot(results):
    """Save boxplot of optimal releases across scenarios."""
    fig, ax = plt.subplots(figsize=(9, 5))
    bp = ax.boxplot(
        [results["all_releases"][:, t] for t in range(N)],
        positions=range(1, N + 1), widths=0.5, patch_artist=True,
        manage_ticks=True,
    )
    for patch in bp["boxes"]:
        patch.set_facecolor("lightblue")
    for t in range(N):
        ax.plot(t + 1, results["det_releases"][t], "rD", markersize=6,
                zorder=5, label="Deterministic" if t == 0 else "")
    ax.set_xlabel("Day")
    ax.set_ylabel("Optimal Release  (m3/s)")
    ax.set_title("Spread of Optimal Releases Across Scenarios")
    ax.set_xticks(range(1, N + 1))
    ax.legend()
    ax.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig("release_uncertainty.png", dpi=150)
    print("  >>  release_uncertainty.png saved")


def write_report(results):
    """Create uncertainty_report.txt."""
    s = results["stats"]
    lines = []
    lines.append("-" * 55)
    lines.append("UNCERTAINTY REPORT  -  Inflow Forecast Uncertainty")
    lines.append("-" * 55)
    lines.append("")
    lines.append(f"  Number of Monte Carlo scenarios  :  {s['num_scenarios']}")
    lines.append("  Error distribution               :  "
                 "Normal(mean=0.0, std=0.10)")
    lines.append("")
    lines.append("  Revenue Statistics ($):")
    lines.append(f"    Deterministic (no error)  :  {s['det_revenue']:>10.2f}")
    lines.append(f"    Mean                      :  {s['mean_revenue']:>10.2f}")
    lines.append(f"    Minimum                   :  {s['min_revenue']:>10.2f}")
    lines.append(f"    Maximum                   :  {s['max_revenue']:>10.2f}")
    lines.append(f"    Standard deviation        :  {s['std_revenue']:>10.2f}")
    lines.append(f"    Coefficient of variation  :  {s['cv_revenue']:>10.4f}")
    lines.append("")
    lines.append("  Storage Statistics (m3):")
    lines.append(f"    Deterministic final       :  {s['det_final_storage']:>10.0f}")
    lines.append(f"    Mean final                :  {s['mean_final_storage']:>10.0f}")
    lines.append("")
    lines.append("  Key Observations:")
    lines.append("")
    lines.append(
        "  1. Inflow uncertainty directly translates into revenue uncertainty. "
        "The spread"
    )
    lines.append(
        "     of revenue outcomes reflects the 10% standard deviation applied "
        "to inflows."
    )
    lines.append("")
    lines.append(
        "  2. The deterministic solution's revenue may differ from the mean "
        "of the"
    )
    lines.append(
        "     stochastic scenarios due to the nonlinear relationship between "
        "inflow,"
    )
    lines.append("     release, head, and power generation.")
    lines.append("")
    lines.append(
        "  3. End-of-horizon storage varies significantly across scenarios, "
        "indicating"
    )
    lines.append(
        "     that the optimal release policy is sensitive to the realised "
        "inflow."
    )
    lines.append("")
    lines.append(
        "  4. The boxplot of releases shows which days are most affected by "
        "inflow"
    )
    lines.append(
        "     uncertainty.  Wider boxes imply greater sensitivity to forecast "
        "errors."
    )
    lines.append("")
    lines.append(
        "  5. These results highlight the value of accurate inflow forecasting "
        "for"
    )
    lines.append(
        "     reservoir operation.  A robust (stochastic) optimisation "
        "approach could"
    )
    lines.append(
        "     reduce downside risk by explicitly considering the distribution "
        "of inflows."
    )
    lines.append("")
    lines.append("-" * 55)

    with open("uncertainty_report.txt", "w") as f:
        f.write("\n".join(lines))
    print("  >>  uncertainty_report.txt written")


# ============================================================================
# MAIN  —  run when executed directly
# ============================================================================

if __name__ == "__main__":
    print()
    print("=" * 72)
    print("  MONTE CARLO UNCERTAINTY ANALYSIS", end="")
    N_S = 100
    print("  (%d scenarios)" % N_S)
    print("=" * 72)

    results = run_uncertainty_analysis(num_scenarios=N_S)
    print_statistics(results)
    save_histograms(results)
    save_release_boxplot(results)
    write_report(results)
    print()