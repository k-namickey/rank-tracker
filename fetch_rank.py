# -*- coding: utf-8 -*-
import csv
import os
import re
import time
import random
import tempfile
from datetime import datetime

import requests
import pandas as pd
from bs4 import BeautifulSoup

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Google Sheets 公開CSV
MASTER_CSV_URL = (
    "https://docs.google.com/spreadsheets/d/"
    "1cJd0AkbbV_8G6mQJQ0pn-Sib4ZuoMVT2ALuucilKt6k"
    "/export?format=csv"
)

# 出力
HISTORY_CSV = os.path.join(BASE_DIR, "rank_history.csv")
LATEST_CSV  = os.path.join(BASE_DIR, "rank_latest.csv")

# 二重起動防止（1時間更新で重要）
LOCK_PATH = os.path.join(BASE_DIR, ".fetch_rank.lock")

UUID_PAT = re.compile(r"/shop-detail/([0-9a-f\-]{36})/", re.I)
RANK_PAT = re.compile(r"^\s*(\d+)\s*位\s*$")
RANK_IN_TEXT_PAT = re.compile(r"(\d+)\s*位")  # フォールバックで「順位表記がある近傍」を判定


def extract_uuid(shop_url: str):
    m = UUID_PAT.search(shop_url or "")
    return m.group(1).lower() if m else None


def _extract_rank_from_container(tag):
    """
    店舗カードっぽい親要素の中から「○位」を探して int で返す。
    画像 alt="1位" も、テキスト "4位" も拾えるようにする。
    """
    # 1) 画像 alt="1位" 形式
    for img in tag.find_all("img"):
        alt = (img.get("alt") or "").strip()
        m = RANK_PAT.match(alt)
        if m:
            return int(m.group(1))

    # 2) テキストで "4位" のように出ているケース
    for s in tag.stripped_strings:
        s = s.strip()
        if len(s) > 12:
            continue
        m = RANK_PAT.match(s)
        if m:
            return int(m.group(1))

    return None


def _container_shop_uuids(tag):
    """このコンテナ内に含まれる shop-detail uuid を集合で返す"""
    uuids = set()
    for a in tag.find_all("a", href=True):
        href = a.get("href") or ""
        m = UUID_PAT.search(href)
        if m:
            uuids.add(m.group(1).lower())
    return uuids


def _has_rank_text_nearby(tag) -> bool:
    """
    フォールバック用：
    「このコンテナはランキングカード近傍か？」を雑に判定。
    どこかに '○位' が含まれていれば True。
    """
    try:
        txt = tag.get_text(" ", strip=True)
    except Exception:
        return False
    if not txt:
        return False
    return bool(RANK_IN_TEXT_PAT.search(txt))


def _download_html(rank_url: str) -> str:
    """
    キャッシュバスター + no-cache ヘッダでHTML取得
    """
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome Safari/537.36"
        ),
        "Cache-Control": "no-cache",
        "Pragma": "no-cache",
    }

    bust = int(time.time() * 1000)
    sep = "&" if "?" in rank_url else "?"
    url = f"{rank_url}{sep}t={bust}"

    r = requests.get(url, headers=headers, timeout=30)
    r.raise_for_status()
    return r.text


def _fetch_rank_map_by_rank_text(soup: BeautifulSoup, rank_url: str):
    """
    旧方式（順位表記から拾う）：
    a → 親へ遡る → 「○位」を拾う。ただし “1位量産” 対策として
    「そのコンテナ内のuuidが1〜2件」のときだけ採用。
    """
    uuid_best = {}

    for a in soup.find_all("a", href=True):
        href = a.get("href") or ""
        m = UUID_PAT.search(href)
        if not m:
            continue

        uid = m.group(1).lower()

        found_rank = None
        found_score = None

        cur = a
        for depth in range(1, 9):  # 1..8
            if cur is None:
                break

            rnk = _extract_rank_from_container(cur)
            if rnk is None:
                cur = cur.parent if hasattr(cur, "parent") else None
                continue

            uuids_in = _container_shop_uuids(cur)
            if uid not in uuids_in:
                cur = cur.parent if hasattr(cur, "parent") else None
                continue

            # ★肝：uuidが多いコンテナはランキング全体/別ブロックの可能性が高いので捨てる
            if len(uuids_in) > 2:
                cur = cur.parent if hasattr(cur, "parent") else None
                continue

            score = (len(uuids_in), depth)
            found_rank = rnk
            found_score = score
            break

        if found_rank is None:
            continue

        if uid in uuid_best:
            old_rank, old_score = uuid_best[uid]
            if found_score < old_score:
                uuid_best[uid] = (found_rank, found_score)
        else:
            uuid_best[uid] = (found_rank, found_score)

    uuid_to_rank = {uid: rk for uid, (rk, _sc) in uuid_best.items()}

    # 同一rankの数をチェック
    rank_to_uids = {}
    for uid, rk in uuid_to_rank.items():
        rank_to_uids.setdefault(rk, []).append(uid)

    dup1 = len(rank_to_uids.get(1, []))
    any_dup = any(len(v) >= 2 for v in rank_to_uids.values())

    return uuid_to_rank, dup1, any_dup


