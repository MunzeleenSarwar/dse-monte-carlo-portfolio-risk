"""Limitations and data problems, built from the saved results.

Used by the report, the Excel workbook and the README so the wording
and the numbers stay the same everywhere. All counts come from
data/data_coverage.csv and data/archive_quality_check.json.
"""
import json
import os

import pandas as pd

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(BASE, "data")


def _row(cov, t):
    return cov[cov.ticker == t].iloc[0]


def build_limitations():
    cov = pd.read_csv(os.path.join(DATA, "data_coverage.csv"))
    with open(os.path.join(DATA, "archive_quality_check.json")) as f:
        arch = json.load(f)
    bx = _row(cov, "BEXIMCO")
    gm = _row(cov, "GEMINISEA")
    fw = _row(cov, "FUWANGCER")
    fw_vol = float(pd.read_csv(os.path.join(DATA, "per_stock_stats.csv"))
                   .set_index("ticker").loc["FUWANGCER", "annualised_volatility_pct"])
    ct = _row(cov, "CITYBANK")
    eb = _row(cov, "EBL")
    ac = _row(cov, "ACI")
    total_bad = sum(v["moves_over_12pct_2021"] + v["moves_over_12pct_2022"]
                    for v in arch.values())
    items = [
        ("History is shorter than planned",
         "The plan was to use January 2021 to 15 October 2026. That window could not be used honestly. "
         "The current DSE archive starts on 3 November 2024. A published archive of DSE prices to April 2025 "
         f"was quality checked and rejected for 2021 and 2022: it contains {total_bad} daily moves above 12% "
         "across the 11 stocks in those two years, in a market where the daily circuit breaker is about 10%, "
         "plus duplicate dates with conflicting closing prices. Examples: BATBC has "
         f"{arch['BATBC']['moves_over_12pct_2021']} such moves in 2021 and BEXIMCO has "
         f"{arch['BEXIMCO']['moves_over_12pct_2021']}. The same archive shows BATBC, ROBI, ACI and BEXIMCO each "
         "with only one unique closing price in the whole of 2023, because prices were held at floor prices. "
         "The window used is therefore 3 November 2024 to 15 October 2026, 469 trading days, taken directly "
         "from the DSE. A shorter window means the mean and covariance are measured with more error."),
        ("BEXIMCO barely traded for most of the window",
         f"BEXIMCO (category B in the portfolio statement, 15 October 2026) has {int(bx.zero_volume_days)} days "
         f"with zero volume out of 469, a median daily volume of {int(bx.median_daily_volume)} shares, and "
         f"{bx.pct_days_zero_return:.1f}% of days with no price change at all. Its price stayed at Tk 110.1 for "
         "the whole of calendar 2025 and then fell to Tk 21.8 by October 2026, a fall of 81.1% over the window. "
         f"It recorded {int(bx.moves_below_minus_9pct)} daily falls beyond 9%, all in the period when trading "
         "restarted. Its measured volatility is therefore not a normal trading volatility: it is close to zero "
         "for long stretches and then very large. The equal weight portfolio gives this stock 9.09% of the money, "
         "which is far more weight than its trading activity would support in practice."),
        ("GEMINISEA is a Z category, thinly traded stock",
         f"GEMINISEA (category Z in the portfolio statement, 15 October 2026) has a median daily volume of "
         f"{int(gm.median_daily_volume):,} shares, the second lowest in the set. It recorded "
         f"{int(gm.moves_above_plus_9pct)} daily rises beyond 9% and {int(gm.moves_below_minus_9pct)} daily falls "
         "beyond 9% in 469 days. Prices that move in steps at the daily limit are not well described by the "
         "smooth distribution used in the GBM method."),
        ("FUWANGCER is a small B category ceramics stock",
         f"FUWANGCER (category B in the portfolio statement, 15 October 2026) has the third highest measured "
         f"volatility in the set, at {fw_vol:.1f}% a year, and {fw.pct_days_zero_return:.1f}% of days with no price change. Small stocks "
         "of this kind can be hard to sell at the quoted price in size, and the simulation assumes selling is "
         "always possible at the closing price."),
        ("Floor prices and circuit breakers",
         "Bangladesh held many share prices at floor prices from 2022 into early 2024. Prices could not fall "
         "below the floor, so measured volatility in that period was close to zero for several large stocks and "
         "did not reflect risk. That period is outside the window used here, which is a benefit of the shorter "
         "window, but it also means the window contains no long market fall held back by a floor. Separately, "
         "the daily circuit breaker of about 10% still applies in the window used: "
         f"across the 11 stocks there were {int(cov.moves_above_plus_9pct.sum())} daily rises "
         f"beyond 9% and {int(cov.moves_below_minus_9pct.sum())} daily falls beyond 9%, and many "
         "of those days closed at or near the limit. Real losses in a falling market can be larger than the "
         "daily data shows, because a holder may not be able to sell at the limit price."),
        ("Prices are not adjusted for dividends",
         "The DSE closing prices used are unadjusted. On the day a stock starts trading without the right to a "
         "cash dividend, the reference price is reset lower and there is no daily price limit, so the recorded "
         "close falls by roughly the dividend. Three such falls appear in the data: "
         f"CITYBANK fell {abs(ct.largest_daily_fall_pct):.2f}% on {ct.largest_fall_date}, "
         f"EBL fell {abs(eb.largest_daily_fall_pct):.2f}% on {eb.largest_fall_date}, and "
         f"ACI fell {abs(ac.largest_daily_fall_pct):.2f}% on {ac.largest_fall_date}. Each follows a day with "
         "zero recorded volume, which matches a record date pattern. These falls are counted in the historical "
         "returns, so historical return and volatility for these three stocks are worse than the price risk "
         "alone, and the simulation treats part of a dividend payment as if it were a loss. No adjustment was "
         "made, because a checked dividend history for all 11 stocks was not available, and inventing one would "
         "be worse. Dividend income is also not added anywhere in the simulation."),
        ("Days with no trading are recorded as no change",
         "The DSE archive gives one row for every trading day for every stock, with the close held at the "
         "previous value when a stock did not trade. No days were filled by this project and no stock has "
         "missing days against the common calendar. The cost of that complete calendar is that no-trade days "
         f"appear as zero returns: CITYBANK has {ct.pct_days_zero_return:.1f}% zero return days and EBL has "
         f"{eb.pct_days_zero_return:.1f}%, which pulls their measured volatility down."),
        ("GBM method limits",
         "The GBM method assumes daily returns follow a normal distribution, that volatility stays constant, "
         "and that the average return of the last 469 days continues. Real DSE returns have more extreme days "
         "than a normal distribution, volatility changes over time, and the window used here was a falling "
         "period for several of these stocks, which pushes the simulated median down. GBM results should be "
         "read as a model estimate, not a forecast."),
        ("Bootstrap method limits",
         "The bootstrap method assumes the future will look like a reshuffle of the last 469 days. It keeps the "
         "real size of daily moves, including limit days and dividend reset days, but it breaks the order of "
         "days, so runs of bad days that happened together in real life are split up. It cannot produce a day "
         "worse than the worst day already seen."),
        ("Other limits",
         "The portfolio is a hypothetical Tk 1,000,000 split equally. It is not adjusted for brokerage costs, "
         "taxes, or the difficulty of buying thin stocks in equal amounts. Weights are held as buy and hold "
         "within each simulated path and are reset to equal only at the start. The Sharpe ratios in this project "
         "use a risk free rate of 0%, stated openly, because the aim is comparison inside the project and not "
         "comparison with Treasury bills."),
    ]
    return items
