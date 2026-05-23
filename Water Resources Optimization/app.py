"""
app.py — Streamlit dashboard for the reservoir dispatch optimisation project.

Displays results produced by ``reservoir_optimize`` and
``uncertainty_analysis`` modules.  Sidebar controls let the user adjust key
reservoir parameters before (re‑)running the optimisation.
"""

import io
import sys
import os
import contextlib

import streamlit as st
import pandas as pd
import numpy as np

from reservoir_optimize import (
    optimize_reservoir,
    run_validation,
    run_tradeoff_analysis,
    INFLOW,
    PRICE,
    N,
)

st.set_page_config(
    page_title="Reservoir Dispatch Optimisation Dashboard",
    layout="wide",
)

# ============================================================================
# SIDEBAR  —  Reservoir parameters
# ============================================================================

st.sidebar.title("Parameters")

S0_sb   = st.sidebar.number_input("Initial Storage (m3)",
                                   value=500_000, step=10_000)
S_MIN_sb= st.sidebar.number_input("Minimum Storage (m3)",
                                   value=100_000, step=10_000)
S_MAX_sb= st.sidebar.number_input("Maximum Storage (m3)",
                                   value=1_000_000, step=10_000)
ECO_TARGET_sb = st.sidebar.number_input("Ecological Flow Target (m3/s)",
                                         value=25.0, step=1.0)

st.sidebar.markdown("---")
st.sidebar.markdown("**Inflow (m3/s)**")
inflow_editable = []
defaults = [15.0, 12.0, 10.0, 8.0, 12.0, 15.0, 18.0]
days = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
for i, d in enumerate(days):
    inflow_editable.append(
        st.sidebar.number_input(f"  {d}", value=defaults[i], step=1.0,
                                key=f"inflow_{i}")
    )

st.sidebar.markdown("---")
st.sidebar.markdown("**Price ($/MWh)**")
price_editable = []
p_defaults = [0.08, 0.08, 0.08, 0.08, 0.10, 0.12, 0.10]
for i, d in enumerate(days):
    price_editable.append(
        st.sidebar.number_input(f"  {d}", value=p_defaults[i],
                                format="%.3f", step=0.01, key=f"price_{i}")
    )


# ============================================================================
# HELPERS
# ============================================================================

def _patch_constants(mod):
    """Store originals and apply sidebar values to *mod*."""
    saved = {
        "S0": mod.S0,
        "S_MIN": mod.S_MIN,
        "S_MAX": mod.S_MAX,
        "PRICE": mod.PRICE.copy(),
        "INFLOW": mod.INFLOW.copy(),
    }
    mod.S0    = S0_sb
    mod.S_MIN = S_MIN_sb
    mod.S_MAX = S_MAX_sb
    mod.PRICE = np.array(price_editable, dtype=float)
    mod.INFLOW = np.array(inflow_editable, dtype=float)
    return saved


def _restore_constants(mod, saved):
    """Restore original constants on *mod* after a run."""
    mod.S0    = saved["S0"]
    mod.S_MIN = saved["S_MIN"]
    mod.S_MAX = saved["S_MAX"]
    mod.PRICE = saved["PRICE"]
    mod.INFLOW = saved["INFLOW"]


def run_optimisation():
    """Run ``optimize_reservoir`` with current sidebar parameters."""
    import reservoir_optimize as mod
    saved = _patch_constants(mod)
    try:
        rels, S, rev, res = optimize_reservoir(
            inflow=np.array(inflow_editable, dtype=float),
        )
    finally:
        _restore_constants(mod, saved)
    return rels, S, rev, res


def run_tradeoff():
    """Run trade-off analysis with current sidebar parameters."""
    import reservoir_optimize as mod
    saved = _patch_constants(mod)
    try:
        run_tradeoff_analysis(
            inflow=np.array(inflow_editable, dtype=float),
            price=np.array(price_editable, dtype=float),
        )
    finally:
        _restore_constants(mod, saved)


def run_validation_helper():
    """Run optimisation then validation with current sidebar parameters.

    Returns the validation report text.
    """
    rels, S, rev, _ = run_optimisation()
    report = run_validation(rels, S, rev)
    return report


def run_uncertainty():
    """Run the Monte Carlo uncertainty analysis (100 scenarios)."""
    import reservoir_optimize as mod
    import uncertainty_analysis as ua

    saved = _patch_constants(mod)
    ua.INFLOW = mod.INFLOW.copy()   # uncertainty_analysis has its own alias

    try:
        results = ua.run_uncertainty_analysis(num_scenarios=100)
    finally:
        _restore_constants(mod, saved)
        ua.INFLOW = saved["INFLOW"]

    return results


# ============================================================================
# MAIN PAGE
# ============================================================================

st.title("Reservoir Dispatch Optimisation Dashboard")

# Tabs for a clean layout
tab_opt, tab_trade, tab_valid, tab_uncert = st.tabs([
    "Optimisation Results",
    "Trade‑off Analysis",
    "Validation",
    "Uncertainty Analysis",
])

# ============================================================================
# TAB A  —  Optimisation Results
# ============================================================================

