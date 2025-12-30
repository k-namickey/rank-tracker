#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import pandas as pd
import matplotlib.pyplot as plt
import matplotlib
from datetime import datetime
from pathlib import Path

# ===== 日本語フォント指定（macOS標準）=====
matplotlib.rcParams["font.family"] = "Hiragino Sans"

# ===== パス設定 =====
BASE = Path(__file__).resolve().parent
DATA_CSV = BASE / "rank_history.csv"
OUT_DIR = BASE / "public" / "summary"
OUT_DIR.mkdir(parents=True, exist_ok=True)
OUT_PNG = OUT_DIR / "summary_today.png"

AREA_NAME = "静岡エリア"

# ===== CSV 読み込み =====
df = pd.read_csv(DATA_CSV, encoding="utf-8")

# ===== 日時列 自動検出 =====
time_col = None
for c in df.columns:
    if "time" in c.lower() or "date" in c.lower():
        time_col = c
        break
if time_col is None:
    time_col = df.columns[0]

df[time_col] = pd.to_datetime(df[time_col], errors="coerce")
df = df.dropna(subset=[time_col])

# ===== 順位列 自動検出 =====
rank_col = None
for c in df.columns:
    if pd.api.types.is_numeric_dtype(df[c]):
        rank_col = c
        break
if rank_col is None:
    raise RuntimeError("順位列を特定できません")

# ===== 最新時刻の行 =====
latest_time = df[time_col].max()
latest_rows = df[df[time_col] == latest_time]

# ===== 店名列 推定 =====
shop_col = None
for c in df.columns:
    if c != rank_col and df[c].dtype == object:
        shop_col = c
        break
if shop_col is None:
    raise RuntimeError("店名列を特定できません")

# ===== 対象店舗（最新データの先頭）=====
target_shop = latest_rows.iloc[0][shop_col]
shop_df = df[df[shop_col] == target_shop].sort_values(time_col)

# ===== 数値算出 =====
now_rank = int(shop_df.iloc[-1][rank_col])
prev_rank = int(shop_df.iloc[-2][rank_col]) if len(shop_df) > 1 else now_rank
delta_now = now_rank - prev_rank

best_rank = int(shop_df[rank_col].min())
worst_rank = int(shop_df[rank_col].max())

# ===== 過去24時間 =====
last_time = shop_df[time_col].max()
last24 = shop_df[shop_df[time_col] >= last_time - pd.Timedelta(hours=24)]

# ===== 描画 =====
plt.figure(figsize=(8, 6))
plt.axis("off")

# タイトル
plt.text(0.01, 0.95, f"Rank Summary（{AREA_NAME}）", fontsize=14, weight="bold")
plt.text(0.01, 0.90, datetime.now().strftime("%Y-%m-%d %H:%M"), fontsize=9)

# 店名
plt.text(0.01, 0.82, f"店舗: {target_shop}", fontsize=11)

# 数値
plt.text(0.01, 0.74, f"Now:    {now_rank}位  ({delta_now:+d})", fontsize=12)
plt.text(0.01, 0.68, f"Best:   {best_rank}位", fontsize=11)
plt.text(0.01, 0.62, f"Worst:  {worst_rank}位", fontsize=11)

# ミニグラフ
ax = plt.axes([0.05, 0.15, 0.9, 0.4])
ax.plot(last24[time_col], last24[rank_col], linewidth=2)
ax.invert_yaxis()
ax.set_xticks([])
ax.set_yticks([])
ax.set_title("Last 24 Hours", fontsize=10)

# 保存
plt.savefig(OUT_PNG, dpi=150, bbox_inches="tight")
plt.close()

print(f"Generated: {OUT_PNG}")
