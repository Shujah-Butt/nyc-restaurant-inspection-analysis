"""
Stage 2: descriptive statistics, assumption checks, hypothesis tests
"""
import pandas as pd, numpy as np, json
from scipy import stats

OUT = "/workspaces/nyc-restaurant-inspection-analysis/analysis_output"
insp = pd.read_csv(f"{OUT}/cleaned_inspections.csv", parse_dates=["inspection_date"])
viol = pd.read_csv(f"{OUT}/cleaned_violations.csv", parse_dates=["inspection_date"])

res = {}  # results store
ALPHA = 0.05

sc = insp.dropna(subset=["score"]).copy()          # scored inspections
sc["score"] = sc["score"].astype(float)

# ===================================================================
# 1. DESCRIPTIVE STATISTICS
# ===================================================================
desc_overall = {
    "n_inspections": int(len(insp)),
    "n_establishments": int(insp["camis"].nunique()),
    "n_scored": int(len(sc)),
    "date_min": str(insp["inspection_date"].min().date()),
    "date_max": str(insp["inspection_date"].max().date()),
    "score_mean": round(sc["score"].mean(), 2),
    "score_sd": round(sc["score"].std(), 2),
    "score_median": round(sc["score"].median(), 2),
    "score_iqr": [float(sc["score"].quantile(.25)), float(sc["score"].quantile(.75))],
    "score_min": float(sc["score"].min()),
    "score_max": float(sc["score"].max()),
    "score_skew": round(stats.skew(sc["score"]), 3),
    "score_kurtosis": round(stats.kurtosis(sc["score"]), 3),
    "pct_grade_A_of_graded": round(insp["grade"].eq("A").sum() /
                                  insp["grade"].isin(["A","B","C","Z","P","N"]).sum() * 100, 1),
    "pct_with_critical_violation": round((insp["n_critical"] > 0).mean() * 100, 1),
    "pct_violations_cited": round(insp["action"].str.contains("Violations", na=False).mean() * 100, 1),
}
res["descriptives_overall"] = desc_overall

# by borough
boro_tab = (sc.groupby("boro")["score"]
              .agg(["count", "mean", "std", "median", "min", "max"]).round(2))
boro_tab["ci95_mean"] = (1.96 * boro_tab["std"] / np.sqrt(boro_tab["count"])).round(2)
res["descriptives_by_boro"] = boro_tab.to_dict("index")
print("== Scores by borough ==\n", boro_tab, "\n")
print("== Overall ==\n", json.dumps(desc_overall, indent=1))

# grade mix by borough
grade_mix = pd.crosstab(insp["boro"], insp["grade"])
res["grade_mix_by_boro"] = grade_mix.to_dict("index")

# by cuisine (n>=5)
cui = sc.groupby("cuisine")["score"].agg(["count", "mean", "std", "median"]).round(2)
cui = cui[cui["count"] >= 5].sort_values("mean", ascending=False)
res["descriptives_by_cuisine"] = cui.to_dict("index")

# by year (2022+)
yr = sc[sc["year"] >= 2022].groupby("year")["score"].agg(["count", "mean", "median"]).round(2)
res["descriptives_by_year"] = yr.to_dict("index")

# ===================================================================
# 2. ASSUMPTION CHECKS
# ===================================================================
assump = {}
# Normality: Shapiro-Wilk on score (overall) and per-group where n>=8
W, p = stats.shapiro(sc["score"])
assump["shapiro_overall"] = {"W": round(W, 4), "p": p}
print(f"Shapiro-Wilk score: W={W:.4f}, p={p:.3e}")

sh_groups = {}
for g, sub in sc.groupby("boro"):
    if len(sub) >= 8:
        w, pw = stats.shapiro(sub["score"])
        sh_groups[g] = {"n": len(sub), "W": round(w, 4), "p": pw}
assump["shapiro_by_boro"] = sh_groups

groups = [g["score"].values for _, g in sc.groupby("boro") if len(g) >= 5]
lev = stats.levene(*groups)
assump["levene_by_boro"] = {"W": round(lev.statistic, 4), "p": lev.pvalue}
print("Levene (boro):", assump["levene_by_boro"])
res["assumptions"] = assump

# ===================================================================
# 3. HYPOTHESIS TESTS
# ===================================================================
tests = {}

# ---- H1: scores differ across boroughs --------------------------------
# parametric ANOVA (for reference)
f_anova, p_anova = stats.f_oneway(*groups)
# non-parametric Kruskal-Wallis (primary, given non-normality)
H, p_kw = stats.kruskal(*groups)
k = len(groups); n = sc[sc["boro"].isin([g for g, sub in sc.groupby('boro') if len(sub) >= 5])]["score"].shape[0]
n_total = sum(len(g) for g in groups)
eps_sq = (H - k + 1) / (n_total - k)  # epsilon-squared effect size
tests["H1_boro_KW"] = {"H": round(H, 3), "p": p_kw, "epsilon_squared": round(eps_sq, 3),
                       "ANOVA_F": round(f_anova, 3), "ANOVA_p": p_anova, "k_groups": k}
print(f"\nH1 Kruskal-Wallis score~boro: H={H:.2f}, p={p_kw:.4f}, eps^2={eps_sq:.3f} | ANOVA p={p_anova:.4f}")