def _fetch_rank_map_by_dom_order(soup: BeautifulSoup, rank_url: str):
    """
    フォールバック方式（最強）：
    “順位表記を信じない”。ランキングカードの並び（DOM順）で 1.. を割り当てる。

    ノイズ除去のための条件：
      - /shop-detail/ の <a> であること
      - その <a> から親へ数階層遡ったどこかに「○位」が含まれる（＝ランキングの近傍）
        ※ これでヘッダ/フッタ/関連記事の shop-detail をかなり除外できる
      - 同一uuidは最初に出た位置だけ採用

    これにより「同一エリアで1位が複数」や「違っているところが全部1位」を強制的に止める。
    """
    ordered = []
    seen = set()

    for a in soup.find_all("a", href=True):
        href = a.get("href") or ""
        m = UUID_PAT.search(href)
        if not m:
            continue
        uid = m.group(1).lower()
        if uid in seen:
            continue

        # 近傍に「○位」があるか（ランキングカード近傍判定）
        cur = a
        ok = False
        for _ in range(7):
            if cur is None:
                break
            if _has_rank_text_nearby(cur):
                ok = True
                break
            cur = cur.parent if hasattr(cur, "parent") else None

        if not ok:
            continue

        seen.add(uid)
        ordered.append(uid)

    uuid_to_rank = {uid: i + 1 for i, uid in enumerate(ordered)}

    # ログ用
    if len(ordered) == 0:
        print("  [WARN] DOM順フォールバックでも0件。URL:", rank_url)

    return uuid_to_rank


def fetch_rank_map(rank_url: str):
    """
    ランキングページから uuid -> rank を取得する（安定版）

    1) まず “順位表記から拾う” 方式で取る
    2) そこで「1位が複数」などの異常兆候が出たら、
       “DOM順で1..を割り当てる” フォールバックに切り替える
    """
    html = _download_html(rank_url)
    soup = BeautifulSoup(html, "html.parser")

    # まず通常方式
    uuid_to_rank, dup1, any_dup = _fetch_rank_map_by_rank_text(soup, rank_url)

    # ここが判断基準：
    #  - 1位が2つ以上 → あなたの症状そのものなので即フォールバック
    #  - 何らかの重複順位がある → フォールバック
    #  - 取得件数が少なすぎる → フォールバック（または空を返すよりマシ）
    if dup1 >= 2 or any_dup or len(uuid_to_rank) < 5:
        print("  [SWITCH] 取得が不安定（1位重複/重複順位/件数不足）。DOM順方式へ切替:", rank_url)
        uuid_to_rank2 = _fetch_rank_map_by_dom_order(soup, rank_url)

        # DOM順でも極端に少ないなら、通常方式の方がまだマシな場合があるので比較
        if len(uuid_to_rank2) >= len(uuid_to_rank):
            uuid_to_rank = uuid_to_rank2

    return uuid_to_rank


def load_master_rows():
    """Google Sheets を読み込む"""
    df = pd.read_csv(MASTER_CSV_URL)

    required = {"z", "店舗名", "area", "rank_url", "shop_url"}
    if not required.issubset(df.columns):
        raise RuntimeError(
            f"Google Sheets に必要な列がありません\n"
            f"必要: {required}\n実際: {list(df.columns)}"
        )

    return df.to_dict(orient="records")


