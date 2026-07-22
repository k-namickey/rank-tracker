#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
make_rank_plots.py
- rank_history.csv を読み、店舗ごとの順位推移PNGを生成
- 毎回 rank_plots を掃除して「古いPNGが残る問題」を根絶
- 日次（直近7日）は rank_plots/daily/ に出す（※ rank_plots_daily は廃止）
- データ点が1件でもPNGを生成
- 日本語フォントを自動で探して設定（見つからなければ警告）
- 1位が上に来るように y軸を反転
- y軸目盛りを「整数のみ」に固定（小数表示を根絶）
- 日付目盛りを抑えて MAXTICKS を回避
"""

from __future__ import annotations

import os
import re
from pathlib import Path
from datetime import timedelta

import pandas as pd

# --- Matplotlib設定をここで固定（update_rank.command 経由でなくても効く） ---
SCRIPT_DIR = Path(__file__).resolve().parent
os.environ.setdefault("MPLCONFIGDIR", str(SCRIPT_DIR / ".mplconfig"))

import matplotlib
matplotlib.use("Agg")  # GUI不要
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.dates import ConciseDateFormatter
from matplotlib import font_manager
import matplotlib.ticker as mticker


def pick_japanese_font() -> str | None:
    candidates = [
        "Hiragino Sans",
        "Hiragino Kaku Gothic ProN",
        "Hiragino Kaku Gothic Pro",
        "Yu Gothic",
        "YuGothic",
        "AppleGothic",
        "Noto Sans CJK JP",
        "Noto Sans JP",
        "IPAexGothic",
        "IPAPGothic",
        "TakaoGothic",
    ]
    available = {f.name for f in font_manager.fontManager.ttflist if f.name}
    for name in candidates:
        if name in available:
            return name
    return None


def safe_filename(name: str) -> str:
    name = name.strip()
    name = name.replace("/", "／").replace("\\", "＼")
    name = re.sub(r'[:*?"<>|]', "_", name)
    return name


def load_history(csv_path: Path) -> pd.DataFrame:
    if not csv_path.exists():
        raise SystemExit(f"ERROR: {csv_path} not found")

    df = pd.read_csv(csv_path)

    need = {"datetime", "shop_name", "rank"}
    if not need.issubset(df.columns):
        raise SystemExit(f"ERROR: columns={list(df.columns)}")

    df["datetime"] = pd.to_datetime(df["datetime"], errors="coerce")
    df = df.dropna(subset=["datetime"])

    df["rank"] = pd.to_numeric(df["rank"], errors="coerce")
    df = df.dropna(subset=["rank"])
    df["rank"] = df["rank"].astype(int)

    df["shop_name"] = df["shop_name"].astype(str)

    # 同一タイムスタンプ同一店舗の重複を消す（最後を採用）
    df = df.sort_values(["datetime", "shop_name"]).drop_duplicates(
        subset=["datetime", "shop_name"], keep="last"
    )

    return df.reset_index(drop=True)


def clean_png_dir(d: Path) -> None:
    d.mkdir(parents=True, exist_ok=True)
    for p in d.glob("*.png"):
        try:
            p.unlink()
        except Exception:
            pass


def make_plot_for_shop(df_shop: pd.DataFrame, out_path: Path, title: str) -> None:
    locator = mdates.AutoDateLocator(minticks=3, maxticks=8)
    formatter = ConciseDateFormatter(locator)

    fig = plt.figure(figsize=(10, 5), dpi=150)
    ax = fig.add_subplot(111)

    ax.plot(df_shop["datetime"], df_shop["rank"], marker="o", linewidth=2)

    ax.set_title(title)
    ax.set_xlabel("日時")
    ax.set_ylabel("順位")

    ax.xaxis.set_major_locator(locator)
    ax.xaxis.set_major_formatter(formatter)

    # 小数表示を根絶（y軸は整数目盛りのみ）
    ax.yaxis.set_major_locator(mticker.MultipleLocator(1))
    ax.yaxis.set_major_formatter(mticker.FormatStrFormatter("%d"))

    # 1位が上
    ax.invert_yaxis()

    rmin = int(df_shop["rank"].min())
    rmax = int(df_shop["rank"].max())
    pad = 1
    ax.set_ylim(rmax + pad, max(1, rmin - pad))

    ax.grid(True, linestyle="--", alpha=0.4)

    fig.tight_layout()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path)
    plt.close(fig)


def main() -> None:
    jp_font = pick_japanese_font()
    if jp_font:
        plt.rcParams["font.family"] = jp_font
    plt.rcParams["axes.unicode_minus"] = False

    csv_path = SCRIPT_DIR / "rank_history.csv"
    df = load_history(csv_path)

    out_dir = SCRIPT_DIR / "rank_plots"
    out_dir_daily = out_dir / "daily"   # ★統一：rank_plots/daily/

    # まず掃除
    clean_png_dir(out_dir)
    clean_png_dir(out_dir_daily)

    latest_dt = df["datetime"].max()
    daily_from = latest_dt - timedelta(days=7)
    df_daily = df[df["datetime"] >= daily_from].copy()

    shops = sorted(df["shop_name"].unique().tolist())

    for shop in shops:
        df_shop = df[df["shop_name"] == shop].sort_values("datetime")
        if len(df_shop) < 1:
            continue

        fname = safe_filename(shop) + ".png"

        make_plot_for_shop(
            df_shop,
            out_dir / fname,
            title=f"{shop} 順位推移",
        )

        df_shop_d = df_daily[df_daily["shop_name"] == shop].sort_values("datetime")
        if len(df_shop_d) >= 1:
            make_plot_for_shop(
                df_shop_d,
                out_dir_daily / fname,
                title=f"{shop}（直近7日）順位推移",
            )

    print("OK: rank_plots generated (clean rebuild)")


if __name__ == "__main__":
    main()
