"""Extended analysis for the DSE Monte Carlo portfolio risk project.

Computes, from the saved price and volume data of the main simulation only:
1. Risk decomposition (marginal and component risk contributions,
   component VaR from reproduced GBM paths, seed 42).
2. Diversification test and rolling 63 day average pairwise correlation.
3. Drawdown and downside measures on a daily rebalanced equal weight
   portfolio of simple returns (the definition is stated in outputs).
4. Distribution tests (skewness, excess kurtosis, Jarque-Bera, tail
   moves against a normal prediction, data for a QQ plot).
5. Liquidity measures (traded value, Amihud illiquidity, days to exit).
6. Rolling 63 day volatility and Sharpe, plus named stress scenarios.
7. EWMA volatility (RiskMetrics lambda 0.94) and a GARCH(1,1) fit for
   the portfolio if the arch package is available and converges.
8. Fat tail Monte Carlo with correlated Student-t shocks, 10,000
   simulations, seed 42, horizons 21 / 63 / 252 days, on the same mean
   and covariance basis as the GBM simulation.

Beta against DSEX and the fundamental snapshot are in separate scripts
(extended_fetch_dsex.py, extended_beta.py, extended_fetch_fundamentals.py)
because they need new data. All extended analysis outputs go to data/ with an
extended prefix and to data/extended_results.json. The main simulation files
are read only and never written.
"""
import json
import os

import numpy as np
import pandas as pd
from scipy import stats

TICKERS = ["BATBC", "BXPHARMA", "CITYBANK", "DBH", "EBL", "ROBI", "ACI",
           "BEXIMCO", "FUWANGCER", "GEMINISEA", "SEAPEARL"]
START_VALUE = 1_000_000.0
POSITION = START_VALUE / len(TICKERS)   # Tk 90,909.09 per stock
N_SIMS = 10_000
SEED = 42
HORIZONS = [21, 63, 252]
TD = 252

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(BASE, "data")


def load():
    closes, volumes = {}, {}
    for t in TICKERS:
        df = pd.read_csv(os.path.join(DATA, f"{t}.csv"), parse_dates=["date"])
        df = df.set_index("date").sort_index()
        closes[t] = df["close"]
        volumes[t] = df["volume"]
    return pd.DataFrame(closes), pd.DataFrame(volumes)


def summ(values):
    r = values / START_VALUE - 1.0
    out = {}
    for p in (1, 5, 25, 50, 75, 95, 99):
        out[f"p{p}_value_tk"] = float(np.percentile(values, p))
        out[f"p{p}_return_pct"] = float(100 * np.percentile(r, p))
    out["prob_loss_pct"] = float(100 * np.mean(r < 0))
    out["prob_loss_over_10pct"] = float(100 * np.mean(r < -0.10))
    out["prob_loss_over_20pct"] = float(100 * np.mean(r < -0.20))
    for lv in (95, 99):
        var_r = float(np.percentile(r, 100 - lv))
        cvar_r = float(r[r <= var_r].mean())
        out[f"var{lv}_pct"] = round(-100 * var_r, 2)
        out[f"var{lv}_tk"] = round(-var_r * START_VALUE, 0)
        out[f"cvar{lv}_pct"] = round(-100 * cvar_r, 2)
        out[f"cvar{lv}_tk"] = round(-cvar_r * START_VALUE, 0)
    out["mean_value_tk"] = float(values.mean())
    out["median_value_tk"] = float(np.median(values))
    return out


