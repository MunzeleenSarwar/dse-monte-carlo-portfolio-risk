"""Build DSE_Extended_Portfolio_Analysis.xlsx from data/extended_results.json
and the extended analysis CSV files. All text is black, no em dashes."""
import json
import os

import pandas as pd
from openpyxl import Workbook
from openpyxl.styles import Font
from openpyxl.utils import get_column_letter

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(BASE, "data")
R = json.load(open(os.path.join(DATA, "extended_results.json")))
P1 = json.load(open(os.path.join(DATA, "results.json")))
BOLD = Font(bold=True)


def put(ws, rows, widths=None):
    for row in rows:
        ws.append(row)
    for r in ws.iter_rows():
        for c in r:
            if isinstance(c.value, str) and c.value.startswith("**"):
                c.value = c.value[2:]
                c.font = BOLD
    if widths:
        for i, wd in enumerate(widths, 1):
            ws.column_dimensions[get_column_letter(i)].width = wd


def table(ws, df):
    ws.append(list(df.columns))
    for c in ws[ws.max_row]:
        c.font = BOLD
    for _, row in df.iterrows():
        ws.append(list(row))


def main():
    wb = Workbook()
    dd = R["drawdown_downside"]
    div = R["diversification"]
    rd = R["risk_decomposition"]
    liq = R["liquidity"]
    st = R["stress_tests"]
    tt = R["student_t"]
    beta = R["beta_vs_dsex"]
    grades = {}
    for g in liq["grades"]:
        grades[g["liquidity_grade"]] = grades.get(g["liquidity_grade"], 0) + 1

    ws = wb.active
    ws.title = "Verdict summary"
    put(ws, [
        ["**Extended analysis verdict summary"],
        ["Portfolio: hypothetical Tk 1,000,000, equal weight across 11 DSE stocks. Window: 3 Nov 2024 to 15 Oct 2026, 469 trading days."],
        [],
        ["**Area", "**Verdict", "**Key evidence"],
        ["Return", "Bad in this window, not proven for the long term",
         f"Total return {dd['total_return_pct']}% on the daily rebalanced path; CAGR {dd['cagr_pct']}%; Monte Carlo median ending value below Tk 1,000,000 under all three methods at 252 days; probability of a one year loss 58.8% to 60.3%."],
        ["Risk", "High",
         f"Volatility 17.36% a year; realised maximum drawdown {dd['max_drawdown_pct']}%; one year VaR 95% between Tk 270,206 and Tk 288,883 across the three methods; GBM CVaR 99% Tk 405,927."],
        ["Diversification", "Good on volatility, weaker on risk concentration",
         f"Diversification ratio {div['diversification_ratio']} (average stock volatility {div['weighted_avg_individual_volatility_pct']}% against portfolio {div['portfolio_volatility_pct']}%); average correlation {div['average_pairwise_correlation']}; effective risk bets {rd['effective_number_of_risk_bets']} of 11; but SEAPEARL, FUWANGCER and GEMINISEA hold 39.9% of total risk on 27.3% of the money."],
        ["Liquidity", "Poor, because of one trapped stock",
         f"Grades: {grades.get('Good', 0)} Good, {grades.get('Thin', 0)} Thin, {grades.get('Trapped', 0)} Trapped. BEXIMCO needs 1,376 days to sell Tk 90,909 at 20% of its median daily traded value of Tk 330 (median volume of 3 shares at its frozen price of Tk 110.1). The other 10 each need less than one day on that rule."],
        ["Data quality", "Weak",
         "History is 1.86 years. Prices are not adjusted for dividends and three dividend reset falls are inside the returns. BEXIMCO price was fixed for a full calendar year. No DSEX index series could be fetched, so beta could not be calculated."],
        [],
        ["Full wording is in DSE_Extended_Portfolio_Analysis_Report.pdf. Nothing in this workbook is a recommendation to buy or sell any stock."],
    ], widths=[20, 42, 110])

    ws = wb.create_sheet("Risk decomposition")
    put(ws, [["**Risk decomposition (share of portfolio volatility)"],
             [f"Portfolio volatility: {rd['portfolio_volatility_pct']}% a year. Effective number of risk bets: {rd['effective_number_of_risk_bets']} of 11."],
             []])
    table(ws, pd.read_csv(os.path.join(DATA, "extended_risk_decomposition.csv")))
    put(ws, [[],
             ["**Component VaR 95% at 252 days, GBM paths (worst 5% of outcomes)"],
             [R["component_var95_252"]["method"]],
             []])
    table(ws, pd.read_csv(os.path.join(DATA, "extended_component_var.csv")))
    put(ws, [[],
             ["Flag: " + rd["note_beximco"]],
             ["Note: BEXIMCO is the largest single part of the tail loss in the GBM component VaR (see table above), even though its share of measured daily volatility risk is the smallest. In the simulation its own volatility acts every day; in the historical covariance its long zero return stretches pull its measured share down."]])

    ws = wb.create_sheet("Diversification")
    put(ws, [
        ["**Diversification"],
        ["Weighted average individual volatility (%)", div["weighted_avg_individual_volatility_pct"]],
        ["Portfolio volatility (%)", div["portfolio_volatility_pct"]],
        ["Diversification ratio", div["diversification_ratio"]],
        ["Average pairwise correlation", div["average_pairwise_correlation"]],
        ["Rolling 63 day average correlation, lowest", div["rolling_63d_avg_corr_min"]],
        ["Rolling 63 day average correlation, highest", div["rolling_63d_avg_corr_max"]],
        ["Rolling 63 day average correlation, latest", div["rolling_63d_avg_corr_latest"]],
        [],
        ["Reading: a diversification ratio of 1.83 means the portfolio volatility is a little over half of the weighted average stock volatility. Correlation is positive but low, which is why the reduction is large."],
    ], widths=[46, 18])

    ws = wb.create_sheet("Drawdown and downside")
    rows = [["**Drawdown and downside"],
            [dd["definition"]], []]
    for k, v in dd.items():
        if k not in ("definition", "worst_10_days"):
            rows.append([k, v])
    put(ws, rows, widths=[42, 60])
    put(ws, [[], ["**Worst 10 portfolio days"], []])
    table(ws, pd.read_csv(os.path.join(DATA, "extended_worst_days.csv")))

    ws = wb.create_sheet("Distribution tests")
    put(ws, [["**Distribution tests"],
             [R["distribution"]["basis"]], []])
    table(ws, pd.read_csv(os.path.join(DATA, "extended_distribution_tests.csv")))
    t = R["distribution"]["tail_simple_returns"]
    put(ws, [[],
             ["**Tail comparison, portfolio daily simple returns"],
             ["Empirical 1% day (%)", t["empirical_p1_pct"]],
             ["Normal prediction for 1% day (%)", t["normal_p1_pct"]],
             ["Empirical 99% day (%)", t["empirical_p99_pct"]],
             ["Normal prediction for 99% day (%)", t["normal_p99_pct"]],
             [],
             ["Reading: normality is rejected for the portfolio and for most stocks. The left tail is fatter than a normal distribution predicts; the right tail at 99% is close to the normal prediction in this window."]])

    ws = wb.create_sheet("Liquidity")
    put(ws, [["**Liquidity"],
             ["Grade rule: " + liq["grade_rule"]],
             ["Amihud: " + liq["amihud_formula"]], []])
    table(ws, pd.read_csv(os.path.join(DATA, "extended_liquidity.csv")))

    ws = wb.create_sheet("Stress tests")
    put(ws, [["**Stress tests (all hypothetical, equal weights, on Tk 1,000,000)"],
             [f"Worst scenario: {st['worst_scenario']}"], []])
    table(ws, pd.read_csv(os.path.join(DATA, "extended_stress_tests.csv")))

    ws = wb.create_sheet("Beta vs DSEX")
    if beta["status"] == "computed":
        table(ws, pd.DataFrame(beta["all"]))
        put(ws, [[], [beta["alpha_statement"]]])
    else:
        put(ws, [["**Beta against DSEX: not computed"],
                 [beta["reason"]],
                 [],
                 ["**Attempts (full log in data/extended_dsex_fetch_log.csv)"]])
        table(ws, pd.DataFrame(beta["attempts"]))

    ws = wb.create_sheet("Volatility models")
    ew, ga = R["ewma"], R["garch"]
    rows = [["**EWMA volatility (RiskMetrics)"],
            ["Lambda", ew["lambda"]],
            ["Latest volatility (% a year)", ew["latest_vol_pct"]],
            ["Lowest (% a year)", ew["min_vol_pct"]],
            ["Highest (% a year)", ew["max_vol_pct"]],
            ["Rolling 63 day volatility range (% a year)",
             f"{R['rolling_risk']['vol_63d_min_pct']} to {R['rolling_risk']['vol_63d_max_pct']}"],
            ["Rolling 63 day Sharpe range",
             f"{R['rolling_risk']['sharpe_63d_min']} to {R['rolling_risk']['sharpe_63d_max']} (latest {R['rolling_risk']['sharpe_63d_latest']})"],
            [],
            ["**GARCH(1,1), portfolio daily log returns"]]
    if ga.get("fitted"):
        rows += [["Omega", ga["omega"]], ["Alpha", ga["alpha"]],
                 ["Beta", ga["beta"]],
                 ["Persistence (alpha + beta)", ga["persistence_alpha_plus_beta"]],
                 ["Next day volatility forecast (%)", ga["next_day_vol_pct"]],
                 ["Next day volatility, annualised (%)", ga["next_day_vol_annualised_pct"]],
                 ["Flag", ga["flag"]]]
    else:
        rows.append(["Not fitted", ga.get("error", "arch package not available")])
    put(ws, rows, widths=[44, 90])

    ws = wb.create_sheet("Fat-tail Monte Carlo")
    put(ws, [["**Fat tail Monte Carlo: correlated Student-t shocks"],
             [tt["df_method"]],
             [f"Portfolio excess kurtosis: {tt['portfolio_excess_kurtosis']}. Degrees of freedom estimated: {tt['df_estimated']}. Used: {tt['df_used']}."],
             [tt["scaling"]],
             [],
             ["**Three method comparison"],
             ["Horizon (days)", "Method", "Median ending value (Tk)", "VaR 95% (Tk)", "VaR 99% (Tk)", "CVaR 95% (Tk)", "CVaR 99% (Tk)", "Probability of loss (%)"]])
    for h in ("21", "63", "252"):
        for m in ("gbm", "bootstrap", "student_t"):
            c = tt["three_method_comparison"][h][m]
            ws.append([int(h), m, c["median_value_tk"], c["var95_tk"],
                       c["var99_tk"], c["cvar95_tk"], c["cvar99_tk"],
                       c["prob_loss_pct"]])

    ws = wb.create_sheet("Fundamentals")
    put(ws, [["**Fundamental snapshot"],
             [R["fundamentals"]["source"]],
             [R["fundamentals"]["fiscal_year_flag"]],
             [f"Group median PE (stocks with a PE shown): {R['fundamentals']['group_median_pe']}"],
             []])
    fdf = pd.read_csv(os.path.join(DATA, "extended_fundamentals.csv"))
    keep = ["ticker", "company_name", "industry", "fiscal_year_end",
            "market_cap_bdt", "eps_ttm_bdt", "eps_basis", "pe_ratio",
            "dividend_yield_pct", "annual_dividend_bdt",
            "latest_cash_dividend", "cash_dividend_pct", "stock_dividend_pct",
            "roe_ttm_pct", "quality_note"]
    table(ws, fdf[keep])

    ws = wb.create_sheet("Limitations")
    put(ws, [
        ["**Extended analysis limitations"],
        ["1. Beta against DSEX could not be calculated. " + (beta["reason"] if beta["status"] != "computed" else "See the Beta vs DSEX sheet.")],
        ["2. The window is 469 trading days (1.86 years). The standard error of the annual mean return is about 12.7 percentage points, so the negative return in this window does not prove the long term return is negative. Risk measures such as volatility are measured more precisely than returns at this length."],
        ["3. " + rd["note_beximco"]],
        ["4. Prices are not adjusted for dividends. CITYBANK fell 16.67% on 2025-05-24, EBL fell 20.74% on 2025-04-24 and ACI fell 14.07% on 2024-11-18, each after a zero volume day, matching dividend record date resets. These falls are inside every return based measure in the extended analysis, and dividend income is not counted."],
        ["5. The daily rebalanced equal weight path used for drawdown and downside is a stated measuring rule. The main simulation used buy and hold paths inside each simulation. The two path definitions give slightly different total returns and both are labelled where used."],
        ["6. The Student-t simulation uses one degrees of freedom value, estimated from the portfolio kurtosis, for all 11 stocks and all days. Real tail weight differs by stock and over time."],
        ["7. GARCH(1,1) was fitted on 468 returns, which is at the low end for this model. Its parameters are a check on EWMA, not a stand alone forecast."],
        ["8. Stress scenarios are simple price shocks at equal weights with no trading costs, no price limits applied after the first day, and no reaction by other holders. Real losses can be larger, in part because a trapped stock cannot be sold at the quoted price."],
        ["9. Liquidity grades rest on median traded value. Medians hide single large trading days, and traded value in a rising market is usually higher than in a falling one."],
        ["10. Fundamental figures are a snapshot from one source on one date. Fiscal years end in June for some companies and December for others. Five of the 11 stocks show no PE because their EPS is negative, which is a fact about the companies, not missing data."],
        ["11. Nothing in the extended analysis is a recommendation to buy or sell any stock."],
    ], widths=[130])
    out = os.path.join(BASE, "DSE_Extended_Portfolio_Analysis.xlsx")
    wb.save(out)
    print("written", out, "sheets:", wb.sheetnames)


if __name__ == "__main__":
    main()