def ensure_history_header():
    if os.path.exists(HISTORY_CSV):
        return
    with open(HISTORY_CSV, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        # 履歴は従来どおり 5列（他スクリプト互換のため）
        w.writerow(["datetime", "shop_id", "shop_name", "area", "rank"])


def atomic_write_csv(path: str, header: list, rows: list):
    """テンポラリに書いて最後に置換（途中で落ちてもファイル破損しない）"""
    tmp_dir = os.path.dirname(path)
    fd, tmp_path = tempfile.mkstemp(prefix=".tmp_", suffix=".csv", dir=tmp_dir)
    try:
        with os.fdopen(fd, "w", encoding="utf-8-sig", newline="") as f:
            w = csv.writer(f)
            w.writerow(header)
            for row in rows:
                w.writerow(row)
        os.replace(tmp_path, path)  # atomic
    finally:
        if os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
            except Exception:
                pass


def acquire_lock():
    """二重起動防止（1時間更新で重要）"""
    if os.path.exists(LOCK_PATH):
        age = time.time() - os.path.getmtime(LOCK_PATH)
        if age < 60 * 55:
            print("[LOCK] すでに実行中の可能性があるため中止:", LOCK_PATH)
            return False
        else:
            print("[LOCK] 古いロックを検出。回収して続行します:", int(age), "sec")
            try:
                os.remove(LOCK_PATH)
            except Exception:
                pass

    with open(LOCK_PATH, "w", encoding="utf-8") as f:
        f.write(str(os.getpid()))
    return True


def release_lock():
    try:
        if os.path.exists(LOCK_PATH):
            os.remove(LOCK_PATH)
    except Exception:
        pass


def main():
    if not acquire_lock():
        return

    start = time.time()
    try:
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
                uuid_to_rank = fetch_rank_map(url)
                url_to_uuid_to_rank[url] = uuid_to_rank
                if len(uuid_to_rank) < 5:
                    print("  [WARN] 取得件数が少なすぎます:", len(uuid_to_rank))
            except Exception as e:
                print("  [ERROR]", url, e)
                url_to_uuid_to_rank[url] = {}

            time.sleep(0.7 + random.random() * 0.6)

        # 今回取得分（最新）
        latest_rows_dict = []
        ok_count = 0

        for r in rows:
            shop_id = (r.get("z") or "").strip()
            shop_name = (r.get("店舗名") or "").strip()
            area = (r.get("area") or "").strip()
            rank_url = (r.get("rank_url") or "").strip()
            shop_url = (r.get("shop_url") or "").strip()

            uid = extract_uuid(shop_url) or (shop_id.lower() if shop_id else None)

            rank = None
            if rank_url and uid:
                rank = url_to_uuid_to_rank.get(rank_url, {}).get(uid)

            if rank is not None:
                ok_count += 1

            latest_rows_dict.append({
                "datetime": now,
                "shop_id": shop_id,
                "shop_name": shop_name,
                "area": area,
                "rank": rank if rank is not None else "",
                "rank_url": rank_url
            })

        # 不安定回で latest を壊さない（全体共有の事故防止）
        total = len(rows)
        coverage = ok_count / total if total else 0.0
        empty_urls = [u for u, mp in url_to_uuid_to_rank.items() if not mp]

        MIN_COVERAGE = 0.75
        if coverage < MIN_COVERAGE or empty_urls:
            print("[ABORT] 今回は取得が不安定と判断。rank_latest.csv を更新しません。")
            print("  coverage:", round(coverage * 100, 1), "%  ok/total:", ok_count, "/", total)
            if empty_urls:
                print("  empty rank_url:", len(empty_urls))
            return

        # 1) 履歴CSVに追記（5列）
        ensure_history_header()
        with open(HISTORY_CSV, "a", encoding="utf-8-sig", newline="") as f:
            w = csv.writer(f)
            for x in latest_rows_dict:
                w.writerow([x["datetime"], x["shop_id"], x["shop_name"], x["area"], x["rank"]])

        # 2) 最新CSV（6列）を atomic 更新
        latest_rows = [
            [x["datetime"], x["shop_id"], x["shop_name"], x["area"], x["rank"], x["rank_url"]]
            for x in latest_rows_dict
        ]
        atomic_write_csv(
            LATEST_CSV,
            header=["datetime", "shop_id", "shop_name", "area", "rank", "rank_url"],
            rows=latest_rows
        )

        elapsed = time.time() - start
        print(
            "OK: 履歴追記 →",
            os.path.basename(HISTORY_CSV),
            "/ 最新更新 →",
            os.path.basename(LATEST_CSV),
            f"({elapsed:.1f}s)",
            "coverage:",
            f"{coverage*100:.1f}%"
        )

    finally:
        release_lock()


if __name__ == "__main__":
    main()
