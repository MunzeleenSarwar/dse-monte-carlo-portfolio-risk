"""Build DSE_Extended_Portfolio_Analysis_Report.pdf from data/extended_results.json.
Report text, headings and tables are black only. Charts may use colour.
Plain language, no em dashes, no first person, author name at top only.
"""
import json
import os
import re

import pandas as pd
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.platypus import (Image, KeepTogether, ListFlowable, ListItem,
                                PageBreak, Paragraph, SimpleDocTemplate, Spacer,
                                Table, TableStyle)
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib import colors

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(BASE, "data")
CH = os.path.join(BASE, "charts")
R = json.load(open(os.path.join(DATA, "extended_results.json")))

from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

_FD = "/usr/share/fonts/truetype/liberation"
_ND = "/usr/share/fonts/truetype/noto"
# Times New Roman is a Microsoft font and is not installed on this
# machine. Liberation Serif is its metric compatible twin (same letter
# widths) and is registered here under the Times name, so body text,
# headings, captions and explanations are set in Times.
pdfmetrics.registerFont(TTFont("Times", f"{_FD}/LiberationSerif-Regular.ttf"))
pdfmetrics.registerFont(TTFont("Times-Bold", f"{_FD}/LiberationSerif-Bold.ttf"))
pdfmetrics.registerFont(TTFont("Times-Italic", f"{_FD}/LiberationSerif-Italic.ttf"))
pdfmetrics.registerFont(TTFont("Times-BoldItalic", f"{_FD}/LiberationSerif-BoldItalic.ttf"))
pdfmetrics.registerFontFamily("Times", normal="Times", bold="Times-Bold",
                              italic="Times-Italic", boldItalic="Times-BoldItalic")
# Tables keep a sans font, Noto Sans.
pdfmetrics.registerFont(TTFont("Sans", f"{_ND}/NotoSans-Regular.ttf"))
pdfmetrics.registerFont(TTFont("Sans-Bold", f"{_ND}/NotoSans-Bold.ttf"))
pdfmetrics.registerFont(TTFont("Sans-Italic", f"{_ND}/NotoSans-Italic.ttf"))
pdfmetrics.registerFont(TTFont("Sans-BoldItalic", f"{_ND}/NotoSans-BoldItalic.ttf"))
pdfmetrics.registerFontFamily("Sans", normal="Sans", bold="Sans-Bold",
                              italic="Sans-Italic", boldItalic="Sans-BoldItalic")

H1 = ParagraphStyle("H1", fontName="Times-Bold", fontSize=17, leading=21,
                    textColor=colors.black, spaceAfter=4, keepWithNext=1)
H2 = ParagraphStyle("H2", fontName="Times-Bold", fontSize=12.5, leading=15,
                    textColor=colors.black, spaceBefore=10, spaceAfter=4,
                    keepWithNext=1)
BODY = ParagraphStyle("Body", fontName="Times", fontSize=9.8, leading=13.4,
                      textColor=colors.black, spaceAfter=5, alignment=4)
SMALL = ParagraphStyle("Small", fontName="Times", fontSize=8.6, leading=11,
                       textColor=colors.black)
SUB = ParagraphStyle("Sub", fontName="Times-Bold", fontSize=9.8, leading=12,
                     textColor=colors.black, spaceBefore=6, spaceAfter=3,
                     keepWithNext=1)
CAPTION = ParagraphStyle("Caption", fontName="Times-Bold", fontSize=9.8,
                         leading=12.5, textColor=colors.black, spaceBefore=7,
                         spaceAfter=3, keepWithNext=1)
EXPL = ParagraphStyle("Expl", fontName="Times", fontSize=9.8, leading=13.4,
                      textColor=colors.black, spaceBefore=3, spaceAfter=7,
                      alignment=4)
EXPL_OPEN = ParagraphStyle("ExplOpen", fontName="Times", fontSize=9.8,
                           leading=13.4, textColor=colors.black,
                           spaceBefore=3, spaceAfter=2, alignment=4)
BULLET = ParagraphStyle("Bullet", fontName="Times", fontSize=9.8,
                        leading=13.4, textColor=colors.black, spaceAfter=2,
                        alignment=4)
CELL = ParagraphStyle("Cell", fontName="Sans", fontSize=8.4, leading=10.4,
                      textColor=colors.black)
CELLB = ParagraphStyle("CellB", fontName="Sans-Bold", fontSize=8.4,
                       leading=10.4, textColor=colors.black)


def tbl(data, widths=None, header=True):
    # Every cell is a Paragraph so long text wraps inside its column
    # instead of running past the right margin. Plain strings in a
    # ReportLab Table do not wrap.
    wrapped = []
    for ri, row_ in enumerate(data):
        wr = []
        for c in row_:
            if isinstance(c, Paragraph):
                wr.append(c)
            elif header and ri == 0:
                wr.append(Paragraph(str(c), CELLB))
            else:
                wr.append(Paragraph(str(c), CELL))
        wrapped.append(wr)
    t = Table(wrapped, colWidths=widths, repeatRows=1 if header else 0,
              hAlign="LEFT")
    style = [("TEXTCOLOR", (0, 0), (-1, -1), colors.black),
             ("GRID", (0, 0), (-1, -1), 0.4, colors.black),
             ("VALIGN", (0, 0), (-1, -1), "TOP"),
             ("TOPPADDING", (0, 0), (-1, -1), 2.5),
             ("BOTTOMPADDING", (0, 0), (-1, -1), 2.5)]
    t.setStyle(TableStyle(style))
    return t


def short_note(note):
    """Shorten a fundamental quality note so it fits its table column."""
    note = str(note)
    if note.startswith("Profitable"):
        for k in ("above", "near", "below"):
            if f"PE {k} the group median" in note:
                return f"Profitable; pays dividend; PE {k} median"
        return "Profitable; pays dividend"
    if "no annual cash dividend" in note:
        return "Loss making; no dividend shown"
    return "Loss making; pays dividend"


def img(name, w=16.2):
    path = os.path.join(CH, name)
    from PIL import Image as PILImage
    iw, ih = PILImage.open(path).size
    return Image(path, width=w * cm, height=w * cm * ih / iw)


_counts = {"table": 0, "figure": 0}


def cap_table(title):
    _counts["table"] += 1
    return Paragraph(f"Table {_counts['table']}: {title}", CAPTION)


def cap_figure(title):
    _counts["figure"] += 1
    return Paragraph(f"Figure {_counts['figure']}: {title}", CAPTION)


