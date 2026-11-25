"""Extended analysis: try to fetch DSEX index daily closes for the main simulation window
(3 Nov 2024 to 15 Oct 2026) from real sources. Every attempt is logged
to data/extended_dsex_fetch_log.csv. If no source returns a daily DSEX
series, data/extended_dsex.csv is not created and the beta section of
The extended analysis reports the failure as a limitation. No proxy index is used.
"""
import os
import sys

import pandas as pd
import requests

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(BASE, "data")
START, END = "2024-11-03", "2026-10-15"
H = {"User-Agent": "Mozilla/5.0", "Accept": "application/json"}
rows = []


def log(source, result, detail):
    rows.append({"source": source, "result": result, "detail": str(detail)[:400]})
    print(f"[{source}] {result}: {str(detail)[:200]}")


def try_dse_api():
    api = "https://dse.com.bd/api/live/data-archive/day-end"
    for inst in ("DSEX", "DSEX_IDX", "DSE30", "DSES", "INDEX"):
        try:
            r = requests.get(api, params={"from": START, "to": END,
                                          "inst": inst, "page": 1},
                             headers=H, timeout=45)
            d = r.json()
            total = d.get("total") or 0
            log("dse_official_api_day_end", "no_rows" if total == 0 else "ok",
                f"inst={inst}: total={total}")
            if total:
                return inst
        except Exception as e:  # noqa: BLE001
            log("dse_official_api_day_end", "failed", f"inst={inst}: {e}")
    return None


def try_stocksurferbd():
    try:
        from stocksurferbd import IndexData
        loader = IndexData(verify=False, timeout=30)
        print("supported indices:", loader.SUPPORTED_INDICES)
        df = loader.get_index_history_df(market="DSE",
                                         start_date=START, end_date=END)
        log("stocksurferbd_index", "ok", f"{len(df)} rows")
        print(df.head(3).to_string())
        print(df.tail(2).to_string())
        print("columns:", list(df.columns))
        return df
    except Exception as e:  # noqa: BLE001
        log("stocksurferbd_index", "failed", str(e))
        return None


def try_stocksurfer_graph():
    try:
        from stocksurferbd import IndexData
        loader = IndexData(verify=False, timeout=30)
        df = loader.get_index_graph_df("DSEX", market="DSE")
        log("stocksurferbd_index_graph", "ok", f"{len(df)} rows")
        print(df.head(3).to_string())
        print("columns:", list(df.columns))
        return df
    except Exception as e:  # noqa: BLE001
        log("stocksurferbd_index_graph", "failed", str(e))
        return None


def try_other_sources():
    for name, url in (
            ("stockanalysis_index_history", "https://stockanalysis.com/index/dsex/history/"),
            ("dsebd_index_archive_page", "https://www.dsebd.org/dseX_full_archive.php"),
            ("dse_api_index_history_guess", "https://dse.com.bd/api/live/market/index-history")):
        try:
            r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"},
                             timeout=30)
            log(name, "failed", f"{url}: HTTP {r.status_code}")
        except Exception as e:  # noqa: BLE001
            log(name, "failed", f"{url}: {e}")


def main():
    try_dse_api()
    try_other_sources()
    df = try_stocksurferbd()
    if df is None or len(df) == 0:
        df = try_stocksurfer_graph()
    ok = False
    if df is not None and len(df) > 100:
        # Normalise whatever came back into date, close if identifiable.
        cols = {c.lower(): c for c in df.columns}
        date_c = next((cols[k] for k in cols if "date" in k or "time" in k), None)
        close_c = next((cols[k] for k in cols
                        if k in ("close", "value", "index", "index_value",
                                 "dsex")), None)
        if date_c and close_c:
            out = pd.DataFrame({"date": pd.to_datetime(df[date_c]).dt.strftime("%Y-%m-%d"),
                                "dsex_close": pd.to_numeric(df[close_c], errors="coerce")})
            out = out.dropna().drop_duplicates("date").sort_values("date")
            out = out[(out.date >= START) & (out.date <= END)]
            if len(out) > 100:
                out.to_csv(os.path.join(DATA, "extended_dsex.csv"), index=False)
                log("saved", "ok", f"extended_dsex.csv: {len(out)} rows "
                                   f"{out.date.min()} to {out.date.max()}")
                ok = True
    if not ok:
        log("outcome", "failed",
            "No daily DSEX series could be fetched. Beta is reported as a "
            "limitation in the extended analysis. No proxy was substituted.")
    pd.DataFrame(rows).to_csv(os.path.join(DATA, "extended_dsex_fetch_log.csv"),
                              index=False)
    print("DSEX fetch ok:", ok)


if __name__ == "__main__":
    sys.exit(main())
