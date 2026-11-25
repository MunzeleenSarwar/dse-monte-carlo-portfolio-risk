"""Build DSE_Extended_Portfolio_Analysis.ipynb (unexecuted). Execute with:
jupyter nbconvert --to notebook --execute --inplace DSE_Extended_Portfolio_Analysis.ipynb
The notebook recomputes the headline extended analysis numbers from the
saved price and volume data of the main simulation and compares them with
data/extended_results.json.
"""
import os

import nbformat as nbf

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

nb = nbf.v4.new_notebook()
nb.metadata = {"kernelspec": {"display_name": "Python 3", "language": "python",
                              "name": "python3"},
               "language_info": {"name": "python", "version": "3.12.3"}}
C = []
C.append(nbf.v4.new_markdown_cell(
    "# Portfolio Risk Analysis: Dhaka Stock Exchange, Extended Analysis\n"
    "Munzeleen Sarwar\n\n"
    "Hypothetical portfolio: Tk 1,000,000, equal weight across 11 DSE "
    "stocks (BATBC, BXPHARMA, CITYBANK, DBH, EBL, ROBI, ACI, BEXIMCO, "
    "FUWANGCER, GEMINISEA, SEAPEARL). Window: 3 Nov 2024 to 15 Oct 2026, "
    "469 trading days. This notebook recomputes the headline extended analysis "
    "numbers from the saved data of the main simulation and checks them against "
    "data/extended_results.json. Seed 42 wherever randomness is used."))
C.append(nbf.v4.new_code_cell(
    "import json\n"
    "import numpy as np\n"
    "import pandas as pd\n"
    "from scipy import stats\n\n"
    "TICKERS = ['BATBC','BXPHARMA','CITYBANK','DBH','EBL','ROBI','ACI',\n"
    "           'BEXIMCO','FUWANGCER','GEMINISEA','SEAPEARL']\n"
    "frames = {}\n"
    "for t in TICKERS:\n"
    "    df = pd.read_csv(f'data/{t}.csv', parse_dates=['date']).set_index('date')\n"
    "    frames[t] = df\n"
    "closes = pd.DataFrame({t: frames[t]['close'] for t in TICKERS}).sort_index()\n"
    "volumes = pd.DataFrame({t: frames[t]['volume'] for t in TICKERS}).sort_index()\n"
    "logret = np.log(closes / closes.shift(1)).dropna()\n"
    "simple = closes.pct_change().dropna()\n"
    "R = json.load(open('data/extended_results.json'))\n"
    "print('closes:', closes.shape, closes.index.min().date(), 'to', closes.index.max().date())"))
C.append(nbf.v4.new_markdown_cell(
    "## 1. Risk decomposition\n"
    "Component contributions from the covariance matrix of daily log returns."))
C.append(nbf.v4.new_code_cell(
    "w = np.full(11, 1/11)\n"
    "cov_a = logret.cov().values * 252\n"
    "port_vol = float(np.sqrt(w @ cov_a @ w))\n"
    "crc = w * (cov_a @ w) / port_vol\n"
    "share = pd.Series(100 * crc / port_vol, index=TICKERS).sort_values(ascending=False)\n"
    "print('Portfolio volatility (% a year):', round(100 * port_vol, 2))\n"
    "print(share.round(2).to_string())\n"
    "print('Saved value:', R['risk_decomposition']['portfolio_volatility_pct'])"))
C.append(nbf.v4.new_markdown_cell(
    "## 2. Diversification"))
C.append(nbf.v4.new_code_cell(
    "indiv = np.sqrt(np.diag(cov_a))\n"
    "wavg = float((w * indiv).sum())\n"
    "corr = logret.corr().values\n"
    "iu = np.triu_indices(11, 1)\n"
    "print('Weighted average individual volatility (%):', round(100 * wavg, 2))\n"
    "print('Diversification ratio:', round(wavg / port_vol, 2))\n"
    "print('Average pairwise correlation:', round(float(corr[iu].mean()), 3))"))
C.append(nbf.v4.new_markdown_cell(
    "## 3. Drawdown and downside\n"
    "Path definition: daily rebalanced equal weight portfolio of simple returns."))
C.append(nbf.v4.new_code_cell(
    "port = simple.mean(axis=1)\n"
    "wealth = 1_000_000 * (1 + port).cumprod()\n"
    "dd = wealth / wealth.cummax() - 1\n"
    "down = np.sqrt((np.minimum(port, 0) ** 2).mean()) * np.sqrt(252)\n"
    "print('Total return (%):', round(100 * float(wealth.iloc[-1] / 1e6 - 1), 2))\n"
    "print('Maximum drawdown (%):', round(100 * float(dd.min()), 2), 'on', dd.idxmin().date())\n"
    "print('Sortino ratio:', round(float(port.mean() * 252 / down), 3))\n"
    "print('Daily VaR95 (%):', round(-100 * float(port.quantile(0.05)), 2))"))
C.append(nbf.v4.new_markdown_cell(
    "## 4. Distribution tests"))
