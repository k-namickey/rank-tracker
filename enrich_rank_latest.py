import pandas as pd

# 入力（既存の最新ランキング）
IN_LATEST = "rank_latest.csv"

# マスター（あなたのローカルのマスターCSV）
# ※ファイル名が違うならここだけ直す
MASTER = "shop_master_utf8.csv"

# 出力（上書きする）
OUT_LATEST = "rank_latest.csv"


def main():
    latest = pd.read_csv(IN_LATEST, encoding="utf-8-sig")
    master = pd.read_csv(MASTER, encoding="utf-8-sig")

    # --- 必須列チェック ---
    if "shop_id" not in latest.columns:
        raise ValueError("rank_latest.csv に shop_id がありません。リンクを正しくするには shop_id が必須です。")

    if "shop_id" not in master.columns:
        raise ValueError("shop_master_utf8.csv に shop_id がありません。リンクを正しくするには shop_id が必須です。")

    # URL列名ゆらぎ吸収
    url_col = None
    for c in ["rank_url", "shop_url", "url"]:
        if c in master.columns:
            url_col = c
            break
    if not url_col:
        raise ValueError("マスターCSVに URL列（rank_url / shop_url / url）が見つかりません。")

    # エリアURL（任意）
    has_area_url = "area_url" in master.columns

    # --- shop_id の重複チェック（ここがズレ防止の要） ---
    if master["shop_id"].duplicated().any():
        dup = master.loc[master["shop_id"].duplicated(), "shop_id"].head(10).tolist()
        raise ValueError(f"マスターCSVの shop_id が重複しています。例: {dup}")

    # --- join（shop_idで確実に結合） ---
    cols = ["shop_id", url_col]
    if has_area_url:
        cols.append("area_url")

    merged = latest.merge(master[cols], on="shop_id", how="left")

    # NaNのURLは空に
    merged[url_col] = merged[url_col].fillna("").astype(str)
    merged[url_col] = merged[url_col].replace("nan", "").replace("NaN", "")

    if has_area_url:
        merged["area_url"] = merged["area_url"].fillna("").astype(str)
        merged["area_url"] = merged["area_url"].replace("nan", "").replace("NaN", "")

    # 列名を rank_url に統一してしまう（make_latest_view.py 側をシンプルにする）
    if url_col != "rank_url":
        merged = merged.rename(columns={url_col: "rank_url"})

    # 出力（上書き）
    merged.to_csv(OUT_LATEST, index=False, encoding="utf-8-sig")
    print("OK: rank_latest.csv を URL付きに更新しました（shop_id結合）")


if __name__ == "__main__":
    main()
