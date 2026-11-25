"""Extended analysis fundamental snapshot for the 11 DSE tickers.

Source: stockanalysis.com DSE pages (statistics, dividend and company
pages), fetched on the access date recorded in the output. Figures are
copied as shown. Any figure the source does not show is recorded as
n/a. Nothing is estimated or filled in.

Fields: company name, industry (shown as the sector field by the
source), fiscal year range and year end month, market cap, PE ratio,
EPS (TTM), dividend yield, annual dividend per share, latest cash
dividend per share with its ex-dividend date, payout ratio, ROE (TTM).
Cash dividend percent and stock dividend percent are not shown as
percents by this source, so they are recorded as n/a and the per share
cash amount is reported instead.

A short quality note per stock is built by rule from the fetched
figures only: profitable or loss making (sign of EPS), pays a dividend
or not (annual dividend shown above zero), and PE below, near or above
the group median (within 20% counts as near). No recommendation of any
kind is made.
"""
import json
import os
import re
import time

import pandas as pd
import requests
from bs4 import BeautifulSoup

TICKERS = ["BATBC", "BXPHARMA", "CITYBANK", "DBH", "EBL", "ROBI", "ACI",
           "BEXIMCO", "FUWANGCER", "GEMINISEA", "SEAPEARL"]
BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(BASE, "data")
ACCESS_DATE = "2026-10-31"
H = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                   "Chrome/120 Safari/537.36"}
SRC = "stockanalysis.com DSE pages (statistics, dividend, company), accessed " + ACCESS_DATE


def fetch(url):
    r = requests.get(url, headers=H, timeout=45)
    r.raise_for_status()
    return BeautifulSoup(r.text, "html.parser")


def kv_tables(soup):
    out = {}
    for tb in soup.find_all("table"):
        for tr in tb.find_all("tr"):
            cells = [c.get_text(strip=True) for c in tr.find_all(["td", "th"])]
            if len(cells) == 2:
                out.setdefault(cells[0], cells[1])
    return out


def num(s):
    if s is None:
        return None
    s = str(s).replace(",", "").replace("%", "").strip()
    try:
        return float(s)
    except ValueError:
        return None


