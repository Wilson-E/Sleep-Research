import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import statsmodels.formula.api as smf

# -----------------------------
# 0) Load data
# -----------------------------
df = pd.read_csv("SleepData.csv")

# Expected columns in your file:
# Date, Weekday, Weekend, SSQ, Refreshed, BedTime, WakeTime, Duration, Awakenings, Caffeine, Alcohol, ParticipantID

# Sort within subject so lagging is correct
df = df.sort_values(["ParticipantID", "Date"]).reset_index(drop=True)

# -----------------------------
# 1) (Paper detail) Exclude subjects with insufficient weekend data
#    "One subject with only weekday and no weekend responses, and another with only one weekend response"
# -----------------------------
weekend_counts = df.groupby("ParticipantID")["Weekend"].sum()
exclude_ids = weekend_counts[weekend_counts <= 1].index.tolist()
df_use = df[~df["ParticipantID"].isin(exclude_ids)].copy()

# -----------------------------
# 2) Create 1-day lag terms for each DV (within-subject)
# -----------------------------
for col in ["SSQ", "Duration", "Awakenings", "Alcohol", "Caffeine"]:
    df_use[f"lag_{col}"] = df_use.groupby("ParticipantID")[col].shift(1)

# Convenience: convert sleep duration minutes -> hours (useful for plotting)
df_use["Duration_hours"] = df_use["Duration"] / 60.0

# -----------------------------
# 3) Fit the 3 primary mixed-effects models (random intercept by subject)
#
# Paper’s example model structure for SSQ:
# SSQ ~ Alcohol + Caffeine + Alcohol:Caffeine + Weekend + Alcohol:Weekend + Caffeine:Weekend + lag(SSQ,1) + (1|Subject)
#  [oai_citation:2‡journal.pone.0291675.pdf](sediment://file_00000000dad4722fadce662ab2f94753)
# -----------------------------
def fit_mixed(dep):
    lag = f"lag_{dep}"
    d = df_use.dropna(subset=[dep, lag]).copy()

    formula = (
        f"{dep} ~ Alcohol + Caffeine + Alcohol:Caffeine "
        f"+ Weekend + Alcohol:Weekend + Caffeine:Weekend "
        f"+ {lag}"
    )

    m = smf.mixedlm(formula, d, groups=d["ParticipantID"])
    r = m.fit(reml=True, method="lbfgs", maxiter=500, disp=False)
    return r, d

res_ssq, d_ssq = fit_mixed("SSQ")
res_dur, d_dur = fit_mixed("Duration")
res_aw,  d_aw  = fit_mixed("Awakenings")

def tidy_result(res, name):
    out = pd.DataFrame({
        "term": res.params.index,
        "coef": res.params.values,
        "se": res.bse.values,
        "z_or_t": res.tvalues.values,      # statsmodels reports z-like values for MixedLM
        "p": res.pvalues.values
    })
    out.insert(0, "model", name)
    return out

tbl = pd.concat([
    tidy_result(res_ssq, "SSQ"),
    tidy_result(res_dur, "Duration(min)"),
    tidy_result(res_aw,  "Awakenings")
], ignore_index=True)

print("\n=== Mixed-effects model coefficients (paper-style predictors) ===")
print(tbl)

# -----------------------------
# 4) Recreate key paper-style plots
#    Fig 1: Caffeine -> Sleep duration (minutes)
#    Fig 2: Alcohol  -> SSQ
#    Fig 3: coefficient plot (SSQ model)
#    Fig 4: coefficient plot (Duration model)
#
# Paper highlights:
# - "for every cup of caffeinated beverage consumed, sleep amount decreased by 10.4 minutes"  [oai_citation:3‡journal.pone.0291675.pdf](sediment://file_00000000dad4722fadce662ab2f94753)
# - "each glass of alcohol consumed predicted a decline in subjective sleep quality of 3 points"  [oai_citation:4‡journal.pone.0291675.pdf](sediment://file_00000000dad4722fadce662ab2f94753)
# - interaction improves SSQ  [oai_citation:5‡journal.pone.0291675.pdf](sediment://file_00000000dad4722fadce662ab2f94753)
# - interaction prevents caffeine-related sleep loss  [oai_citation:6‡journal.pone.0291675.pdf](sediment://file_00000000dad4722fadce662ab2f94753)
# -----------------------------

def marginal_line(res, dep, xvar, xgrid, controls):
    """
    Build a fixed-effects marginal prediction line:
    dep ~ ... using res.fe_params (fixed effects), with other covariates held constant.
    controls is a dict like {"Alcohol":mean, "Caffeine":mean, "Weekend":0, "lag_dep":mean}
    """
    fe = res.fe_params

    def predict_row(x):
        row = controls.copy()
        row[xvar] = x
        # Interactions need to be consistent
        # (statsmodels uses "Alcohol:Caffeine" etc. in fe index)
        y = fe.get("Intercept", 0.0)

        # main effects
        for k in ["Alcohol", "Caffeine", "Weekend"]:
            if k in fe.index:
                y += fe[k] * row.get(k, 0.0)

        # interactions
        if "Alcohol:Caffeine" in fe.index:
            y += fe["Alcohol:Caffeine"] * row.get("Alcohol", 0.0) * row.get("Caffeine", 0.0)
        if "Alcohol:Weekend" in fe.index:
            y += fe["Alcohol:Weekend"] * row.get("Alcohol", 0.0) * row.get("Weekend", 0.0)
        if "Caffeine:Weekend" in fe.index:
            y += fe["Caffeine:Weekend"] * row.get("Caffeine", 0.0) * row.get("Weekend", 0.0)

        # lag
        lag_name = [c for c in fe.index if c.startswith("lag_")]
        if lag_name:
            y += fe[lag_name[0]] * row.get(lag_name[0], 0.0)

        return y

    yhat = np.array([predict_row(x) for x in xgrid])
    return yhat

