"""
Stage 3: publication-quality visualizations (300 dpi, colorblind-safe)
"""
import pandas as pd, numpy as np, json
import matplotlib as mpl
import matplotlib.pyplot as plt
from matplotlib.patches import Patch
from matplotlib.lines import Line2D
import seaborn as sns
from scipy import stats

OUT = "/workspaces/nyc-restaurant-inspection-analysis/analysis_output"
FIG = f"{OUT}/figures"
insp = pd.read_csv(f"{OUT}/cleaned_inspections.csv", parse_dates=["inspection_date"])
viol = pd.read_csv(f"{OUT}/cleaned_violations.csv", parse_dates=["inspection_date"])
res  = json.load(open(f"{OUT}/stats_results.json"))

# ---------------- style ----------------
mpl.rcParams.update({
    "font.family": "DejaVu Sans", "font.size": 10,
    "axes.titlesize": 12, "axes.titleweight": "bold",
    "axes.labelsize": 10.5, "axes.edgecolor": "#333333",
    "axes.linewidth": 0.8, "axes.grid": True,
    "grid.color": "#d9d9d9", "grid.linewidth": 0.6, "grid.alpha": 0.8,
    "xtick.labelsize": 9.5, "ytick.labelsize": 9.5,
    "legend.fontsize": 9, "figure.dpi": 300, "savefig.dpi": 300,
    "savefig.bbox": "tight", "savefig.facecolor": "white",
})
# Okabe-Ito colorblind-safe palette
OI = {"blue":"#0072B2","orange":"#E69F00","green":"#009E73","verm":"#D55E00",
      "sky":"#56B4E9","yellow":"#F0E442","purple":"#CC79A7","grey":"#999999"}
GRADE_COL = {"A": OI["green"], "B": OI["orange"], "C": OI["verm"],
             "Z": OI["purple"], "P": OI["sky"], "N": OI["grey"]}
BORO_ORDER = ["Manhattan", "Brooklyn", "Queens", "Bronx", "Staten Island"]
BORO_COL = dict(zip(BORO_ORDER, [OI["blue"], OI["green"], OI["verm"], OI["orange"], OI["purple"]]))

sc = insp.dropna(subset=["score"]).copy(); sc["score"] = sc["score"].astype(float)

def savefig(fig, name):
    fig.savefig(f"{FIG}/{name}.png"); fig.savefig(f"{FIG}/{name}.pdf"); plt.close(fig)
    print("saved", name)

# =================================================================
# FIG 1 - Score distribution with grade bands
# =================================================================
fig, ax = plt.subplots(figsize=(7.2, 4.2))
bins = np.arange(0, 86, 2)
band_colors = {0: OI["green"], 14: OI["orange"], 28: OI["verm"]}
counts, edges, patches = ax.hist(sc["score"], bins=bins, edgecolor="white", linewidth=0.5)
for p_, e in zip(patches, edges[:-1]):
    p_.set_facecolor(band_colors[0 if e < 14 else (14 if e < 28 else 28)])
    p_.set_alpha(0.85)
med = sc["score"].median(); mean = sc["score"].mean()
ax.axvline(med, color="#222222", ls="--", lw=1.4, label=f"Median = {med:.0f}")
ax.axvline(mean, color="#555555", ls=":", lw=1.4, label=f"Mean = {mean:.1f}")
ymax = ax.get_ylim()[1]
for x, lab in [(13.5, "A|B cutoff\n(score 14)"), (27.5, "B|C cutoff\n(score 28)")]:
    ax.axvline(x, color="#222222", lw=0.8, alpha=0.65)
    ax.text(x + 1.2, ymax*0.045, lab, fontsize=7.5, color="#222222", va="bottom", ha="left")
leg = [Line2D([0],[0], color="#222222", ls="--", lw=1.4, label=f"Median = {med:.0f}"),
       Line2D([0],[0], color="#555555", ls=":", lw=1.4, label=f"Mean = {mean:.1f}"),
       Patch(facecolor=OI["green"], alpha=0.85, label="Grade A range (0–13)"),
       Patch(facecolor=OI["orange"], alpha=0.85, label="Grade B range (14–27)"),
       Patch(facecolor=OI["verm"], alpha=0.85, label="Grade C range (≥28)")]
ax.legend(handles=leg, frameon=False, loc="upper right")
ax.set_title(f"Distribution of NYC restaurant inspection scores, 2016–2025 (n = {len(sc)} inspections)")
ax.set_xlabel("Violation score (higher = more violations)")
ax.set_ylabel("Number of inspections")
ax.set_xlim(-1, 84); ax.set_axisbelow(True)
savefig(fig, "fig1_score_distribution")

