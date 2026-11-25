"""Build the report PDF from data/results.json.

Rules followed: plain direct language, no first person, no em dashes,
the author name appears at the top only, all report text, headings and
tables in black, charts may use colour.
Run with a Python that has reportlab installed.
"""
import json
import os
import re
import sys

import pandas as pd
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (Image, KeepTogether, ListFlowable, ListItem,
                                PageBreak, Paragraph, SimpleDocTemplate, Spacer,
                                Table, TableStyle)

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from limitations import build_limitations  # noqa: E402

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(BASE, "data")
CHARTS = os.path.join(BASE, "charts")
OUT = os.path.join(BASE, "DSE_Monte_Carlo_Portfolio_Risk_Report.pdf")

FD = "/usr/share/fonts/truetype/liberation"
ND = "/usr/share/fonts/truetype/noto"
# Times New Roman is a Microsoft font and is not installed on this
# machine. Liberation Serif is its metric compatible twin (same letter
# widths) and is registered here under the Times name, so body text,
# headings, captions and explanations are set in Times.
pdfmetrics.registerFont(TTFont("Times", f"{FD}/LiberationSerif-Regular.ttf"))
pdfmetrics.registerFont(TTFont("Times-Bold", f"{FD}/LiberationSerif-Bold.ttf"))
pdfmetrics.registerFont(TTFont("Times-Italic", f"{FD}/LiberationSerif-Italic.ttf"))
pdfmetrics.registerFont(TTFont("Times-BoldItalic", f"{FD}/LiberationSerif-BoldItalic.ttf"))
pdfmetrics.registerFontFamily("Times", normal="Times", bold="Times-Bold",
                              italic="Times-Italic", boldItalic="Times-BoldItalic")
# Tables keep a sans font, Noto Sans.
pdfmetrics.registerFont(TTFont("Sans", f"{ND}/NotoSans-Regular.ttf"))
pdfmetrics.registerFont(TTFont("Sans-Bold", f"{ND}/NotoSans-Bold.ttf"))
pdfmetrics.registerFont(TTFont("Sans-Italic", f"{ND}/NotoSans-Italic.ttf"))
pdfmetrics.registerFont(TTFont("Sans-BoldItalic", f"{ND}/NotoSans-BoldItalic.ttf"))
pdfmetrics.registerFontFamily("Sans", normal="Sans", bold="Sans-Bold",
                              italic="Sans-Italic", boldItalic="Sans-BoldItalic")

S = {
    "title": ParagraphStyle("title", fontName="Times-Bold", fontSize=19, leading=23, textColor=colors.black),
    "name": ParagraphStyle("name", fontName="Times", fontSize=12, leading=15, textColor=colors.black),
    "h1": ParagraphStyle("h1", fontName="Times-Bold", fontSize=13.5, leading=17, spaceBefore=10, spaceAfter=4, keepWithNext=1, textColor=colors.black),
    "h2": ParagraphStyle("h2", fontName="Times-Bold", fontSize=11.5, leading=15, spaceBefore=8, spaceAfter=3, keepWithNext=1, textColor=colors.black),
    "body": ParagraphStyle("body", fontName="Times", fontSize=10.3, leading=14.2, spaceAfter=5, alignment=4, textColor=colors.black),
    "small": ParagraphStyle("small", fontName="Times", fontSize=9, leading=12, spaceAfter=4, textColor=colors.black),
    "cell": ParagraphStyle("cell", fontName="Sans", fontSize=7.8, leading=9.6, textColor=colors.black),
    "cellb": ParagraphStyle("cellb", fontName="Sans-Bold", fontSize=7.8, leading=9.6, textColor=colors.black),
    "cellw": ParagraphStyle("cellw", fontName="Sans-Bold", fontSize=7.8, leading=9.6, textColor=colors.white),
    "caption": ParagraphStyle("caption", fontName="Times-Bold", fontSize=10.3, leading=13.5, spaceBefore=7, spaceAfter=3, keepWithNext=1, textColor=colors.black),
    "expl": ParagraphStyle("expl", fontName="Times", fontSize=10.3, leading=14.2, spaceBefore=3, spaceAfter=7, alignment=4, textColor=colors.black),
    "expl_open": ParagraphStyle("expl_open", fontName="Times", fontSize=10.3, leading=14.2, spaceBefore=3, spaceAfter=2, alignment=4, textColor=colors.black),
    "bullet": ParagraphStyle("bullet", fontName="Times", fontSize=10.3, leading=14.2, spaceAfter=2, alignment=4, textColor=colors.black),
}


