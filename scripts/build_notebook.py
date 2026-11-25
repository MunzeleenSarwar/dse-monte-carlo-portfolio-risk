"""Build the analysis notebook (unexecuted).

Run afterwards with:
  jupyter nbconvert --to notebook --execute --inplace \
      DSE_Monte_Carlo_Portfolio_Risk.ipynb
The notebook is self-contained: it reads the CSVs in data/ and repeats
the full analysis (coverage, statistics, correlation, both simulations)
with charts inline. Its results match scripts/simulate.py because both
use seed 42 and the same formulas.
"""
import os

import nbformat as nbf

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(BASE, "DSE_Monte_Carlo_Portfolio_Risk.ipynb")

nb = nbf.v4.new_notebook()
nb.metadata = {"kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
               "language_info": {"name": "python", "version": "3.12"}}
cells = []
md = lambda t: cells.append(nbf.v4.new_markdown_cell(t))  # noqa: E731
code = lambda t: cells.append(nbf.v4.new_code_cell(t))  # noqa: E731

md("# Monte Carlo Portfolio Risk Simulation: Dhaka Stock Exchange\n"
   "Munzeleen Sarwar\n\n"
   "Hypothetical portfolio: Tk 1,000,000, equal weight across 11 DSE stocks "
   "(BATBC, BXPHARMA, CITYBANK, DBH, EBL, ROBI, ACI, BEXIMCO, FUWANGCER, GEMINISEA, SEAPEARL). "
   "Two methods, 10,000 simulations each, seed 42: correlated Geometric Brownian Motion and "
   "historical bootstrap. Horizons: 21, 63 and 252 trading days.")
code("import json\n"
     "import numpy as np\n"
     "import pandas as pd\n"
     "import matplotlib.pyplot as plt\n\n"
     "TICKERS = ['BATBC','BXPHARMA','CITYBANK','DBH','EBL','ROBI','ACI','BEXIMCO','FUWANGCER','GEMINISEA','SEAPEARL']\n"
     "START = 1_000_000.0\n"
     "N_SIMS, SEED = 10_000, 42\n"
     "HORIZONS = [21, 63, 252]")
md("## 1. Load the price data\n"
   "Prices are the unadjusted daily closing prices published by the Dhaka Stock Exchange, "
   "downloaded by `scripts/fetch_data.py` and saved in `data/`.")
code("frames = {t: pd.read_csv(f'data/{t}.csv', parse_dates=['date']).set_index('date') for t in TICKERS}\n"
     "closes = pd.DataFrame({t: frames[t]['close'] for t in TICKERS}).sort_index()\n"
     "volumes = pd.DataFrame({t: frames[t]['volume'] for t in TICKERS}).sort_index()\n"
     "print('window:', closes.index.min().date(), 'to', closes.index.max().date())\n"
     "print('trading days:', len(closes), '| missing values:', int(closes.isna().sum().sum()))\n"
     "closes.head(3)")
md("## 2. Data coverage and problem counts")
code("daily = closes.pct_change().dropna()\n"
     "cov_rows = []\n"
     "for t in TICKERS:\n"
     "    cov_rows.append({'ticker': t, 'rows': int(closes[t].notna().sum()),\n"
     "                     'pct_zero_return_days': round(100 * (daily[t] == 0).mean(), 2),\n"
     "                     'zero_volume_days': int((volumes[t] == 0).sum()),\n"
     "                     'median_daily_volume': float(volumes[t].median()),\n"
     "                     'falls_beyond_9pct': int((daily[t] < -0.09).sum()),\n"
     "                     'rises_beyond_9pct': int((daily[t] > 0.09).sum())})\n"
     "coverage = pd.DataFrame(cov_rows)\n"
     "coverage")
md("BEXIMCO stands out: most days have no price change and the median daily volume is close to zero. "
   "Section 8 lists all data problems with counts.")
md("## 3. Per-stock statistics and correlation")
code("logret = np.log(closes / closes.shift(1)).dropna()\n"
     "stats = pd.DataFrame({\n"
     "    'total_return_pct': (closes.iloc[-1] / closes.iloc[0] - 1) * 100,\n"
     "    'annualised_return_pct': logret.mean() * 252 * 100,\n"
     "    'annualised_volatility_pct': logret.std(ddof=1) * np.sqrt(252) * 100,\n"
     "    'worst_day_pct': (np.expm1(logret.min())) * 100,\n"
     "    'sharpe_rf_0pct': (logret.mean() * 252) / (logret.std(ddof=1) * np.sqrt(252)),\n"
     "}).round(2)\n"
     "stats")
