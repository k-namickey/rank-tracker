#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import re
from datetime import timedelta
from pathlib import Path

import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import matplotlib.ticker as mticker


HISTORY_CSV = Path("rank_history.csv")
OUT_DIR = Path("rank_plots")
OUT_DAILY_DIR = OUT_DIR / "daily"

HOURS_WINDOW = 24
MAJOR_HOUR_INTERVAL = 3
MINOR_HOUR_INTERVAL = 1


def safe_filename(name: str) -> str:
    s = re.sub(r"[\\/:*?\"<>|]", "_", str(name))
    s = s.strip()
    return s if s else "noname"


def normalize_rank_to_int(series: pd.Series) -> pd.Series:
    s = series.astype(str).str.strip()
    s = s.replace({
        "": pd.NA,
        "nan": pd.NA,
        "None": pd.NA,
        "圏外": pd.NA,
        "-": pd.NA,
        "―": pd.NA,
        "—": pd.NA,
    })
    x = pd.to_numeric(s, errors="coerce")
    return x.round(0)


def pick_col(df: pd.DataFrame, candidates):
    for c in candidates:
        if c in df.columns:
            return c
    return None


def fmt_jp_range(start_dt, end_dt) -> str:
    return (
        f"{start_dt.month}月{start_dt.day}日 {start_dt.hour:02d}時 → "
        f"{end_dt.month}月{end_dt.day}日 {end_dt.hour:02d}時 ({HOURS_WINDOW}時間推移)"
    )


def ensure_dirs():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    OUT_DAILY_DIR.mkdir(parents=True, exist_ok=True)


def plot_one_shop(shop: str, d: pd.DataFrame, date_col: str, rank_int_col: str):
    if d[rank_int_col].notna().sum() == 0:
        return

    end_dt = d[date_col].dropna().max()
    if pd.isna(end_dt):
        return
    if hasattr(end_dt, "to_pydatetime"):
        end_dt = end_dt.to_pydatetime()

    start_dt = end_dt - timedelta(hours=HOURS_WINDOW)

    dd = d[(d[date_col] >= start_dt) & (d[date_col] <= end_dt)].copy()

    if dd.empty or dd[rank_int_col].notna().sum() == 0:
        dd = d.tail(200).copy()
        if dd.empty or dd[rank_int_col].notna().sum() == 0:
            return

    y = dd[rank_int_col].dropna()
    if y.empty:
        return

    best = int(y.min())
    worst = int(y.max())
    current = int(y.iloc[-1])

    plt.figure(figsize=(12.5, 5.2))
    ax = plt.gca()

    ax.plot(dd[date_col], dd[rank_int_col], marker="o", linewidth=2)

    # y軸は整数表示
    ax.yaxis.set_major_locator(mticker.MaxNLocator(integer=True))
    ax.yaxis.set_major_formatter(mticker.StrMethodFormatter("{x:.0f}"))

    # 1位を上に固定
    pad = 1
    top_y = max(1, best - pad)
    bottom_y = worst + pad
    ax.set_ylim(bottom_y, top_y)

    # x軸は直近24時間
    ax.set_xlim(start_dt, end_dt)
    ax.xaxis.set_major_locator(mdates.HourLocator(interval=MAJOR_HOUR_INTERVAL))
    ax.xaxis.set_minor_locator(mdates.HourLocator(interval=MINOR_HOUR_INTERVAL))
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%m/%d %H:%M"))
    plt.xticks(rotation=30, ha="right")

    ax.set_xlabel("時刻")
    ax.set_ylabel("順位")
    ax.set_title(shop, fontsize=22, pad=18)

    plt.gcf().text(
        0.01, 0.98,
        fmt_jp_range(start_dt, end_dt),
        ha="left", va="top", fontsize=12
    )

    plt.gcf().text(
        0.99, 0.98,
        f"Best: {best}位   Worst: {worst}位   Now: {current}位",
        ha="right", va="top", fontsize=12
    )

    ax.grid(True, linestyle="--", alpha=0.35)
    plt.tight_layout(rect=[0, 0, 1, 0.95])

    out_name = safe_filename(shop) + ".png"
    out_path = OUT_DIR / out_name
    daily_path = OUT_DAILY_DIR / out_name

    plt.savefig(out_path, dpi=150)
    plt.savefig(daily_path, dpi=150)
    plt.close()


def main():
    ensure_dirs()

    if not HISTORY_CSV.exists():
        print(f"ERROR: {HISTORY_CSV} not found")
        raise SystemExit(1)

    df = pd.read_csv(HISTORY_CSV)

    shop_col = pick_col(df, ["shop_name", "shop", "name"])
    date_col = pick_col(df, ["datetime", "date", "timestamp"])
    rank_col = pick_col(df, ["rank", "ranking"])

    if shop_col is None or date_col is None or rank_col is None:
        print("ERROR: required columns not found. columns =", list(df.columns))
        raise SystemExit(1)

    df[date_col] = pd.to_datetime(df[date_col], errors="coerce")
    df["_rank_int"] = normalize_rank_to_int(df[rank_col])
    df = df.dropna(subset=[date_col])

    shops = df[shop_col].dropna().unique()
    for shop in shops:
        d = df[df[shop_col] == shop].sort_values(date_col).copy()
        plot_one_shop(str(shop), d, date_col, "_rank_int")

    print("OK: rank_plots generated (plot_rank_per_shop.py)")


if __name__ == "__main__":
    main()