def split_sentences(text):
    return [s for s in re.split(r"(?<=[.!?])\s+(?=[A-Z(])", str(text).strip()) if s]


def bullet_list(items):
    lf = ListFlowable([ListItem(Paragraph(it, BULLET), leftIndent=16) for it in items],
                      bulletType="bullet", leftIndent=16,
                      bulletFontName="Times", bulletFontSize=8)
    lf.spaceAfter = 6
    return lf


def expl_block(text):
    sents = split_sentences(text)
    if len(sents) <= 1:
        return [Paragraph(text, EXPL)]
    return [Paragraph(sents[0], EXPL_OPEN), bullet_list(sents[1:])]


def expl_table(text):
    return expl_block(text)


def expl_figure(text):
    return expl_block(text)


def bulleted(text, style=None, n_open=1, n_close=0, groups=None):
    style = BODY if style is None else style
    sents = split_sentences(text)
    out = []
    end = len(sents) - n_close if n_close else len(sents)
    body_sents = sents[n_open:end]
    if n_open:
        out.append(Paragraph(" ".join(sents[:n_open]), style))
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
        out.append(Paragraph(" ".join(sents[end:]), style))
    return out


def main():
    dd = R["drawdown_downside"]
    div = R["diversification"]
    rd = R["risk_decomposition"]
    dist = R["distribution"]
    liq = pd.read_csv(os.path.join(DATA, "extended_liquidity.csv"))
    stress = pd.read_csv(os.path.join(DATA, "extended_stress_tests.csv"))
    risk = pd.read_csv(os.path.join(DATA, "extended_risk_decomposition.csv"))
    comp = pd.read_csv(os.path.join(DATA, "extended_component_var.csv"))
    fund = pd.read_csv(os.path.join(DATA, "extended_fundamentals.csv"))
    beta = R["beta_vs_dsex"]
    ew, ga = R["ewma"], R["garch"]
    tt = R["student_t"]
    roll = R["rolling_risk"]
    grades = {}
    for g in R["liquidity"]["grades"]:
        grades[g["liquidity_grade"]] = grades.get(g["liquidity_grade"], 0) + 1

    S = []
    S.append(Paragraph("Portfolio Risk Analysis: Dhaka Stock Exchange, Extended Analysis", H1))
    S.append(Paragraph("Munzeleen Sarwar", BODY))
    S.append(Paragraph("Introduction", H2))
    S.append(Paragraph("This report is the extended analysis of a Monte Carlo portfolio risk simulation of 11 stocks listed on the Dhaka Stock Exchange. The portfolio is hypothetical: Tk 1,000,000 split equally across BATBC, BXPHARMA, CITYBANK, DBH, EBL, ROBI, ACI, BEXIMCO, FUWANGCER, GEMINISEA and SEAPEARL, which is Tk 90,909 in each stock, and no real holding amounts were used at any point. The main simulation drew 10,000 possible future paths for this portfolio at horizons of 21, 63 and 252 trading days, using two methods. The first, correlated Geometric Brownian Motion, draws random daily returns with the same averages, volatilities and joint movements as the measured history. The second, a historical bootstrap, builds new paths out of actual past daily returns of the portfolio picked at random. Both methods used the same daily closing prices, from 3 November 2024 to 15 October 2026, a window of 469 trading days.", BODY))
    S.append(Paragraph("Over 252 trading days, about one trading year, the main simulation found a median ending value of Tk 952,265 under the GBM method and Tk 961,601 under the bootstrap. The probability of ending the year with a loss was 60.3% under GBM and 58.8% under the bootstrap. Value at Risk at 95% was Tk 288,883 under GBM and Tk 270,206 under the bootstrap, and the average loss in the worst 5% of GBM outcomes, CVaR at 95%, was Tk 337,436. Inside the GBM one year paths, the median largest fall from a peak was 19.12%, and in 5% of paths the largest fall was 34.26% or more. The two methods agreed closely, so the size of the risk is not much in doubt. What those numbers mean for the quality of the portfolio is a separate question, and it is the question this report takes up.", BODY))
    S.extend(bulleted("A single set of simulation results cannot say how good or bad a portfolio is, for five reasons. First, a total risk number does not show where the risk comes from: a portfolio in which every stock carries a similar share of risk is a different holding from one in which three stocks carry most of it, even if the two totals match. Second, it does not show whether diversification worked, that is, whether holding the 11 stocks together reduced risk compared with the risk of the stocks taken one at a time. Third, it says nothing about how the portfolio behaved on days that have already happened: how far it fell from its highest point, how long the fall lasted, and what its worst single days looked like. Fourth, a simulation result is a statement about prices, not about the ability to trade: a holding that cannot be sold at its recorded price carries a risk that no price based measure records. Fifth, prices say nothing about the companies themselves, whether they earn money, pay dividends, or are priced high or low against their earnings. Each of these gaps can change the verdict, and in this portfolio several of them do.", BODY, n_open=1, n_close=1))
    S.extend(bulleted("The sections that follow take these gaps in order. Section 1 asks which stocks create the risk, and answers the question twice, once for everyday volatility and once for the worst 5% of simulated outcomes. Section 2 asks whether diversification worked. Section 3 asks how the portfolio actually fell inside the window, using drawdown and downside measures and its ten worst days. Section 4 asks whether daily returns follow the normal distribution that the GBM method assumes. Section 5 asks how fast each position could be sold. Section 6 asks how risk moved over time, using rolling volatility, an EWMA model and a GARCH model, and it records the attempt to measure the portfolio against the DSEX index. Section 7 asks what named shocks would cost, in taka, if they happened to the equal weights. Section 8 asks whether the risk answer changes when the simulation is given fatter tails than the normal distribution allows. Section 9 asks what the companies earn and pay, from their latest reported figures. Section 10 draws the answers together into a verdict on return, risk, diversification, liquidity and data quality, and Section 11 lists the limits that apply to the whole report.", BODY, n_open=1))
    S.append(Paragraph("Every price based measure in this report is worked out from the same data as the main simulation: daily closing prices, volumes and trade counts for the 11 stocks from the Dhaka Stock Exchange, for the window stated above, with no missing days and no filled values. Where simulation is used, in Sections 1 and 8, it uses 10,000 paths and the fixed random seed 42, so the results can be reproduced exactly. The GBM paths behind the tail loss shares in Section 1 are the main simulation paths themselves, regenerated with the same code and seed, and their median ending value matches the main simulation to the taka. The company figures in Section 9 come from a different source and a single date, stockanalysis.com, fetched on 31 October 2026, with earnings per share on a trailing twelve month basis. Fiscal years end in June for five of the companies and in December for six, so those figures are not for identical periods, and comparisons between companies in that section are not exact.", BODY))
    S.append(Paragraph("The overall verdict, set out with its evidence in Section 10, is as follows:", BODY))
    S.append(bullet_list([
        "The portfolio lost money in this window.",
        "Its risk is high and concentrated in three small stocks, SEAPEARL, FUWANGCER and GEMINISEA, which together hold 39.89% of the total risk on 27.27% of the money and are all loss making on current earnings.",
        "Diversification did work on volatility (the diversification ratio is 1.83).",
        "Liquidity is poor because one stock, BEXIMCO, would take 1,376 days to sell at 20% of its median daily traded value.",
        "The data are weak: 469 trading days, prices not adjusted for dividends, one stock whose price was fixed for a full calendar year, and no DSEX index series, so the portfolio cannot be compared with the market and no beta can be calculated.",
    ]))
    S.append(Paragraph("The window is also too short to settle the long term return, because the standard error of the annual mean return over 1.86 years is about 12.7 percentage points. Nothing in this report is a recommendation to buy or sell any stock.", BODY))

    S.append(Paragraph("1. Risk decomposition: where the risk comes from", H2))
    S.append(Paragraph(
        f"Portfolio volatility is {rd['portfolio_volatility_pct']}% a year. "
        "The table shows each stock's share of that volatility. Shares are "
        "worked out from the covariance matrix of daily log returns: a "
        "stock's share is high when its own volatility is high and when it "
        "tends to move with the rest of the portfolio. The effective number "
        f"of risk bets is {rd['effective_number_of_risk_bets']} out of 11, "
        "which means risk is spread almost as if the 11 positions were "
        "separate bets of equal risk, but not fully.", BODY))
    rows = [["Stock", "Capital weight (%)", "Volatility (% a year)", "Share of portfolio risk (%)"]]
    for _, r in risk.iterrows():
        rows.append([r["ticker"], f"{r['capital_weight_pct']:.2f}",
                     f"{r['annualised_volatility_pct']:.2f}",
                     f"{r['pct_of_portfolio_risk']:.2f}"])
    S.append(KeepTogether([cap_table("Share of portfolio volatility by stock"),
                           tbl(rows, widths=[2.6 * cm, 3.4 * cm, 4.2 * cm, 5.0 * cm])]))
    S.extend(expl_table(
        "Each row is one stock. The capital weight column is 9.09% for every stock "
        "because the money is split equally, the volatility column is that "
        "stock's own volatility per year, and the last column is its share of "
        "the portfolio's total volatility, so the last column adds to 100%. "
        "Three stocks sit well above their money share: SEAPEARL at 13.74%, "
        "FUWANGCER at 13.16% and GEMINISEA at 12.99%, together 39.89% of the "
        "risk on 27.27% of the money. BEXIMCO, at 4.36%, looks like the safest "
        "stock in the table, and that reading is wrong: its price did not "
        "change on 81.6% of days, so the calculation sees long runs of zeros "
        "rather than traded risk, which Table 2 makes clear."))
    S.append(Spacer(1, 4))
    S.append(KeepTogether([cap_figure("Share of portfolio risk by stock"),
                           img("extended_risk_contribution.png", w=14.8)]))
    S.extend(expl_figure(
        "The blue bars repeat the last column of Table 1 as a picture, with the "
        "longest bar at the top. The horizontal axis is the share of portfolio "
        "risk in percent, and the red dashed line marks 9.09%, the share each "
        "stock would hold if risk were spread in line with the money. Four bars "
        "cross that line: SEAPEARL, FUWANGCER, GEMINISEA and BXPHARMA at "
        "10.29%, while the other seven fall short of it. BEXIMCO has by far the "
        "shortest bar, at 4.36%, for the reason given under Table 1: a price "
        "that barely moved cannot show its risk in a volatility calculation."))
    S.append(Paragraph(
        "SEAPEARL (13.74%), FUWANGCER (13.16%) and GEMINISEA (12.99%) "
        "together hold 39.89% of the total risk on 27.27% of the money. "
        "BEXIMCO holds the smallest share, 4.36%. That BEXIMCO figure is "
        "understated and should not be read as safety: the stock had 149 "
        "zero volume days and no price change on 81.6% of days, so most of "
        "its recorded daily returns are zero by record, not by trading. "
        "The next table shows why this matters. It uses the GBM "
        "simulations, reproduced exactly with the same code and seed "
        "(median ending value Tk 952,265, matching the main simulation to the taka). "
        "For the worst 5% of simulated outcomes at 252 days, each stock's "
        "average shortfall against its starting Tk 90,909 is its component "
        "VaR. On that measure BEXIMCO is the largest single part of the "
        "tail loss, at 17.06%, because inside the simulation its own high "
        "volatility acts every day, while in the historical covariance its "
        "long zero return stretches hold its measured share down.", BODY))
    rows = [["Stock", "Component VaR 95% (Tk)", "Share of tail loss (%)"]]
    for _, r in comp.iterrows():
        rows.append([r["ticker"], f"{r['component_var95_tk']:,.0f}",
                     f"{r['pct_of_cvar_tail_loss']:.2f}"])
    S.append(KeepTogether([cap_table("Each stock's share of the tail loss, worst 5% of GBM outcomes at 252 days"),
                           tbl(rows, widths=[3.0 * cm, 4.6 * cm, 4.6 * cm])]))
    S.extend(expl_table(
        "The rows are the 11 stocks, the middle column is each stock's average "
        "loss in taka inside the worst 5% of GBM outcomes at 252 days, measured "
        "against its starting Tk 90,909, and the last column is that loss as a "
        "share of the whole tail loss, so it adds to 100%. The order is almost "
        "the reverse of Table 1: BEXIMCO, the smallest contributor to everyday "
        "volatility, is the largest here at Tk 57,579, or 17.06% of the tail "
        "loss, followed by GEMINISEA at Tk 49,858 (14.78%). The two tables are "
        "not in conflict: volatility is an average over all days, while this "
        "table looks only at the bad outcomes, where a stock with high "
        "volatility and a frozen trading record does its damage. Together they "
        "say that BEXIMCO's risk is hidden on normal days and concentrated in "
        "bad ones."))

    S.append(PageBreak())
    S.append(Paragraph("2. Diversification", H2))
    S.extend(bulleted(
        f"The weighted average volatility of the 11 stocks on their own is "
        f"{div['weighted_avg_individual_volatility_pct']}% a year. The "
        f"portfolio volatility is {div['portfolio_volatility_pct']}%. The "
        f"diversification ratio is {div['diversification_ratio']}: the "
        "portfolio carries a little over half the risk of the average stock "
        f"it holds. The average correlation between pairs of stocks is "
        f"{div['average_pairwise_correlation']}, which is low, and that is "
        "why the reduction is large. The rolling 63 day average correlation "
        f"moved between {div['rolling_63d_avg_corr_min']} and "
        f"{div['rolling_63d_avg_corr_max']} inside the window and ended at "
        f"{div['rolling_63d_avg_corr_latest']}, so the diversification "
        "benefit was weaker at some times than the full window figure "
        "suggests, but it never disappeared.", BODY, n_open=1))
    S.append(Paragraph("3. Drawdown and downside", H2))
    S.extend(bulleted(
        "This section uses one stated path definition: a daily rebalanced "
        "equal weight portfolio of simple daily returns. On that path the "
        f"portfolio returned {dd['total_return_pct']}% in total over the "
        f"window and ended at Tk {dd['ending_value_tk']:,.0f}. The compound "
        f"annual growth rate was {dd['cagr_pct']}%. The maximum drawdown, "
        "the largest fall from a peak to a later low, was "
        f"{dd['max_drawdown_pct']}%: the peak was on {dd['peak_date']} and "
        f"the low was on {dd['trough_date']}, "
        f"{dd['drawdown_duration_trading_days']} trading days later, and "
        "the portfolio had not recovered to the peak value by the end of "
        "the window. The Calmar ratio (compound annual growth rate divided "
        f"by the size of the maximum drawdown) was {dd['calmar_ratio_cagr_over_maxdd']}. "
        f"The downside deviation, which counts only falling days, was "
        f"{dd['downside_deviation_pct']}% a year, and the Sortino ratio "
        f"(return divided by downside deviation, risk free rate 0%) was "
        f"{dd['sortino_ratio_rf0']}. Both ratios are negative because the "
        f"return was negative. Only {dd['pct_positive_days']}% of days were "
        f"positive. The daily VaR 95% was {dd['daily_var95_pct']}% and the "
        f"daily CVaR 95% was {dd['daily_cvar95_pct']}%; at 99% the figures "
        f"were {dd['daily_var99_pct']}% and {dd['daily_cvar99_pct']}%.", BODY, n_open=1))
    S.append(KeepTogether([cap_figure("Portfolio value and drawdown, daily rebalanced equal weight path"),
                           img("extended_drawdown.png", w=14.6)]))
    S.extend(expl_figure(
        "The top panel is the value of the daily rebalanced equal weight "
        "portfolio in taka lakh (units of Tk 100,000) across the window, "
        "starting at 10 lakh, and the bottom panel is the drawdown at each "
        "date, meaning the percentage fall from the highest value reached up "
        "to that date, shaded in red. The value peaked a little above 12 lakh "
        "in September 2025 and ended the window at about 9.3 lakh, which is "
        "the Tk 934,070 ending value given in the text. The red shading "
        "deepens in three long stretches rather than in one short crash, and "
        "it reaches its deepest point, -23.94%, at the end of the window. A "
        "holder would therefore have spent most of the second half of the "
        "window below the peak value, not just a few bad days."))
    rows = [["Date", "Portfolio return (%)", "Stocks that fell most that day"]]
    for r in dd["worst_10_days"]:
        rows.append([r["date"], f"{r['portfolio_return_pct']:.2f}", r["worst_stocks"]])
    S.append(KeepTogether([cap_table("Worst 10 portfolio days in the window"),
                           tbl(rows, widths=[2.6 * cm, 3.4 * cm, 10.5 * cm])]))
    S.extend(expl_table(
        "Each row is one of the ten worst days for the portfolio as a whole, "
        "worst first: the date, the portfolio's return that day, and the three "
        "stocks that fell most that day with their own returns. The worst day, "
        "8 March 2026 at -5.51%, was a broad fall led by SEAPEARL (-8.20%), "
        "CITYBANK (-7.31%) and DBH (-7.18%), not a single stock event. One row "
        "is different in kind: 24 April 2025, at -3.85%, was driven by EBL "
        "falling 20.74%, a fall beyond the normal daily limit that matches a "
        "dividend reset day on unadjusted prices. Most other rows also show "
        "several stocks falling together, which is why the portfolio's worst "
        "days are as large as they are even though the average correlation "
        "between the stocks is low, at 0.236."))

    S.append(PageBreak())
    S.append(Paragraph("4. Distribution of returns: fat tails", H2))
    p = dist["portfolio"]
    S.append(Paragraph(
        f"For the portfolio daily log returns, skewness is {p['skewness']} "
        f"and excess kurtosis is {p['excess_kurtosis']}. A normal "
        "distribution has values of zero for both. The Jarque-Bera test "
        f"statistic is {p['jarque_bera']} with a p-value below 0.001, so "
        "the normal distribution is rejected as a description of these "
        "returns. Normality is also rejected for 10 of the 11 stocks; the "
        "exception is BEXIMCO, whose recorded returns are mostly zeros. "
        "The tail comparison makes the same point in plain numbers. The "
        f"worst 1% of portfolio days start at "
        f"{dist['tail_simple_returns']['empirical_p1_pct']}% on simple "
        f"returns, while a normal distribution at the same volatility "
        f"predicts {dist['tail_simple_returns']['normal_p1_pct']}%. The "
        "left tail is fatter than normal. The right tail at 99% is close "
        "to the normal prediction in this window ("
        f"{dist['tail_simple_returns']['empirical_p99_pct']}% against "
        f"{dist['tail_simple_returns']['normal_p99_pct']}%). The plain "
        "conclusion is that bad days are larger than a normal model "
        "expects, which is one reason the main simulation used a bootstrap method "
        "alongside GBM, and why Section 7 adds a fat tail simulation.", BODY))
    S.append(KeepTogether([cap_figure("QQ plot of portfolio daily log returns against the normal distribution"),
                           img("extended_qq_plot.png", w=9.6)]))
    S.extend(expl_figure(
        "Each blue dot is one daily log return of the portfolio, placed by its "
        "size: the horizontal axis is the value a normal distribution would "
        "give at that rank, and the vertical axis is the actual return in "
        "percent, while the red line is where the dots would sit if the "
        "returns were exactly normal. In the middle of the figure the dots "
        "follow the line closely, so ordinary days are close to normal. At "
        "both ends the dots pull away from the line: the lowest dot sits near "
        "-5.7%, well below the line, and the highest sits above it at about "
        "4.8%, which is the picture form of the fat tails measured in the text "
        "(excess kurtosis 2.957). The left end pulling down is the part that "
        "matters for risk, because it means very bad days are larger than a "
        "normal model expects."))

    S.append(Paragraph("5. Liquidity: how fast each position could be sold", H2))
    S.extend(bulleted(
        "Liquidity is measured from traded value (volume multiplied by the "
        "closing price). The days to exit figures show how many trading "
        "days it would take to sell one Tk 90,909 position if selling were "
        "limited to the full median daily traded value, or to 20% of it, "
        "which is a more realistic limit for not moving the price. The "
        "Amihud measure is the average of the absolute daily return "
        "divided by the daily traded value, shown multiplied by 1e9: the "
        "higher it is, the more a given amount of trading moves the price. "
        "Grades follow one stated rule: Good means the position sells "
        "within one day at the 20% limit, with zero return days at most "
        "10% and zero volume days at most 5; Trapped means more than five "
        "days are needed at the 20% limit; every other stock is Thin.", BODY, n_open=1))
    rows = [["Stock", "Median traded value (Tk/day)", "Amihud (x1e9)", "Zero volume days", "Days to exit at 20%", "Grade"]]
    for _, r in liq.iterrows():
        rows.append([r["ticker"], f"{r['median_daily_traded_value_tk']:,.0f}",
                     f"{r['amihud_illiquidity_x1e9']:.2f}",
                     f"{int(r['zero_volume_days'])}",
                     f"{r['days_to_exit_20pct_of_median']:.2f}", r["liquidity_grade"]])
    S.append(KeepTogether([cap_table("Liquidity of each stock and days needed to sell one equal weight position"),
                           tbl(rows, widths=[2.7 * cm, 3.9 * cm, 2.4 * cm, 2.8 * cm, 3.0 * cm, 2.0 * cm])]))
    S.extend(expl_table(
        "Each row is one stock, and the columns give its median traded value "
        "per day in taka, its Amihud measure (higher means a given amount of "
        "trading moves the price more), its count of zero volume days, the "
        "days needed to sell one Tk 90,909 position using only 20% of a "
        "median day's trading, and the grade that follows from those figures. "
        "Ten stocks need about a tenth of a day or less on that rule and are "
        "graded Good or Thin. BEXIMCO is the exception in every column at "
        "once: a median traded value of Tk 330 a day, an Amihud value of "
        "38.97 against a next highest of 4.47 (GEMINISEA), 149 zero volume "
        "days, and 1,376.16 days to exit, which is why it alone is graded "
        "Trapped. The Thin grades for CITYBANK, EBL, ROBI and FUWANGCER come "
        "from stale recorded prices rather than low traded value, as the text "
        "below the table explains."))
    S.append(Paragraph(
        "BEXIMCO is in a class of its own. Its median traded value is "
        "Tk 330 a day (a median volume of 3 shares at its frozen price of "
        "Tk 110.1). Selling Tk 90,909 would take 275 days even using the "
        "full median day's trading, and 1,376 days at the 20% limit. Its "
        "Amihud value, 38.97, is about nine times the next highest "
        "(GEMINISEA, 4.47). Its mean traded value is far higher than its "
        "median because trading returned in size only near the end of the "
        "window; a holder during the frozen period could not rely on that. "
        f"The other 10 stocks each need less than one day at the 20% "
        f"limit. Grades in total: {grades.get('Good', 0)} Good, "
        f"{grades.get('Thin', 0)} Thin, {grades.get('Trapped', 0)} Trapped. "
        "The Thin grades for CITYBANK, EBL, ROBI and FUWANGCER come from "
        "their high shares of zero return days, which point to stale "
        "recorded prices, not from traded value, which is large.", BODY))
    S.append(KeepTogether([cap_figure("Days needed to sell one equal weight position, by stock"),
                           img("extended_liquidity_days.png", w=14.8)]))
    S.extend(expl_figure(
        "The bars show, for each stock, the days needed to sell one "
        "Tk 90,909 position at 20% of its median daily traded value, and the "
        "horizontal axis is a log scale, which means each step to the right "
        "multiplies the time by ten rather than adding a fixed amount. A log "
        "scale is the only way to draw this figure at all: BEXIMCO's bar runs "
        "to 1,376 days while every other bar stops at 0.10 days or less, so "
        "on an ordinary scale the other ten bars would be invisible. The "
        "figure is therefore best read as a gap, not a ranking: ten positions "
        "could be sold the same day, and one could not be sold in fewer than "
        "1,376 trading days on this rule."))

    S.append(Paragraph("6. Rolling risk, volatility models, and beta", H2))
    S.extend(bulleted(
        f"Rolling 63 day portfolio volatility moved between "
        f"{roll['vol_63d_min_pct']}% and {roll['vol_63d_max_pct']}% a year "
        f"and ended at {roll['vol_63d_latest_pct']}%. Risk in this "
        "portfolio is not steady, and a single volatility number hides a "
        "range of more than three times between the calmest and the most "
        " unsettled periods. The rolling 63 day Sharpe ratio moved between "
        f"{roll['sharpe_63d_min']} and {roll['sharpe_63d_max']} and ended "
        f"at {roll['sharpe_63d_latest']}; swings of that size over 63 day "
        "windows are mostly noise and are reported for completeness, not "
        "as a performance claim. The EWMA volatility (RiskMetrics, lambda "
        f"0.94) ended at {ew['latest_vol_pct']}% a year, close to the "
        "rolling figure, after ranging between "
        f"{ew['min_vol_pct']}% and {ew['max_vol_pct']}%.", BODY, n_open=1))
    if ga.get("fitted"):
        S.append(Paragraph(
            f"A GARCH(1,1) model fitted to the 468 portfolio daily log "
            f"returns gave alpha {ga['alpha']} and beta {ga['beta']}, a "
            f"persistence of {ga['persistence_alpha_plus_beta']}: shocks "
            "to volatility fade slowly. Its next day volatility forecast "
            f"is {ga['next_day_vol_pct']}%, or "
            f"{ga['next_day_vol_annualised_pct']}% annualised, close to "
            "the EWMA figure. With 468 returns the fit is at the low end "
            "of sample sizes used for this model, so it is treated as a "
            "check on EWMA, not as a separate forecast.", BODY))
    S.append(KeepTogether([cap_figure("Rolling 63 day volatility and EWMA volatility"),
                           img("extended_rolling_vol_ewma.png", w=14.8)]))
    S.extend(expl_figure(
        "The two lines are two ways of measuring the same thing, the "
        "portfolio's volatility per year, over time: one line is the "
        "volatility of the previous 63 trading days, recalculated each day, "
        "and the other is the EWMA measure, which gives more weight to "
        "recent days (lambda 0.94). The lines rise and fall together and end "
        "close to each other, at 16.00% for the rolling measure and 15.96% "
        "for EWMA. Between them they cover a wide range inside the window, "
        "from 7.43% to 36.33% on the EWMA measure and from 8.07% to 25.73% "
        "on the rolling measure. That movement is the point of the figure: "
        "the single full window volatility of 17.36% used elsewhere in this "
        "report is an average over calm and unsettled periods, not a "
        "constant."))
    S.append(Paragraph(
        "Beta against the DSEX index could not be calculated, and no "
        "substitute index was used. The DSE day-end archive that supplied "
        "the stock prices holds no index series: requests for DSEX, "
        "DSEX_IDX, DSE30, DSES and INDEX each returned zero rows. The "
        "stocksurferbd index history reads the legacy DSE site, which did "
        "not respond. Its graph endpoint does not serve DSEX. "
        "stockanalysis.com has no DSEX index page (HTTP 404) and the DSE "
        "index archive page returns HTTP 410. Every attempt is logged in "
        "data/extended_dsex_fetch_log.csv. The cost of this gap is real: "
        "there is no market benchmark in this project, so no statement "
        "can be made about whether the portfolio moved more or less than "
        "the market, or about alpha.", BODY))

    S.append(Paragraph("7. Stress tests", H2))
    S.append(Paragraph(
        "Each scenario below is a simple, named price shock applied to "
        "the equal weights. All are hypothetical. Losses are shown on "
        "Tk 1,000,000.", BODY))
    rows = [["Scenario (hypothetical)", "Loss (%)", "Loss (Tk)", "Ending value (Tk)"]]
    for _, r in stress.iterrows():
        name = r["scenario"].split(". ", 1)[-1].replace(" (hypothetical)", "")
        rows.append([name, f"{r['loss_pct']:.2f}", f"{r['loss_tk']:,.0f}",
                     f"{r['ending_value_tk']:,.0f}"])
    S.append(KeepTogether([cap_table("Stress test losses on Tk 1,000,000 at equal weights (all scenarios hypothetical)"),
                           tbl(rows, widths=[8.6 * cm, 2.2 * cm, 2.8 * cm, 3.4 * cm])]))
    S.extend(expl_table(
        "Each row is one named, hypothetical shock applied to the equal "
        "weights, and the columns give the loss as a percentage of "
        "Tk 1,000,000, the loss in taka, and the ending value. The rows are "
        "ordered by size of loss, and the largest is not a single stock "
        "event: joining the five worst real days in the window back to back "
        "costs 19.04%, or Tk 190,448. Single stock shocks are capped by the "
        "equal weight itself, so even BEXIMCO falling to zero costs 9.09% "
        "(Tk 90,909), and the bank shock, three stocks falling 20% at once, "
        "is the smallest row at 5.45% (Tk 54,545). These figures are the "
        "arithmetic results of the stated shocks, not forecasts, and the "
        "BEXIMCO row understates the practical problem, because Section 5 "
        "shows the position could not have been sold during the frozen "
        "period."))
    S.append(Paragraph(
        "The largest loss comes from joining the five worst real days in "
        "the window back to back: 19.04%, or Tk 190,448. It is larger "
        "than the combined scenario (every stock falls 10%, then BEXIMCO "
        "falls to zero: 18.18%, Tk 181,818) because the five real days "
        "include falls of 5.51% and 4.53% driven by many stocks at once, "
        "compounded over five days. The single stock scenarios are "
        "smaller than they may look because each stock is only 9.09% of "
        "the portfolio: even BEXIMCO falling to zero costs 9.09% "
        "(Tk 90,909) on paper. In practice that scenario is worse than "
        "the number, because Section 5 shows the position could not have "
        "been sold during the frozen period at any price close to the "
        "recorded one.", BODY))
    S.append(KeepTogether([cap_figure("Stress test losses by scenario"),
                           img("extended_stress_tests.png", w=14.8)]))
    S.extend(expl_figure(
        "Each bar is one scenario from Table 5 and the horizontal axis is "
        "the loss in thousands of taka on Tk 1,000,000. The two longest "
        "bars, 190.4 and 181.8 thousand, are the two combined scenarios: "
        "the five worst real days joined back to back, and every stock "
        "falling 10% followed by BEXIMCO falling to zero. Both are longer "
        "than the 100.0 thousand bar for a single day in which every stock "
        "falls 10%. The shortest bar, 54.5 thousand, is the bank shock. The "
        "figure makes the ordering in Table 5 easy to see: losses grow when "
        "falls happen together, or follow each other over several days, "
        "rather than when one stock falls alone."))

    S.append(Paragraph("8. Fat tail Monte Carlo: Student-t shocks", H2))
    S.append(Paragraph(
        f"The degrees of freedom for the Student-t distribution were "
        f"estimated from the portfolio excess kurtosis of "
        f"{tt['portfolio_excess_kurtosis']} by the method of moments "
        f"(excess kurtosis = 6 / (df - 4)), giving df = "
        f"{tt['df_estimated']}; the value used is {tt['df_used']}. Shocks "
        "are drawn with the same correlations as the main simulation and scaled so "
        "the simulated covariance matches the historical covariance. "
        "10,000 simulations, seed 42.", BODY))
    labels = {"gbm": "GBM", "bootstrap": "Bootstrap",
              "student_t": "Student-t"}
    # Two smaller tables instead of one nine column table, so every
    # header and value fits inside the page margins.
    rows = [["Horizon", "Method", "Median value (Tk)", "VaR 95% (Tk)",
             "CVaR 95% (Tk)", "Probability of loss (%)"]]
    for h in ("21", "63", "252"):
        for m in ("gbm", "bootstrap", "student_t"):
            c = tt["three_method_comparison"][h][m]
            rows.append([h + " days" if m == "gbm" else "", labels[m],
                         f"{c['median_value_tk']:,.0f}", f"{c['var95_tk']:,.0f}",
                         f"{c['cvar95_tk']:,.0f}", f"{c['prob_loss_pct']:.2f}"])
    S.append(KeepTogether([cap_table("Three method comparison: median, 95% measures and probability of loss"),
                           tbl(rows, widths=[1.9 * cm, 2.9 * cm, 3.2 * cm, 2.8 * cm, 2.9 * cm, 3.5 * cm])]))
    S.extend(expl_table(
        "The rows are grouped by horizon, three rows to a horizon, one for "
        "each method, and the columns give the median ending value, the VaR "
        "and CVaR losses at 95%, and the probability of a loss, all for a "
        "Tk 1,000,000 start. The comparison that matters is the Student-t row "
        "against the GBM row at the same horizon, because those two differ "
        "only in the shape of the random shocks: at 252 days the Student-t "
        "median is Tk 954,377 against the GBM Tk 952,265, and its VaR 95% is "
        "Tk 284,293 against Tk 288,883. The Student-t figures are close to, "
        "and slightly smaller than, the GBM figures at every horizon, which "
        "is the result discussed in the text after Table 7. The bootstrap "
        "rows are included so that all three methods can be compared in one "
        "place."))
    rows = [["Horizon", "Method", "VaR 99% (Tk)", "CVaR 99% (Tk)"]]
    for h in ("21", "63", "252"):
        for m in ("gbm", "bootstrap", "student_t"):
            c = tt["three_method_comparison"][h][m]
            rows.append([h + " days" if m == "gbm" else "", labels[m],
                         f"{c['var99_tk']:,.0f}", f"{c['cvar99_tk']:,.0f}"])
    S.append(KeepTogether([cap_table("Three method comparison: 99% measures"),
                           tbl(rows, widths=[1.9 * cm, 2.9 * cm, 3.0 * cm, 3.0 * cm])]))
    S.extend(expl_table(
        "This table is the 99% counterpart of Table 6, with the same rows and "
        "methods but only the two deeper tail measures, VaR 99% and "
        "CVaR 99%. At 252 days the Student-t CVaR 99% is Tk 399,738, between "
        "the bootstrap figure of Tk 395,525 and the GBM figure of "
        "Tk 405,927, so the ordering of the three methods at the 99% level "
        "matches the ordering at 95%. CVaR is larger than VaR in every row, "
        "because it averages the worst 1% of outcomes rather than marking "
        "its edge. Even at this deeper level the fat tail method does not "
        "produce the largest losses, for the reason given in the text that "
        "follows: daily extremes partly cancel when they are added together "
        "over many days."))
    S.append(Paragraph(
        "The Student-t results sit close to the GBM results at every "
        "horizon and slightly below them at 252 days (VaR 95% Tk 284,293 "
        "against Tk 288,883). That is a smaller difference than the "
        "distance between either model and the bootstrap, and it is "
        "within the range that simulation noise alone can produce at "
        "10,000 paths. The reason the fat tail does not add much at these "
        "horizons is that daily shocks are added together over 21 to 252 "
        "days, and sums of daily returns move toward a normal shape even "
        "when single days do not have one. The fat tail is a daily fact "
        "(Section 4); at the horizons used here it does not change the "
        "risk answer. All three methods agree on the answer that matters: "
        "a one year loss is more likely than not, and a loss beyond "
        "Tk 270,000 sits inside the worst 5% of outcomes under every "
        "method.", BODY))

    S.append(Paragraph("9. Fundamental snapshot", H2))
    S.append(Paragraph(
        "Price risk is only half of the picture. The table gives the "
        "latest figures shown by stockanalysis.com for each company, "
        "fetched on 31 October 2026. EPS is trailing twelve months. "
        "Fiscal years end in June for five companies and December for "
        "six, so the annual figures are not for the same period and "
        "comparisons are not exact. Cash dividend percent and stock "
        "dividend percent are not shown as percents by the source, so "
        "they are recorded as not available; the cash amount per share "
        "is reported instead. No recommendation is made for any stock.", BODY))
    rows = [["Stock", "EPS (Tk)", "PE", "Dividend yield (%)", "ROE (%)", "Note"]]
    for _, r in fund.iterrows():
        pe = "n/a" if pd.isna(r["pe_ratio"]) else f"{r['pe_ratio']:.2f}"
        dy = "n/a" if pd.isna(r["dividend_yield_pct"]) else f"{r['dividend_yield_pct']:.2f}"
        roe = "n/a" if pd.isna(r["roe_ttm_pct"]) else f"{r['roe_ttm_pct']:.2f}"
        rows.append([r["ticker"], f"{r['eps_ttm_bdt']:.2f}", pe, dy, roe,
                     short_note(r["quality_note"])])
    S.append(KeepTogether([cap_table("Fundamental snapshot: earnings, valuation and dividends by company"),
                           tbl(rows, widths=[2.6 * cm, 1.7 * cm, 1.3 * cm, 2.7 * cm, 1.6 * cm, 6.9 * cm])]))
    S.extend(expl_table(
        "Each row is one company, and the columns give earnings per share "
        "over the trailing twelve months in taka, the price to earnings "
        "ratio, the dividend yield, and the return on equity, followed by a "
        "short note. A PE is shown as n/a for the five loss making "
        "companies, because a PE has no useful meaning when earnings are "
        "negative; that is a result, not missing data. Among the six "
        "profitable companies the PE runs from 3.36 for CITYBANK to 29.97 "
        "for BATBC, against a group median of 7.59, and the dividend yield "
        "runs from 10.55% for EBL down to 0.15% for SEAPEARL. The note "
        "column should be read together with Sections 1 and 5: the five "
        "loss making rows, ACI, BEXIMCO, FUWANGCER, GEMINISEA and SEAPEARL, "
        "are the same stocks that carry the highest price risk and the "
        "weakest liquidity in this report."))
    S.extend(bulleted(
        "Six companies are profitable on trailing EPS and five are loss "
        "making. The five loss making companies are ACI, BEXIMCO, "
        "FUWANGCER, GEMINISEA and SEAPEARL: the same group that carries "
        "the highest price risk and the weakest liquidity in this report. "
        "That overlap is the most useful finding in this section. The "
        "stocks that look worst on price behaviour also look worst on "
        "current earnings. The profitable group is not uniform: CITYBANK "
        "shows a PE of 3.36 and ROE of 27.19%, while BATBC shows a PE of "
        "29.97, the highest in the set, on an ROE of 6.51%. Market caps "
        "range from Tk 155.57 billion (ROBI) down to Tk 1.14 billion "
        "(GEMINISEA), so equal weights put far more weight, relative to "
        "company size, on the smallest companies than a market value "
        "weighting would.", BODY, n_open=1))
    S.append(KeepTogether([cap_figure("Earnings per share by stock, trailing twelve months"),
                           img("extended_fundamentals_eps.png", w=14.8)]))
    S.extend(expl_figure(
        "The bars are earnings per share over the trailing twelve months "
        "for each stock, in taka, and the red bars are the loss making "
        "companies, as the chart title states. The zero line is the "
        "dividing line of the whole figure: six bars rise above it and five "
        "fall below it. BXPHARMA has the tallest bar, at Tk 19.39, well "
        "above the next company, while GEMINISEA has the deepest, at "
        "Tk -7.41, followed by BEXIMCO at Tk -4.21. The figure shows "
        "earnings only, not value for money: BATBC earns Tk 6.98 per share "
        "yet carries the highest PE in Table 8, so a tall bar does not by "
        "itself mean a cheap stock."))

    S.append(PageBreak())
    S.append(Paragraph("10. Overall verdict", H2))
    rows = [["Area", "Verdict", "Evidence"]]
    rows.append(["Return", "Bad in this window; long term not proven",
                 f"Total return {dd['total_return_pct']}% over the window on the daily rebalanced path; compound annual growth rate {dd['cagr_pct']}%; median one year ending value below Tk 1,000,000 under all three simulation methods; probability of a one year loss between 58.8% and 60.3%. The standard error of the annual mean return over 1.86 years is about 12.7 percentage points, so this window cannot prove the long term return is negative."])
    rows.append(["Risk", "High",
                 f"Volatility {rd['portfolio_volatility_pct']}% a year; maximum drawdown {dd['max_drawdown_pct']}%, not recovered by the end of the window; one year VaR 95% between Tk 270,206 and Tk 288,883 across methods; GBM CVaR 99% Tk 405,927; daily returns have fat tails (excess kurtosis {dist['portfolio']['excess_kurtosis']})."])
    rows.append(["Diversification", "Worked on volatility; did not fix concentration",
                 f"Diversification ratio {div['diversification_ratio']}; average correlation {div['average_pairwise_correlation']}; effective risk bets {rd['effective_number_of_risk_bets']} of 11. Against that, SEAPEARL, FUWANGCER and GEMINISEA hold 39.89% of total risk on 27.27% of the money, and those three are loss making on current earnings."])
    rows.append(["Liquidity", "Poor, because of one stock",
                 f"{grades.get('Good', 0)} Good, {grades.get('Thin', 0)} Thin, {grades.get('Trapped', 0)} Trapped. BEXIMCO: median traded value Tk 330 a day; 1,376 days to sell one position at 20% of that value. The other 10 stocks each need less than one day on the same rule."])
    rows.append(["Data quality", "Weak",
                 "469 trading days only. Prices not adjusted for dividends, with three dividend reset falls inside the returns. BEXIMCO price fixed for a full calendar year. No DSEX series could be fetched, so there is no market benchmark and no beta. Five of 11 companies are loss making, which the price data alone would not show."])
    S.append(KeepTogether([cap_table("Overall verdict by area, with the evidence for each verdict"),
                           tbl(rows, widths=[2.6 * cm, 4.6 * cm, 10.2 * cm])]))
    S.extend(expl_table(
        "Each row is one of the five areas set out in the introduction, the "
        "middle column gives the verdict for that area in a few words, and "
        "the last column gives the evidence for it, with the numbers that "
        "support it. Read in order, the rows show a pattern: the parts that "
        "can be measured most precisely are the most critical, with return "
        "negative in the window, risk high, and liquidity failing on one "
        "stock, while diversification is the one area that worked as "
        "intended. The return row carries its own limit inside its "
        "evidence: the standard error of the annual mean return is about "
        "12.7 percentage points, so that verdict is stated for this window "
        "only, not for the long term. No row of this table is a "
        "recommendation about any stock; the table sums up measurements "
        "that are set out in the sections above it."))
    S.append(Paragraph(
        "In one paragraph: this is a portfolio whose risk is real and "
        "measured consistently by three different methods, whose "
        "diversification genuinely reduced volatility, and whose weak "
        "points are specific and named rather than general: three small, "
        "loss making, high volatility stocks carry about 40% of the risk, "
        "and one stock cannot be sold at its recorded price in any "
        "reasonable time. Its return over the only window that can be "
        "measured was negative, but that window is too short to settle "
        "the long term return, and the report does not claim that it "
        "does.", BODY))
    S.append(Paragraph("11. Limitations", H2))
    for i, text in enumerate([
        "Beta and alpha against DSEX could not be calculated because no daily DSEX series could be fetched. Attempts are logged in data/extended_dsex_fetch_log.csv. No proxy index was used in its place.",
        "The window is 469 trading days. Return estimates at this length carry a standard error of about 12.7 percentage points a year. Volatility, correlation and drawdown are measured more precisely than return at this length, and the verdict weights them accordingly.",
        "BEXIMCO measured risk is understated in every covariance based measure because its recorded returns are zero on 81.6% of days. Its component VaR rank and its liquidity grade give the opposite signal, and both are reported so the reader can see the conflict.",
        "Prices are not adjusted for dividends. Three falls beyond the daily limit in the data match dividend record date resets (CITYBANK, EBL, ACI) and are counted as losses in every return based measure. Dividend income is not counted anywhere.",
        "Two path definitions are used and labelled: buy and hold inside the main simulation, and daily rebalanced equal weight for the drawdown section of this report. Total returns differ slightly between the two and neither is hidden.",
        "The Student-t simulation uses one degrees of freedom value for all stocks and all days, estimated from portfolio kurtosis. Real tail weight differs by stock.",
        "GARCH(1,1) was fitted on 468 returns, at the low end for the model. It is used as a check on EWMA only.",
        "Stress scenarios are single shocks at equal weights, with no trading costs and no allowance for the fact that a falling market usually brings lower traded value, which would make exit slower than Section 5 states.",
        "Fundamental figures come from one source on one date, and fiscal year ends differ between June and December across the set.",
    ], 1):
        S.append(Paragraph(f"{i}. {text}", BODY))

    doc = SimpleDocTemplate(os.path.join(BASE, "DSE_Extended_Portfolio_Analysis_Report.pdf"),
                            pagesize=A4, leftMargin=1.6 * cm, rightMargin=1.6 * cm,
                            topMargin=1.5 * cm, bottomMargin=1.5 * cm,
                            title="Portfolio Risk Analysis: Dhaka Stock Exchange, Extended Analysis",
                            author="Munzeleen Sarwar")
    doc.build(S)
    print("report built")


if __name__ == "__main__":
    main()
