
# Reservoir Dispatch Optimization System

A Python-based reservoir operation optimization system developed for the Smart Water Lab Series. The project uses constrained optimization techniques to determine optimal reservoir release schedules during drought conditions while balancing hydropower generation and environmental flow requirements.

## Project Overview

Reservoir operators often face conflicting objectives when managing water resources during low-flow periods. Releasing more water increases hydropower production and revenue, while conserving water helps maintain reservoir storage for future demands. At the same time, environmental regulations require minimum downstream ecological flows.

This project formulates the problem as a constrained optimization model and solves it using SciPy's Sequential Least Squares Programming (SLSQP) algorithm. Additional analyses include trade-off evaluation between hydropower revenue and ecological protection, solution validation, uncertainty assessment using Monte Carlo simulation, and an optional Streamlit dashboard for interactive visualization.

---

## Features

### Core Optimization
- 7-day reservoir release scheduling
- Hydropower revenue maximization
- Reservoir storage continuity constraints
- Minimum and maximum storage limits
- Ecological flow requirements
- Release capacity constraints
- SLSQP optimization using `scipy.optimize`

### Trade-Off Analysis
- Multi-objective optimization
- Revenue versus ecological protection evaluation
- Pareto frontier generation
- Weight-based scenario comparison

### Validation Module
- Storage bounds verification
- Release constraint verification
- Mass balance validation
- Revenue calculation verification
- Feasibility reporting

### Uncertainty Analysis (Optional Extension)
- Monte Carlo simulation
- Random inflow forecast perturbations
- Revenue sensitivity assessment
- Storage variability analysis
- Risk evaluation under uncertain inflow conditions

### Interactive Dashboard (Optional Extension)
- Streamlit-based graphical interface
- Interactive parameter adjustment
- Visualization of optimization results
- Trade-off analysis display
- Validation report viewer
- Uncertainty analysis results viewer

---

## Problem Description

### Reservoir Characteristics

| Parameter | Value |
|------------|--------|
| Initial Storage | 500,000 m³ |
| Minimum Storage | 100,000 m³ |
| Maximum Storage | 1,000,000 m³ |
| Minimum Ecological Release | 10 m³/s |
| Maximum Release | 100 m³/s |
| Optimization Horizon | 7 Days |

### Inflow Forecast

| Day | Inflow (m³/s) |
|------|-------------|
| 1 | 15 |
| 2 | 12 |
| 3 | 10 |
| 4 | 8 |
| 5 | 12 |
| 6 | 15 |
| 7 | 18 |

### Hydropower Prices

| Day | Price ($/kWh) |
|------|-------------|
| 1 | 0.08 |
| 2 | 0.08 |
| 3 | 0.08 |
| 4 | 0.08 |
| 5 | 0.10 |
| 6 | 0.12 |
| 7 | 0.10 |

---

## Mathematical Formulation

### Decision Variables

The optimization determines the daily reservoir releases:

\[
Q_t , \quad t = 1,2,\ldots,7
\]

where:

- \(Q_t\) = release on day \(t\)

---

### Objective Function

Maximize total hydropower revenue:

\[
\max \sum_{t=1}^{7} Revenue_t
\]

Hydropower revenue depends on:

- Water release
- Hydraulic head
- Turbine efficiency
- Electricity price

---

### Storage Continuity Equation

\[
S_{t+1} = S_t + (I_t - Q_t)\Delta t
\]

where:

- \(S_t\) = storage
- \(I_t\) = inflow
- \(Q_t\) = release
- \(\Delta t\) = one day

---

### Constraints

Storage limits:

\[
S_{min} \leq S_t \leq S_{max}
\]

Release limits:

\[
Q_{eco} \leq Q_t \leq Q_{max}
\]

Mass balance:

\[
S_{t+1}=S_t+(I_t-Q_t)\Delta t
\]

---

## Project Structure