# Controls (hold at sample means; Weekend=0 to approximate a "weekday" marginal line)
controls_ssq = {
    "Alcohol": d_ssq["Alcohol"].mean(),
    "Caffeine": d_ssq["Caffeine"].mean(),
    "Weekend": 0,
    "lag_SSQ": d_ssq["lag_SSQ"].mean()
}
controls_dur = {
    "Alcohol": d_dur["Alcohol"].mean(),
    "Caffeine": d_dur["Caffeine"].mean(),
    "Weekend": 0,
    "lag_Duration": d_dur["lag_Duration"].mean()
}

# --- Fig 1-style: caffeine vs duration
x_caf = np.linspace(d_dur["Caffeine"].min(), d_dur["Caffeine"].max(), 200)
y_dur = marginal_line(res_dur, "Duration", "Caffeine", x_caf, controls_dur)

plt.figure()
plt.scatter(d_dur["Caffeine"], d_dur["Duration"], alpha=0.35)
plt.plot(x_caf, y_dur, linewidth=2)
plt.xlabel("Caffeine (cups)")
plt.ylabel("Sleep Duration (minutes)")
plt.title("Effect of caffeine on sleep duration (MixedLM marginal line)")
plt.show()

# --- Fig 2-style: alcohol vs SSQ
x_alc = np.linspace(d_ssq["Alcohol"].min(), d_ssq["Alcohol"].max(), 200)
y_ssq = marginal_line(res_ssq, "SSQ", "Alcohol", x_alc, controls_ssq)

plt.figure()
plt.scatter(d_ssq["Alcohol"], d_ssq["SSQ"], alpha=0.35)
plt.plot(x_alc, y_ssq, linewidth=2)
plt.xlabel("Alcohol (glasses)")
plt.ylabel("Subjective Sleep Quality (0-100)")
plt.title("Effect of alcohol on subjective sleep quality (MixedLM marginal line)")
plt.show()

def coef_plot(res, title, drop=("Group Var",)):
    fe = res.params.copy()
    se = res.bse.copy()

    terms = [t for t in fe.index if t not in drop]
    coef = np.array([fe[t] for t in terms])
    err = np.array([1.96 * se[t] for t in terms])

    # Order for readability
    order = np.argsort(coef)
    terms = [terms[i] for i in order]
    coef = coef[order]
    err = err[order]

    plt.figure()
    plt.errorbar(coef, np.arange(len(terms)), xerr=err, fmt='o')
    plt.axvline(0, linewidth=1)
    plt.yticks(np.arange(len(terms)), terms)
    plt.title(title)
    plt.xlabel("Coefficient (95% CI)")
    plt.tight_layout()
    plt.show()

coef_plot(res_ssq, "Fig 3-style coefficient plot: SSQ model")
coef_plot(res_dur, "Fig 4-style coefficient plot: Duration model (minutes)")

# -----------------------------
# 5) Bidirectionality models (sleep -> next-day caffeine/alcohol)
# Paper: sleep variables as IVs; DV is next-day alcohol or caffeine; controls: weekend + lag(DV,1)  [oai_citation:7‡journal.pone.0291675.pdf](sediment://file_00000000dad4722fadce662ab2f94753)
# -----------------------------
def fit_bidirectional(dv, sleep_iv):
    d = df_use.dropna(subset=[dv, f"lag_{dv}", sleep_iv]).copy()
    formula = f"{dv} ~ {sleep_iv} + Weekend + lag_{dv}"
    m = smf.mixedlm(formula, d, groups=d["ParticipantID"])
    r = m.fit(reml=True, method="lbfgs", maxiter=500, disp=False)
    return r

# Next-day caffeine predicted by prior-night sleep variables
b_caf_ssq = fit_bidirectional("Caffeine", "SSQ")
b_caf_dur = fit_bidirectional("Caffeine", "Duration")
b_caf_aw  = fit_bidirectional("Caffeine", "Awakenings")

# Next-day alcohol predicted by prior-night sleep variables
b_alc_ssq = fit_bidirectional("Alcohol", "SSQ")
b_alc_dur = fit_bidirectional("Alcohol", "Duration")
b_alc_aw  = fit_bidirectional("Alcohol", "Awakenings")

print("\n=== Bidirectionality: Next-day Caffeine ~ Sleep + Weekend + lag(Caffeine,1) ===")
print("Caffeine ~ SSQ:\n", b_caf_ssq.summary())
print("Caffeine ~ Duration:\n", b_caf_dur.summary())
print("Caffeine ~ Awakenings:\n", b_caf_aw.summary())

print("\n=== Bidirectionality: Next-day Alcohol ~ Sleep + Weekend + lag(Alcohol,1) ===")
print("Alcohol ~ SSQ:\n", b_alc_ssq.summary())
print("Alcohol ~ Duration:\n", b_alc_dur.summary())
print("Alcohol ~ Awakenings:\n", b_alc_aw.summary())