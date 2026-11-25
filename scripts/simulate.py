"""Monte Carlo portfolio risk simulation for the 11 DSE tickers.

Methods (10,000 paths each, seed 42, horizons 21 / 63 / 252 trading days):
1. Correlated Geometric Brownian Motion. Daily log returns are drawn
   from a multivariate normal distribution using the historical mean
   vector and covariance matrix. The covariance matrix is split with a
   Cholesky decomposition so the simulated stocks keep the correlations
   seen in the real data. Prices are simulated stock by stock and then
   combined with equal weights.
2. Historical bootstrap. Actual historical daily portfolio returns
   (equal weight, the mean of the 11 stock returns each day) are
   resampled with replacement and compounded.

Starting value: Tk 1,000,000, equal weight (1/11 in each stock).
Risk-free rate for Sharpe: 0%, stated here and in the report.
Prices are the unadjusted closing prices published by the DSE.
"""
import json
import os

import numpy as np
import pandas as pd

TICKERS = ["BATBC", "BXPHARMA", "CITYBANK", "DBH", "EBL", "ROBI", "ACI",
           "BEXIMCO", "FUWANGCER", "GEMINISEA", "SEAPEARL"]
START_VALUE = 1_000_000.0
N_SIMS = 10_000
SEED = 42
HORIZONS = [21, 63, 252]
TRADING_DAYS = 252
RISK_FREE = 0.0

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(BASE, "data")


def load_prices():
    frames = {}
    for t in TICKERS:
        df = pd.read_csv(os.path.join(DATA, f"{t}.csv"), parse_dates=["date"])
        frames[t] = df.set_index("date")
    closes = pd.DataFrame({t: frames[t]["close"] for t in TICKERS}).sort_index()
    volumes = pd.DataFrame({t: frames[t]["volume"] for t in TICKERS}).sort_index()
    return closes, volumes, frames


def coverage(closes, volumes, frames):
    """Per-ticker data coverage and problem counts, from the real data."""
    all_days = len(closes)
    rows = []
    for t in TICKERS:
        s = closes[t]
        daily = s.pct_change().dropna()
        f = frames[t].reset_index()
        rows.append({
            "ticker": t,
            "first_date": s.index.min().strftime("%Y-%m-%d"),
            "last_date": s.index.max().strftime("%Y-%m-%d"),
            "rows": int(s.notna().sum()),
            "missing_days_vs_common_calendar": int(all_days - s.notna().sum()),
            "pct_days_zero_return": round(100 * float((daily == 0).mean()), 2),
            "zero_volume_days": int((volumes[t] == 0).sum()),
            "median_daily_volume": float(volumes[t].median()),
            "moves_above_plus_9pct": int((daily > 0.09).sum()),
            "moves_below_minus_9pct": int((daily < -0.09).sum()),
            "largest_daily_rise_pct": round(100 * float(daily.max()), 2),
            "largest_daily_fall_pct": round(100 * float(daily.min()), 2),
            "largest_fall_date": daily.idxmin().strftime("%Y-%m-%d"),
            "filled_days": 0,
        })
    return pd.DataFrame(rows)


def per_stock_stats(closes):
    logret = np.log(closes / closes.shift(1)).dropna()
    rows = []
    for t in TICKERS:
        r = logret[t]
        ann_ret = float(r.mean() * TRADING_DAYS)
        ann_vol = float(r.std(ddof=1) * np.sqrt(TRADING_DAYS))
        rows.append({
            "ticker": t,
            "start_close_tk": float(closes[t].iloc[0]),
            "end_close_tk": float(closes[t].iloc[-1]),
            "total_return_pct": round(100 * float(closes[t].iloc[-1] / closes[t].iloc[0] - 1), 2),
            "annualised_return_pct": round(100 * ann_ret, 2),
            "annualised_volatility_pct": round(100 * ann_vol, 2),
            "best_day_pct": round(100 * float(np.expm1(r.max())), 2),
            "worst_day_pct": round(100 * float(np.expm1(r.min())), 2),
            "sharpe_rf_0pct": round((ann_ret - RISK_FREE) / ann_vol, 3) if ann_vol else None,
        })
    return pd.DataFrame(rows), logret


def summarise_endings(endings):
    """endings: array of ending portfolio values for one horizon."""
    rets = endings / START_VALUE - 1.0
    out = {}
    for p in (1, 5, 25, 50, 75, 95, 99):
        out[f"p{p}_value_tk"] = float(np.percentile(endings, p))
        out[f"p{p}_return_pct"] = float(100 * np.percentile(rets, p))
    out["prob_loss_pct"] = float(100 * np.mean(rets < 0))
    out["prob_loss_over_10pct"] = float(100 * np.mean(rets < -0.10))
    out["prob_loss_over_20pct"] = float(100 * np.mean(rets < -0.20))
    for level in (95, 99):
        tail = 100 - level
        var_ret = float(np.percentile(rets, tail))          # negative number
        cvar_ret = float(rets[rets <= var_ret].mean())
        out[f"var{level}_pct"] = round(-100 * var_ret, 2)   # loss, positive
        out[f"var{level}_tk"] = round(-var_ret * START_VALUE, 0)
        out[f"cvar{level}_pct"] = round(-100 * cvar_ret, 2)
        out[f"cvar{level}_tk"] = round(-cvar_ret * START_VALUE, 0)
    out["mean_value_tk"] = float(endings.mean())
    return out


