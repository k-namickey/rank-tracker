# -*- coding: utf-8 -*-
import csv
import os
import re
import time
from datetime import datetime

import requests
from bs4 import BeautifulSoup

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# 入力（店舗マスター）
MASTER_CSV = os.path.join(BASE_DIR, "rank_log.csv")

# 出力（履歴）
HISTORY_CSV = os.path.join(BASE_DIR, "rank_history.csv")

# 出力（最新だけ）
LATEST_CSV = os.path.join(BASE_DIR, "rank_latest.csv")

UUID_PAT = re.compile(r"/shop-detail/([0-9a-f\-]{36})/", re.I)


def extract_uuid(shop_url: str):
    m = UUID_PAT.search(shop_url or "")
    return m.group(1).lower() if m else None


def fetch_rank_list(rank_url: str):
    """ランキングページから uuid を順位順で取得"""
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome Safari/537.36"
        )
    }
    r = requests.get(rank_url, headers=headers, timeout=30)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "html.parser")

    seen = set()
    ordered = []
    for a in soup.select('a[href*="/shop-detail/"]'):
        href = a.get("href") or ""
        m = UUID_PAT.search(href)
        if not m:
            continue
        u = m.group(1).lower()
        if u in seen:
            continue
        seen.add(u)
        ordered.append(u)

    return ordered


def load_master_rows():
    """rank_log.csv を読み込む"""
    with open(MASTER_CSV, "r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    required = {"shop_id", "店舗名", "area", "rank_url", "shop_url"}
    if not rows or not required.issubset(rows[0].keys()):
        raise RuntimeError(
            f"MASTER_CSV に必要な列がありません\n"
            f"必要: {required}\n実際: {list(rows[0].keys()) if rows else 'empty'}"
        )

    return rows


def ensure_history_header():
    if os.path.exists(HISTORY_CSV):
        return
    with open(HISTORY_CSV, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(["datetime", "shop_id", "shop_name", "area", "rank"])


def main():
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    rows = load_master_rows()

    # rank_url ごとに一括取得
    unique_rank_urls = []
    for r in rows:
        url = (r.get("rank_url") or "").strip()
        if url and url not in unique_rank_urls:
            unique_rank_urls.append(url)

    url_to_uuid_to_rank = {}

    for url in unique_rank_urls:
        print("取得中:", url)
        try:
            uuids = fetch_rank_list(url)
            url_to_uuid_to_rank[url] = {u: i + 1 for i, u in enumerate(uuids)}
        except Exception as e:
            print("  [ERROR]", url, e)
            url_to_uuid_to_rank[url] = {}

        time.sleep(0.5)

    # 今回取得分（最新）
    latest_rows = []
    for r in rows:
        shop_id = (r.get("shop_id") or "").strip()
        shop_name = (r.get("店舗名") or "").strip()
        area = (r.get("area") or "").strip()
        rank_url = (r.get("rank_url") or "").strip()
        shop_url = (r.get("shop_url") or "").strip()

        uid = extract_uuid(shop_url) or shop_id.lower()
        rank = None
        if rank_url:
            rank = url_to_uuid_to_rank.get(rank_url, {}).get(uid)

        latest_rows.append({
            "datetime": now,
            "shop_id": shop_id,
            "shop_name": shop_name,
            "area": area,
            "rank": rank if rank is not None else ""
        })

    # 1) 履歴CSVに追記
    ensure_history_header()
    with open(HISTORY_CSV, "a", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        for x in latest_rows:
            w.writerow([x["datetime"], x["shop_id"], x["shop_name"], x["area"], x["rank"]])

    # 2) 最新CSVを上書き
    with open(LATEST_CSV, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(["datetime", "shop_id", "shop_name", "area", "rank"])
        for x in latest_rows:
            w.writerow([x["datetime"], x["shop_id"], x["shop_name"], x["area"], x["rank"]])

    print(
        "OK: 履歴追記 →",
        os.path.basename(HISTORY_CSV),
        "/ 最新更新 →",
        os.path.basename(LATEST_CSV),
    )


if __name__ == "__main__":
    main()
