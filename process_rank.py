import os
import pandas as pd
import matplotlib
import matplotlib.pyplot as plt

# ========= 日本語フォント設定（Mac標準） =========
matplotlib.rcParams["font.family"] = "Hiragino Sans"
matplotlib.rcParams["axes.unicode_minus"] = False
# ===============================================

# ========= 設定 =========
RAW_CSV = "rank_raw.csv"
LOG_CSV = "rank_log.csv"
OUT_PNG = "rank_last10.png"
LAST_N = 10
# ========================


def main():
    raw = pd.read_csv(RAW_CSV, encoding="utf-8-sig")

    required = {"datetime", "shop_id", "shop_name", "area", "rank"}
    if not required.issubset(set(raw.columns)):
        raise ValueError("rank_raw.csv の列が不足しています")

    raw["rank"] = pd.to_numeric(raw["rank"], errors="coerce")

    if os.path.exists(LOG_CSV):
        log = pd.read_csv(LOG_CSV, encoding="utf-8-sig")
        log = pd.concat([log, raw], ignore_index=True)
    else:
        log = raw.copy()

    log["datetime"] = pd.to_datetime(log["datetime"], errors="coerce")

    log.to_csv(LOG_CSV, index=False, encoding="utf-8-sig")

    last = (
        log.sort_values("datetime")
           .groupby("shop_id", as_index=False)
           .tail(LAST_N)
    )

    plt.figure(figsize=(14, 8))

    for shop_id, g in last.groupby("shop_id"):
        g = g.sort_values("datetime")
        plt.plot(
            g["datetime"],
            g["rank"],
            marker="o",
            label=g["shop_name"].iloc[0]
        )

    plt.gca().invert_yaxis()
    plt.xlabel("日時")
    plt.ylabel("順位")
    plt.title(f"直近{LAST_N}回の順位推移（全店舗）")
    plt.legend(fontsize=8)
    plt.grid(True)
    plt.tight_layout()

    plt.savefig(OUT_PNG, dpi=150)
    plt.close()

    print(f"OK: {OUT_PNG} を生成しました（日本語フォント対応済み）")


if __name__ == "__main__":
    main()