# Dunn post-hoc with Bonferroni (manual)
def dunn_bonf(df_, val, grp):
    gs = {g: d[val].values for g, d in df_.groupby(grp)}
    ranks = stats.rankdata(df_[val])
    df_=df_.copy(); df_["r"] = ranks
    mean_r = df_.groupby(grp)["r"].mean(); ns = df_.groupby(grp)[val].count()
    N = len(df_); pairs = {}
    names = sorted(gs)
    for i in range(len(names)):
        for j in range(i+1, len(names)):
            a, b = names[i], names[j]
            se = np.sqrt((N*(N+1)/12 - df_[val].duplicated().sum()*0) * (1/ns[a] + 1/ns[b]))
            z = (mean_r[a] - mean_r[b]) / se
            p_raw = 2 * (1 - stats.norm.cdf(abs(z)))
            pairs[f"{a} vs {b}"] = {"z": round(z, 3), "p_bonf": min(p_raw * len(names)*(len(names)-1)/2, 1.0)}
    return pairs

if p_kw < ALPHA:
    boros5 = sc[sc["boro"].isin(boro_tab[boro_tab["count"] >= 5].index)]
    tests["H1_dunn_posthoc"] = dunn_bonf(boros5, "score", "boro")
    print("Dunn post-hoc:", json.dumps(tests["H1_dunn_posthoc"], indent=1))

# ---- H2: initial vs re-inspection scores (Cycle inspections) ----------
cyc = sc[sc["inspection_type"].str.contains("Cycle Inspection", na=False)].copy()
cyc["visit"] = np.where(cyc["inspection_type"].str.contains("Re-inspection"), "Re-inspection", "Initial")
g1 = cyc.loc[cyc["visit"] == "Initial", "score"]
g2 = cyc.loc[cyc["visit"] == "Re-inspection", "score"]
U, p_u = stats.mannwhitneyu(g1, g2, alternative="two-sided")
rbc = 1 - 2 * U / (len(g1) * len(g2))   # rank-biserial correlation
tests["H2_initial_vs_reinspection_MW"] = {
    "n_initial": len(g1), "n_re": len(g2),
    "median_initial": float(g1.median()), "median_re": float(g2.median()),
    "U": U, "p": p_u, "rank_biserial_r": round(rbc, 3)}
print(f"\nH2 Cycle initial vs re-inspection: med {g1.median():.0f} vs {g2.median():.0f}, U={U:.0f}, p={p_u:.4f}, r={rbc:.3f}")

# ---- H3: critical violation presence ~ borough (chi-square) -----------
insp["any_critical"] = insp["n_critical"] > 0
ct = pd.crosstab(insp["boro"], insp["any_critical"])
ct = ct.loc[ct.sum(axis=1) >= 20]   # keep boroughs with enough inspections
chi2, p_chi, dof, exp = stats.chi2_contingency(ct)
ncell = exp.size; n_exp_lt5 = (exp < 5).sum()
cramers_v = np.sqrt(chi2 / (ct.values.sum() * (min(ct.shape) - 1)))
tests["H3_critical_by_boro_chi2"] = {"chi2": round(chi2, 3), "p": p_chi, "dof": dof,
                                     "cramers_v": round(cramers_v, 3),
                                     "expected_cells_below_5": int(n_exp_lt5),
                                     "table": ct.to_dict("index")}
print(f"\nH3 chi2 critical~boro: chi2={chi2:.2f}, dof={dof}, p={p_chi:.4f}, V={cramers_v:.3f}, cells<5: {n_exp_lt5}")

# ---- H4: critical violation association with cuisine (top cuisines) ---
top_cui = insp["cuisine"].value_counts()
keep = top_cui[top_cui >= 8].index
ct2 = pd.crosstab(insp.loc[insp["cuisine"].isin(keep), "cuisine"],
                  insp.loc[insp["cuisine"].isin(keep), "any_critical"])
chi2c, p_c, dofc, expc = stats.chi2_contingency(ct2)
vc = np.sqrt(chi2c / (ct2.values.sum() * (min(ct2.shape) - 1)))
tests["H4_critical_by_cuisine_chi2"] = {"chi2": round(chi2c, 3), "p": p_c, "dof": dofc,
                                        "cramers_v": round(vc, 3),
                                        "expected_cells_below_5": int((expc < 5).sum()),
                                        "table": ct2.to_dict("index")}
print(f"H4 chi2 critical~cuisine: chi2={chi2c:.2f}, dof={dofc}, p={p_c:.4f}, V={vc:.3f}, cells<5: {(expc<5).sum()}")

# ---- H5: year trend in scores (Spearman, 2022+) -----------------------
recent = sc[sc["year"] >= 2022]
rho, p_rho = stats.spearmanr(recent["year"], recent["score"])
tests["H5_score_year_spearman"] = {"rho": round(rho, 3), "p": p_rho, "n": len(recent)}
print(f"H5 Spearman score~year (2022+): rho={rho:.3f}, p={p_rho:.4f}, n={len(recent)}")

# ---- H6 (sanity): # critical violations vs score ----------------------
rho2, p2 = stats.spearmanr(sc["n_critical"], sc["score"])
tests["H6_ncrit_vs_score_spearman"] = {"rho": round(rho2, 3), "p": p2}
print(f"H6 Spearman n_critical~score: rho={rho2:.3f}, p={p2:.3e}")

res["hypothesis_tests"] = tests

# violation code frequency (violation-level) with canonical descriptions
vl = viol[viol["violation_code"].notna()].copy()
canon = vl.groupby("violation_code")["violation_description"].agg(lambda s: s.value_counts().idxmax())
vl["canonical"] = vl["violation_code"].map(canon)
topv = vl.groupby(["violation_code", "canonical", "critical_flag"]).size() \
         .reset_index(name="n").sort_values("n", ascending=False).head(14)
topv.to_csv(f"{OUT}/top_violations.csv", index=False)

with open(f"{OUT}/stats_results.json", "w") as f:
    json.dump(res, f, indent=1, default=str)
print("\nSaved stats_results.json + top_violations.csv")
