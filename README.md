# Monte Carlo Portfolio Risk Simulation: Dhaka Stock Exchange

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

- Window used: 2024-11-03 to 2026-10-15, 469 trading days, the same for all 11 stocks.
- No missing days against the common calendar and no values were filled by this project.
- Prices are published closing prices and are not adjusted for dividends.
- The requested window from January 2021 could not be used. The reasons, with counts, are in the Limitations section below and in `data/fetch_log.csv` and `data/archive_quality_check.json`.
- Sharpe ratios use a risk free rate of 0%, stated openly.

Over the window used, the equal weight portfolio fell at a rate of 7.46% a year, with volatility of 17.36% a year. Its worst single day was -5.53% and its best day was 4.90%.

## Headline results, 252 trading days

| Measure | Correlated GBM | Historical bootstrap |
| --- | --- | --- |
| Median ending value (Tk) | 952,265 | 961,601 |
| 5th percentile ending value (Tk) | 711,117 | 729,794 |
| 95th percentile ending value (Tk) | 1,284,195 | 1,273,812 |
| Probability of a loss (%) | 60.3 | 58.8 |
| Probability of a loss over 10% (%) | 37.9 | 35.4 |
| Probability of a loss over 20% (%) | 16.5 | 13.8 |
| VaR 95% (Tk loss) | 288,883 | 270,206 |
| CVaR 95% (Tk loss) | 337,436 | 320,693 |
| VaR 99% (Tk loss) | 372,312 | 353,576 |
| CVaR 99% (Tk loss) | 405,927 | 395,525 |

At 21 trading days, VaR 95% was Tk 85,068 under GBM and Tk 82,230 under the bootstrap.

Maximum drawdown inside the 252 day GBM paths: median 19.12%, 95th percentile 34.26%, 99th percentile 40.47%.

## Limitations and data problems

These problems are part of the findings. Full wording with counts is also in the report (Section 5) and in the Excel workbook (Limitations sheet).

### History is shorter than planned
The plan was to use January 2021 to 15 October 2026. That window could not be used honestly. The current DSE archive starts on 3 November 2024. A published archive of DSE prices to April 2025 was quality checked and rejected for 2021 and 2022: it contains 666 daily moves above 12% across the 11 stocks in those two years, in a market where the daily circuit breaker is about 10%, plus duplicate dates with conflicting closing prices. Examples: BATBC has 45 such moves in 2021 and BEXIMCO has 67. The same archive shows BATBC, ROBI, ACI and BEXIMCO each with only one unique closing price in the whole of 2023, because prices were held at floor prices. The window used is therefore 3 November 2024 to 15 October 2026, 469 trading days, taken directly from the DSE. A shorter window means the mean and covariance are measured with more error.

### BEXIMCO barely traded for most of the window
BEXIMCO (category B in the portfolio statement, 15 October 2026) has 149 days with zero volume out of 469, a median daily volume of 3 shares, and 81.6% of days with no price change at all. Its price stayed at Tk 110.1 for the whole of calendar 2025 and then fell to Tk 21.8 by October 2026, a fall of 81.1% over the window. It recorded 13 daily falls beyond 9%, all in the period when trading restarted. Its measured volatility is therefore not a normal trading volatility: it is close to zero for long stretches and then very large. The equal weight portfolio gives this stock 9.09% of the money, which is far more weight than its trading activity would support in practice.

### GEMINISEA is a Z category, thinly traded stock
GEMINISEA (category Z in the portfolio statement, 15 October 2026) has a median daily volume of 38,259 shares, the second lowest in the set. It recorded 5 daily rises beyond 9% and 2 daily falls beyond 9% in 469 days. Prices that move in steps at the daily limit are not well described by the smooth distribution used in the GBM method.

### FUWANGCER is a small B category ceramics stock
FUWANGCER (category B in the portfolio statement, 15 October 2026) has the third highest measured volatility in the set, at 39.6% a year, and 14.7% of days with no price change. Small stocks of this kind can be hard to sell at the quoted price in size, and the simulation assumes selling is always possible at the closing price.

### Floor prices and circuit breakers
Bangladesh held many share prices at floor prices from 2022 into early 2024. Prices could not fall below the floor, so measured volatility in that period was close to zero for several large stocks and did not reflect risk. That period is outside the window used here, which is a benefit of the shorter window, but it also means the window contains no long market fall held back by a floor. Separately, the daily circuit breaker of about 10% still applies in the window used: across the 11 stocks there were 18 daily rises beyond 9% and 22 daily falls beyond 9%, and many of those days closed at or near the limit. Real losses in a falling market can be larger than the daily data shows, because a holder may not be able to sell at the limit price.

