"""Charts for the DSE Monte Carlo portfolio risk project.

Reads data/results.json, data/gbm_fan_chart.csv, data/correlation.csv,
data/combined_close.csv and data/ending_values.npz, which are produced
by scripts/simulate.py. Charts may use colour; report text may not.
"""
import json
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(BASE, "data")
CHARTS = os.path.join(BASE, "charts")
os.makedirs(CHARTS, exist_ok=True)
START = 1_000_000.0


def main():
    with open(os.path.join(DATA, "results.json")) as f:
        res = json.load(f)
    fan = pd.read_csv(os.path.join(DATA, "gbm_fan_chart.csv"))
    closes = pd.read_csv(os.path.join(DATA, "combined_close.csv"),
                         parse_dates=["date"], index_col="date")
    endings = np.load(os.path.join(DATA, "ending_values.npz"))

    # 1. Fan chart, GBM 252 days
    fig, ax = plt.subplots(figsize=(9, 5))
    ax.fill_between(fan.day, fan.p1, fan.p99, color="#c7d7ea", label="1st to 99th percentile")
    ax.fill_between(fan.day, fan.p5, fan.p95, color="#8fb0d8", label="5th to 95th percentile")
    ax.fill_between(fan.day, fan.p25, fan.p75, color="#4f7fb8", label="25th to 75th percentile")
    ax.plot(fan.day, fan.p50, color="#0b2e59", lw=2, label="Median")
    ax.axhline(START, color="black", lw=1, ls="--")
    ax.set_xlabel("Trading days ahead")
    ax.set_ylabel("Portfolio value (Tk)")
    ax.set_title("Simulated portfolio value, correlated GBM, 10,000 paths")
    ax.legend(loc="upper left", fontsize=8)
    ax.yaxis.set_major_formatter(lambda v, p: f"{v:,.0f}")
    fig.tight_layout(); fig.savefig(os.path.join(CHARTS, "fan_chart_gbm_252.png"), dpi=160); plt.close(fig)

    # 2 and 3. Ending value histograms at 252 days
    for key, title, fname, colour in (
            ("gbm_252", "Ending value after 252 days, correlated GBM", "histogram_gbm_252.png", "#4f7fb8"),
            ("boot_252", "Ending value after 252 days, historical bootstrap", "histogram_bootstrap_252.png", "#7aa05a")):
        vals = endings[key] / 1000.0
        fig, ax = plt.subplots(figsize=(9, 5))
        ax.hist(vals, bins=60, color=colour, edgecolor="white", lw=0.3)
        ax.axvline(1000, color="black", lw=1.5, ls="--", label="Starting value Tk 1,000,000")
        ax.axvline(float(np.percentile(vals, 5)), color="#b03a2e", lw=1.5,
                   label="5th percentile (VaR 95 point)")
        ax.set_xlabel("Ending portfolio value (Tk thousand)")
        ax.set_ylabel("Number of simulations")
        ax.set_title(title)
        ax.legend(fontsize=8)
        fig.tight_layout(); fig.savefig(os.path.join(CHARTS, fname), dpi=160); plt.close(fig)

    # 4. Correlation heatmap
    corr = pd.read_csv(os.path.join(DATA, "correlation.csv"), index_col=0)
    fig, ax = plt.subplots(figsize=(8.5, 7))
    im = ax.imshow(corr.values, cmap="RdYlBu_r", vmin=-1, vmax=1)
    ax.set_xticks(range(len(corr)), corr.columns, rotation=45, ha="left", fontsize=8)
    ax.set_yticks(range(len(corr)), corr.index, fontsize=8)
    for i in range(len(corr)):
        for j in range(len(corr)):
            ax.text(j, i, f"{corr.values[i, j]:.2f}", ha="center", va="center", fontsize=7)
    ax.set_title("Correlation of daily log returns, 3 Nov 2024 to 15 Oct 2026")
    fig.colorbar(im, ax=ax, shrink=0.85)
    fig.tight_layout(); fig.savefig(os.path.join(CHARTS, "correlation_heatmap.png"), dpi=160); plt.close(fig)

    # 5. Normalised price history (start = 100)
    norm = closes / closes.iloc[0] * 100
    fig, ax = plt.subplots(figsize=(9, 5))
    for c in norm.columns:
        ax.plot(norm.index, norm[c], lw=1.1, label=c)
    ax.axhline(100, color="black", lw=0.8, ls="--")
    ax.set_ylabel("Price, first day = 100")
    ax.set_title("Price history used in the simulation, unadjusted DSE closing prices")
    ax.legend(ncol=4, fontsize=8, loc="upper center", bbox_to_anchor=(0.5, -0.14))
    fig.tight_layout(); fig.savefig(os.path.join(CHARTS, "price_history_normalised.png"), dpi=160); plt.close(fig)

    # 6. Historical equal-weight portfolio value, Tk 1,000,000 start (price return only)
    port = (closes / closes.iloc[0]).mean(axis=1) * START
    fig, ax = plt.subplots(figsize=(9, 4.5))
    ax.plot(port.index, port.values, color="#0b2e59", lw=1.4)
    ax.axhline(START, color="black", lw=0.9, ls="--")
    ax.set_ylabel("Value (Tk)")
    ax.set_title("What Tk 1,000,000 equal weight would have done, 3 Nov 2024 to 15 Oct 2026 (prices only)")
    ax.yaxis.set_major_formatter(lambda v, p: f"{v:,.0f}")
    fig.tight_layout(); fig.savefig(os.path.join(CHARTS, "historical_portfolio_value.png"), dpi=160); plt.close(fig)

    # 7. VaR comparison across horizons and methods
    labels, g95, b95, g99, b99 = [], [], [], [], []
    for h in ("21", "63", "252"):
        labels.append(f"{h} days")
        g95.append(res["gbm"][h]["var95_pct"]); b95.append(res["bootstrap"][h]["var95_pct"])
        g99.append(res["gbm"][h]["var99_pct"]); b99.append(res["bootstrap"][h]["var99_pct"])
    x = np.arange(len(labels)); w = 0.2
    fig, ax = plt.subplots(figsize=(9, 5))
    ax.bar(x - 1.5 * w, g95, w, label="GBM VaR 95%", color="#4f7fb8")
    ax.bar(x - 0.5 * w, b95, w, label="Bootstrap VaR 95%", color="#7aa05a")
    ax.bar(x + 0.5 * w, g99, w, label="GBM VaR 99%", color="#0b2e59")
    ax.bar(x + 1.5 * w, b99, w, label="Bootstrap VaR 99%", color="#3d5a2a")
    ax.set_xticks(x, labels); ax.set_ylabel("Loss (% of starting value)")
    ax.set_title("Value at Risk by horizon and method (loss, % of Tk 1,000,000)")
    ax.legend(fontsize=8)
    fig.tight_layout(); fig.savefig(os.path.join(CHARTS, "var_comparison.png"), dpi=160); plt.close(fig)

    print("charts:", sorted(os.listdir(CHARTS)))


if __name__ == "__main__":
    main()
