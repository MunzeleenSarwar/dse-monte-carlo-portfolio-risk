"""Build README.md from data/results.json so headline numbers match."""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from limitations import build_limitations  # noqa: E402

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(BASE, "data")


def tk(v):
    return f"{v:,.0f}"


def main():
    with open(os.path.join(DATA, "results.json")) as f:
        res = json.load(f)
    w, ph, dd = res["window"], res["portfolio_history"], res["gbm_max_drawdown_252"]
    g, b = res["gbm"]["252"], res["bootstrap"]["252"]
    g21, b21 = res["gbm"]["21"], res["bootstrap"]["21"]
    lims = build_limitations()
    lim_text = "\n".join(f"### {h}\n{t}\n" for h, t in lims)
    readme = f"""# Monte Carlo Portfolio Risk Simulation: Dhaka Stock Exchange

Munzeleen Sarwar

## What this project does

This project measures the risk of a hypothetical portfolio of Tk 1,000,000 split equally across 11 stocks listed on the Dhaka Stock Exchange (DSE): BATBC, BXPHARMA, CITYBANK, DBH, EBL, ROBI, ACI, BEXIMCO, FUWANGCER, GEMINISEA and SEAPEARL. Each stock starts with Tk 90,909. The ticker list came from a portfolio statement dated 15 October 2026. No real holding amounts were used, and no account details of any kind are in this project.

The portfolio is simulated 10,000 times over 21, 63 and 252 trading days. The output is a range of possible ending values and risk measures, not a single forecast. Nothing in this project is a recommendation to buy or sell any stock.

## Method in plain language

Monte Carlo simulation means running the same calculation many times with random inputs, to see the range of outcomes.

Two methods are used, both with a fixed random seed of 42 so the results can be repeated:

1. Correlated Geometric Brownian Motion (GBM). The average daily return, the daily volatility and the pattern of how the 11 stocks moved together are taken from the real data. Random daily returns are then drawn with the same pattern, using a Cholesky decomposition of the covariance matrix so that stocks which moved together in real life also move together in the simulation. Each stock is simulated separately and the results are combined with equal weights.
2. Historical bootstrap. Actual past daily returns of the equal weight portfolio are picked at random, with replacement, and joined into new paths. This method uses no assumed distribution, but it can only reuse days that already happened.

Risk measures reported for each method and each horizon: ending value percentiles (1, 5, 25, 50, 75, 95, 99), probability of a loss, probability of a loss over 10% and over 20%, Value at Risk (VaR) at 95% and 99%, and CVaR (expected shortfall) at 95% and 99%. VaR 95% is the loss that was exceeded in 5% of simulations. CVaR 95% is the average loss inside that worst 5%. Maximum drawdown, the largest fall from a peak to a later low inside a path, is reported for the 252 day GBM paths.

## Data

Daily closing prices, volumes and trade counts were downloaded from the Dhaka Stock Exchange public archive at dse.com.bd.

- Window used: {w['first_date']} to {w['last_date']}, {w['trading_days']} trading days, the same for all 11 stocks.
- No missing days against the common calendar and no values were filled by this project.
- Prices are published closing prices and are not adjusted for dividends.
- The requested window from January 2021 could not be used. The reasons, with counts, are in the Limitations section below and in `data/fetch_log.csv` and `data/archive_quality_check.json`.
- Sharpe ratios use a risk free rate of 0%, stated openly.

Over the window used, the equal weight portfolio fell at a rate of {abs(ph['annualised_return_pct']):.2f}% a year, with volatility of {ph['annualised_volatility_pct']:.2f}% a year. Its worst single day was {ph['worst_day_pct']:.2f}% and its best day was {ph['best_day_pct']:.2f}%.

## Headline results, 252 trading days

| Measure | Correlated GBM | Historical bootstrap |
| --- | --- | --- |
| Median ending value (Tk) | {tk(g['p50_value_tk'])} | {tk(b['p50_value_tk'])} |
| 5th percentile ending value (Tk) | {tk(g['p5_value_tk'])} | {tk(b['p5_value_tk'])} |
| 95th percentile ending value (Tk) | {tk(g['p95_value_tk'])} | {tk(b['p95_value_tk'])} |
| Probability of a loss (%) | {g['prob_loss_pct']:.1f} | {b['prob_loss_pct']:.1f} |
| Probability of a loss over 10% (%) | {g['prob_loss_over_10pct']:.1f} | {b['prob_loss_over_10pct']:.1f} |
| Probability of a loss over 20% (%) | {g['prob_loss_over_20pct']:.1f} | {b['prob_loss_over_20pct']:.1f} |
| VaR 95% (Tk loss) | {tk(g['var95_tk'])} | {tk(b['var95_tk'])} |
| CVaR 95% (Tk loss) | {tk(g['cvar95_tk'])} | {tk(b['cvar95_tk'])} |
| VaR 99% (Tk loss) | {tk(g['var99_tk'])} | {tk(b['var99_tk'])} |
| CVaR 99% (Tk loss) | {tk(g['cvar99_tk'])} | {tk(b['cvar99_tk'])} |

At 21 trading days, VaR 95% was Tk {tk(g21['var95_tk'])} under GBM and Tk {tk(b21['var95_tk'])} under the bootstrap.

Maximum drawdown inside the 252 day GBM paths: median {dd['median_max_drawdown_pct']:.2f}%, 95th percentile {dd['p95_max_drawdown_pct']:.2f}%, 99th percentile {dd['p99_max_drawdown_pct']:.2f}%.

## Limitations and data problems

These problems are part of the findings. Full wording with counts is also in the report (Section 5) and in the Excel workbook (Limitations sheet).

{lim_text}
## Files

- `DSE_Monte_Carlo_Portfolio_Risk_Report.pdf`: report, 7 pages.
- `DSE_Monte_Carlo_Portfolio_Risk.xlsx`: workbook with Summary, Per-stock stats, Correlation, GBM results, Bootstrap results, Data coverage and Limitations sheets.
- `DSE_Monte_Carlo_Portfolio_Risk.ipynb`: executed notebook that runs the full analysis.
- `data/`: one price CSV per ticker, `combined_close.csv`, `data_coverage.csv`, `per_stock_stats.csv`, `correlation.csv`, `gbm_results.csv`, `bootstrap_results.csv`, `gbm_fan_chart.csv`, `results.json`, `ending_values.npz`, `fetch_log.csv`, `archive_quality_check.json`.
- `charts/`: fan chart, ending value histograms for both methods, correlation heatmap, normalised price history, historical portfolio value, VaR comparison.
- `scripts/`: `fetch_data.py`, `simulate.py`, `charts.py`, `build_workbook.py`, `build_report.py`, `build_notebook.py`, `build_readme.py`, `limitations.py`.

## How to run

```
pip install pandas numpy matplotlib openpyxl reportlab nbformat bdshare stocksurferbd
python scripts/fetch_data.py
python scripts/simulate.py
python scripts/charts.py
python scripts/build_workbook.py
python scripts/build_report.py
python scripts/build_notebook.py
jupyter nbconvert --to notebook --execute --inplace DSE_Monte_Carlo_Portfolio_Risk.ipynb
python scripts/build_readme.py
```

Notes on running the fetch step: `bdshare` and `stocksurferbd` are tried first and their failures are logged, which is expected in many networks because the current DSE site rejects the bdshare user agent with HTTP 403 and the legacy site at old.dsebd.org does not respond. The fetch then uses the DSE public API directly with a browser user agent, which is the source of the saved data. The report builder needs reportlab.

## CV bullets

- Built a Monte Carlo portfolio risk simulation in Python for 11 Dhaka Stock Exchange stocks, with 10,000 simulated paths at 21, 63 and 252 trading days.
- Measured one year Value at Risk at 95% at Tk {tk(g['var95_tk'])} on a hypothetical Tk 1,000,000 equal weight portfolio using correlated Geometric Brownian Motion.
- Ran a historical bootstrap as a second method and showed both methods gave close results, with a {b['prob_loss_pct']:.0f}% probability of a one year loss under the bootstrap.
- Downloaded and cleaned 469 trading days of daily prices for 11 stocks directly from the Dhaka Stock Exchange archive.
- Found and quantified data problems in the stock set, including one stock with 149 zero volume days and a price fixed for a full calendar year, and reported them as limitations with counts.

## Interview talking points

- Why two methods were used: GBM can create outcomes worse than anything in the sample, while the bootstrap only reuses real days, so agreement between them is a check on the size of the risk numbers.
- Why correlation matters: simulating each stock on its own would understate portfolio risk, so the covariance matrix and a Cholesky decomposition were used to keep the real pattern of joint moves.
- Why the history starts in November 2024 and not January 2021: the earlier archive data was tested and rejected with counts, including 666 daily moves above 12% in a market with a 10% daily limit, and prices frozen at floor prices through 2023.
- What CVaR adds beyond VaR: VaR gives the line that bad outcomes cross, CVaR gives the average loss once that line is crossed, and here it is about one sixth larger than VaR.
- Why unadjusted prices matter: three stocks show single day falls beyond the daily limit that match dividend reset days, so part of what looks like price risk in the data is a dividend payment recorded as a fall, and dividend income is not counted anywhere in the simulation.
"""
    with open(os.path.join(BASE, "README.md"), "w") as f:
        f.write(readme)
    print("saved README.md, chars:", len(readme))


if __name__ == "__main__":
    main()