### Prices are not adjusted for dividends
The DSE closing prices used are unadjusted. On the day a stock starts trading without the right to a cash dividend, the reference price is reset lower and there is no daily price limit, so the recorded close falls by roughly the dividend. Three such falls appear in the data: CITYBANK fell 16.67% on 2025-05-24, EBL fell 20.74% on 2025-04-24, and ACI fell 14.07% on 2024-11-18. Each follows a day with zero recorded volume, which matches a record date pattern. These falls are counted in the historical returns, so historical return and volatility for these three stocks are worse than the price risk alone, and the simulation treats part of a dividend payment as if it were a loss. No adjustment was made, because a checked dividend history for all 11 stocks was not available, and inventing one would be worse. Dividend income is also not added anywhere in the simulation.

### Days with no trading are recorded as no change
The DSE archive gives one row for every trading day for every stock, with the close held at the previous value when a stock did not trade. No days were filled by this project and no stock has missing days against the common calendar. The cost of that complete calendar is that no-trade days appear as zero returns: CITYBANK has 20.3% zero return days and EBL has 23.5%, which pulls their measured volatility down.

### GBM method limits
The GBM method assumes daily returns follow a normal distribution, that volatility stays constant, and that the average return of the last 469 days continues. Real DSE returns have more extreme days than a normal distribution, volatility changes over time, and the window used here was a falling period for several of these stocks, which pushes the simulated median down. GBM results should be read as a model estimate, not a forecast.

### Bootstrap method limits
The bootstrap method assumes the future will look like a reshuffle of the last 469 days. It keeps the real size of daily moves, including limit days and dividend reset days, but it breaks the order of days, so runs of bad days that happened together in real life are split up. It cannot produce a day worse than the worst day already seen.

### Other limits
The portfolio is a hypothetical Tk 1,000,000 split equally. It is not adjusted for brokerage costs, taxes, or the difficulty of buying thin stocks in equal amounts. Weights are held as buy and hold within each simulated path and are reset to equal only at the start. The Sharpe ratios in this project use a risk free rate of 0%, stated openly, because the aim is comparison inside the project and not comparison with Treasury bills.

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
- Measured one year Value at Risk at 95% at Tk 288,883 on a hypothetical Tk 1,000,000 equal weight portfolio using correlated Geometric Brownian Motion.
- Ran a historical bootstrap as a second method and showed both methods gave close results, with a 59% probability of a one year loss under the bootstrap.
- Downloaded and cleaned 469 trading days of daily prices for 11 stocks directly from the Dhaka Stock Exchange archive.
- Found and quantified data problems in the stock set, including one stock with 149 zero volume days and a price fixed for a full calendar year, and reported them as limitations with counts.

## Interview talking points

- Why two methods were used: GBM can create outcomes worse than anything in the sample, while the bootstrap only reuses real days, so agreement between them is a check on the size of the risk numbers.
- Why correlation matters: simulating each stock on its own would understate portfolio risk, so the covariance matrix and a Cholesky decomposition were used to keep the real pattern of joint moves.
- Why the history starts in November 2024 and not January 2021: the earlier archive data was tested and rejected with counts, including 666 daily moves above 12% in a market with a 10% daily limit, and prices frozen at floor prices through 2023.
- What CVaR adds beyond VaR: VaR gives the line that bad outcomes cross, CVaR gives the average loss once that line is crossed, and here it is about one sixth larger than VaR.
- Why unadjusted prices matter: three stocks show single day falls beyond the daily limit that match dividend reset days, so part of what looks like price risk in the data is a dividend payment recorded as a fall, and dividend income is not counted anywhere in the simulation.

## Extended analysis: how good or bad is this portfolio?

The extended analysis was added after the main simulation and does not change any number in it. It runs nine further analyses on the same data and the same hypothetical Tk 1,000,000 equal weight portfolio: risk decomposition, a diversification test, drawdown and downside measures, distribution tests, liquidity modelling, rolling risk with named stress tests, beta against DSEX with EWMA and GARCH volatility models, a fat tail Monte Carlo with Student-t shocks, and a fundamental snapshot of all 11 companies.

### Extended analysis headline results