with tab_opt:
    col1, col2 = st.columns([1, 3])

    with col1:
        run_btn = st.button("Run Optimisation", type="primary")

    with col2:
        st.caption(
            "Adjust reservoir parameters in the sidebar, then click "
            "**Run Optimisation** to compute a new optimal release schedule."
        )

    if run_btn or "opt_rels" not in st.session_state:
        with st.spinner("Solving the optimisation problem …"):
            rels, S, rev, res = run_optimisation()
        st.session_state["opt_rels"] = rels
        st.session_state["opt_S"]    = S
        st.session_state["opt_rev"]  = rev
        st.session_state["opt_res"]  = res

    if "opt_rels" in st.session_state:
        rels = st.session_state["opt_rels"]
        S    = st.session_state["opt_S"]
        rev  = st.session_state["opt_rev"]

        # Metrics row
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Total Revenue", f"${rev:,.2f}")
        m2.metric("Final Storage", f"{S[-1]:,.0f} m3")
        m3.metric("Initial Storage", f"{S[0]:,.0f} m3")
        m4.metric("Solver Status",
                  "Converged" if st.session_state["opt_res"].success else "Failed")

        # Build & show schedule table
        day_revs = []
        for t in range(N):
            S_avg = 0.5 * (S[t] + S[t + 1])
            head = 10.0 + (S_avg - S_MIN_sb) / (S_MAX_sb - S_MIN_sb) * 40.0
            power_mw = 0.9 * 1000.0 * 9.81 * rels[t] * head / 1.0e6
            rev_day = power_mw * 24.0 * price_editable[t]
            day_revs.append(rev_day)

        df_schedule = pd.DataFrame({
            "Day":          range(1, N + 1),
            "Inflow (m3/s)": inflow_editable,
            "Release (m3/s)": [f"{r:.2f}" for r in rels],
            "Storage (m3)":  [f"{s:,.0f}" for s in S[1:]],
            "Revenue ($)":   [f"{r:.2f}" for r in day_revs],
        })
        st.subheader("Optimal Schedule")
        st.dataframe(df_schedule, width='stretch', hide_index=True)

        # Save CSV so the "optimal_schedule.csv" file is always current
        df_schedule.to_csv("optimal_schedule.csv", index=False)

# ============================================================================
# TAB B  —  Trade-off Analysis
# ============================================================================

with tab_trade:
    st.subheader("Pareto Frontier — Revenue vs. Ecological Deficit")

    tcol1, tcol2 = st.columns([1, 3])
    with tcol1:
        trade_btn = st.button("Run Trade-off Analysis", type="primary",
                              key="trade_btn")
    with tcol2:
        st.caption(
            "Solves 11 weighted combinations (w_rev from 0.0 to 1.0) "
            "and plots the Pareto frontier."
        )

    if trade_btn:
        with st.spinner("Running 11 weighted optimisations …"):
            run_tradeoff()
        st.success("Trade-off analysis complete.")

    if os.path.exists("tradeoff_analysis.png"):
        st.image("tradeoff_analysis.png", width='stretch')
    else:
        st.warning("Click **Run Trade-off Analysis** to generate the plot.")

# ============================================================================
# TAB C  —  Validation
# ============================================================================

with tab_valid:
    st.subheader("Validation Report")

    vcol1, vcol2 = st.columns([1, 3])
    with vcol1:
        valid_btn = st.button("Run Validation", type="primary",
                              key="valid_btn")
    with vcol2:
        st.caption(
            "Checks storage bounds, release bounds, mass balance, and "
            "revenue for the current optimal solution."
        )

    if valid_btn or "valid_report" not in st.session_state:
        if valid_btn:
            with st.spinner("Running optimisation & validation …"):
                report = run_validation_helper()
            st.session_state["valid_report"] = report
            st.success("Validation complete.")

    if "valid_report" in st.session_state:
        st.text(st.session_state["valid_report"])
    elif os.path.exists("validation_report.txt"):
        with open("validation_report.txt") as f:
            st.text(f.read())
    else:
        st.warning("Click **Run Validation** to generate the report.")

# ============================================================================
# TAB D  —  Uncertainty Analysis
# ============================================================================

with tab_uncert:
    ucol1, ucol2 = st.columns([1, 3])
    with ucol1:
        uncert_btn = st.button("Run Uncertainty Analysis", type="primary")
    with ucol2:
        st.caption(
            "Runs 100 Monte Carlo scenarios with 10 % inflow uncertainty."
        )

    if uncert_btn:
        with st.spinner("Running 100 Monte Carlo scenarios …"):
            run_uncertainty()
        st.success("Uncertainty analysis complete.")
        # Force a refresh so the newly-created files are visible
        st.rerun()

    c1, c2 = st.columns(2)

    with c1:
        st.subheader("Report")
        if os.path.exists("uncertainty_report.txt"):
            with open("uncertainty_report.txt") as f:
                st.text(f.read())
        else:
            st.info("No report yet — click the button above.")

    with c2:
        st.subheader("Visualisations")

        rev_path   = "revenue_uncertainty.png"
        stor_path  = "storage_uncertainty.png"
        rel_path   = "release_uncertainty.png"

        if os.path.exists(rev_path):
            st.image(rev_path, width='stretch')
        else:
            st.info("Revenue histogram not yet generated.")

        if os.path.exists(stor_path):
            st.image(stor_path, width='stretch')

        if os.path.exists(rel_path):
            st.image(rel_path, width='stretch')