def P(text, style="body"):
    return Paragraph(text, S[style])


_counts = {"table": 0, "figure": 0}


def cap_table(title):
    _counts["table"] += 1
    return P(f"Table {_counts['table']}: {title}", "caption")


def cap_figure(title):
    _counts["figure"] += 1
    return P(f"Figure {_counts['figure']}: {title}", "caption")


def split_sentences(text):
    return [s for s in re.split(r"(?<=[.!?])\s+(?=[A-Z(])", str(text).strip()) if s]


def bullet_list(items, style="bullet"):
    lf = ListFlowable([ListItem(P(it, style), leftIndent=16) for it in items],
                      bulletType="bullet", leftIndent=16,
                      bulletFontName="Times", bulletFontSize=8)
    lf.spaceAfter = 6
    return lf


def expl_block(text):
    sents = split_sentences(text)
    if len(sents) <= 1:
        return [P(text, "expl")]
    return [P(sents[0], "expl_open"), bullet_list(sents[1:])]


def expl_table(text):
    return expl_block(text)


def expl_figure(text):
    return expl_block(text)


def bulleted(text, style="body", n_open=1, n_close=0, groups=None):
    sents = split_sentences(text)
    out = []
    end = len(sents) - n_close if n_close else len(sents)
    body_sents = sents[n_open:end]
    if n_open:
        out.append(P(" ".join(sents[:n_open]), style))
    if groups:
        items, i = [], 0
        for g in groups:
            items.append(" ".join(body_sents[i:i + g]))
            i += g
        if i < len(body_sents):
            items.append(" ".join(body_sents[i:]))
    else:
        items = body_sents
    if items:
        out.append(bullet_list(items))
    if n_close:
        out.append(P(" ".join(sents[end:]), style))
    return out


def table(data, widths, header=True):
    t = Table(data, colWidths=widths, repeatRows=1 if header else 0, hAlign="LEFT")
    style = [("VALIGN", (0, 0), (-1, -1), "TOP"),
             ("LEFTPADDING", (0, 0), (-1, -1), 3), ("RIGHTPADDING", (0, 0), (-1, -1), 3),
             ("TOPPADDING", (0, 0), (-1, -1), 2.5), ("BOTTOMPADDING", (0, 0), (-1, -1), 2.5),
             ("LINEBELOW", (0, -1), (-1, -1), 0.7, colors.black)]
    if header:
        style += [("BACKGROUND", (0, 0), (-1, 0), colors.black),
                  ("LINEBELOW", (0, 0), (-1, 0), 0.7, colors.black)]
    t.setStyle(TableStyle(style))
    return t


def head_row(cells):
    return [Paragraph(c, S["cellw"]) for c in cells]


def row(cells, bold_first=False):
    out = []
    for i, c in enumerate(cells):
        out.append(Paragraph(str(c), S["cellb"] if (bold_first and i == 0) else S["cell"]))
    return out


def tk(v):
    return f"{v:,.0f}"