```text
Water-resources-Optimization/
│
├── reservoir_optimize.py
├── uncertainty_analysis.py
├── app.py
├── README.md
├── requirements.txt
│
├── outputs/
│   ├── optimal_schedule.csv
│   ├── tradeoff_analysis.png
│   ├── validation_report.txt
│   ├── uncertainty_report.txt
│   ├── revenue_uncertainty.png
│   ├── storage_uncertainty.png
│   └── release_uncertainty.png
│
└── screenshots/
```

---

## Installation

### Clone Repository

```bash
git clone https://github.com/Qaiseu/Water-resources-Optimization.git
cd Water-resources-Optimization
```

### Create Virtual Environment (Optional)

```bash
python -m venv venv
```

Activate environment:

Windows:

```bash
venv\Scripts\activate
```

Linux/macOS:

```bash
source venv/bin/activate
```

### Install Dependencies

```bash
pip install -r requirements.txt
```

---

## Required Libraries

- Python 3.10+
- NumPy
- SciPy
- Pandas
- Matplotlib
- Streamlit

---

## Running the Optimization

Execute:

```bash
python reservoir_optimize.py
```

Example output:

```text
7-DAY RESERVOIR DISPATCH OPTIMISATION

Status: Optimization terminated successfully

Total Revenue: $80.43
Final Storage: 652600 m³
```

Generated files:

```text
optimal_schedule.csv
tradeoff_analysis.png
validation_report.txt
```


## Running the Uncertainty Analysis

Execute:

```bash
python uncertainty_analysis.py
```

This performs Monte Carlo simulations with inflow uncertainty and generates:

```text
uncertainty_report.txt
revenue_uncertainty.png
storage_uncertainty.png
release_uncertainty.png
```

## Running the Streamlit Dashboard

Launch the interactive dashboard:

```bash
streamlit run app.py
```

Features available:

- Optimization results viewer
- Optimal schedule table
- Trade-off analysis visualization
- Validation report viewer
- Uncertainty analysis display
- Interactive parameter controls

---

## Example Results

### Optimization Results

| Metric | Value |
|----------|---------|
| Total Revenue | \$80.43 |
| Final Storage | 652,600 m³ |
| Constraint Violations | 0 |
| Optimization Status | Successful |

### Validation Results

- Storage Bounds Check: PASS
- Release Bounds Check: PASS
- Mass Balance Check: PASS
- Revenue Verification: PASS

### Uncertainty Analysis

Using 100 Monte Carlo scenarios with 10% inflow forecast uncertainty:

| Metric | Value |
|----------|---------|
| Mean Revenue | \$77.27 |
| Minimum Revenue | \$48.39 |
| Maximum Revenue | \$89.34 |
| Standard Deviation | \$6.39 |

Results indicate that inflow uncertainty can significantly influence reservoir performance and economic outcomes.

---

## Discussion

The optimization successfully identified a feasible release schedule that satisfies all reservoir storage and release constraints while maximizing hydropower revenue. Trade-off analysis demonstrated how increased ecological protection requirements can reduce economic returns but improve environmental performance. An ecological target flow of 25 m³/s was used during the trade-off study to create a meaningful conflict between revenue generation and ecological objectives, allowing construction of a Pareto frontier.

The uncertainty analysis further showed that forecast errors can impact both final storage and hydropower revenue. This highlights the importance of accurate inflow prediction and suggests potential benefits from future stochastic optimization approaches.


## Optional Extensions

Implemented:
- Monte Carlo inflow uncertainty analysis
- Streamlit interactive dashboard


## Learning Outcomes

This project demonstrates:

- Multi-objective optimization
- Reservoir operation modeling
- Constrained nonlinear optimization
- Trade-off analysis
- Monte Carlo simulation
- Data visualization
- Interactive dashboard development
- Scientific Python programming

---

## Author

Qais Douae — 3125999076 — Xi'an Jiaotong University — 2026