- Risk decomposition: SEAPEARL holds 13.74% of total portfolio risk, FUWANGCER 13.16% and GEMINISEA 12.99%. The three together hold 39.89% of the risk on 27.27% of the money. BEXIMCO holds the smallest measured share, 4.36%, and that figure is understated because the stock barely traded. In the component VaR from the GBM paths, BEXIMCO is the largest single part of the tail loss at 17.06%.
- Diversification: weighted average stock volatility 31.74% a year against portfolio volatility 17.36%, a diversification ratio of 1.83. Average pairwise correlation 0.236. Effective number of risk bets 10.46 out of 11.
- Drawdown and downside (daily rebalanced equal weight path, the stated definition for these figures): total return -6.59% over the window, maximum drawdown -23.94% from 8 September 2025 to 14 September 2026, not recovered by the end of the window. Sortino ratio -0.173. Daily VaR 95% 1.66%, daily CVaR 95% 2.54%.
- Distribution: portfolio skewness -0.415, excess kurtosis 2.957, Jarque-Bera 184.0 with a p-value below 0.001. Normality is rejected. The worst 1% of days start at -2.76% against a normal prediction of -2.54%, so the left tail is fatter than normal.
- Liquidity: 6 stocks grade Good, 4 Thin, 1 Trapped under the stated rule. BEXIMCO median daily traded value is Tk 330 (median volume 3 shares at its frozen price of Tk 110.1). Selling one Tk 90,909 position at 20% of that median value would take 1,376 trading days. The other 10 stocks each take less than one day on the same rule.
- Rolling risk: 63 day volatility ranged from 8.07% to 25.73% a year. EWMA volatility (lambda 0.94) ended at 15.96%. A GARCH(1,1) fit gave alpha 0.130 and beta 0.815, persistence 0.945, and a next day volatility forecast of 14.73% annualised, flagged as borderline on 468 returns.
- Stress tests (all hypothetical): the largest loss comes from joining the five worst real days in the window back to back, 19.04% or Tk 190,448. The combined scenario (every stock falls 10%, then BEXIMCO falls to zero) loses 18.18% or Tk 181,818. BEXIMCO falling to zero on its own loses 9.09% or Tk 90,909 on paper, and more in practice because the position could not be sold during the frozen period.
- Fat tail Monte Carlo: Student-t shocks with degrees of freedom 6.03, estimated from portfolio excess kurtosis by the method of moments, 10,000 simulations, seed 42. At 252 days the median ending value is Tk 954,377, VaR 95% is Tk 284,293 and CVaR 95% is Tk 333,510, close to the GBM figures (Tk 952,265, Tk 288,883, Tk 337,436). All three methods agree that a one year loss is more likely than not.
- Beta against DSEX could not be calculated. No daily DSEX series could be fetched: the DSE day-end API holds no index instruments, stocksurferbd index history reads a legacy site that did not respond, its graph endpoint does not serve DSEX, stockanalysis.com has no DSEX index page, and the DSE index archive page returns HTTP 410. Attempts are logged in `data/extended_dsex_fetch_log.csv`. No proxy index was used.
- Fundamental snapshot (stockanalysis.com, accessed 31 October 2026): six companies are profitable on trailing EPS and five are loss making: ACI, BEXIMCO, FUWANGCER, GEMINISEA and SEAPEARL, the same group with the highest price risk. Group median PE is 7.59 for the six stocks with a PE shown. Fiscal years end in June for five companies and December for six, so comparisons are not exact.

### Extended analysis verdict in short

Return: bad in this window, not proven for the long term. Risk: high. Diversification: worked on volatility, did not fix risk concentration. Liquidity: poor because of one trapped stock. Data quality: weak, with a 1.86 year window, unadjusted prices and no index benchmark. The full verdict with evidence is in Section 10 of the extended analysis report.

### Extended analysis files

- `DSE_Extended_Portfolio_Analysis_Report.pdf`: Extended Analysis report, 9 pages.
- `DSE_Extended_Portfolio_Analysis.xlsx`: workbook with Verdict summary, Risk decomposition, Diversification, Drawdown and downside, Distribution tests, Liquidity, Stress tests, Beta vs DSEX, Volatility models, Fat-tail Monte Carlo, Fundamentals and Limitations sheets.
- `DSE_Extended_Portfolio_Analysis.ipynb`: executed notebook that recomputes the headline extended analysis numbers.
- `data/extended_results.json` and the `extended_` CSV files in `data/`: every Extended Analysis output, including the DSEX fetch log and the fundamental snapshot.
- `charts/`: seven `extended_` charts (risk contribution, drawdown, QQ plot, rolling volatility with EWMA, liquidity days to exit, stress test losses, EPS by stock).
- `scripts/`: `extended_analysis.py`, `extended_fetch_dsex.py`, `extended_beta.py`, `extended_fetch_fundamentals.py`, `extended_charts.py`, `extended_build_workbook.py`, `extended_build_report.py`, `extended_build_notebook.py`.

### Additional CV bullets (extended analysis)

- Measured risk contributions for an 11 stock DSE portfolio and showed three small stocks held 39.9% of total risk on 27.3% of the capital.
- Built a liquidity model from traded value that graded one stock as trapped, with 1,376 trading days needed to sell a Tk 90,909 position at 20% of its median daily traded value.
- Ran a fat tail Monte Carlo with correlated Student-t shocks and showed its one year VaR at 95% of Tk 284,293 was close to the GBM and bootstrap results, so the risk finding holds across three methods.