# =================================================================
# FIG 2 - Scores by borough: box + strip, KW annotation
# =================================================================
fig, ax = plt.subplots(figsize=(7.2, 4.4))
order = (sc.groupby("boro")["score"].median()
           .reindex(BORO_ORDER).sort_values(ascending=False).index.tolist())
sns.boxplot(data=sc, x="boro", y="score", order=order, ax=ax, width=0.55,
            palette=[BORO_COL[b] for b in order], fliersize=0, linewidth=1.0, medianprops={"color":"black","linewidth":1.5})
sns.stripplot(data=sc, x="boro", y="score", order=order, ax=ax, color="#333333",
              size=2.6, alpha=0.45, jitter=0.22)
for i, b in enumerate(order):
    n = int((sc["boro"] == b).sum())
    ax.text(i, -11.5, f"n = {n}", ha="center", fontsize=9, color="#444444")
    ax.text(i, 87, f"med {sc.loc[sc['boro']==b,'score'].median():.0f}",
            ha="center", fontsize=8.5, color="#444444")
kw = res["hypothesis_tests"]["H1_boro_KW"]
ax.set_title(f"Inspection scores by borough\nKruskal–Wallis H({kw['k_groups']-1}) = {kw['H']:.2f}, p = {float(kw['p']):.3f}, ε² = {kw['epsilon_squared']:.3f}", fontsize=11.5)
ax.set_xlabel(""); ax.set_ylabel("Violation score")
ax.set_ylim(-14, 92); ax.set_axisbelow(True)
savefig(fig, "fig2_scores_by_borough")

# =================================================================
# FIG 3 - Grade mix by borough + critical-violation rate w/ Wilson CI
# =================================================================
fig, axes = plt.subplots(1, 2, figsize=(10.5, 4.3), gridspec_kw={"width_ratios": [1.15, 1]})
# (a) stacked grade mix (graded inspections only)
ga = insp[insp["grade"].isin(list(GRADE_COL))].copy()
gm = pd.crosstab(ga["boro"], ga["grade"], normalize="index").reindex(BORO_ORDER).dropna(how="all")
gm = gm[[c for c in ["A","B","C","Z","P","N"] if c in gm.columns]]
left = np.zeros(len(gm))
for g in gm.columns:
    axes[0].barh(gm.index, gm[g]*100, left=left, color=GRADE_COL[g], edgecolor="white",
                 linewidth=0.6, label=f"Grade {g}")
    for y, (v, l) in enumerate(zip(gm[g]*100, left)):
        if v >= 7:
            axes[0].text(l + v/2, y, f"{g}\n{v:.0f}%", ha="center", va="center",
                         fontsize=8, color="white", fontweight="bold")
    left += gm[g]*100
axes[0].set_xlabel("Share of graded inspections (%)")
axes[0].set_title("(a) Letter-grade mix by borough")
axes[0].invert_yaxis()
axes[0].legend(frameon=False, ncol=6, loc="lower center", bbox_to_anchor=(0.5, -0.34), fontsize=8)
axes[0].set_xlim(0, 100); axes[0].set_ylabel("")
# (b) critical violation rate with Wilson 95% CI
boros = [b for b in BORO_ORDER if (insp["boro"] == b).sum() >= 10]
rates, lo_ci, hi_ci, ns = [], [], [], []
for b in boros:
    x = int((insp.loc[insp["boro"] == b, "n_critical"] > 0).sum())
    n = int((insp["boro"] == b).sum())
    z = stats.norm.ppf(0.975); ph = x/n
    c = (ph + z**2/(2*n)) / (1 + z**2/n)
    h = z*np.sqrt(ph*(1-ph)/n + z**2/(4*n**2)) / (1 + z**2/n)
    rates.append(ph*100); lo_ci.append((ph-(c-h))*100); hi_ci.append(((c+h)-ph)*100); ns.append(n)
axes[1].bar(range(len(boros)), rates, color=[BORO_COL[b] for b in boros], alpha=0.9, width=0.62)
chi = res["hypothesis_tests"]["H3_critical_by_boro_chi2"]
for i, (r, lo, hi, n) in enumerate(zip(rates, lo_ci, hi_ci, ns)):
    axes[1].errorbar(i, r, yerr=[[lo],[hi]], color="#222222", capsize=4, lw=1.3)
    axes[1].text(i, r + hi + 3.5, f"n={n}", ha="center", fontsize=8.5, color="#444444")
