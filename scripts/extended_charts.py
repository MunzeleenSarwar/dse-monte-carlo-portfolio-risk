"""Extended analysis charts. Reads the saved extended analysis CSV files only."""
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy import stats

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(BASE, "data")
CH = os.path.join(BASE, "charts")
os.makedirs(CH, exist_ok=True)


def main():
    risk = pd.read_csv(os.path.join(DATA, "extended_risk_decomposition.csv"))
    fig, ax = plt.subplots(figsize=(8, 4.6))
    ax.barh(risk["ticker"][::-1], risk["pct_of_portfolio_risk"][::-1],
            color="#4472C4")
    ax.axvline(100 / 11, color="red", ls="--", lw=1,
               label="Equal capital weight (9.09%)")
    ax.set_xlabel("Share of portfolio risk (%)")
    ax.set_title("Extended analysis: share of portfolio risk by stock")
    ax.legend()
    fig.tight_layout()
    fig.savefig(os.path.join(CH, "extended_risk_contribution.png"), dpi=150)
    plt.close(fig)

    dd = pd.read_csv(os.path.join(DATA, "extended_drawdown_series.csv"),
                     parse_dates=["date"])
    fig, axes = plt.subplots(2, 1, figsize=(8, 5), sharex=True)
    axes[0].plot(dd["date"], dd["wealth_tk"] / 1e5, color="#4472C4")
    axes[0].set_ylabel("Value (Tk lakh)")
    axes[0].set_title("Extended analysis: daily rebalanced equal weight portfolio value")
    axes[1].fill_between(dd["date"], dd["drawdown_pct"], 0, color="#C00000",
                         alpha=0.6)
    axes[1].set_ylabel("Drawdown (%)")
    fig.tight_layout()
    fig.savefig(os.path.join(CH, "extended_drawdown.png"), dpi=150)
    plt.close(fig)

    qq = pd.read_csv(os.path.join(DATA, "extended_qq_data.csv"))
    fig, ax = plt.subplots(figsize=(5.2, 5.2))
    ax.scatter(qq["theoretical_quantile"], qq["sample_quantile"] * 100,
               s=8, color="#4472C4")
    lo = float(np.nanmin(qq["sample_quantile"] * 100))
    hi = float(np.nanmax(qq["sample_quantile"] * 100))
    theo = stats.norm.ppf([0.001, 0.999]) * float(
        np.std(pd.read_csv(os.path.join(DATA, "extended_qq_data.csv"))["sample_quantile"], ddof=1)) * 100
    ax.plot(theo, theo, color="red", lw=1, label="Normal line")
    ax.set_xlabel("Normal theoretical quantile")
    ax.set_ylabel("Sample quantile of daily log returns (%)")
    ax.set_title("Extended analysis: QQ plot, portfolio daily log returns")
    ax.legend()
    fig.tight_layout()
    fig.savefig(os.path.join(CH, "extended_qq_plot.png"), dpi=150)
    plt.close(fig)

    ew = pd.read_csv(os.path.join(DATA, "extended_ewma.csv"), parse_dates=["date"])
    fig, ax = plt.subplots(figsize=(8, 4.2))
    ax.plot(ew["date"], ew["rolling_vol_63d_pct"], color="#7F7F7F",
            label="Rolling 63 day volatility")
    ax.plot(ew["date"], ew["ewma_vol_pct"], color="#4472C4",
            label="EWMA volatility (lambda 0.94)")
    ax.set_ylabel("Volatility (% a year)")
    ax.set_title("Extended analysis: rolling volatility and EWMA volatility")
    ax.legend()
    fig.tight_layout()
    fig.savefig(os.path.join(CH, "extended_rolling_vol_ewma.png"), dpi=150)
    plt.close(fig)

    liq = pd.read_csv(os.path.join(DATA, "extended_liquidity.csv"))
    liq = liq.sort_values("days_to_exit_20pct_of_median")
    fig, ax = plt.subplots(figsize=(8, 4.6))
    ax.barh(liq["ticker"], liq["days_to_exit_20pct_of_median"],
            color="#4472C4")
    ax.set_xscale("log")
    ax.set_xlabel("Days to sell Tk 90,909 at 20% of median daily traded value (log scale)")
    ax.set_title("Extended analysis: days needed to sell one equal weight position")
    fig.tight_layout()
    fig.savefig(os.path.join(CH, "extended_liquidity_days.png"), dpi=150)
    plt.close(fig)

    st = pd.read_csv(os.path.join(DATA, "extended_stress_tests.csv"))
    st = st.sort_values("loss_tk")
    labels = [s.split(". ", 1)[-1].split(" (hypothetical)")[0] for s in st["scenario"]]
    fig, ax = plt.subplots(figsize=(8, 4.8))
    ax.barh(labels, st["loss_tk"] / 1000, color="#C00000")
    ax.set_xlabel("Loss (Tk thousand) on Tk 1,000,000")
    ax.set_title("Stress test losses (hypothetical)")
    fig.tight_layout()
    fig.savefig(os.path.join(CH, "extended_stress_tests.png"), dpi=150)
    plt.close(fig)

    fund = pd.read_csv(os.path.join(DATA, "extended_fundamentals.csv"))
    eps = pd.to_numeric(fund["eps_ttm_bdt"], errors="coerce")
    fig, ax = plt.subplots(figsize=(8, 4.4))
    colors = ["#4472C4" if v >= 0 else "#C00000" for v in eps]
    ax.bar(fund["ticker"], eps, color=colors)
    ax.axhline(0, color="black", lw=0.8)
    ax.set_ylabel("EPS, trailing twelve months (Tk)")
    ax.set_title("Extended analysis: earnings per share by stock (red: loss making)")
    plt.setp(ax.get_xticklabels(), rotation=30, ha="left")
    fig.tight_layout()
    fig.savefig(os.path.join(CH, "extended_fundamentals_eps.png"), dpi=150)
    plt.close(fig)
    print("Extended Analysis charts written to", CH)


if __name__ == "__main__":
    main()
