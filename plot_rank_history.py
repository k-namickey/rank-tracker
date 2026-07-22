# -*- coding: utf-8 -*-
"""
rank_log.csv から
・全店舗まとめて
・直近10回分の順位推移
を折れ線グラフ（PNG）で出力する
"""

import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path

# ===== 設定 =====
CSV_PATH = Path("rank_log.csv")
OUT_PNG  = Path("rank_last10_allshops.png")
LAST_N   = 10

# macOS 日本語フォント（文字化け防止）
plt.rcParams["font.family"] = "Hiragino Sans"

# ===== CSV 読み込み =====
df = pd.read_csv(CSV_PATH)

# 列名を内部用に正規化
df = df.rename(columns={
    "店舗名": "shop_name",
    "_converted_at": "datetime"
})

# 必須列チェック
required = {"datetime", "shop_name", "rank"}
missing = required - set(df.columns)
if missing:
    raise RuntimeError(f"CSVに必要な列がありません: {missing}")

# datetime を datetime 型に
df["datetime"] = pd.to_datetime(df["datetime"], errors="coerce")

# rank を数値化（念のため）
df["rank"] = pd.to_numeric(df["rank"], errors="coerce")

# ===== 直近 N 回に絞る =====
df = (
    df.dropna(subset=["datetime", "rank"])
      .sort_values("datetime")
      .groupby("shop_name", as_index=False)
      .tail(LAST_N)
)

# ===== プロット =====
plt.figure(figsize=(14, 8))

for shop, g in df.groupby("shop_name"):
    plt.plot(
        g["datetime"],
        g["rank"],
        marker="o",
        linewidth=1,
        alpha=0.9,
        label=shop
    )

# 順位なので上下反転（1位が上）
plt.gca().invert_yaxis()

plt.title("直近10回の順位推移（全店舗）")
plt.xlabel("日時")
plt.ylabel("順位")
plt.grid(True, alpha=0.3)

plt.legend(
    bbox_to_anchor=(1.02, 1),
    loc="upper left",
    fontsize=9
)

plt.tight_layout()
plt.savefig(OUT_PNG, dpi=150)
plt.close()

print(f"OK: 折れ線グラフを生成しました → {OUT_PNG}")