axes[1].set_xticks(range(len(boros))); axes[1].set_xticklabels([b.replace(" ", "\n") for b in boros])
axes[1].set_ylabel("Inspections with ≥1 critical violation (%)")
axes[1].set_title("(b) Critical-violation rate by borough")
axes[1].text(0.02, 0.97, f"χ²({chi['dof']}) = {chi['chi2']:.2f}, p = {float(chi['p']):.2f}, V = {chi['cramers_v']:.2f}",
             transform=axes[1].transAxes, va="top", fontsize=9, style="italic")
axes[1].set_ylim(0, 100); axes[1].set_axisbelow(True)
fig.suptitle("Inspection outcomes across NYC boroughs", fontweight="bold", y=1.02)
fig.tight_layout()
savefig(fig, "fig3_borough_outcomes")

# =================================================================
# FIG 4 - Top 10 violation codes, stacked by criticality
# =================================================================
vl = viol[viol["violation_code"].notna()].copy()
vl["crit"] = vl["critical_flag"].map({"Critical": "Critical", "Not Critical": "Non-critical"}).fillna("N/A")
top_codes = vl["violation_code"].value_counts().head(10).index.tolist()
dd = vl[vl["violation_code"].isin(top_codes) & vl["crit"].isin(["Critical","Non-critical"])].copy()
# canonical description per code (descriptions were reworded by DOHMH over time): use most frequent
canon = (dd.groupby("violation_code")["violation_description"]
           .agg(lambda s: s.value_counts().idxmax()))
dd["canonical"] = dd["violation_code"].map(canon)
dd["label"] = dd["violation_code"] + " — " + dd["canonical"].str.slice(0, 52) + \
              np.where(dd["canonical"].str.len() > 52, "…", "")
order4 = dd.groupby("label").size().sort_values().index
fig, ax = plt.subplots(figsize=(8.6, 5.0))
left = np.zeros(len(order4))
for cat, col in [("Non-critical", OI["blue"]), ("Critical", OI["verm"])]:
    vals = (dd[dd["crit"] == cat].groupby("label").size().reindex(order4).fillna(0))
    ax.barh(order4, vals, left=left, color=col, alpha=0.9,
            edgecolor="white", linewidth=0.5, label=cat, height=0.68)
    left += vals.values
for y, v in enumerate(left):
    ax.text(v + 0.6, y, str(int(v)), va="center", fontsize=8.5, color="#444444")
ax.set_xlabel("Number of citations (violation-level records)")
ax.set_title("Ten most frequently cited violations")
ax.legend(frameon=False, loc="lower right", title="Severity", title_fontsize=9)
ax.set_xlim(0, left.max()*1.12); ax.set_ylabel(""); ax.tick_params(axis="y", labelsize=8.6)
ax.set_axisbelow(True)
savefig(fig, "fig4_top_violations")

# =================================================================
# FIG 5 - Mean score by cuisine (n>=5) with 95% CI
# =================================================================
cui = sc.groupby("cuisine")["score"].agg(["count","mean","std"]).query("count >= 5")
cui["se"] = cui["std"] / np.sqrt(cui["count"])
cui = cui.sort_values("mean")
fig, ax = plt.subplots(figsize=(7.6, 4.8))
cols = [OI["verm"] if m > 19.04 else (OI["green"] if m < 15 else OI["blue"]) for m in cui["mean"]]
ax.barh(cui.index, cui["mean"], xerr=cui["se"]*1.96, color=cols, alpha=0.88,
        edgecolor="white", height=0.66, error_kw=dict(ecolor="#333333", lw=1.1, capsize=3))
for y, (m, n) in enumerate(zip(cui["mean"], cui["count"])):
    ax.text(m + cui["se"].iloc[y]*1.96 + 0.9, y, f"n={int(n)}", va="center", fontsize=8, color="#444444")
ax.axvline(19.04, ls="--", lw=1.1, color="#555555")
ax.text(19.04+0.5, -0.62, "overall mean = 19.0", fontsize=8.2, va="bottom", color="#555555")
ax.set_xlabel("Mean violation score (± 95% CI)")
ax.set_title("Mean inspection score by cuisine (cuisines with ≥5 scored inspections)")
ax.set_xlim(0, 52); ax.set_ylabel(""); ax.tick_params(axis="y", labelsize=9)
ax.set_axisbelow(True)
savefig(fig, "fig5_cuisine_scores")

# =================================================================
# FIG 6 - Geospatial scatter of inspections
# =================================================================
geo = sc.dropna(subset=["latitude","longitude"])
fig, ax = plt.subplots(figsize=(6.8, 6.4))
scat = ax.scatter(geo["longitude"], geo["latitude"], c=geo["score"],
                  cmap="RdYlGn_r", vmin=0, vmax=60, s=26, alpha=0.8,
                  edgecolor="white", linewidth=0.4)