code("corr = logret.corr()\n"
     "fig, ax = plt.subplots(figsize=(8, 6.5))\n"
     "im = ax.imshow(corr.values, cmap='RdYlBu_r', vmin=-1, vmax=1)\n"
     "ax.set_xticks(range(11), corr.columns, rotation=45, ha='left', fontsize=8)\n"
     "ax.set_yticks(range(11), corr.index, fontsize=8)\n"
     "for i in range(11):\n"
     "    for j in range(11):\n"
     "        ax.text(j, i, f'{corr.values[i, j]:.2f}', ha='center', va='center', fontsize=7)\n"
     "fig.colorbar(im, ax=ax, shrink=0.85)\n"
     "ax.set_title('Correlation of daily log returns')\n"
     "plt.show()")
code("norm = closes / closes.iloc[0] * 100\n"
     "norm.plot(figsize=(10, 5), lw=1.1)\n"
     "plt.axhline(100, color='black', lw=0.8, ls='--')\n"
     "plt.ylabel('Price, first day = 100')\n"
     "plt.legend(ncol=4, fontsize=8)\n"
     "plt.title('Price history used, unadjusted DSE closing prices')\n"
     "plt.show()")
md("## 4. Risk summary function\n"
   "VaR 95% is the loss exceeded in 5% of simulations. CVaR 95% is the average loss in that worst 5%.")
code("def summarise(endings):\n"
     "    rets = endings / START - 1.0\n"
     "    out = {f'p{p}_tk': float(np.percentile(endings, p)) for p in (1, 5, 25, 50, 75, 95, 99)}\n"
     "    out['prob_loss_pct'] = float(100 * np.mean(rets < 0))\n"
     "    out['prob_loss_over_10pct'] = float(100 * np.mean(rets < -0.10))\n"
     "    out['prob_loss_over_20pct'] = float(100 * np.mean(rets < -0.20))\n"
     "    for level in (95, 99):\n"
     "        var = float(np.percentile(rets, 100 - level))\n"
     "        out[f'var{level}_tk'] = round(-var * START)\n"
     "        out[f'cvar{level}_tk'] = round(-rets[rets <= var].mean() * START)\n"
     "    return out")
md("## 5. Method 1: correlated Geometric Brownian Motion\n"
   "The Cholesky decomposition of the covariance matrix keeps the real correlations in the simulated returns.")
code("mu = logret.mean().values\n"
     "cov = logret.cov().values\n"
     "chol = np.linalg.cholesky(cov)\n"
     "rng = np.random.default_rng(SEED)\n"
     "max_h = 252\n"
     "endings = {h: np.empty(N_SIMS) for h in HORIZONS}\n"
     "fan_days = [0] + list(range(6, max_h + 1, 6)) + [max_h]\n"
     "fan = {d: np.empty(N_SIMS) for d in fan_days}\n"
     "max_dd = np.empty(N_SIMS)\n"
     "done = 0\n"
     "while done < N_SIMS:\n"
     "    b = min(1000, N_SIMS - done)\n"
     "    z = rng.standard_normal((b, max_h, 11))\n"
     "    daily_log = (mu - 0.5 * np.diag(cov)) + z @ chol.T\n"
     "    port = np.exp(np.cumsum(daily_log, axis=1)).mean(axis=2)\n"
     "    paths = START * port\n"
     "    for h in HORIZONS:\n"
     "        endings[h][done:done + b] = paths[:, h - 1]\n"
     "    for d in fan_days:\n"
     "        fan[d][done:done + b] = START if d == 0 else paths[:, d - 1]\n"
     "    full = np.hstack([np.full((b, 1), START), paths])\n"
     "    run_max = np.maximum.accumulate(full, axis=1)\n"
     "    max_dd[done:done + b] = ((run_max - full) / run_max).max(axis=1)\n"
     "    done += b\n"
     "gbm_results = pd.DataFrame({h: summarise(endings[h]) for h in HORIZONS}).T\n"
     "gbm_results")
code("print('GBM 252 day maximum drawdown: median %.2f%%, 95th percentile %.2f%%' % (\n"
     "    100 * np.median(max_dd), 100 * np.percentile(max_dd, 95)))\n"
     "fan_df = pd.DataFrame({d: fan[d] for d in fan_days}).T\n"
     "fan_pct = fan_df.quantile([0.01, 0.05, 0.25, 0.5, 0.75, 0.95, 0.99], axis=1).T\n"
     "fig, ax = plt.subplots(figsize=(9, 5))\n"
     "ax.fill_between(fan_pct.index, fan_pct[0.01], fan_pct[0.99], color='#c7d7ea')\n"
     "ax.fill_between(fan_pct.index, fan_pct[0.05], fan_pct[0.95], color='#8fb0d8')\n"
     "ax.fill_between(fan_pct.index, fan_pct[0.25], fan_pct[0.75], color='#4f7fb8')\n"
     "ax.plot(fan_pct.index, fan_pct[0.5], color='#0b2e59', lw=2)\n"
     "ax.axhline(START, color='black', lw=1, ls='--')\n"
     "ax.set_title('GBM fan chart, 252 days')\n"
     "ax.set_xlabel('Trading days ahead')\n"
     "ax.set_ylabel('Portfolio value (Tk)')\n"
     "plt.show()")
