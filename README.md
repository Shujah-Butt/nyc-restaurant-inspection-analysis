# 🍽️ NYC Restaurant Inspection Analysis
### From Raw CSV to Statistical Insights

![Python](https://img.shields.io/badge/Python-3.x-blue?logo=python&logoColor=white)
![pandas](https://img.shields.io/badge/pandas-EDA-orange)
![SciPy](https://img.shields.io/badge/SciPy-Hypothesis_Testing-green)
![matplotlib](https://img.shields.io/badge/matplotlib-Visualization-red)
![License](https://img.shields.io/badge/license-MIT-lightgrey)

> End-to-end statistical analysis of **1,000 NYC restaurant health-inspection records**:
> data cleaning → EDA → descriptive statistics → assumption checking → **6 hypothesis tests** →
> **8 publication-quality visualizations** → actionable findings.

![Score distribution](analysis_output/figures/fig1_score_distribution.png)

---

## 🎯 The Problem

NYC's Department of Health (DOHMH) publishes one of the largest open restaurant-inspection
datasets in the world — but the raw export is messy and misleading if taken at face value:

- **78% of rows** in this extract are *pre-permit* placeholders (sentinel date `1900-01-01`) with no inspection at all
- Coordinates stored as **text**, with `(0, 0)` "null island" values
- Scores, ZIP codes, and dates typed as **strings**
- The same violation code **re-worded by the city over the years**, fragmenting categories
- **One inspection spans many rows** (one per violation cited) — naïve summaries double-count

> **Research question:** Do inspection outcomes actually differ across boroughs, cuisines,
> and time — once the data is properly cleaned and statistical assumptions are checked?

---

## 📊 Dataset

| Property | Value |
|---|---|
| **Source** | NYC DOHMH Restaurant Inspection Results (1,000-row extract) |
| **Coverage** | 212 inspections of 195 establishments · 2016–2025 |
| **Grain change** | 1,000 violation-level rows → 212 inspection-level rows |
| **Analyzed** | 180 scored inspections · 80 letter-graded · 147 violation citations |

---

## 🔍 Methodology

1. **Data cleaning** — sentinel-value detection, type coercion, NYC bounding-box geovalidation,
   deduplication, canonical violation descriptions, inspection-level aggregation
   (full audit trail in `cleaning_log.txt`)
2. **EDA** — distributions, borough/cuisine/year breakdowns, violation-frequency profiling
3. **Descriptive statistics** — central tendency, dispersion, skew/kurtosis, confidence intervals
4. **Assumption checking** — Shapiro–Wilk normality (overall + per-group), Levene homogeneity
   of variance, chi-square expected-count validation, Q–Q diagnostics
5. **Hypothesis testing** — 6 tests with effect sizes (Kruskal–Wallis, Mann–Whitney U, χ²,
   Spearman), **chosen based on the assumption-check results** (normality failed → non-parametric)
6. **Visualization** — 8 figures @ 300 DPI, colorblind-safe Okabe–Ito palette, PNG + PDF

---

## 📌 Key Findings

| # | Hypothesis | Test | Verdict | Result |
|---|---|---|---|---|
| H1 | Scores differ across boroughs | Kruskal–Wallis | ⚠️ Borderline | H(4) = 9.42, *p* = .051, ε² = 0.03 |
| H2 | Re-inspections score better than initial | Mann–Whitney U | ❌ Not supported | *p* = .31, r = 0.12 |
| H3 | Critical-violation rate ~ borough | χ² test | ❌ Not supported | χ²(3) = 1.25, *p* = .74 |
| H4 | Critical-violation rate ~ cuisine | χ² test | ❌ Not supported | χ²(9) = 10.13, *p* = .34 |
| H5 | Scores change over time (2022–25) | Spearman | ❌ Not supported | ρ = −0.13, *p* = .10 |
| H6 | Critical violations drive total score | Spearman | ✅ **Confirmed** | ρ = 0.46, *p* < .001 |

**In plain English:**

- 🍎 **62.5%** of graded inspections earned an **A** — but **45.8%** included at least one **critical** violation (improper holding temperatures, pests)
- 🗺️ Queens & Bronx medians (24) are **double** Manhattan/Brooklyn (13) — visible, but *not statistically significant* at this sample size → **suggestive, not proven**
- 🌡️ Code **02B — "hot food not held ≥ 140 °F"** — is cited **3× more** than any other violation (52 times, always critical), followed by roaches (04M) and mice (04L)
- 🍜 Chinese, Spanish & Latin American venues average near the C-grade threshold; Coffee/Tea shops average a score of 2
- 📉 No evidence scores are improving or worsening across 2022–2025
- ⚖️ The one significant result (H6) is a **construct check**: critical violations track total score (ρ = 0.46), validating score as a risk proxy

---

## 📈 Selected Figures

| Score distribution & grade cutoffs | Scores by borough (Kruskal–Wallis) |
|:---:|:---:|
| ![fig1](analysis_output/figures/fig1_score_distribution.png) | ![fig2](analysis_output/figures/fig2_scores_by_borough.png) |
| **Borough grade mix & critical rates** | **Top-10 cited violations** |
| ![fig3](analysis_output/figures/fig3_borough_outcomes.png) | ![fig4](analysis_output/figures/fig4_top_violations.png) |

All 8 figures (cuisine ranking, geographic scatter, yearly trends, Q–Q diagnostics)
are in [`analysis_output/figures/`](analysis_output/figures/).

---

## 🧠 Honest Limitations

- Small extract (n = 180 scored inspections; only 5 in Staten Island) → underpowered for medium effects
- 2025 is a partial year (data through October)
- Violation score measures **code compliance at inspection time**, not foodborne illness
- Some establishments were inspected multiple times (mild dependence between observations)

---

## 🚀 Reproduce

```bash
pip install pandas numpy scipy statsmodels matplotlib seaborn

python analysis/01_clean.py   # raw CSV → cleaned frames + audit log
python analysis/02_stats.py   # descriptives, assumptions, hypothesis tests → JSON
python analysis/03_viz.py     # 8 figures @ 300 DPI (PNG + PDF)
```

**Repo structure:**

```text
├── uploads/43nn-pn8j.csv            # raw data
├── analysis/                        # pipeline (clean → stats → viz)
├── analysis_output/
│   ├── cleaned_inspections.csv      # inspection-level frame (212 rows)
│   ├── cleaned_violations.csv       # violation-level frame (1,000 rows)
│   ├── stats_results.json           # every test statistic & p-value
│   ├── cleaning_log.txt             # data-quality audit trail
│   ├── report.md                    # full written report
│   └── figures/                     # 8 publication-quality figures
└── portfolio/                       # LinkedIn / Fiverr write-ups
```

---

## 💼 Skills Demonstrated

Data cleaning with sentinel-value handling · multi-grain data aggregation ·
non-parametric inference · assumption-driven test selection · effect-size reporting ·
uncertainty communication for non-technical stakeholders.

---

## 📫 Author

**Muhammad Shujah U Din Butt**
[LinkedIn](https://www.linkedin.com/in/muhammad-shujah-u-din-butt/) ·
[muhammadshujahuddin@gmail.com](mailto:muhammadshujahuddin@gmail.com)

⭐ If you found this useful, consider giving the repo a star!
