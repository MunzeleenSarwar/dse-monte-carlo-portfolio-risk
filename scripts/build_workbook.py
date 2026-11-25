"""Build the Excel workbook from the saved results.

Sheets: Summary, Per-stock stats, Correlation, GBM results,
Bootstrap results, Data coverage, Limitations.
All text is black. Numbers come only from data/results.json and the
CSVs written by scripts/simulate.py.
"""
import json
import os
import sys

import pandas as pd
from openpyxl import Workbook
from openpyxl.styles import Font
from openpyxl.utils import get_column_letter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from limitations import build_limitations  # noqa: E402

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(BASE, "data")
OUT = os.path.join(BASE, "DSE_Monte_Carlo_Portfolio_Risk.xlsx")
BOLD = Font(bold=True)
BLACK = Font(color="000000")


def title_block(ws, title, lines):
    ws["A1"] = title
    ws["A1"].font = Font(bold=True, size=14)
    r = 2
    for ln in lines:
        ws.cell(row=r, column=1, value=ln)
        r += 1
    return r + 1


def write_table(ws, start_row, df, index=False):
    data = df.reset_index() if index else df
    for j, col in enumerate(data.columns, start=1):
        c = ws.cell(row=start_row, column=j, value=str(col))
        c.font = BOLD
    for i, (_, row) in enumerate(data.iterrows(), start=start_row + 1):
        for j, v in enumerate(row, start=1):
            ws.cell(row=i, column=j, value=v)
    return start_row + len(data) + 2


def widen(ws, widths):
    for i, w in enumerate(widths, start=1):
        ws.column_dimensions[get_column_letter(i)].width = w


def results_table(res, method):
    rows = []
    for h in ("21", "63", "252"):
        d = res[method][h]
        rows.append({
            "Horizon (trading days)": int(h),
            "Median ending value (Tk)": round(d["p50_value_tk"]),
            "5th percentile (Tk)": round(d["p5_value_tk"]),
            "95th percentile (Tk)": round(d["p95_value_tk"]),
            "Probability of loss (%)": round(d["prob_loss_pct"], 1),
            "Probability of loss over 10% (%)": round(d["prob_loss_over_10pct"], 1),
            "Probability of loss over 20% (%)": round(d["prob_loss_over_20pct"], 1),
            "VaR 95% (% loss)": d["var95_pct"],
            "VaR 95% (Tk loss)": d["var95_tk"],
            "CVaR 95% (% loss)": d["cvar95_pct"],
            "CVaR 95% (Tk loss)": d["cvar95_tk"],
            "VaR 99% (% loss)": d["var99_pct"],
            "VaR 99% (Tk loss)": d["var99_tk"],
            "CVaR 99% (% loss)": d["cvar99_pct"],
            "CVaR 99% (Tk loss)": d["cvar99_tk"],
        })
    return pd.DataFrame(rows)


def percentile_table(res, method):
    rows = []
    for h in ("21", "63", "252"):
        d = res[method][h]
        row = {"Horizon (trading days)": int(h)}
        for p in (1, 5, 25, 50, 75, 95, 99):
            row[f"P{p} value (Tk)"] = round(d[f"p{p}_value_tk"])
            row[f"P{p} return (%)"] = round(d[f"p{p}_return_pct"], 2)
        rows.append(row)
    return pd.DataFrame(rows)