def main():
    closes, volumes = load()
    logret = np.log(closes / closes.shift(1)).dropna()
    simple = closes.pct_change().dropna()
    n = len(TICKERS)
    w = np.full(n, 1.0 / n)
    R = {}

    # ---------- portfolio daily series (two stated definitions) ----
    # Log-return equal weight series: main simulation basis (mean of log returns).
    port_log = logret.mean(axis=1)
    # Simple-return daily rebalanced equal weight series: drawdown basis.
    port_simple = simple.mean(axis=1)

    # ---------- 1. Risk decomposition ------------------------------
    cov_d = logret.cov().values                    # daily covariance
    cov_a = cov_d * TD
    port_var_a = float(w @ cov_a @ w)
    port_vol_a = float(np.sqrt(port_var_a))
    mrc = (cov_a @ w) / port_vol_a                 # marginal contributions
    crc = w * mrc                                  # component contributions
    risk_rows = []
    for i, t in enumerate(TICKERS):
        risk_rows.append({
            "ticker": t, "capital_weight_pct": round(100 * w[i], 2),
            "annualised_volatility_pct": round(100 * float(np.sqrt(cov_a[i, i])), 2),
            "marginal_risk_contribution": round(float(mrc[i]), 4),
            "component_risk_tk_vol": round(float(crc[i]), 4),
            "pct_of_portfolio_risk": round(100 * float(crc[i] / port_vol_a), 2),
        })
    risk_df = pd.DataFrame(risk_rows).sort_values("pct_of_portfolio_risk",
                                                  ascending=False)
    risk_df.to_csv(os.path.join(DATA, "extended_risk_decomposition.csv"), index=False)
    p = (risk_df["pct_of_portfolio_risk"].values / 100.0)
    p = p[p > 0]
    enb = float(np.exp(-(p * np.log(p)).sum()))
    R["risk_decomposition"] = {
        "portfolio_volatility_pct": round(100 * port_vol_a, 2),
        "effective_number_of_risk_bets": round(enb, 2),
        "top3": risk_df.head(3)[["ticker", "pct_of_portfolio_risk"]]
                .to_dict(orient="records"),
        "beximco_pct_of_risk": float(risk_df.loc[
            risk_df.ticker == "BEXIMCO", "pct_of_portfolio_risk"].iloc[0]),
        "all": risk_df.to_dict(orient="records"),
        "note_beximco": ("BEXIMCO measured risk share is understated: it has "
                         "149 zero volume days and 81.6% zero return days, so "
                         "its daily returns are zero on most days by record, "
                         "not by trading."),
    }

    # Component VaR from GBM paths reproduced with the main simulation code and
    # seed: the same random draws as scripts/simulate.py run_gbm.
    mu = logret.mean().values
    chol = np.linalg.cholesky(cov_d)
    drift = mu - 0.5 * np.diag(cov_d)
    rng = np.random.default_rng(SEED)
    max_h = max(HORIZONS)
    endings_stock = np.empty((N_SIMS, n))
    endings_port = np.empty(N_SIMS)
    done = 0
    while done < N_SIMS:
        b = min(1000, N_SIMS - done)
        z = rng.standard_normal((b, max_h, n))
        daily_log = drift + z @ chol.T
        growth = np.exp(np.cumsum(daily_log, axis=1))
        stock_end = POSITION * growth[:, 251, :]           # per stock, Tk
        endings_stock[done:done + b] = stock_end
        endings_port[done:done + b] = stock_end.sum(axis=1)
        done += b
    check_median = float(np.median(endings_port))
    main_sim = json.load(open(os.path.join(DATA, "results.json")))
    p1_median = float(main_sim["gbm"]["252"]["p50_value_tk"])
    R["gbm_reproduction_check"] = {
        "reproduced_median_252_tk": round(check_median, 2),
        "main_sim_median_252_tk": round(p1_median, 2),
        "difference_tk": round(check_median - p1_median, 2),
    }
    # Worst 5% of portfolio outcomes: average Tk shortfall per stock
    # against its starting Tk 90,909, as a share of total shortfall.
    cutoff = np.percentile(endings_port, 5)
    tail = endings_port <= cutoff
    shortfall = POSITION - endings_stock[tail]             # Tk per stock
    comp_var = shortfall.mean(axis=0)
    comp_rows = []
    for i, t in enumerate(TICKERS):
        comp_rows.append({"ticker": t,
                          "component_var95_tk": round(float(comp_var[i]), 0),
                          "pct_of_cvar_tail_loss": round(
                              100 * float(comp_var[i] / comp_var.sum()), 2)})
    comp_df = pd.DataFrame(comp_rows).sort_values("component_var95_tk",
                                                  ascending=False)
    comp_df.to_csv(os.path.join(DATA, "extended_component_var.csv"), index=False)
    R["component_var95_252"] = {
        "method": ("GBM paths reproduced with seed 42 and the main simulation code. "
                   "For the worst 5% of portfolio outcomes at 252 days, the "
                   "average shortfall of each stock against its starting "
                   "Tk 90,909 is its component VaR; shares sum to 100% of "
                   "the average tail shortfall."),
        "reproduction_ok": bool(abs(check_median - p1_median) < 1.0),
        "all": comp_df.to_dict(orient="records"),
    }

    # ---------- 2. Diversification ---------------------------------
    indiv_vol = np.sqrt(np.diag(cov_a))
    wavg_vol = float((w * indiv_vol).sum())
    corr = logret.corr().values
    iu = np.triu_indices(n, 1)
    avg_corr = float(corr[iu].mean())
    roll_corr = (logret.rolling(63).corr()
                 .groupby(level=0).apply(
                     lambda m: m.values[iu].mean() if m.shape == (n, n)
                     else np.nan).dropna())
    roll_corr.rename("avg_pairwise_corr_63d").to_csv(
        os.path.join(DATA, "extended_rolling_correlation.csv"))
    R["diversification"] = {
        "weighted_avg_individual_volatility_pct": round(100 * wavg_vol, 2),
        "portfolio_volatility_pct": round(100 * port_vol_a, 2),
        "diversification_ratio": round(wavg_vol / port_vol_a, 2),
        "average_pairwise_correlation": round(avg_corr, 3),
        "rolling_63d_avg_corr_min": round(float(roll_corr.min()), 3),
        "rolling_63d_avg_corr_max": round(float(roll_corr.max()), 3),
        "rolling_63d_avg_corr_latest": round(float(roll_corr.iloc[-1]), 3),
    }

    # ---------- 3. Drawdown and downside ---------------------------
    cum = (1.0 + port_simple).cumprod()
    wealth = START_VALUE * cum
    run_max = wealth.cummax()
    dd_series = wealth / run_max - 1.0
    trough_date = dd_series.idxmin()
    max_dd = float(dd_series.min())
    peak_date = wealth.loc[:trough_date].idxmax()
    after = wealth.loc[trough_date:]
    rec = after[after >= wealth.loc[peak_date]]
    recovered = len(rec) > 0
    total_ret = float(cum.iloc[-1] - 1.0)
    years = len(port_simple) / TD
    cagr = float(cum.iloc[-1] ** (1.0 / years) - 1.0)
    downside = np.sqrt((np.minimum(port_simple, 0) ** 2).mean()) * np.sqrt(TD)
    arith_ann = float(port_simple.mean() * TD)
    sortino = arith_ann / float(downside) if downside > 0 else None
    calmar = cagr / abs(max_dd) if max_dd < 0 else None
    q = {}
    for lv, tailp in ((95, 0.05), (99, 0.01)):
        v = float(port_simple.quantile(tailp))
        cv = float(port_simple[port_simple <= v].mean())
        q[f"daily_var{lv}_pct"] = round(-100 * v, 2)
        q[f"daily_cvar{lv}_pct"] = round(-100 * cv, 2)
    worst10 = port_simple.nsmallest(10)
    worst_rows = []
    for d, r in worst10.items():
        day = simple.loc[d].nsmallest(3)
        worst_rows.append({
            "date": d.strftime("%Y-%m-%d"), "portfolio_return_pct": round(100 * float(r), 2),
            "worst_stocks": ", ".join(f"{t} {100 * float(v):.2f}%"
                                      for t, v in day.items())})
    pd.DataFrame(worst_rows).to_csv(
        os.path.join(DATA, "extended_worst_days.csv"), index=False)
    dd_df = pd.DataFrame({"date": wealth.index.strftime("%Y-%m-%d"),
                          "wealth_tk": wealth.values,
                          "drawdown_pct": 100 * dd_series.values})
    dd_df.to_csv(os.path.join(DATA, "extended_drawdown_series.csv"), index=False)
    R["drawdown_downside"] = {
        "definition": ("Portfolio path: daily rebalanced equal weight "
                       "portfolio of simple (percentage) daily returns. "
                       "This path definition is used for every number in "
                       "this section."),
        "total_return_pct": round(100 * total_ret, 2),
        "ending_value_tk": round(float(wealth.iloc[-1]), 0),
        "cagr_pct": round(100 * cagr, 2),
        "arithmetic_annualised_return_pct": round(100 * arith_ann, 2),
        "max_drawdown_pct": round(100 * max_dd, 2),
        "peak_date": peak_date.strftime("%Y-%m-%d"),
        "trough_date": trough_date.strftime("%Y-%m-%d"),
        "drawdown_duration_trading_days": int(
            list(wealth.index).index(trough_date) - list(wealth.index).index(peak_date)),
        "recovered_by_end": bool(recovered),
        "recovery_date": (rec.index[0].strftime("%Y-%m-%d") if recovered else None),
        "calmar_ratio_cagr_over_maxdd": round(float(calmar), 3) if calmar else None,
        "downside_deviation_pct": round(100 * float(downside), 2),
        "sortino_ratio_rf0": round(float(sortino), 3) if sortino else None,
        "pct_positive_days": round(100 * float((port_simple > 0).mean()), 2),
        **q,
        "worst_10_days": worst_rows,
    }

    # ---------- 4. Distribution tests -------------------------------
    dist_rows = []
    for name, series in [(t, logret[t]) for t in TICKERS] + [("PORTFOLIO", port_log)]:
        jb_stat, jb_p = stats.jarque_bera(series.values)
        dist_rows.append({
            "series": name,
            "skewness": round(float(stats.skew(series.values)), 3),
            "excess_kurtosis": round(float(stats.kurtosis(series.values)), 3),
            "jarque_bera": round(float(jb_stat), 1),
            "jarque_bera_p": float(jb_p),
            "normality_rejected_5pct": bool(jb_p < 0.05),
        })
    dist_df = pd.DataFrame(dist_rows)
    dist_df.to_csv(os.path.join(DATA, "extended_distribution_tests.csv"), index=False)
    mu_s, sd_s = float(port_simple.mean()), float(port_simple.std(ddof=1))
    emp = {"empirical_p1_pct": round(100 * float(port_simple.quantile(0.01)), 2),
           "empirical_p99_pct": round(100 * float(port_simple.quantile(0.99)), 2),
           "normal_p1_pct": round(100 * float(mu_s + sd_s * stats.norm.ppf(0.01)), 2),
           "normal_p99_pct": round(100 * float(mu_s + sd_s * stats.norm.ppf(0.99)), 2)}
    theo = stats.norm.ppf((np.arange(1, len(port_log) + 1) - 0.5) / len(port_log))
    qq = pd.DataFrame({"theoretical_quantile": theo,
                       "sample_quantile": np.sort(port_log.values)})
    qq.to_csv(os.path.join(DATA, "extended_qq_data.csv"), index=False)
    prow = dist_df[dist_df.series == "PORTFOLIO"].iloc[0]
    R["distribution"] = {
        "basis": "Daily log returns for skewness, kurtosis and Jarque-Bera; daily simple returns for the tail comparison.",
        "portfolio": prow.to_dict(),
        "tail_simple_returns": emp,
        "all": dist_rows,
    }

    # ---------- 5. Liquidity ----------------------------------------
    liq_rows = []
    for t in TICKERS:
        traded = (volumes[t] * closes[t])          # Tk per day
        absret = simple[t].abs()
        valid = traded > 0
        amihud = float((absret[valid] / traded[valid]).mean() * 1e9)
        med = float(traded.median())
        days100 = POSITION / med if med > 0 else float("inf")
        days20 = POSITION / (0.20 * med) if med > 0 else float("inf")
        zret = float((simple[t] == 0).mean() * 100)
        zvol = int((volumes[t] == 0).sum())
        if days20 > 5:
            grade = "Trapped"
        elif days20 <= 1 and zret <= 10 and zvol <= 5:
            grade = "Good"
        else:
            grade = "Thin"
        liq_rows.append({
            "ticker": t, "median_daily_traded_value_tk": round(med, 0),
            "mean_daily_traded_value_tk": round(float(traded.mean()), 0),
            "amihud_illiquidity_x1e9": round(amihud, 4),
            "zero_volume_days": zvol,
            "pct_zero_return_days": round(zret, 2),
            "days_to_exit_100pct_of_median": round(float(days100), 3),
            "days_to_exit_20pct_of_median": round(float(days20), 2),
            "liquidity_grade": grade,
        })
    liq_df = pd.DataFrame(liq_rows)
    liq_df.to_csv(os.path.join(DATA, "extended_liquidity.csv"), index=False)
    R["liquidity"] = {
        "grade_rule": ("Good: position sells within 1 day at 20% of median "
                       "daily traded value, zero return days at most 10% and "
                       "zero volume days at most 5. Trapped: more than 5 days "
                       "needed at 20% of median daily traded value. All other "
                       "stocks: Thin."),
        "amihud_formula": ("Average over trading days of absolute daily "
                           "return divided by daily traded value in Tk "
                           "(volume x close), shown multiplied by 1e9. "
                           "Higher means a given Tk of trading moves the "
                           "price more."),
        "grades": liq_df[["ticker", "liquidity_grade",
                          "days_to_exit_20pct_of_median"]]
                  .to_dict(orient="records"),
        "all": liq_df.to_dict(orient="records"),
    }

    # ---------- 6. Rolling risk and stress tests --------------------
    roll_vol = port_log.rolling(63).std(ddof=1) * np.sqrt(TD)
    roll_mean = port_simple.rolling(63).mean() * TD
    roll_sd = port_simple.rolling(63).std(ddof=1) * np.sqrt(TD)
    roll_sharpe = (roll_mean / roll_sd).replace([np.inf, -np.inf], np.nan)
    roll = pd.DataFrame({"date": port_log.index.strftime("%Y-%m-%d"),
                         "rolling_vol_63d_pct": 100 * roll_vol.values,
                         "rolling_sharpe_63d": roll_sharpe.values})
    roll.to_csv(os.path.join(DATA, "extended_rolling_risk.csv"), index=False)
    R["rolling_risk"] = {
        "vol_63d_min_pct": round(100 * float(roll_vol.min()), 2),
        "vol_63d_max_pct": round(100 * float(roll_vol.max()), 2),
        "vol_63d_latest_pct": round(100 * float(roll_vol.iloc[-1]), 2),
        "sharpe_63d_min": round(float(roll_sharpe.min()), 2),
        "sharpe_63d_max": round(float(roll_sharpe.max()), 2),
        "sharpe_63d_latest": round(float(roll_sharpe.iloc[-1]), 2),
    }

    def loss(shocks):
        """shocks: dict ticker -> fractional price change. Equal weights."""
        frac = float(np.mean([shocks.get(t, 0.0) for t in TICKERS]))
        return frac
    worst5 = port_simple.nsmallest(5).values
    s_a = float(np.prod(1.0 + worst5) - 1.0)
    scenarios = [
        ("A. Five worst real days back to back (hypothetical)",
         s_a, "The five worst real portfolio days in the window, joined as if they happened one after another."),
        ("B. CITYBANK, EBL and DBH each fall 20% (hypothetical)",
         loss({"CITYBANK": -0.20, "EBL": -0.20, "DBH": -0.20}),
         "Three of the 11 equal weights fall 20%; the other eight do not move."),
        ("C. BEXIMCO falls to zero (hypothetical)",
         loss({"BEXIMCO": -1.0}),
         "One equal weight of 9.09% is lost in full."),
        ("D. Every stock falls 10% in one day (hypothetical)",
         loss({t: -0.10 for t in TICKERS}),
         "A full circuit breaker day for the whole set."),
        ("E. SEAPEARL, FUWANGCER and GEMINISEA each fall 30% (hypothetical)",
         loss({"SEAPEARL": -0.30, "FUWANGCER": -0.30, "GEMINISEA": -0.30}),
         "The three highest risk contributors fall 30% together."),
        ("F. Every stock falls 10%, then BEXIMCO falls to zero (hypothetical)",
         float((10.0 / 11) * 0.90 + (1.0 / 11) * 0.0 - 1.0),
         "First a 10% fall in all 11, then the remaining BEXIMCO value is lost in full."),
    ]
    stress_rows = [{"scenario": name, "loss_pct": round(-100 * f, 2),
                    "loss_tk": round(-f * START_VALUE, 0),
                    "ending_value_tk": round((1 + f) * START_VALUE, 0),
                    "detail": detail}
                   for name, f, detail in scenarios]
    stress_df = pd.DataFrame(stress_rows).sort_values("loss_tk", ascending=False)
    stress_df.to_csv(os.path.join(DATA, "extended_stress_tests.csv"), index=False)
    R["stress_tests"] = {"worst_5_real_days_pct": [round(100 * float(x), 2) for x in worst5],
                         "scenarios": stress_df.to_dict(orient="records"),
                         "worst_scenario": stress_df.iloc[0]["scenario"]}

    # ---------- 7b. EWMA and GARCH ----------------------------------
    lam = 0.94
    var_ewma = np.empty(len(port_log))
    var_ewma[0] = float(port_log.var(ddof=1))
    r2 = port_log.values ** 2
    for i in range(1, len(port_log)):
        var_ewma[i] = lam * var_ewma[i - 1] + (1 - lam) * r2[i - 1]
    ewma_vol = np.sqrt(var_ewma * TD)
    pd.DataFrame({"date": port_log.index.strftime("%Y-%m-%d"),
                  "ewma_vol_pct": 100 * ewma_vol,
                  "rolling_vol_63d_pct": 100 * roll_vol.values}).to_csv(
        os.path.join(DATA, "extended_ewma.csv"), index=False)
    R["ewma"] = {"lambda": lam,
                 "latest_vol_pct": round(100 * float(ewma_vol[-1]), 2),
                 "min_vol_pct": round(100 * float(ewma_vol.min()), 2),
                 "max_vol_pct": round(100 * float(ewma_vol.max()), 2)}
    garch = {"attempted": False}
    try:
        from arch import arch_model
        garch["attempted"] = True
        am = arch_model(port_log.values * 100, vol="Garch", p=1, q=1,
                        rescale=False)
        res = am.fit(disp="off")
        prm = res.params
        omega, alpha, beta = (float(prm["omega"]), float(prm["alpha[1]"]),
                              float(prm["beta[1]"]))
        fc = res.forecast(horizon=1, reindex=False)
        next_var = float(fc.variance.values[-1, 0])     # in %^2 units
        garch.update({
            "fitted": True, "omega": round(omega, 4), "alpha": round(alpha, 4),
            "beta": round(beta, 4), "persistence_alpha_plus_beta": round(alpha + beta, 4),
            "next_day_vol_pct": round(float(np.sqrt(next_var)), 3),
            "next_day_vol_annualised_pct": round(float(np.sqrt(next_var) * np.sqrt(TD)), 2),
            "loglikelihood": round(float(res.loglikelihood), 1),
            "flag": ("Sample is 468 daily returns. GARCH(1,1) results at "
                     "this size are borderline and are shown as a check on "
                     "the EWMA result, not as a separate forecast to trade on."),
        })
    except Exception as e:  # noqa: BLE001
        garch.update({"fitted": False, "error": str(e)[:300]})
    R["garch"] = garch

    # ---------- 8. Fat tail Monte Carlo (Student-t) ------------------
    excess_kurt = float(stats.kurtosis(port_log.values))
    df_est = 4.0 + 6.0 / excess_kurt if excess_kurt > 0 else 30.0
    df_use = float(min(max(df_est, 3.5), 30.0))
    rng_t = np.random.default_rng(SEED)
    endings_t = {h: np.empty(N_SIMS) for h in HORIZONS}
    scale = np.sqrt((df_use - 2.0) / df_use)
    done = 0
    while done < N_SIMS:
        b = min(1000, N_SIMS - done)
        z = rng_t.standard_normal((b, max_h, n))
        corr_z = z @ chol.T
        chi = rng_t.chisquare(df_use, size=(b, max_h, 1))
        t_shocks = corr_z / np.sqrt(chi / df_use) * scale
        daily_log = drift + t_shocks
        growth = np.exp(np.cumsum(daily_log, axis=1))
        port = growth.mean(axis=2)
        for h in HORIZONS:
            endings_t[h][done:done + b] = START_VALUE * port[:, h - 1]
        done += b
    t_res = {str(h): summ(endings_t[h]) for h in HORIZONS}
    pd.DataFrame(t_res).T.to_csv(os.path.join(DATA, "extended_student_t_results.csv"))
    np.savez_compressed(os.path.join(DATA, "extended_ending_values.npz"),
                        **{f"studentt_{k}": v for k, v in endings_t.items()})
    comp = {}
    for h in HORIZONS:
        hs = str(h)
        comp[hs] = {}
        for method, src in (("gbm", main_sim["gbm"][hs]),
                            ("bootstrap", main_sim["bootstrap"][hs]),
                            ("student_t", t_res[hs])):
            comp[hs][method] = {
                "median_value_tk": round(float(src["p50_value_tk"]), 0),
                "var95_tk": float(src["var95_tk"]), "var99_tk": float(src["var99_tk"]),
                "cvar95_tk": float(src["cvar95_tk"]), "cvar99_tk": float(src["cvar99_tk"]),
                "prob_loss_pct": round(float(src["prob_loss_pct"]), 2)}
    R["student_t"] = {
        "df_method": ("Method of moments from the excess kurtosis of the "
                      "portfolio daily log returns: excess kurtosis = "
                      "6 / (df - 4) for a Student-t, so df = 4 + 6 / "
                      "excess kurtosis."),
        "portfolio_excess_kurtosis": round(excess_kurt, 3),
        "df_estimated": round(df_est, 2), "df_used": round(df_use, 2),
        "scaling": ("Shocks are divided by their standard deviation so the "
                    "simulated covariance matches the historical covariance, "
                    "the same basis as the GBM simulation."),
        "results": t_res, "three_method_comparison": comp,
    }

    with open(os.path.join(DATA, "extended_results.json"), "w") as f:
        json.dump(R, f, indent=1, default=str)
    print(json.dumps({k: R[k] for k in ("risk_decomposition", "diversification",
                                        "drawdown_downside", "rolling_risk",
                                        "ewma", "garch")}, indent=1, default=str)[:3000])
    print("student-t df:", df_use, "252 median/var95/cvar95:",
          t_res["252"]["median_value_tk"], t_res["252"]["var95_tk"],
          t_res["252"]["cvar95_tk"], "prob loss", t_res["252"]["prob_loss_pct"])
    print("stress worst:", stress_df.iloc[0].to_dict())
    print("liquidity grades:", liq_df[["ticker", "liquidity_grade",
                                       "days_to_exit_20pct_of_median"]].to_dict(orient="records"))


if __name__ == "__main__":
    main()