C.append(nbf.v4.new_code_cell(
    "port_log = logret.mean(axis=1)\n"
    "jb = stats.jarque_bera(port_log.values)\n"
    "print('Skewness:', round(float(stats.skew(port_log.values)), 3))\n"
    "print('Excess kurtosis:', round(float(stats.kurtosis(port_log.values)), 3))\n"
    "print('Jarque-Bera:', round(float(jb.statistic), 1), 'p-value:', float(jb.pvalue))"))
C.append(nbf.v4.new_markdown_cell(
    "## 5. Liquidity: BEXIMCO check"))
C.append(nbf.v4.new_code_cell(
    "traded = volumes['BEXIMCO'] * closes['BEXIMCO']\n"
    "med = float(traded.median())\n"
    "print('BEXIMCO median daily traded value (Tk):', med)\n"
    "print('Median daily volume (shares):', float(volumes['BEXIMCO'].median()))\n"
    "print('Days to exit Tk 90,909 at 20% of median:', round(90909.09 / (0.2 * med), 1))\n"
    "liq = pd.read_csv('data/extended_liquidity.csv')\n"
    "print(liq[['ticker', 'liquidity_grade']].to_string(index=False))"))
C.append(nbf.v4.new_markdown_cell(
    "## 6. Rolling volatility, EWMA and stress test check"))
C.append(nbf.v4.new_code_cell(
    "roll = port_log.rolling(63).std(ddof=1) * np.sqrt(252)\n"
    "print('Rolling 63d vol range (%):', round(100 * float(roll.min()), 2), 'to', round(100 * float(roll.max()), 2))\n"
    "var = np.empty(len(port_log)); var[0] = float(port_log.var(ddof=1))\n"
    "r2 = port_log.values ** 2\n"
    "for i in range(1, len(port_log)):\n"
    "    var[i] = 0.94 * var[i-1] + 0.06 * r2[i-1]\n"
    "print('EWMA latest vol (% a year):', round(100 * float(np.sqrt(var[-1] * 252)), 2))\n"
    "worst5 = port.nsmallest(5).values\n"
    "print('Stress A, five worst days back to back, loss (Tk):', round(-(float(np.prod(1 + worst5)) - 1) * 1e6))"))
C.append(nbf.v4.new_markdown_cell(
    "## 7. Fat tail Monte Carlo (Student-t), 252 days\n"
    "Same mean and covariance basis as the GBM simulation, seed 42, 10,000 paths. "
    "Degrees of freedom from portfolio excess kurtosis by the method of moments."))
C.append(nbf.v4.new_code_cell(
    "excess = float(stats.kurtosis(port_log.values))\n"
    "df_use = min(max(4 + 6 / excess, 3.5), 30.0)\n"
    "print('Degrees of freedom used:', round(df_use, 2))\n"
    "mu = logret.mean().values\n"
    "cov_d = logret.cov().values\n"
    "chol = np.linalg.cholesky(cov_d)\n"
    "drift = mu - 0.5 * np.diag(cov_d)\n"
    "rng = np.random.default_rng(42)\n"
    "scale = np.sqrt((df_use - 2) / df_use)\n"
    "endings = np.empty(10_000)\n"
    "done = 0\n"
    "while done < 10_000:\n"
    "    b = min(1000, 10_000 - done)\n"
    "    z = rng.standard_normal((b, 252, 11))\n"
    "    chi = rng.chisquare(df_use, size=(b, 252, 1))\n"
    "    shocks = (z @ chol.T) / np.sqrt(chi / df_use) * scale\n"
    "    growth = np.exp(np.cumsum(drift + shocks, axis=1))\n"
    "    endings[done:done + b] = 1_000_000 * growth.mean(axis=2)[:, -1]\n"
    "    done += b\n"
    "rets = endings / 1e6 - 1\n"
    "print('Median ending value (Tk):', round(float(np.median(endings))))\n"
    "print('VaR95 (Tk):', round(-float(np.percentile(rets, 5)) * 1e6))\n"
    "print('Saved:', R['student_t']['results']['252']['median_value_tk'],\n"
    "      R['student_t']['results']['252']['var95_tk'])"))
C.append(nbf.v4.new_markdown_cell(
    "## 8. Beta against DSEX and fundamentals\n"
    "Beta status comes from data/extended_results.json. Fundamental figures "
    "are read from data/extended_fundamentals.csv."))
C.append(nbf.v4.new_code_cell(
    "print('Beta status:', R['beta_vs_dsex']['status'])\n"
    "print(R['beta_vs_dsex']['reason'][:300])\n"
    "fund = pd.read_csv('data/extended_fundamentals.csv')\n"
    "print(fund[['ticker', 'eps_ttm_bdt', 'pe_ratio', 'dividend_yield_pct']].to_string(index=False))\n"
    "print('Loss making stocks:', fund.loc[fund['eps_ttm_bdt'] < 0, 'ticker'].tolist())"))
nb.cells = C
out = os.path.join(BASE, "DSE_Extended_Portfolio_Analysis.ipynb")
nbf.write(nb, out)
print("written", out)