def main():
    with open(os.path.join(DATA, "results.json")) as f:
        res = json.load(f)
    w = res["window"]
    g, b = res["gbm"]["252"], res["bootstrap"]["252"]
    dd = res["gbm_max_drawdown_252"]
    ph = res["portfolio_history"]
    wb = Workbook()

    ws = wb.active
    ws.title = "Summary"
    r = title_block(ws, "Monte Carlo Portfolio Risk Simulation, Dhaka Stock Exchange", [
        "Munzeleen Sarwar",
        "Hypothetical portfolio: Tk 1,000,000, equal weight (1/11 each) across 11 DSE stocks.",
        "Stocks: BATBC, BXPHARMA, CITYBANK, DBH, EBL, ROBI, ACI, BEXIMCO, FUWANGCER, GEMINISEA, SEAPEARL.",
        f"Price history used: {w['first_date']} to {w['last_date']}, {w['trading_days']} trading days, "
        "daily closing prices from the Dhaka Stock Exchange (unadjusted).",
        "Methods: correlated Geometric Brownian Motion and historical bootstrap. 10,000 simulations each, seed 42.",
        "Horizons: 21, 63 and 252 trading days. Sharpe ratios use a risk free rate of 0%.",
        "",
        f"Historical equal weight portfolio over the window: return {ph['annualised_return_pct']}% a year, "
        f"volatility {ph['annualised_volatility_pct']}% a year, worst day {ph['worst_day_pct']}%.",
    ])
    summary = pd.DataFrame([
        {"Measure, 252 trading days": "Median ending value, GBM (Tk)", "Value": round(g["p50_value_tk"])},
        {"Measure, 252 trading days": "Median ending value, bootstrap (Tk)", "Value": round(b["p50_value_tk"])},
        {"Measure, 252 trading days": "Probability of loss, GBM (%)", "Value": round(g["prob_loss_pct"], 1)},
        {"Measure, 252 trading days": "Probability of loss, bootstrap (%)", "Value": round(b["prob_loss_pct"], 1)},
        {"Measure, 252 trading days": "VaR 95%, GBM (Tk loss)", "Value": g["var95_tk"]},
        {"Measure, 252 trading days": "VaR 95%, bootstrap (Tk loss)", "Value": b["var95_tk"]},
        {"Measure, 252 trading days": "CVaR 95%, GBM (Tk loss)", "Value": g["cvar95_tk"]},
        {"Measure, 252 trading days": "CVaR 95%, bootstrap (Tk loss)", "Value": b["cvar95_tk"]},
        {"Measure, 252 trading days": "Median maximum drawdown, GBM paths (%)", "Value": dd["median_max_drawdown_pct"]},
        {"Measure, 252 trading days": "95th percentile maximum drawdown, GBM paths (%)", "Value": dd["p95_max_drawdown_pct"]},
    ])
    r = write_table(ws, r, summary)
    ws.cell(row=r, column=1, value="See the Limitations sheet before using any of these numbers.").font = BOLD
    widen(ws, [52, 18])

    ws = wb.create_sheet("Per-stock stats")
    r = title_block(ws, "Per-stock historical statistics", [
        f"Window: {w['first_date']} to {w['last_date']}. Annualised figures use 252 trading days. "
        "Sharpe uses a risk free rate of 0%. Prices are unadjusted, so dividend reset days count as falls."])
    stats = pd.read_csv(os.path.join(DATA, "per_stock_stats.csv"))
    write_table(ws, r, stats)
    widen(ws, [14, 14, 14, 16, 16, 18, 12, 12, 12])

    ws = wb.create_sheet("Correlation")
    r = title_block(ws, "Correlation of daily log returns", [
        "Correlation runs from -1 to 1. A value near 0 means two stocks did not tend to move together "
        "in this window. A value near 1 means they moved together, so holding both gave less risk reduction."])
    corr = pd.read_csv(os.path.join(DATA, "correlation.csv"), index_col=0).round(3)
    write_table(ws, r, corr, index=True)
    widen(ws, [14] + [11] * 11)

    for sheet, method in (("GBM results", "gbm"), ("Bootstrap results", "bootstrap")):
        ws = wb.create_sheet(sheet)
        name = "Correlated Geometric Brownian Motion" if method == "gbm" else "Historical bootstrap"
        r = title_block(ws, f"{name}: results by horizon", [
            "VaR 95% is the loss that is exceeded in 5% of simulations. CVaR 95% is the average loss in "
            "those worst 5% of simulations. Both are stated as losses on Tk 1,000,000."])
        r = write_table(ws, r, results_table(res, method))
        r = write_table(ws, r, percentile_table(res, method))
        if method == "gbm":
            ws.cell(row=r, column=1,
                    value=f"Maximum drawdown inside the 252 day GBM paths: median {dd['median_max_drawdown_pct']}%, "
                          f"95th percentile {dd['p95_max_drawdown_pct']}%, 99th percentile {dd['p99_max_drawdown_pct']}%.").font = BOLD
        widen(ws, [16, 16, 16, 16, 16, 18, 18, 14, 14, 14, 14, 14, 14, 14, 14])

    ws = wb.create_sheet("Data coverage")
    r = title_block(ws, "Data coverage and problem counts per stock", [
        "One row per stock from the DSE archive. The archive gives one row per trading day, with the close "
        "held at the previous value on days a stock did not trade, so no days are missing and no days were "
        "filled by this project. Zero return days and zero volume days show how often that happened."])
    cov = pd.read_csv(os.path.join(DATA, "data_coverage.csv"))
    write_table(ws, r, cov)
    widen(ws, [14, 12, 12, 8, 14, 14, 12, 14, 14, 14, 14, 14, 14, 10])

    ws = wb.create_sheet("Limitations")
    r = title_block(ws, "Limitations and data problems", [
        "These problems are part of the results. They are stated with counts from the data used."])
    for head, text in build_limitations():
        c = ws.cell(row=r, column=1, value=head); c.font = BOLD
        r += 1
        c = ws.cell(row=r, column=1, value=text)
        c.alignment = c.alignment.copy(wrap_text=True, vertical="top")
        ws.row_dimensions[r].height = 105
        r += 2
    ws.column_dimensions["A"].width = 150

    wb.save(OUT)
    print("saved", OUT, "sheets:", wb.sheetnames)


if __name__ == "__main__":
    main()