code("plt.figure(figsize=(9, 5))\n"
     "plt.hist(endings[252] / 1000, bins=60, color='#4f7fb8', edgecolor='white', lw=0.3)\n"
     "plt.axvline(1000, color='black', lw=1.5, ls='--')\n"
     "plt.xlabel('Ending value after 252 days (Tk thousand)')\n"
     "plt.title('GBM ending values, 252 days')\n"
     "plt.show()")
md("## 6. Method 2: historical bootstrap\n"
   "Actual daily portfolio returns are resampled with replacement and compounded.")
code("port_daily = np.expm1(logret).mean(axis=1).values\n"
     "rng = np.random.default_rng(SEED)\n"
     "boot_results = {}\n"
     "boot_endings = {}\n"
     "for h in HORIZONS:\n"
     "    idx = rng.integers(0, len(port_daily), size=(N_SIMS, h))\n"
     "    ends = START * np.prod(1.0 + port_daily[idx], axis=1)\n"
     "    boot_endings[h] = ends\n"
     "    boot_results[h] = summarise(ends)\n"
     "pd.DataFrame(boot_results).T")
code("plt.figure(figsize=(9, 5))\n"
     "plt.hist(boot_endings[252] / 1000, bins=60, color='#7aa05a', edgecolor='white', lw=0.3)\n"
     "plt.axvline(1000, color='black', lw=1.5, ls='--')\n"
     "plt.xlabel('Ending value after 252 days (Tk thousand)')\n"
     "plt.title('Bootstrap ending values, 252 days')\n"
     "plt.show()")
md("## 7. Comparison at 252 days")
code("compare = pd.DataFrame({\n"
     "    'GBM': {k: gbm_results.loc[252, k] for k in ('p50_tk', 'prob_loss_pct', 'var95_tk', 'cvar95_tk', 'var99_tk', 'cvar99_tk')},\n"
     "    'Bootstrap': {k: boot_results[252][k] for k in ('p50_tk', 'prob_loss_pct', 'var95_tk', 'cvar95_tk', 'var99_tk', 'cvar99_tk')},\n"
     "})\n"
     "compare")
md("## 8. Limitations and data problems\n"
   "- History is shorter than planned. The plan was January 2021 to October 2026. The DSE archive in its "
   "current form starts on 3 November 2024, and a published archive for the earlier years was checked and "
   "rejected: it contains 666 daily moves above 12% across the 11 stocks in 2021 and 2022, in a market with "
   "a daily circuit breaker of about 10%, plus duplicate dates with conflicting closes.\n"
   "- Floor prices held many DSE prices fixed from 2022 into early 2024. In the rejected archive, BATBC, ROBI, "
   "ACI and BEXIMCO each have only one unique closing price in the whole of 2023.\n"
   "- BEXIMCO barely traded: 149 zero volume days, median daily volume of 3 shares, 81.6% of days with no price "
   "change, price fixed at Tk 110.1 through calendar 2025, then a fall to Tk 21.8.\n"
   "- GEMINISEA is category Z and thinly traded, median daily volume 38,259 shares, with 5 rises and 2 falls "
   "beyond 9% in the window.\n"
   "- FUWANGCER is a small category B ceramics stock, third highest volatility in the set, 14.7% of days with "
   "no price change.\n"
   "- Prices are unadjusted. CITYBANK fell 16.67% on 2025-05-24, EBL fell 20.74% on 2025-04-24 and ACI fell "
   "14.07% on 2024-11-18. Each follows a zero volume day and matches a dividend record date pattern, so part "
   "of each fall is a dividend reset recorded as a price loss. No adjustment was made and no dividend income "
   "is added in the simulation.\n"
   "- The daily circuit breaker of about 10% truncates real moves: across the set there were 18 rises beyond "
   "9% and 22 falls beyond 9% in 469 days.\n"
   "- GBM assumes normal returns and constant volatility. The bootstrap assumes the last 469 days repeat, and "
   "it splits up real runs of bad days.\n"
   "- Costs, taxes and the difficulty of trading thin stocks are not included. Sharpe ratios use a risk free "
   "rate of 0%.")

nb.cells = cells
nbf.write(nb, OUT)
print("saved", OUT, "cells:", len(cells))