hr = insp[(insp["n_critical"] > 0)].dropna(subset=["latitude","longitude"])
ax.scatter(hr["longitude"], hr["latitude"], facecolor="none", edgecolor="#222222",
           s=34, linewidth=0.7, alpha=0.75, label="≥1 critical violation")
cb = fig.colorbar(scat, ax=ax, shrink=0.72, pad=0.02)
cb.set_label("Violation score")
ax.set_xlabel("Longitude"); ax.set_ylabel("Latitude")
ax.set_title(f"Geography of {len(geo)} scored inspections (color = score)")
ax.legend(frameon=False, loc="upper left")
ax.grid(True)
savefig(fig, "fig6_map")

# =================================================================
# FIG 7 - Score trend by year (2022-2025) + assumption diagnostics appendix
# =================================================================
fig, axes = plt.subplots(1, 2, figsize=(10.5, 4.1))
recent = sc[sc["year"] >= 2022]
sns.boxplot(data=recent, x="year", y="score", ax=axes[0], width=0.5,
            color=OI["sky"], fliersize=0, medianprops={"color":"black","linewidth":1.5})
sns.stripplot(data=recent, x="year", y="score", ax=axes[0], color="#333333", size=2.4, alpha=0.4, jitter=0.2)
h5 = res["hypothesis_tests"]["H5_score_year_spearman"]
axes[0].text(0.02, 0.97, f"Spearman ρ = {h5['rho']:.2f}, p = {float(h5['p']):.2f} (n = {h5['n']})",
             transform=axes[0].transAxes, va="top", fontsize=9, style="italic")
axes[0].set_title("(a) Scores by inspection year, 2022–2025")
axes[0].set_xlabel("Year"); axes[0].set_ylabel("Violation score")
axes[0].set_xticks(range(4)); axes[0].set_xticklabels(["2022", "2023", "2024", "2025"])
axes[0].set_ylim(-3, 88)
# (b) Q-Q plot
(osm, osr), (slope, intercept, r) = stats.probplot(sc["score"], dist="norm")
axes[1].scatter(osm, osr, s=12, alpha=0.5, color=OI["blue"], edgecolor="none")
xs = np.array([osm.min(), osm.max()])
axes[1].plot(xs, slope*xs + intercept, color=OI["verm"], lw=1.3)
sh = res["assumptions"]["shapiro_overall"]
axes[1].text(0.05, 0.95, f"Shapiro–Wilk W = {sh['W']:.3f}, p < 0.001\n(normality rejected → non-parametric tests)",
             transform=axes[1].transAxes, va="top", fontsize=9)
axes[1].set_title("(b) Normal Q–Q plot of scores")
axes[1].set_xlabel("Theoretical normal quantiles"); axes[1].set_ylabel("Sample quantiles")
fig.tight_layout()
savefig(fig, "fig7_trend_and_qq")

# =================================================================
# FIG 8 - Initial vs re-inspection (H2)
# =================================================================
cyc = sc[sc["inspection_type"].str.contains("Cycle Inspection", na=False)].copy()
cyc["visit"] = np.where(cyc["inspection_type"].str.contains("Re-inspection"), "Re-inspection\n(n=%d)" % (cyc['inspection_type'].str.contains('Re-inspection')).sum(),
                        "Initial\n(n=%d)" % (~cyc['inspection_type'].str.contains('Re-inspection')).sum())
fig, ax = plt.subplots(figsize=(5.4, 4.2))
sns.boxplot(data=cyc, x="visit", y="score", ax=ax, width=0.45, palette=[OI["blue"], OI["orange"]],
            fliersize=0, medianprops={"color":"black","linewidth":1.5})
sns.stripplot(data=cyc, x="visit", y="score", ax=ax, color="#333333", size=3, alpha=0.5, jitter=0.18)
h2 = res["hypothesis_tests"]["H2_initial_vs_reinspection_MW"]
ax.text(0.03, 0.97, f"Mann–Whitney U = {h2['U']:.0f}, p = {float(h2['p']):.2f}, r = {h2['rank_biserial_r']:.2f}",
        transform=ax.transAxes, va="top", fontsize=9, style="italic")
ax.set_title("Cycle inspections: initial vs. re-inspection scores")
ax.set_xlabel(""); ax.set_ylabel("Violation score")
ax.set_axisbelow(True)
savefig(fig, "fig8_initial_vs_reinspection")
print("ALL FIGURES DONE")
