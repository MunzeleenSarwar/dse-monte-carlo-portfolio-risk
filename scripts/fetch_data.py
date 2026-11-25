"""Fetch DSE daily prices for the 11 project tickers.

Sources are tried in this order and every attempt is logged to
data/fetch_log.csv:
1. bdshare (pip package) - in this environment its user agent receives
   HTTP 403 from the current DSE site, and the legacy site it falls back
   to (old.dsebd.org) does not respond.
2. stocksurferbd (pip package) - reads only the legacy site, which does
   not respond in this environment. The legacy pages on dsebd.org
   return HTTP 410 (retired).
3. Direct call to the current DSE public API at dse.com.bd
   (api/live/data-archive/day-end) with a browser user agent. This works.
   Its archive starts on 3 Nov 2024 for every instrument checked.
4. A published archive dataset (Mendeley Data, DOI 10.17632/5mww8rb9td.1,
   DSE prices 1999 to Apr 2025) is quality-checked as a possible source
   for Jan 2021 to Oct 2024. The check counts daily moves above 12% in a
   market with a 10% daily circuit breaker. The 2021 and 2022 segments
   contain many such impossible moves and duplicate dates with
   conflicting closes, and the 2023 segment is frozen at floor prices
   (BATBC and ROBI each have one unique close in the whole of 2023).
   That archive is therefore NOT used. The counts are logged so the
   decision can be checked.

The window used is the longest honest common window from the official
source: 3 Nov 2024 to 15 Oct 2026.

No price is fabricated or filled. The DSE API returns one row per
trading day per instrument, with the close carried at the previous
value on days the instrument did not trade (volume is then 0 or very
low). Those days are counted, not removed.
"""
import io
import json
import os
import sys
import zipfile

import pandas as pd
import requests

TICKERS = ["BATBC", "BXPHARMA", "CITYBANK", "DBH", "EBL", "ROBI", "ACI",
           "BEXIMCO", "FUWANGCER", "GEMINISEA", "SEAPEARL"]
START_REQUEST = "2021-01-01"   # requested window
END = "2026-10-15"             # statement date, 15 Oct 2026
API = "https://dse.com.bd/api/live/data-archive/day-end"
HEADERS = {"User-Agent": "Mozilla/5.0", "Accept": "application/json"}

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(BASE, "data")
os.makedirs(DATA, exist_ok=True)

log_rows = []


def log(source, result, detail):
    log_rows.append({"source": source, "result": result, "detail": detail})
    print(f"[{source}] {result}: {detail}")


def try_bdshare():
    try:
        from bdshare import get_historical_data
        df = get_historical_data("2026-09-01", END, "BATBC")
        log("bdshare", "ok", f"{len(df)} rows")
        return True
    except Exception as e:  # noqa: BLE001
        log("bdshare", "failed", str(e)[:300])
        return False


def try_stocksurferbd():
    try:
        from stocksurferbd import PriceData
        loader = PriceData(verify=False, timeout=30)
        df = loader.get_price_history_df("BATBC", market="DSE",
                                         start_date="2026-09-01", end_date=END)
        log("stocksurferbd", "ok", f"{len(df)} rows")
        return True
    except Exception as e:  # noqa: BLE001
        log("stocksurferbd", "failed", str(e)[:300])
        return False


def fetch_api(ticker):
    """All rows for one ticker from the official DSE API, paged."""
    rows, page = [], 1
    while True:
        r = requests.get(API, params={"from": START_REQUEST, "to": END,
                                      "inst": ticker, "page": page},
                         headers=HEADERS, timeout=60)
        r.raise_for_status()
        d = r.json()
        rows.extend(d.get("rows") or [])
        total, size = d.get("total") or 0, d.get("pageSize") or len(rows) or 1
        if page * size >= total or not d.get("rows"):
            break
        page += 1
    df = pd.DataFrame(rows)
    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values("date").drop_duplicates(subset=["date"])
    out = pd.DataFrame({
        "date": df["date"].dt.strftime("%Y-%m-%d"),
        "open": df["openp"], "high": df["high"], "low": df["low"],
        "close": df["closep"], "ycp": df["ycp"],
        "volume": df["volume"], "trades": df["trade"], "value_mn": df["value"],
    })
    return out


def check_mendeley_archive():
    """Quantify why the published 1999-2025 archive is not used pre-2023."""
    try:
        meta = requests.get("https://data.mendeley.com/public-api/datasets/5mww8rb9td",
                            headers={"Accept": "application/json"}, timeout=60).json()
        urls = {f["filename"].replace(".csv", ""): f["content_details"]["download_url"]
                for f in meta["files"]}
        summary = {}
        for t in TICKERS:
            raw = requests.get(urls[t], headers=HEADERS, timeout=60).content
            d = pd.read_csv(io.BytesIO(raw), parse_dates=["Date"])
            d = d.drop_duplicates().sort_values("Date")
            bad = {}
            for y in (2021, 2022):
                s = d[d.Date.dt.year == y]
                r = s.Close.pct_change().abs()
                bad[y] = int((r > 0.12).sum())
            s23 = d[d.Date.dt.year == 2023]
            summary[t] = {"moves_over_12pct_2021": bad[2021],
                          "moves_over_12pct_2022": bad[2022],
                          "unique_closes_2023": int(s23.Close.nunique())}
        log("mendeley_archive_quality_check", "rejected",
            json.dumps(summary))
        with open(os.path.join(DATA, "archive_quality_check.json"), "w") as f:
            json.dump(summary, f, indent=1)
    except Exception as e:  # noqa: BLE001
        log("mendeley_archive_quality_check", "check_failed", str(e)[:300])


def main():
    try_bdshare()
    try_stocksurferbd()
    check_mendeley_archive()
    frames = {}
    for t in TICKERS:
        df = fetch_api(t)
        df.to_csv(os.path.join(DATA, f"{t}.csv"), index=False)
        frames[t] = df.set_index("date")["close"]
        log("dse_official_api", "ok",
            f"{t}: {len(df)} rows, {df.date.min()} to {df.date.max()}")
        print(f"{t}: {len(df)} rows {df.date.min()}..{df.date.max()}")
    combined = pd.DataFrame(frames)
    combined.index.name = "date"
    combined.to_csv(os.path.join(DATA, "combined_close.csv"))
    pd.DataFrame(log_rows).to_csv(os.path.join(DATA, "fetch_log.csv"), index=False)
    print("combined:", combined.shape)


if __name__ == "__main__":
    sys.exit(main())
