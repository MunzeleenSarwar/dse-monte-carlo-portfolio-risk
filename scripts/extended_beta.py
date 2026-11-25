"""Beta against DSEX (extended analysis).

Reads data/extended_dsex.csv if extended_fetch_dsex.py managed to fetch it
and runs OLS regressions of daily log returns on DSEX daily log
returns for the portfolio and each stock (alpha, beta, standard errors,
p-values, correlation, R-squared, using statsmodels).

At the time the extended analysis was built, no source returned a daily DSEX series
for the window (attempts are logged in data/extended_dsex_fetch_log.csv),
so this script records the beta section as a limitation in
data/extended_results.json and does not substitute any proxy.
"""
import json
import os

import numpy as np
import pandas as pd

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(BASE, "data")
TICKERS = ["BATBC", "BXPHARMA", "CITYBANK", "DBH", "EBL", "ROBI", "ACI",
           "BEXIMCO", "FUWANGCER", "GEMINISEA", "SEAPEARL"]


def main():
    path = os.path.join(DATA, "extended_results.json")
    R = json.load(open(path))
    dsex_path = os.path.join(DATA, "extended_dsex.csv")
    if not os.path.exists(dsex_path):
        attempts = pd.read_csv(os.path.join(DATA, "extended_dsex_fetch_log.csv"))
        R["beta_vs_dsex"] = {
            "status": "not_computed",
            "reason": ("No daily DSEX index series for 3 Nov 2024 to 15 Oct "
                       "2026 could be fetched from any source tried. The "
                       "DSE day-end API used for the stock prices holds no "
                       "index instruments (DSEX, DSEX_IDX, DSE30, DSES and "
                       "INDEX all returned zero rows). stocksurferbd index "
                       "history reads old.dsebd.org, which did not respond. "
                       "The graph endpoint of the same library does not "
                       "serve DSEX. stockanalysis.com has no DSEX index page "
                       "(HTTP 404) and the DSE index archive page returns "
                       "HTTP 410. Full attempts: data/extended_dsex_fetch_log.csv."),
            "proxy_substituted": False,
            "attempts": attempts.to_dict(orient="records"),
        }
        json.dump(R, open(path, "w"), indent=1, default=str)
        print("Beta not computed: DSEX fetch failed, recorded as limitation.")
        return
    import statsmodels.api as sm
    closes = pd.read_csv(os.path.join(DATA, "combined_close.csv"),
                         parse_dates=["date"], index_col="date")
    dsex = pd.read_csv(dsex_path, parse_dates=["date"], index_col="date")
    mkt = np.log(dsex["dsex_close"] / dsex["dsex_close"].shift(1))
    logret = np.log(closes / closes.shift(1))
    df = pd.DataFrame({"DSEX": mkt}).join(logret, how="inner").dropna()
    rows = []
    series = {"PORTFOLIO": df[TICKERS].mean(axis=1)}
    for t in TICKERS:
        series[t] = df[t]
    for name, y in series.items():
        X = sm.add_constant(df["DSEX"].values)
        res = sm.OLS(y.values, X).fit()
        rows.append({"series": name,
                     "beta": round(float(res.params[1]), 3),
                     "alpha_daily_pct": round(100 * float(res.params[0]), 4),
                     "alpha_se_daily_pct": round(100 * float(res.bse[0]), 4),
                     "alpha_p_value": float(res.pvalues[0]),
                     "alpha_annualised_pct": round(100 * float(res.params[0]) * 252, 2),
                     "correlation": round(float(np.corrcoef(y, df["DSEX"])[0, 1]), 3),
                     "r_squared": round(float(res.rsquared), 3),
                     "observations": int(len(y))})
    out = pd.DataFrame(rows)
    out.to_csv(os.path.join(DATA, "extended_beta.csv"), index=False)
    port = out[out.series == "PORTFOLIO"].iloc[0]
    R["beta_vs_dsex"] = {
        "status": "computed", "observations": int(port["observations"]),
        "portfolio": port.to_dict(), "all": rows,
        "alpha_statement": ("Portfolio alpha is statistically separate from "
                            "zero at 5%." if port["alpha_p_value"] < 0.05 else
                            "Portfolio alpha is not statistically separate "
                            "from zero at 5%."),
    }
    json.dump(R, open(path, "w"), indent=1, default=str)
    print(out.to_string(index=False))


if __name__ == "__main__":
    main()
