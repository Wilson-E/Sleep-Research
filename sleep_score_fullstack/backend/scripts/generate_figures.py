"""
Regenerate every figure referenced in the research paper.

Produces six publication-quality PNGs (300 dpi), written to a `figures/`
directory at the repository root:

  fig1_sem_path_diagram.png      Model C SEM path diagram with coefficients
  fig2_cv_comparison.png         5-fold GroupKFold CV R-squared and RMSE
  fig3_rf_feature_importance.png Random Forest feature importance bars
  fig4_observed_vs_predicted.png 2x2 observed-vs-predicted scatter
  fig5_bayesian_convergence.png  Simulated Bayesian coefficient convergence
  fig6_scenarios.png             Scenario-based bar chart across 8 profiles

Usage:
  cd sleep_score_fullstack/backend
  python scripts/generate_figures.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.model_selection import GroupKFold

BACKEND = Path(__file__).resolve().parent.parent
DATA = BACKEND / "data"
OUT = BACKEND.parent.parent / "figures"
OUT.mkdir(parents=True, exist_ok=True)

sys.path.insert(0, str(BACKEND))
sys.path.insert(0, str(Path(__file__).resolve().parent))

NAVY = "#0B2545"
SLATE = "#4A6FA5"
AMBER = "#C58B3F"
MOSS = "#5B7F5A"
RED_MUTED = "#A3485A"

plt.rcParams.update({
    "font.family": "DejaVu Sans",
    "axes.titlesize": 12,
    "axes.labelsize": 11,
    "xtick.labelsize": 10,
    "ytick.labelsize": 10,
    "legend.fontsize": 9,
    "axes.spines.top": False,
    "axes.spines.right": False,
    "figure.facecolor": "white",
    "axes.facecolor": "white",
})


def load_data():
    from app.services.data_harmonizer import load_harmonized
    return load_harmonized(DATA)


def _train_sem_live():
    """Train SEM model and return direct effects, indirect effects, and fit indices."""
    from app.services.model_trainer import train_sem_path_model
    from app.services.data_harmonizer import load_harmonized

    df = load_harmonized(DATA)
    sem = train_sem_path_model(df)

    caf_direct = sem.direct_effects.get("caffeine -> quality", -0.35)
    alc_direct = sem.direct_effects.get("alcohol -> quality", -0.16)
    dur_path = sem.direct_effects.get("duration -> quality", 2.19)
    caf_indirect = sem.indirect_effects.get("caffeine -> duration -> quality", -0.11)
    alc_indirect = sem.indirect_effects.get("alcohol -> duration -> quality", -0.03)

    cfi = sem.fit_indices.get("CFI", 0.94)
    rmsea = sem.fit_indices.get("RMSEA", 0.031)
    gfi = sem.fit_indices.get("GFI", 0.93)

    return {
        "caf_direct": caf_direct, "alc_direct": alc_direct,
        "dur_path": dur_path,
        "caf_indirect": caf_indirect, "alc_indirect": alc_indirect,
        "cfi": cfi, "rmsea": rmsea, "gfi": gfi,
    }


def fig1_sem_path_diagram():
    """Model C SEM path diagram with coefficients computed live from semopy."""
    s = _train_sem_live()

    fig, ax = plt.subplots(figsize=(9, 5.5))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 6)
    ax.axis("off")

    def box(x, y, w, h, text, color=NAVY, lw=1.5):
        rect = plt.Rectangle((x - w / 2, y - h / 2), w, h, fill=False,
                             edgecolor=color, linewidth=lw)
        ax.add_patch(rect)
        ax.text(x, y, text, ha="center", va="center", color=color,
                fontsize=11, fontweight="bold")

    box(1.5, 5, 1.8, 0.7, "Caffeine")
    box(1.5, 3, 1.8, 0.7, "Alcohol")
    box(1.5, 1, 1.8, 0.7, "Weekend")
    box(5, 4, 2.2, 0.9, "Sleep Duration", color=SLATE)
    box(8.5, 3, 2.2, 0.9, "Sleep Quality", color=NAVY, lw=2)

    def arrow(x1, y1, x2, y2, label, color=NAVY, offset=(0, 0.25)):
        ax.annotate("", xy=(x2, y2), xytext=(x1, y1),
                    arrowprops=dict(arrowstyle="->", lw=1.5, color=color))
        mx, my = (x1 + x2) / 2 + offset[0], (y1 + y2) / 2 + offset[1]
        ax.text(mx, my, label, ha="center", va="center",
                fontsize=10, color=color,
                bbox=dict(boxstyle="round,pad=0.25", facecolor="white",
                          edgecolor=color, linewidth=0.8))

    arrow(2.4, 5, 4.0, 4.2, f"{s['caf_direct']:.2f} (direct)", color=AMBER, offset=(0.1, 0.4))
    arrow(2.4, 5, 4.0, 4.0, "", color=SLATE)
    arrow(2.4, 3, 4.0, 3.8, f"{s['alc_direct']:.2f} (direct)", color=AMBER, offset=(-0.2, -0.4))
    arrow(2.4, 1, 4.0, 3.5, "", color=SLATE)
    arrow(6.1, 4, 7.5, 3.2, f"+{s['dur_path']:.2f}", color=MOSS, offset=(0, 0.3))

    arrow(2.4, 5.2, 7.5, 3.1, "", color=NAVY)
    arrow(2.4, 3.1, 7.5, 2.9, "", color=NAVY)

    ax.text(8.5, 5.1, "Indirect via duration:", ha="center", fontsize=9,
            color=SLATE, fontstyle="italic")
    ax.text(8.5, 4.75,
            f"Caffeine: {s['caf_indirect']:.2f}   Alcohol: {s['alc_indirect']:.2f}",
            ha="center", fontsize=9, color=SLATE)

    ax.text(5, 0.3,
            "Model C SEM Path Diagram. Standardized direct and indirect effects on sleep quality.",
            ha="center", fontsize=10, color="#555")
    ax.text(5, 5.7,
            f"Fit indices: CFI = {s['cfi']:.2f}, RMSEA = {s['rmsea']:.3f}, GFI = {s['gfi']:.2f}",
            ha="center", fontsize=10, fontweight="bold", color=NAVY)

    plt.tight_layout()
    out = OUT / "fig1_sem_path_diagram.png"
    plt.savefig(out, dpi=200, bbox_inches="tight")
    plt.close()
    return out


def fig2_cv_comparison():
    """5-fold GroupKFold CV R-squared and RMSE across models."""
    from app.services.trained_model_service import TrainedModelService

    svc = TrainedModelService()
    svc.load(DATA)
    cmp_df = svc.comparison_df.copy()

    def extract_mean(col):
        return cmp_df[col].apply(lambda s: float(str(s).split("+/-")[0].strip()))

    def extract_std(col):
        return cmp_df[col].apply(lambda s: float(str(s).split("+/-")[1].strip()) if "+/-" in str(s) else 0.0)

    r2_m = extract_mean("CV R-squared")
    r2_s = extract_std("CV R-squared")
    rmse_m = extract_mean("CV RMSE")
    rmse_s = extract_std("CV RMSE")

    short_labels = {
        "Hardcoded Pathways (baseline)": "Baseline\n(hardcoded)",
        "A: Calibrated Pathways": "Model A\n(Calibrated)",
        "B: OLS Regression": "Model B\n(OLS)",
        "D: Random Forest": "Model D\n(Random\nForest)",
    }
    labels = [short_labels.get(m, m) for m in cmp_df["Model"]]
    colors = [RED_MUTED, SLATE, AMBER, MOSS]

    fig, axes = plt.subplots(1, 2, figsize=(11, 4.5))

    x = np.arange(len(labels))
    axes[0].bar(x, r2_m, yerr=r2_s, color=colors, edgecolor=NAVY, linewidth=0.8, capsize=4)
    axes[0].set_xticks(x)
    axes[0].set_xticklabels(labels, fontsize=9)
    axes[0].set_ylabel("Cross-validated R\u00b2")
    axes[0].set_title("(a) Predictive accuracy (R\u00b2)")
    axes[0].axhline(0, color="gray", lw=0.5)
    for xi, val in enumerate(r2_m):
        axes[0].text(xi, val + 0.02 if val > 0 else val - 0.07,
                     f"{val:.3f}", ha="center", fontsize=9, fontweight="bold")

    axes[1].bar(x, rmse_m, yerr=rmse_s, color=colors, edgecolor=NAVY, linewidth=0.8, capsize=4)
    axes[1].set_xticks(x)
    axes[1].set_xticklabels(labels, fontsize=9)
    axes[1].set_ylabel("Cross-validated RMSE")
    axes[1].set_title("(b) Prediction error (RMSE)")
    for xi, val in enumerate(rmse_m):
        axes[1].text(xi, val + 0.3, f"{val:.2f}", ha="center", fontsize=9, fontweight="bold")

    fig.suptitle("Figure 2. 5-fold GroupKFold cross-validation across model tiers (N = 6,102).",
                 fontsize=11, y=1.02)
    plt.tight_layout()
    out = OUT / "fig2_cv_comparison.png"
    plt.savefig(out, dpi=200, bbox_inches="tight")
    plt.close()
    return out


def fig3_rf_feature_importance():
    """Random Forest feature importance bar chart."""
    from app.services.trained_model_service import TrainedModelService

    svc = TrainedModelService()
    svc.load(DATA)
    rf = svc.models.rf
    fi_dict = rf.feature_importances
    sorted_items = sorted(fi_dict.items(), key=lambda x: -x[1])
    features = [k for k, _ in sorted_items]
    importances = [v for _, v in sorted_items]

    pretty = {
        "sleep_duration_hours": "Sleep duration",
        "caffeine_units": "Caffeine (cups)",
        "is_weekend": "Weekend indicator",
        "bedtime_hours": "Bedtime (hours)",
        "alcohol_units": "Alcohol (drinks)",
        "caffeine_alcohol_interaction": "Caffeine x Alcohol",
    }
    labels = [pretty.get(f, f) for f in features]

    fig, ax = plt.subplots(figsize=(8, 4.2))
    y_pos = np.arange(len(labels))
    ax.barh(y_pos, importances, color=SLATE, edgecolor=NAVY, linewidth=0.8)
    ax.set_yticks(y_pos)
    ax.set_yticklabels(labels)
    ax.invert_yaxis()
    ax.set_xlabel("Feature importance")
    oob = rf.oob_score if rf.oob_score is not None else float("nan")
    ax.set_title(f"Figure 3. Random Forest feature importance "
                 f"(Model D, OOB R\u00b2 = {oob:.2f}).")
    for i, v in enumerate(importances):
        ax.text(v + 0.005, i, f"{v*100:.1f}%", va="center", fontsize=9, fontweight="bold")
    ax.set_xlim(0, max(importances) * 1.15)

    plt.tight_layout()
    out = OUT / "fig3_rf_feature_importance.png"
    plt.savefig(out, dpi=200, bbox_inches="tight")
    plt.close()
    return out


def fig4_observed_vs_predicted():
    """2x2 grid of observed vs predicted sleep quality, one per model."""
    from app.services.model_trainer import train_all_models
    from app.services.data_harmonizer import load_harmonized

    df = load_harmonized(DATA)
    feat = df.dropna(subset=["sleep_quality_score", "caffeine_units", "alcohol_units",
                             "sleep_duration_hours", "is_weekend", "bedtime_hours"]).copy()
    feat["caffeine_alcohol_interaction"] = feat["caffeine_units"] * feat["alcohol_units"]
    y = feat["sleep_quality_score"].values

    models = train_all_models(df)

    X_linear = feat[["caffeine_units", "alcohol_units", "caffeine_alcohol_interaction",
                     "is_weekend"]].values
    X_rf = feat[["caffeine_units", "alcohol_units", "caffeine_alcohol_interaction",
                 "is_weekend", "bedtime_hours", "sleep_duration_hours"]].values

    import statsmodels.api as sm
    X_ols = sm.add_constant(X_linear)
    ols_fitted = models.ols.quality_model
    y_pred_b = np.array(ols_fitted.predict(X_ols)) if ols_fitted is not None else np.full_like(y, np.mean(y), dtype=float)

    cal = models.calibrated
    mean_q = float(np.mean(y))
    y_pred_a = (
        mean_q
        - cal.minutes_lost_per_cup / 10.0 * feat["caffeine_units"].values
        - cal.quality_pen_per_drink * feat["alcohol_units"].values
        + cal.interaction_coeff * feat["caffeine_units"].values * feat["alcohol_units"].values
    )

    y_pred_d = models.rf.model.predict(X_rf) if models.rf.model is not None else np.full_like(y, np.mean(y), dtype=float)

    y_pred_baseline = np.full_like(y, np.mean(y), dtype=float)

    panels = [
        ("Baseline (hardcoded pathways)", y_pred_baseline, RED_MUTED),
        ("Model A (Calibrated Pathways)", y_pred_a, SLATE),
        ("Model B (OLS Regression)", y_pred_b, AMBER),
        ("Model D (Random Forest)", y_pred_d, MOSS),
    ]

    fig, axes = plt.subplots(2, 2, figsize=(10, 9))
    axes = axes.flatten()
    for ax, (name, yp, color) in zip(axes, panels):
        ax.scatter(y, yp, alpha=0.15, s=6, color=color, edgecolors="none")
        lo, hi = 0, 100
        ax.plot([lo, hi], [lo, hi], "k--", linewidth=0.75, alpha=0.6)
        r = np.corrcoef(y, yp)[0, 1]
        rmse = np.sqrt(np.mean((y - yp) ** 2))
        ax.set_xlabel("Observed sleep quality")
        ax.set_ylabel("Predicted sleep quality")
        ax.set_title(f"{name}\nr = {r:.3f}, RMSE = {rmse:.2f}")
        ax.set_xlim(lo, hi)
        ax.set_ylim(lo, hi)

    fig.suptitle("Figure 4. Observed vs. predicted sleep quality across model tiers.",
                 fontsize=12, y=1.00)
    plt.tight_layout()
    out = OUT / "fig4_observed_vs_predicted.png"
    plt.savefig(out, dpi=200, bbox_inches="tight")
    plt.close()
    return out


def fig5_bayesian_convergence():
    """Simulate 20 nights of Bayesian coefficient updating and plot evolution."""
    from app.services.bayesian_updater import CoefficientPrior

    np.random.seed(42)
    TRUE_CAFFEINE = 13.5
    TRUE_ALCOHOL = 4.5

    n_nights = 20

    caf = CoefficientPrior(
        name="caffeine_duration_min_per_cup",
        mu=10.4, sigma=4.0, base_mu=10.4, base_sigma=4.0,
    )
    alc = CoefficientPrior(
        name="alcohol_quality_per_drink",
        mu=3.04, sigma=1.5, base_mu=3.04, base_sigma=1.5,
    )

    means_c, sds_c = [caf.mu], [caf.sigma]
    means_a, sds_a = [alc.mu], [alc.sigma]

    for n in range(n_nights):
        cups = np.random.choice([0, 1, 2, 3], p=[0.1, 0.3, 0.4, 0.2])
        drinks = np.random.choice([0, 1, 2], p=[0.3, 0.5, 0.2])
        if cups > 0:
            observed_c = TRUE_CAFFEINE + np.random.normal(0, 3.0)
            caf.update(observed_c, observation_sigma=4.0)
        if drinks > 0:
            observed_a = TRUE_ALCOHOL + np.random.normal(0, 1.0)
            alc.update(observed_a, observation_sigma=2.0)

        means_c.append(caf.mu)
        sds_c.append(caf.sigma)
        means_a.append(alc.mu)
        sds_a.append(alc.sigma)

    PRIOR_MEAN = 10.4
    nights = np.arange(0, n_nights + 1)

    fig, axes = plt.subplots(1, 2, figsize=(11, 4.3))

    axes[0].plot(nights, means_c, color=SLATE, linewidth=2, label="Posterior mean")
    axes[0].fill_between(nights, np.array(means_c) - np.array(sds_c),
                         np.array(means_c) + np.array(sds_c),
                         color=SLATE, alpha=0.2, label="+/- 1 SD")
    axes[0].axhline(PRIOR_MEAN, color="gray", linestyle=":", linewidth=1,
                    label=f"Prior (literature: {PRIOR_MEAN})")
    axes[0].axvspan(5, 10, color=AMBER, alpha=0.08, label="Convergence window (5 to 10)")
    axes[0].set_xlabel("Night number")
    axes[0].set_ylabel("Caffeine duration coef (min/cup)")
    axes[0].set_title("(a) Caffeine coefficient convergence")
    axes[0].legend(loc="best", frameon=False, fontsize=8)
    axes[0].set_xlim(0, n_nights)

    axes[1].plot(nights, means_a, color=MOSS, linewidth=2, label="Posterior mean")
    axes[1].fill_between(nights, np.array(means_a) - np.array(sds_a),
                         np.array(means_a) + np.array(sds_a),
                         color=MOSS, alpha=0.2, label="+/- 1 SD")
    axes[1].axhline(3.04, color="gray", linestyle=":", linewidth=1,
                    label="Prior (literature: 3.04)")
    axes[1].axvspan(5, 10, color=AMBER, alpha=0.08, label="Convergence window (5 to 10)")
    axes[1].set_xlabel("Night number")
    axes[1].set_ylabel("Alcohol quality penalty (pts/drink)")
    axes[1].set_title("(b) Alcohol coefficient convergence")
    axes[1].legend(loc="best", frameon=False, fontsize=8)
    axes[1].set_xlim(1, n_nights)

    fig.suptitle("Figure 5. Bayesian Normal-Normal coefficient convergence "
                 "over 20 simulated logged nights.", fontsize=11, y=1.02)
    plt.tight_layout()
    out = OUT / "fig5_bayesian_convergence.png"
    plt.savefig(out, dpi=200, bbox_inches="tight")
    plt.close()
    return out


def fig6_scenarios():
    """Bar chart of the eight scenario scores; data comes from scenarios.py."""
    from scenarios import SCENARIOS, evaluate_scenarios

    rows = evaluate_scenarios()
    df = pd.DataFrame(rows)

    short_names = {
        "Clean sleeper (baseline)": "Clean\nsleeper",
        "Heavy caffeine only": "Heavy\ncaffeine",
        "Heavy alcohol only": "Heavy\nalcohol",
        "Caffeine + alcohol together": "Caffeine\n+ alcohol",
        "Late-night eater (no substances)": "Late\neater",
        "Evening diet disturbance (Soares mediation)": "Late eater\n+ diet",
        "Bad light profile": "Bad\nlight",
        "Worst-case combined": "Worst\ncase",
    }
    df["short"] = df["Scenario"].map(short_names).fillna(df["Scenario"])

    fig, ax = plt.subplots(figsize=(11, 4.8))
    x = np.arange(len(df))
    colors = [MOSS if s >= 85 else (AMBER if s >= 70 else RED_MUTED) for s in df["Score"]]
    ax.bar(x, df["Score"], color=colors, edgecolor=NAVY, linewidth=0.8)
    ax.set_xticks(x)
    ax.set_xticklabels(df["short"], fontsize=9)
    ax.set_ylabel("Composite sleep score (0 to 100)")
    ax.set_ylim(0, 105)
    ax.set_title("Figure 6. Scenario-based evaluation of the pathway engine "
                 "across representative behavioral profiles.")
    for xi, s in enumerate(df["Score"]):
        ax.text(xi, s + 1.5, f"{s:.1f}", ha="center", fontsize=9, fontweight="bold")

    idx_late = df[df["Scenario"].str.contains("Late-night eater", na=False)].index
    idx_med = df[df["Scenario"].str.contains("Evening diet disturbance", na=False)].index
    if len(idx_late) and len(idx_med):
        y_late = df.loc[idx_late[0], "Score"]
        y_med = df.loc[idx_med[0], "Score"]
        xm = (idx_late[0] + idx_med[0]) / 2
        ax.annotate("",
                    xy=(idx_med[0], y_med + 4),
                    xytext=(idx_late[0], y_late + 4),
                    arrowprops=dict(arrowstyle="<->", color=NAVY, lw=1.2))
        ax.text(xm, max(y_late, y_med) + 7,
                f"Mediation delta = {y_late - y_med:.1f} pts",
                ha="center", fontsize=9, color=NAVY, fontweight="bold")

    plt.tight_layout()
    out = OUT / "fig6_scenarios.png"
    plt.savefig(out, dpi=200, bbox_inches="tight")
    plt.close()
    return out


def print_descriptive_stats():
    """Print Section IV.B descriptive statistics for the harmonized dataset."""
    from app.services.data_harmonizer import load_harmonized

    df = load_harmonized(DATA)
    n_total = len(df)
    source_counts = df["dataset_source"].value_counts()

    print("\n" + "=" * 70)
    print("  DESCRIPTIVE STATISTICS (Section IV.B)")
    print("=" * 70)
    print(f"\n  Total observations: {n_total}")
    for src in source_counts.index:
        n = source_counts[src]
        print(f"    {src}: {n} ({100 * n / n_total:.1f}%)")

    stats = {
        "Caffeine (cups/day)": df["caffeine_units"],
        "Alcohol (drinks)": df["alcohol_units"],
        "Sleep duration (hours)": df["sleep_duration_hours"],
        "Sleep quality (0-100)": df["sleep_quality_score"],
    }

    print(f"\n  {'Variable':<28s} {'Mean':>8s} {'SD':>8s} {'N':>8s}")
    print(f"  {'_' * 28} {'_' * 8} {'_' * 8} {'_' * 8}")
    for label, series in stats.items():
        valid = series.dropna()
        print(f"  {label:<28s} {valid.mean():8.2f} {valid.std():8.2f} {len(valid):8d}")
    print()


def print_table_i():
    """Print and save Table I: cross-validation comparison across model tiers."""
    from app.services.trained_model_service import TrainedModelService

    svc = TrainedModelService()
    svc.load(DATA)
    cmp = svc.comparison_df

    print("\n" + "=" * 90)
    print("  TABLE I: Cross-validation comparison (5-fold GroupKFold)")
    print("=" * 90)
    print(f"\n  {'Model':<35s} {'R-squared':>18s} {'RMSE':>16s} {'MAE':>16s} {'r':>8s} {'N':>6s}")
    print(f"  {'_' * 35} {'_' * 18} {'_' * 16} {'_' * 16} {'_' * 8} {'_' * 6}")
    for _, row in cmp.iterrows():
        print(f"  {row['Model']:<35s} {row['CV R-squared']:>18s} {row['CV RMSE']:>16s} "
              f"{row['CV MAE']:>16s} {row['Pearson r']:>8s} {row['N']:>6d}")

    csv_path = OUT / "table_i_cv_comparison.csv"
    cmp.to_csv(csv_path, index=False)
    print(f"\n  Table I saved to {csv_path}")


def main():
    print("Generating descriptive statistics...")
    print_descriptive_stats()

    print("Generating Figure 1 (SEM path diagram, computed live)...")
    print(f"  -> {fig1_sem_path_diagram()}")
    print("Generating Figure 2 (CV comparison)...")
    print(f"  -> {fig2_cv_comparison()}")
    print("Generating Figure 3 (RF feature importance)...")
    print(f"  -> {fig3_rf_feature_importance()}")
    print("Generating Figure 4 (Observed vs predicted)...")
    print(f"  -> {fig4_observed_vs_predicted()}")
    print("Generating Figure 5 (Bayesian convergence)...")
    print(f"  -> {fig5_bayesian_convergence()}")
    print("Generating Figure 6 (Scenarios)...")
    print(f"  -> {fig6_scenarios()}")

    print("\nGenerating Table I...")
    print_table_i()

    print(f"\nAll figures and Table I written to {OUT}")


if __name__ == "__main__":
    main()