def main():
    rows = []
    for t in TICKERS:
        base = f"https://stockanalysis.com/quote/dse/{t}/"
        row = {"ticker": t, "source": SRC}
        try:
            stats = fetch(base + "statistics/")
            kv = kv_tables(stats)
            text = stats.get_text(" ", strip=True)
            row["market_cap_bdt"] = kv.get("Market Cap", "n/a")
            row["pe_ratio"] = num(kv.get("PE Ratio")) if kv.get("PE Ratio") not in (None, "n/a") else "n/a"
            m = re.search(r"Earnings Per Share \(EPS\)\s+(-?[\d,]*\.?\d+)", text)
            row["eps_ttm_bdt"] = num(m.group(1)) if m else "n/a"
            row["eps_basis"] = "TTM, statistics page"
            if row["eps_ttm_bdt"] == "n/a":
                main_kv = kv_tables(fetch(base))
                mm = re.search(r"-?[\d.]+", main_kv.get("EPS", ""))
                v = num(mm.group(0)) if mm else None
                if v is not None:
                    row["eps_ttm_bdt"] = v
                    row["eps_basis"] = "TTM, main quote page (statistics page shows no EPS line for this stock)"
            m = re.search(r"Return on Equity \(ROE\)\s+(-?[\d.]+)%", text)
            row["roe_ttm_pct"] = num(m.group(1)) if m else "n/a"
            m = re.search(r"Dividend Yield\s+([\d.]+)%", text)
            row["dividend_yield_pct"] = num(m.group(1)) if m else "n/a"
            m = re.search(r"Payout Ratio\s+(-?[\d.]+)%", text)
            row["payout_ratio_pct"] = num(m.group(1)) if m else "n/a"
            div = fetch(base + "dividend/")
            dtext = div.get_text(" ", strip=True)
            m = re.search(r"Annual Dividend\s+([\d.]+) BDT", dtext)
            row["annual_dividend_bdt"] = num(m.group(1)) if m else "n/a"
            latest = None
            for tb in div.find_all("table"):
                trs = tb.find_all("tr")
                if not trs:
                    continue
                head = [c.get_text(strip=True) for c in trs[0].find_all(["td", "th"])]
                if any("Ex-Dividend" in h for h in head) and len(trs) > 1:
                    cells = [c.get_text(strip=True) for c in trs[1].find_all(["td", "th"])]
                    if len(cells) >= 2:
                        latest = (cells[0], cells[1])
                    break
            row["latest_cash_dividend"] = (f"{latest[1]} per share, ex-date {latest[0]}"
                                           if latest else "n/a")
            comp = fetch(base + "company/")
            ckv = kv_tables(comp)
            row["industry"] = ckv.get("Industry", "n/a")
            fy = ckv.get("Fiscal Year", "n/a")
            row["fiscal_year"] = fy
            row["fiscal_year_end"] = (fy.split("-")[-1].strip()
                                      if fy != "n/a" else "n/a")
            title = comp.title.get_text(strip=True) if comp.title else ""
            m = re.search(r"^(.*?)\s*\((?:DSE:)?" + t, title)
            row["company_name"] = m.group(1).strip() if m else "n/a"
            row["fetch_status"] = "ok"
        except Exception as e:  # noqa: BLE001
            row["fetch_status"] = f"failed: {str(e)[:150]}"
            for k in ("market_cap_bdt", "pe_ratio", "eps_ttm_bdt", "roe_ttm_pct",
                      "dividend_yield_pct", "payout_ratio_pct",
                      "annual_dividend_bdt", "latest_cash_dividend",
                      "industry", "fiscal_year", "fiscal_year_end",
                      "company_name"):
                row.setdefault(k, "n/a")
            row.setdefault("eps_basis", "TTM, statistics page")
        row["cash_dividend_pct"] = "n/a (not shown as a percent by the source; per share amount is reported)"
        row["stock_dividend_pct"] = "n/a (not shown by the source)"
        rows.append(row)
        print(t, row["fetch_status"], "EPS:", row.get("eps_ttm_bdt"),
              "PE:", row.get("pe_ratio"), "MCap:", row.get("market_cap_bdt"))
        time.sleep(1)
    df = pd.DataFrame(rows)
    pes = pd.to_numeric(df["pe_ratio"], errors="coerce")
    med = float(pes.median()) if pes.notna().any() else None
    notes = []
    for _, r in df.iterrows():
        bits = []
        eps = r["eps_ttm_bdt"]
        if isinstance(eps, (int, float)):
            bits.append("Profitable on TTM EPS" if eps > 0 else "Loss making on TTM EPS")
        else:
            bits.append("EPS not shown by the source")
        if isinstance(r["annual_dividend_bdt"], (int, float)) and r["annual_dividend_bdt"] > 0:
            bits.append("pays a cash dividend")
        else:
            bits.append("no annual cash dividend shown")
        pe = r["pe_ratio"]
        if isinstance(pe, (int, float)) and med:
            if pe < 0:
                bits.append("PE is negative because EPS is negative")
            elif pe < 0.8 * med:
                bits.append("PE below the group median")
            elif pe > 1.2 * med:
                bits.append("PE above the group median")
            else:
                bits.append("PE near the group median")
        notes.append("; ".join(bits) + ".")
    df["quality_note"] = notes
    df.to_csv(os.path.join(DATA, "extended_fundamentals.csv"), index=False)
    R = json.load(open(os.path.join(DATA, "extended_results.json")))
    R["fundamentals"] = {
        "source": SRC,
        "group_median_pe": round(med, 2) if med else None,
        "fiscal_year_flag": ("Fiscal year ends differ across the set (June "
                             "for some companies, December for others), so "
                             "annual figures are not for the same period and "
                             "comparisons are not exact."),
        "rows": df.to_dict(orient="records"),
    }
    json.dump(R, open(os.path.join(DATA, "extended_results.json"), "w"),
              indent=1, default=str)
    print("group median PE:", med)
    print(df[["ticker", "company_name", "industry", "fiscal_year_end"]].to_string(index=False))


if __name__ == "__main__":
    main()