def main():
    with open(os.path.join(DATA, "results.json")) as f:
        res = json.load(f)
    w, ph, dd = res["window"], res["portfolio_history"], res["gbm_max_drawdown_252"]
    stats = pd.read_csv(os.path.join(DATA, "per_stock_stats.csv"))
    cov = pd.read_csv(os.path.join(DATA, "data_coverage.csv"))
    corr = pd.read_csv(os.path.join(DATA, "correlation.csv"), index_col=0)
    # average off-diagonal correlation
    n = len(corr)
    avg_corr = float((corr.values.sum() - n) / (n * (n - 1)))

    story = []
    story.append(P("Monte Carlo Portfolio Risk Simulation: Dhaka Stock Exchange", "title"))
    story.append(Spacer(1, 3 * mm))
    story.append(P("Munzeleen Sarwar", "name"))
    story.append(P("Hypothetical portfolio of Tk 1,000,000, split equally across 11 stocks listed on the "
                   "Dhaka Stock Exchange. Prices from 3 November 2024 to 15 October 2026.", "small"))
    story.append(P("Summary", "h1"))
    g, b = res["gbm"]["252"], res["bootstrap"]["252"]
    story.extend(bulleted(
        f"A hypothetical Tk 1,000,000 portfolio, split equally across 11 Dhaka Stock Exchange stocks, was "
        f"simulated 10,000 times over 21, 63 and 252 trading days, using two methods. Over 252 trading days, "
        f"about one trading year, the median ending value was Tk {tk(g['p50_value_tk'])} with the correlated "
        f"GBM method and Tk {tk(b['p50_value_tk'])} with the historical bootstrap method. The probability of "
        f"ending the year with a loss was {g['prob_loss_pct']:.1f}% under GBM and {b['prob_loss_pct']:.1f}% "
        f"under the bootstrap. Value at Risk at 95% for one year was Tk {tk(g['var95_tk'])} under GBM and "
        f"Tk {tk(b['var95_tk'])} under the bootstrap. In plain terms, in 5% of simulations the portfolio lost "
        f"more than about Tk {tk(g['var95_tk'])}. The average loss in that worst 5% of simulations, called "
        f"CVaR or expected shortfall, was Tk {tk(g['cvar95_tk'])} under GBM. Inside the simulated one year "
        f"paths, the median largest fall from a peak was {dd['median_max_drawdown_pct']:.1f}%, and in 5% of "
        f"paths the largest fall was {dd['p95_max_drawdown_pct']:.1f}% or more.", n_open=1))

    story.append(P(
        f"The two methods give close results, which supports the size of the numbers. Both methods rest on a "
        f"difficult history: over the 469 trading days used, the equal weight portfolio fell at a rate of "
        f"{abs(ph['annualised_return_pct']):.1f}% a year with volatility of {ph['annualised_volatility_pct']:.1f}% "
        f"a year. The results are a measurement of risk in that period, not a prediction that the same will happen. "
        f"Section 5 lists serious data problems in this stock set, including one stock that barely traded for "
        f"most of the period. Those problems are part of the findings."))
    story.append(P("Headline results, 252 trading days, Tk 1,000,000 start", "h2"))
    data = [head_row(["Measure", "Correlated GBM", "Historical bootstrap"]),
            row(["Median ending value (Tk)", tk(g["p50_value_tk"]), tk(b["p50_value_tk"])], True),
            row(["5th percentile ending value (Tk)", tk(g["p5_value_tk"]), tk(b["p5_value_tk"])], True),
            row(["95th percentile ending value (Tk)", tk(g["p95_value_tk"]), tk(b["p95_value_tk"])], True),
            row(["Probability of a loss (%)", f"{g['prob_loss_pct']:.1f}", f"{b['prob_loss_pct']:.1f}"], True),
            row(["Probability of a loss over 10% (%)", f"{g['prob_loss_over_10pct']:.1f}", f"{b['prob_loss_over_10pct']:.1f}"], True),
            row(["Probability of a loss over 20% (%)", f"{g['prob_loss_over_20pct']:.1f}", f"{b['prob_loss_over_20pct']:.1f}"], True),
            row(["VaR 95% (Tk loss)", tk(g["var95_tk"]), tk(b["var95_tk"])], True),
            row(["CVaR 95% (Tk loss)", tk(g["cvar95_tk"]), tk(b["cvar95_tk"])], True),
            row(["VaR 99% (Tk loss)", tk(g["var99_tk"]), tk(b["var99_tk"])], True),
            row(["CVaR 99% (Tk loss)", tk(g["cvar99_tk"]), tk(b["cvar99_tk"])], True)]
    story.append(KeepTogether([cap_table("Headline results at 252 trading days, both methods"),
                               table(data, [62 * mm, 48 * mm, 48 * mm])]))
    story.extend(expl_table(
        "The rows are risk measures and the two columns are the two simulation methods, both "
        "starting from Tk 1,000,000. Read across a row to compare the methods on the same "
        "measure: the median ending value is Tk 952,265 under GBM and Tk 961,601 under the "
        "bootstrap, so the two methods put the middle outcome in almost the same place. Read "
        "down a column to see how the measures relate to each other: CVaR 95% is larger than "
        "VaR 95% in both columns (Tk 337,436 against Tk 288,883 under GBM), because CVaR "
        "averages the losses beyond the VaR point rather than marking its edge. The distance "
        "between the 5th and 95th percentile rows shows how wide the spread of outcomes is, "
        "from Tk 711,117 to Tk 1,284,195 under GBM."))

    story.append(P("1. What was done", "h1"))
    story.append(P(
        "The portfolio holds equal amounts of 11 stocks: BATBC, BXPHARMA, CITYBANK, DBH, EBL, ROBI, ACI, "
        "BEXIMCO, FUWANGCER, GEMINISEA and SEAPEARL. Each stock starts with Tk 90,909, which is one eleventh "
        "of Tk 1,000,000. The amounts are hypothetical and no real holding amounts were used."))
    story.append(P(
        "Monte Carlo simulation means running the same calculation many times with random inputs, to get a "
        "range of possible outcomes instead of a single number. Here, 10,000 possible future paths were "
        "created for the portfolio at each of three horizons: 21 trading days (about one month), 63 trading "
        "days (about three months) and 252 trading days (about one year). A fixed random seed, 42, was used, "
        "so anyone running the code gets the same results."))
    story.extend(bulleted(
        "Two methods were used. The first, correlated Geometric Brownian Motion, takes the average daily "
        "return and the daily volatility of each stock, and how the stocks moved together, and draws random "
        "daily returns with the same pattern. A Cholesky decomposition, a standard way of splitting a "
        "covariance matrix, is used so that stocks which moved together in real life also move together in "
        "the simulation. Each stock price is simulated on its own and the 11 results are then combined with "
        "equal weights. The second method, the historical bootstrap, works directly on the real record: it "
        "picks actual past daily returns of the portfolio at random, with replacement, and joins them into a "
        "new path. The bootstrap uses no assumed distribution, but it can only reuse days that already happened.", n_open=1, groups=[3, 2]))

    story.extend(bulleted(
        "Four risk measures are reported. The ending value percentiles show the spread of outcomes: the 5th "
        "percentile is a bad outcome that only 5% of simulations fell below. The probability of loss is the "
        "share of simulations that ended below Tk 1,000,000. Value at Risk (VaR) at 95% is the loss level "
        "that was exceeded in 5% of simulations over the horizon. CVaR, also called expected shortfall, is "
        "the average loss inside that worst 5%, so it is always larger than VaR and describes how bad the "
        "bad cases were on average. Maximum drawdown is the largest fall from a peak value to a later low "
        "value inside a path, and it is reported for the 252 day GBM paths.", n_open=1))

    story.append(P("2. Data", "h1"))
    story.append(P(
        f"Daily closing prices, volumes and trade counts came from the Dhaka Stock Exchange public archive "
        f"at dse.com.bd. The window used is {w['first_date']} to {w['last_date']}, {w['trading_days']} trading "
        f"days, the same for all 11 stocks, with no missing days and no filled values. Prices are the "
        f"published closing prices and are not adjusted for dividends. Section 5 explains why the earlier "
        f"history that was requested, from January 2021, could not be used, with counts from the data that "
        f"was checked and rejected."))
    data = [head_row(["Stock", "First close (Tk)", "Last close (Tk)", "Change (%)",
                      "Return (% a year)", "Volatility (% a year)", "Worst day (%)", "Sharpe, risk free 0%"])]
    for _, r in stats.iterrows():
        data.append(row([r.ticker, f"{r.start_close_tk:,.1f}", f"{r.end_close_tk:,.1f}",
                         f"{r.total_return_pct:.1f}", f"{r.annualised_return_pct:.1f}",
                         f"{r.annualised_volatility_pct:.1f}", f"{r.worst_day_pct:.1f}",
                         f"{r.sharpe_rf_0pct:.2f}"]))
    story.append(KeepTogether([cap_table("Price record and risk of each stock over the data window"),
                               table(data, [22 * mm, 21 * mm, 21 * mm, 16 * mm, 22 * mm, 25 * mm, 17 * mm, 24 * mm])]))
    story.extend(expl_table(
        "Each row is one stock, and the columns run from its first and last closing price in "
        "the window to its total change, its return and volatility per year, its worst single "
        "day, and its Sharpe ratio at a 0% risk free rate. The range is wide: BXPHARMA gained "
        "96.5% in total while BEXIMCO lost 81.1%, and volatility runs from 22.4% a year for "
        "ROBI to 44.2% a year for SEAPEARL. The worst day column needs care, because the "
        "largest falls shown for CITYBANK (-16.7%), EBL (-20.7%) and ACI (-14.1%) match "
        "dividend reset days on unadjusted prices, as Section 5 explains. BEXIMCO stands out "
        "in a different way: its -81.1% total fall came after a long stretch in which its "
        "price barely moved at all, so the path matters as much as the totals in this table."))
    story.append(P(
        f"The range across stocks is wide. BXPHARMA rose 96.5% over the window while BEXIMCO fell 81.1% and "
        f"BATBC fell 40.2%. Measured volatility runs from 22.4% a year for ROBI to 44.2% a year for SEAPEARL. "
        f"The average correlation between pairs of stocks in this window was {avg_corr:.2f}, which is low, so "
        f"the stocks often did not move together. Low correlation reduces portfolio volatility compared with "
        f"the single stock volatilities: the equal weight portfolio volatility was "
        f"{ph['annualised_volatility_pct']:.1f}% a year. Low measured correlation in this set should be read "
        f"with care, because several stocks had many days with no price change, and a stock that does not move "
        f"looks unrelated to everything else.", "body"))
    story.append(KeepTogether([cap_figure("Price history of the 11 stocks, each set to 100 on the first day"),
                               Image(os.path.join(CHARTS, "price_history_normalised.png"), width=165 * mm, height=105 * mm)]))
    story.extend(expl_figure(
        "Each coloured line is one stock, with every price divided by its own price on the "
        "first day so that all lines start at 100 on the left; the legend at the bottom "
        "matches colours to stocks, and the dashed line marks 100, the starting level. A line "
        "ending near 197 means the price almost doubled, which is where BXPHARMA (orange) "
        "ends after its 96.5% rise, while BEXIMCO (grey) is the flat line near 95 that drops "
        "off a cliff in mid 2026 and ends near 19 after its 81.1% fall. Most other lines end "
        "between about 60 and 150, so the stocks did not move as one group over the window. "
        "The flat stretches are a warning, not a sign of calm: they are periods with little "
        "or no trading, and the prices are unadjusted for dividends."))
    story.append(KeepTogether([cap_figure("Correlation of daily log returns between each pair of stocks"),
                               Image(os.path.join(CHARTS, "correlation_heatmap.png"), width=140 * mm, height=115 * mm)]))
    story.extend(expl_figure(
        "The rows and columns are the same 11 stocks in the same order, and each square is "
        "the correlation between the daily log returns of the row stock and the column "
        "stock, also printed as a number inside the square. The colour scale on the right "
        "runs from -1 to 1, and the deep red diagonal is each stock against itself, which is "
        "always 1.00. Off the diagonal the squares are pale orange and yellow, and no pair is "
        "higher than 0.44 (DBH with ROBI), so no two stocks in this set moved closely "
        "together, which is part of why the portfolio volatility is lower than the single "
        "stock volatilities in Table 2. BEXIMCO is the palest row and column of all, with "
        "values from 0.00 to 0.07, because its price barely changed on most days; that makes "
        "it look unrelated to the rest rather than genuinely independent."))
    story.append(PageBreak())

    story.append(P("3. Results", "h1"))
    for method, label in (("gbm", "Correlated GBM"), ("bootstrap", "Historical bootstrap")):
        story.append(P(f"{label}, results by horizon", "h2"))
        data = [head_row(["Horizon", "Median (Tk)", "P5 (Tk)", "P95 (Tk)", "Prob. loss (%)",
                          "VaR 95% (Tk)", "CVaR 95% (Tk)", "VaR 99% (Tk)", "CVaR 99% (Tk)"])]
        for h in ("21", "63", "252"):
            d = res[method][h]
            data.append(row([f"{h} days", tk(d["p50_value_tk"]), tk(d["p5_value_tk"]), tk(d["p95_value_tk"]),
                             f"{d['prob_loss_pct']:.1f}", tk(d["var95_tk"]), tk(d["cvar95_tk"]),
                             tk(d["var99_tk"]), tk(d["cvar99_tk"])]))
        story.append(KeepTogether([cap_table(f"Simulation results by horizon, {label}"),
                                   table(data, [16 * mm, 20 * mm, 18 * mm, 20 * mm, 18 * mm, 20 * mm, 21 * mm, 20 * mm, 21 * mm])]))
        if method == "gbm":
            story.extend(expl_table(
                "The rows are the three horizons and the columns give the median, 5th and 95th "
                "percentile ending values, the probability of a loss, and the VaR and CVaR "
                "losses at 95% and 99%, all in taka except the probability. Every risk figure "
                "grows with the horizon: VaR 95% rises from Tk 85,068 at 21 days to "
                "Tk 151,034 at 63 days and Tk 288,883 at 252 days. The median ending value "
                "falls as the horizon lengthens, from Tk 993,272 at 21 days to Tk 952,265 at "
                "252 days, because the average return in the measured window was negative. "
                "CVaR is larger than VaR at every horizon, so the average bad outcome is "
                "worse than the VaR line alone suggests."))
        else:
            story.extend(expl_table(
                "The layout is the same as Table 3, so the two tables can be compared row by "
                "row: the rows are the three horizons and the columns give the median, 5th "
                "and 95th percentile ending values, the probability of a loss, and the VaR "
                "and CVaR losses at 95% and 99%. The pattern matches the GBM table, with "
                "VaR 95% rising from Tk 82,230 at 21 days to Tk 270,206 at 252 days and the "
                "median ending value falling from Tk 997,957 to Tk 961,601. At 252 days the "
                "bootstrap tail losses are smaller than the GBM ones (VaR 95% Tk 270,206 "
                "against Tk 288,883), because this method can only reuse days that actually "
                "happened, while GBM can combine shocks into paths worse than any in the "
                "record. The bootstrap probability of a loss at 252 days, 58.8%, is also "
                "lower than the GBM figure of 60.3% for the same reason."))
    story.append(P(
        f"Risk grows with the horizon, as expected. At 21 days the GBM VaR 95% is Tk "
        f"{tk(res['gbm']['21']['var95_tk'])}, which is {res['gbm']['21']['var95_pct']:.1f}% of the starting "
        f"value. At 252 days it is Tk {tk(g['var95_tk'])}, or {g['var95_pct']:.1f}%. The chance of some loss "
        f"also rises with time in these results, from {res['gbm']['21']['prob_loss_pct']:.1f}% at 21 days to "
        f"{g['prob_loss_pct']:.1f}% at 252 days under GBM, because the average return in the measured window "
        f"was negative. The bootstrap gives slightly smaller tail losses than GBM at 252 days: VaR 95% of Tk "
        f"{tk(b['var95_tk'])} against Tk {tk(g['var95_tk'])}. The bootstrap is limited by the worst days in "
        f"the sample, while GBM can draw combinations worse than any single historical stretch."))
    story.append(KeepTogether([cap_figure("Spread of simulated portfolio values over 252 trading days, correlated GBM"),
                               Image(os.path.join(CHARTS, "fan_chart_gbm_252.png"), width=165 * mm, height=92 * mm)]))
    story.extend(expl_figure(
        "The horizontal axis is trading days ahead, from 0 to 252, and the vertical axis is "
        "the portfolio value in taka. The blue bands are percentile ranges across the 10,000 "
        "GBM paths at each day, as the legend shows: the darkest band is the middle half of "
        "paths (25th to 75th percentile), the mid blue band reaches from the 5th to the 95th "
        "percentile, and the palest band reaches from the 1st to the 99th percentile. The "
        "dark line is the median path and the dashed line is the Tk 1,000,000 starting value. "
        "The bands widen steadily, so the spread of possible outcomes grows with time, and "
        "the median line drifts down to Tk 952,265 at day 252, below the starting value, "
        "where the 5th to 95th percentile range runs from Tk 711,117 to Tk 1,284,195."))
    story.append(KeepTogether([cap_figure("Value at Risk by horizon and method"),
                               Image(os.path.join(CHARTS, "var_comparison.png"), width=165 * mm, height=92 * mm)]))
    story.extend(expl_figure(
        "Each group of four bars is one horizon, and the bar heights are losses as a "
        "percentage of the Tk 1,000,000 starting value. Blue bars are GBM and green bars are "
        "the bootstrap, with the lighter shade of each colour for VaR 95% and the darker "
        "shade for VaR 99%, as the legend shows. Two patterns hold at every horizon: the 99% "
        "bars are taller than the 95% bars, and the GBM bars are slightly taller than the "
        "bootstrap bars, for example 28.9% against 27.0% for VaR 95% at 252 days. The "
        "tallest bar in the figure is GBM VaR 99% at 252 days, 37.2% of the starting value, "
        "which is the Tk 372,312 figure in Table 3."))
    story.append(KeepTogether([cap_figure("Distribution of ending values after 252 days, correlated GBM"),
                               Image(os.path.join(CHARTS, "histogram_gbm_252.png"), width=165 * mm, height=92 * mm)]))
    story.extend(expl_figure(
        "The horizontal axis is the ending portfolio value after 252 days, in thousands of "
        "taka, and the height of each blue bar is how many of the 10,000 GBM simulations "
        "ended in that range. The dashed black line marks the Tk 1,000,000 starting value "
        "(1,000 on the axis) and the red line marks the 5th percentile ending value, "
        "Tk 711,117, which is the point behind the VaR 95% figure in Table 3. The bulk of "
        "the bars sit to the left of the dashed line and the tallest bars are around "
        "Tk 900,000, so a typical outcome was a loss, in line with the 60.3% probability of "
        "loss in Table 1. The right hand tail is long and thin, so large gains were "
        "possible but rare: only 5% of simulations ended above Tk 1,284,195."))
    story.append(P(
        f"Maximum drawdown inside the 252 day GBM paths: the median path had a largest fall of "
        f"{dd['median_max_drawdown_pct']:.1f}%, the 95th percentile was {dd['p95_max_drawdown_pct']:.1f}% and "
        f"the 99th percentile was {dd['p99_max_drawdown_pct']:.1f}%. Drawdown matters separately from the "
        f"ending value: a holder sees the fall while it is happening, even if the value later recovers."))

    story.append(P("4. What the results mean", "h1"))
    story.append(P(
        "First, on the evidence of the last 469 trading days, this equal weight set carried high risk for a "
        "negative average return. A one year loss was more likely than a gain in both methods, and a loss of "
        "more than 20% had a probability of "
        f"{g['prob_loss_over_20pct']:.1f}% under GBM and {b['prob_loss_over_20pct']:.1f}% under the bootstrap."))
    story.append(P(
        "Second, the tail is heavy. CVaR 95% is about one sixth larger than VaR 95% in the GBM results "
        f"(Tk {tk(g['cvar95_tk'])} against Tk {tk(g['var95_tk'])}), so when the bad 5% of outcomes happened, "
        "the average loss was well beyond the VaR line. Planning on VaR alone would understate the bad cases."))
    story.append(P(
        "Third, the stock set, not the method, is the main problem. One stock was effectively frozen for a "
        "year and then fell sharply, one is a Z category stock with very low trading volume, and three "
        "stocks show single day falls beyond the normal daily limit that match dividend reset days on "
        "unadjusted prices. A risk number is only as good as the price history behind it, and Section 5 "
        "quantifies each of these points."))
    story.append(P(
        "Nothing in this report is a recommendation to buy or sell any stock. The portfolio is hypothetical, "
        "the starting amount is hypothetical, and the simulation measures the risk of a past pattern, it does "
        "not forecast prices."))

    story.append(P("5. Limitations and data problems", "h1"))
    story.append(P("The problems below were found in the actual data used, or in the data that had to be "
                   "rejected, and are stated with counts. They limit how far the results can be trusted."))
    for head_text, text in build_limitations():
        story.append(P(head_text, "h2"))
        if len(split_sentences(text)) >= 5:
            story.extend(bulleted(text, n_open=1))
        else:
            story.append(P(text))

    story.append(P("6. Sources and how to reproduce", "h1"))
    story.append(P(
        "Prices: Dhaka Stock Exchange public data archive, dse.com.bd, day end archive, downloaded for each "
        "of the 11 tickers for 3 November 2024 to 15 October 2026, 469 rows per ticker, saved as CSV files in "
        "the project data folder. Stock categories for BEXIMCO, FUWANGCER and GEMINISEA: portfolio statement, "
        "15 October 2026, used for the ticker list and categories only. Rejected source: Mendeley Data, "
        "Dhaka Stock Exchange Historical Data 1999 to 2025, DOI 10.17632/5mww8rb9td.1, quality counts saved "
        "in the project data folder. Software: Python with pandas, numpy and matplotlib. The fetch, "
        "simulation, chart, workbook and report scripts are in the project scripts folder and run in that "
        "order. All results in this report are read from data/results.json, which the simulation script "
        "writes, so every number can be traced to a saved output."))

    doc = SimpleDocTemplate(OUT, pagesize=A4, leftMargin=16 * mm, rightMargin=16 * mm,
                            topMargin=15 * mm, bottomMargin=15 * mm,
                            title="Monte Carlo Portfolio Risk Simulation: Dhaka Stock Exchange",
                            author="Munzeleen Sarwar")
    doc.build(story)
    print("saved", OUT)


if __name__ == "__main__":
    main()