def run_gbm(logret):
    mu = logret.mean().values                     # daily, per stock
    cov = logret.cov().values                      # daily
    chol = np.linalg.cholesky(cov)
    rng = np.random.default_rng(SEED)
    max_h = max(HORIZONS)
    n = len(TICKERS)
    # Simulate the longest horizon once, in blocks to limit memory.
    # endings[h] collects the ending value at each horizon.
    endings = {h: np.empty(N_SIMS) for h in HORIZONS}
    fan_days = [0] + list(range(6, max_h + 1, 6)) + [max_h]
    fan = {d: np.empty(N_SIMS) for d in fan_days}
    max_dd = np.empty(N_SIMS)
    block = 1000
    done = 0
    while done < N_SIMS:
        b = min(block, N_SIMS - done)
        z = rng.standard_normal((b, max_h, n))
        shocks = z @ chol.T                        # correlated log returns
        drift = mu - 0.5 * np.diag(cov)
        daily_log = drift + shocks                 # (b, days, stocks)
        stock_growth = np.exp(np.cumsum(daily_log, axis=1))   # relative to 1
        port = stock_growth.mean(axis=2)           # equal weight portfolio
        paths = START_VALUE * port                 # (b, days)
        for h in HORIZONS:
            endings[h][done:done + b] = paths[:, h - 1]
        for d in fan_days:
            if d == 0:
                fan[d][done:done + b] = START_VALUE
            else:
                fan[d][done:done + b] = paths[:, d - 1]
        running_max = np.maximum.accumulate(
            np.hstack([np.full((b, 1), START_VALUE), paths]), axis=1)
        dd = (running_max - np.hstack([np.full((b, 1), START_VALUE), paths])) / running_max
        max_dd[done:done + b] = dd.max(axis=1)
        done += b
    results = {h: summarise_endings(endings[h]) for h in HORIZONS}
    fan_rows = []
    for d in fan_days:
        vals = fan[d]
        fan_rows.append({"day": d,
                         **{f"p{p}": float(np.percentile(vals, p))
                            for p in (1, 5, 25, 50, 75, 95, 99)}})
    dd = {"median_max_drawdown_pct": round(100 * float(np.median(max_dd)), 2),
          "p95_max_drawdown_pct": round(100 * float(np.percentile(max_dd, 95)), 2),
          "p99_max_drawdown_pct": round(100 * float(np.percentile(max_dd, 99)), 2),
          "mean_max_drawdown_pct": round(100 * float(max_dd.mean()), 2)}
    endings_out = {str(h): endings[h] for h in HORIZONS}
    return results, pd.DataFrame(fan_rows), dd, endings_out


def run_bootstrap(logret):
    port_daily = np.expm1(logret).mean(axis=1).values   # simple returns
    rng = np.random.default_rng(SEED)
    results, endings_out = {}, {}
    for h in HORIZONS:
        idx = rng.integers(0, len(port_daily), size=(N_SIMS, h))
        growth = np.prod(1.0 + port_daily[idx], axis=1)
        endings = START_VALUE * growth
        results[h] = summarise_endings(endings)
        endings_out[str(h)] = endings
    return results, endings_out


def main():
    closes, volumes, frames = load_prices()
    cov_df = coverage(closes, volumes, frames)
    cov_df.to_csv(os.path.join(DATA, "data_coverage.csv"), index=False)
    stats, logret = per_stock_stats(closes)
    stats.to_csv(os.path.join(DATA, "per_stock_stats.csv"), index=False)
    corr = logret.corr()
    corr.to_csv(os.path.join(DATA, "correlation.csv"))
    port_log = logret.mean(axis=1)
    gbm, fan, dd, gbm_end = run_gbm(logret)
    boot, boot_end = run_bootstrap(logret)
    for name, res in (("gbm", gbm), ("bootstrap", boot)):
        pd.DataFrame(res).T.to_csv(os.path.join(DATA, f"{name}_results.csv"))
    fan.to_csv(os.path.join(DATA, "gbm_fan_chart.csv"), index=False)
    np.savez_compressed(os.path.join(DATA, "ending_values.npz"),
                        **{f"gbm_{k}": v for k, v in gbm_end.items()},
                        **{f"boot_{k}": v for k, v in boot_end.items()})
    results = {
        "window": {"first_date": closes.index.min().strftime("%Y-%m-%d"),
                   "last_date": closes.index.max().strftime("%Y-%m-%d"),
                   "trading_days": int(len(closes)),
                   "return_observations": int(len(logret))},
        "settings": {"start_value_tk": START_VALUE, "weights": "equal, 1/11 each",
                     "simulations": N_SIMS, "seed": SEED, "horizons": HORIZONS,
                     "risk_free_rate_pct": 0.0},
        "portfolio_history": {
            "annualised_return_pct": round(100 * float(port_log.mean() * TRADING_DAYS), 2),
            "annualised_volatility_pct": round(100 * float(port_log.std(ddof=1) * np.sqrt(TRADING_DAYS)), 2),
            "best_day_pct": round(100 * float(np.expm1(port_log.max())), 2),
            "worst_day_pct": round(100 * float(np.expm1(port_log.min())), 2),
            "pct_days_zero_portfolio_return": round(100 * float((np.expm1(port_log) == 0).mean()), 2),
        },
        "gbm": {str(k): v for k, v in gbm.items()},
        "bootstrap": {str(k): v for k, v in boot.items()},
        "gbm_max_drawdown_252": dd,
        "coverage": cov_df.to_dict(orient="records"),
        "per_stock": stats.to_dict(orient="records"),
    }
    with open(os.path.join(DATA, "results.json"), "w") as f:
        json.dump(results, f, indent=1)
    print(json.dumps({"window": results["window"],
                      "portfolio_history": results["portfolio_history"],
                      "gbm_252": gbm[252], "boot_252": boot[252], "dd": dd}, indent=1))
    print(stats.to_string(index=False))
    print(cov_df.to_string(index=False))


if __name__ == "__main__":
    main()
