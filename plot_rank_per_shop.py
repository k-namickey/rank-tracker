import os
import re
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib as mpl

mpl.rcParams["font.family"] = "sans-serif"
mpl.rcParams["font.sans-serif"] = [
    "Hiragino Sans",
    "Hiragino Kaku Gothic ProN",
    "Yu Gothic",
    "Meiryo",
    "Noto Sans CJK JP",
    "IPAexGothic",
    "IPAGothic"
]
mpl.rcParams["axes.unicode_minus"] = False

df = pd.read_csv("rank_history.csv")
df["datetime"] = pd.to_datetime(df["datetime"])

df["rank"] = pd.to_numeric(df["rank"], errors="coerce")
df = df.dropna(subset=["rank"]).copy()
df["rank"] = df["rank"].astype(int)

out_dir = "rank_plots"
os.makedirs(out_dir, exist_ok=True)

def safe_filename(name):
    return re.sub(r'[\\/:*?"<>|]', "_", str(name))[:120]

for shop, g in df.groupby("shop_name"):
    g = g.sort_values("datetime")

    plt.figure(figsize=(8, 4))
    plt.plot(g["datetime"], g["rank"], marker="o")
    ax = plt.gca()
    ax.invert_yaxis()
    ax.set_yticks(range(int(g["rank"].min()), int(g["rank"].max()) + 1))

    plt.title(shop)
    plt.xlabel("Time")
    plt.ylabel("Rank")
    plt.grid(True)
    plt.tight_layout()

    plt.savefig(os.path.join(out_dir, safe_filename(shop) + ".png"), dpi=150)
    plt.close()
