# -*- coding: utf-8 -*-
import os
import re
from datetime import timedelta

import pandas as pd
import matplotlib.pyplot as plt
import matplotlib as mpl
from matplotlib.ft2font import FT2Font
from matplotlib.font_manager import FontProperties, fontManager

# =========================
# フォント：固定（推奨順）
# =========================
CANDIDATE_FONT_FILES = [
    "/Library/Fonts/IPAexGothic.ttf",
    "/System/Library/Fonts/Supplemental/IPAexGothic.ttf",
    "/System/Library/Fonts/Supplemental/Hiragino Sans GB.ttc",
    "/System/Library/Fonts/Hiragino Sans.ttc",
    "/System/Library/Fonts/Supplemental/Arial Unicode.ttf",
]

def pick_font_file():
    for p in CANDIDATE_FONT_FILES:
        if os.path.exists(p):
            return p
    return None

FONT_FILE = pick_font_file()

FONT_PROP = None
_font_checker = None

if FONT_FILE:
    print("Using font file:", FONT_FILE)
    try:
        # Matplotlib にフォントを登録して明示使用
        fontManager.addfont(FONT_FILE)
    except Exception:
        pass

    try:
        FONT_PROP = FontProperties(fname=FONT_FILE)
    except Exception:
        FONT_PROP = None

    try:
        _font_checker = FT2Font(FONT_FILE)
    except Exception:
        _font_checker = None
else:
    print("WARN: font file not found. Use matplotlib default font.")

mpl.rcParams["axes.unicode_minus"] = False

# rc側にも一応入れておく（保険）
if FONT_PROP is not None:
    try:
        mpl.rcParams["font.family"] = FONT_PROP.get_name()
    except Exception:
        pass


# =========================================================
# 指定フォントが「その文字」を持っているかチェックして置換
# =========================================================
def font_has_char(ch: str) -> bool:
    if not _font_checker:
        return True
    try:
        return _font_checker.get_char_index(ord(ch)) != 0
    except Exception:
        return True


def normalize_text(text: str) -> str:
    if text is None:
        return ""
    s = str(text)

    # よく問題になる記号を安全側に寄せる
    s = s.replace("～", "〜")
    s = s.replace("♡", "♥")

    # フォント未対応文字は「□」に置換
    if _font_checker:
        out = []
        for ch in s:
            if ch == "\n":
                out.append(ch)
            else:
                out.append(ch if font_has_char(ch) else "□")
        s = "".join(out)

    return s


# ===== データ読み込み =====
df = pd.read_csv("rank_history.csv")
df["datetime"] = pd.to_datetime(df["datetime"], errors="coerce")
df["rank"] = pd.to_numeric(df["rank"], errors="coerce")
df = df.dropna(subset=["datetime", "rank", "shop_name"]).copy()
df["rank"] = df["rank"].astype(int)

# ===== 出力先 =====
out_dir = "rank_text"
os.makedirs(out_dir, exist_ok=True)


def safe_filename(name):
    return re.sub(r'[\\/:*?"<>|]', "_", str(name))[:120]


# ===== フォントサイズ =====
TITLE_SIZE = 42
HEADER_SIZE = 32
TEXT_SIZE = 30


# ===== 店舗ごと =====
for shop, g in df.groupby("shop_name"):
    g = g.sort_values("datetime")

    last_time = g["datetime"].max()
    g24 = g[g["datetime"] >= last_time - timedelta(hours=24)].copy()
    if g24.empty:
        continue

    now = int(g24.iloc[-1]["rank"])
    best_d = int(g24["rank"].min())
    worst_d = int(g24["rank"].max())

    last_dt = g["datetime"].max()
    monday = (last_dt - timedelta(days=last_dt.weekday())).replace(
        hour=0, minute=0, second=0, microsecond=0
    )

    gw = g[g["datetime"] >= monday]
    if not gw.empty:
        best_w = int(gw["rank"].min())
        worst_w = int(gw["rank"].max())
        weekly_lines = [f"最高 {best_w}位", f"最低 {worst_w}位"]
    else:
        weekly_lines = ["データなし"]

    g7 = g[g["datetime"] >= last_dt - timedelta(days=7)]
    if not g7.empty:
        best_7 = int(g7["rank"].min())
        worst_7 = int(g7["rank"].max())
        last7_lines = [f"最高 {best_7}位", f"最低 {worst_7}位"]
    else:
        last7_lines = ["データなし"]

    # ===== 描画 =====
    fig = plt.figure(figsize=(6, 10))
    plt.axis("off")

    y = 0.95
    line_h = 0.075

    def draw(text, y, size=TEXT_SIZE, weight="normal"):
        kwargs = dict(
            x=0.5,
            y=y,
            s=normalize_text(text),
            ha="center",
            va="top",
            fontsize=size,
            fontweight=weight,
        )
        if FONT_PROP is not None:
            kwargs["fontproperties"] = FONT_PROP
        plt.text(**kwargs)

    draw(shop, y, size=TITLE_SIZE, weight="bold")
    y -= line_h * 1.5

    draw("当日", y, size=HEADER_SIZE, weight="bold")
    y -= line_h
    draw(f"最高 {best_d}位", y)
    y -= line_h
    draw(f"最低 {worst_d}位", y)
    y -= line_h
    draw(f"現在 {now}位", y, weight="bold")
    y -= line_h * 1.4

    draw("今週（月曜〜日曜）", y, size=HEADER_SIZE, weight="bold")
    y -= line_h
    for t in weekly_lines:
        draw(t, y)
        y -= line_h

    y -= line_h * 0.8

    draw("直近7日", y, size=HEADER_SIZE, weight="bold")
    y -= line_h
    for t in last7_lines:
        draw(t, y)
        y -= line_h

    plt.savefig(
        os.path.join(out_dir, safe_filename(shop) + ".png"),
        dpi=150,
        bbox_inches="tight"
    )
    plt.close()

print("OK: rank_text generated")