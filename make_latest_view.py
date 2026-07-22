#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import html
from pathlib import Path
from urllib.parse import quote
from zoneinfo import ZoneInfo

import pandas as pd


SCRIPT_DIR = Path(__file__).resolve().parent
CSV_LATEST = SCRIPT_DIR / "rank_latest.csv"
OUT_HTML = SCRIPT_DIR / "rank_latest_view.html"


def url_quote_keep_scheme(url: str) -> str:
    if not isinstance(url, str):
        return ""
    url = url.strip()
    if not url:
        return ""
    return quote(url, safe=":/?&=#%+-._~")


def file_href(path_str: str) -> str:
    if not isinstance(path_str, str):
        return ""
    path_str = path_str.strip().lstrip("./")
    return quote(path_str, safe="/-._~")


def pick_col(df: pd.DataFrame, candidates: list[str]) -> str | None:
    for c in candidates:
        if c in df.columns:
            return c
    return None


def format_latest_time_jst(df: pd.DataFrame) -> str:
    col_dt = pick_col(df, ["datetime", "timestamp", "date"])
    if col_dt is None:
        return "不明"

    dt = pd.to_datetime(df[col_dt], errors="coerce").dropna()
    if dt.empty:
        return "不明"

    latest = dt.max()

    if getattr(latest, "tzinfo", None) is None:
        return latest.strftime("%Y-%m-%d %H:%M:%S JST")

    latest_jst = latest.tz_convert(ZoneInfo("Asia/Tokyo"))
    return latest_jst.strftime("%Y-%m-%d %H:%M:%S JST")


def main() -> None:
    if not CSV_LATEST.exists():
        raise SystemExit(f"ERROR: {CSV_LATEST} not found")

    df = pd.read_csv(CSV_LATEST)

    col_shop = pick_col(df, ["shop_name", "name", "shop"])
    col_rank = pick_col(df, ["rank", "順位"])
    col_area = pick_col(df, ["area", "pref", "region"])
    col_url = pick_col(df, ["shop_url", "rank_url", "url", "area_url", "link"])

    if col_shop is None or col_rank is None:
        raise SystemExit(f"ERROR: rank_latest.csv columns={list(df.columns)}")

    updated_text = format_latest_time_jst(df)

    df[col_rank] = pd.to_numeric(df[col_rank], errors="coerce")
    df = df.dropna(subset=[col_rank])
    df[col_rank] = df[col_rank].astype(int)
    df = df.sort_values([col_rank, col_shop], ascending=[True, True]).reset_index(drop=True)

    rows_html = []

    for _, r in df.iterrows():
        shop = str(r[col_shop])
        rank = int(r[col_rank])
        area = str(r[col_area]) if col_area else ""

        href_ext = ""
        if col_url:
            href_ext = url_quote_keep_scheme(str(r[col_url]))

        png_plot = file_href(f"rank_plots/{shop}.png")
        png_text = file_href(f"rank_text/{shop}.png")

        shop_esc = html.escape(shop)
        area_esc = html.escape(area)
        shop_key = html.escape(shop, quote=True)

        if href_ext:
            shop_cell = (
                f'<a class="shop-name" href="{href_ext}" '
                f'target="_blank" rel="noopener noreferrer" '
                f'data-shop="{shop_key}">{shop_esc}</a>'
            )
        else:
            shop_cell = f'<span class="shop-name" data-shop="{shop_key}">{shop_esc}</span>'

        rows_html.append(
            f'<tr data-shop="{shop_key}">'
            f'<td class="check"><button type="button" class="check-btn" data-shop="{shop_key}">✓</button></td>'
            f'<td class="rank">{rank}</td>'
            f'<td class="shop">{shop_cell}<div class="area">{area_esc}</div></td>'
            f'<td class="links"><a href="{png_plot}" target="_blank" rel="noopener noreferrer">plot</a>'
            f'<span> / </span><a href="{png_text}" target="_blank" rel="noopener noreferrer">text</a></td>'
            f'</tr>'
        )

    rows_joined = "\n".join(rows_html)

    html_template = """<!doctype html>
<html lang="ja">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Rank Latest</title>
<style>
body {
  font-family: -apple-system, BlinkMacSystemFont, "Hiragino Sans", "Yu Gothic", sans-serif;
  margin: 16px;
}
h1 {
  margin: 0 0 6px;
  font-size: 18px;
}
.updated-at {
  margin: 0 0 12px;
  color: #666;
  font-size: 13px;
}
.note {
  margin: 0 0 12px;
  color: #888;
  font-size: 12px;
}
table {
  border-collapse: collapse;
  width: 100%;
}
th, td {
  border-bottom: 1px solid #ddd;
  padding: 10px 8px;
  vertical-align: top;
}
th {
  text-align: left;
  background: #f7f7f7;
}
td.check {
  width: 44px;
  text-align: center;
}
td.rank {
  width: 70px;
  font-size: 18px;
  font-weight: 700;
}
td.links {
  width: 110px;
  white-space: nowrap;
}
.area {
  color: #666;
  font-size: 12px;
  margin-top: 2px;
}
a {
  color: #0366d6;
  text-decoration: none;
}
a:hover {
  text-decoration: underline;
}
.shop-name {
  font-weight: 600;
  cursor: pointer;
}
.check-btn {
  width: 30px;
  height: 30px;
  border: 1px solid #bbb;
  border-radius: 50%;
  background: #fff;
  color: #aaa;
  font-size: 16px;
  font-weight: 700;
  cursor: pointer;
}
.check-btn:hover {
  border-color: #666;
  color: #333;
}
tr.checked {
  background: #eeeeee;
  opacity: 0.55;
}
tr.checked .check-btn {
  background: #333;
  color: #fff;
  border-color: #333;
}
tr.checked .shop-name {
  text-decoration: line-through;
}
</style>
</head>
<body>
<h1>最新ランキング</h1>
<div class="updated-at">最終更新：__UPDATED_TEXT__</div>
<div class="note">店舗名をクリックすると自動でチェック済みになり、約0.1秒後に別タブで店舗ページを開きます。左の✓でも手動チェックできます。リロードでリセットされます。</div>

<table>
<thead>
<tr><th>済</th><th>順位</th><th>店舗</th><th>画像</th></tr>
</thead>
<tbody>
__ROWS_HTML__
</tbody>
</table>

<script>
(function () {
  var checked = {};

  function markRow(shop) {
    var rows = document.querySelectorAll("tr[data-shop]");
    rows.forEach(function (row) {
      if (row.getAttribute("data-shop") === shop) {
        row.classList.add("checked");
      }
    });
  }

  function unmarkRow(shop) {
    var rows = document.querySelectorAll("tr[data-shop]");
    rows.forEach(function (row) {
      if (row.getAttribute("data-shop") === shop) {
        row.classList.remove("checked");
      }
    });
  }

  function toggle(shop) {
    if (!shop) {
      return;
    }

    if (checked[shop]) {
      delete checked[shop];
      unmarkRow(shop);
    } else {
      checked[shop] = true;
      markRow(shop);
    }
  }

  function mark(shop) {
    if (!shop) {
      return;
    }

    checked[shop] = true;
    markRow(shop);
  }

  document.querySelectorAll(".check-btn").forEach(function (button) {
    button.addEventListener("click", function () {
      toggle(button.getAttribute("data-shop"));
    });
  });

  document.querySelectorAll(".shop-name").forEach(function (link) {
    link.addEventListener("click", function (event) {
      var shop = link.getAttribute("data-shop");
      var href = link.getAttribute("href");

      mark(shop);

      if (href) {
        event.preventDefault();
        setTimeout(function () {
          window.open(href, "_blank", "noopener,noreferrer");
        }, 100);
      }
    });
  });
})();
</script>

</body>
</html>
"""

    html_text = html_template.replace("__UPDATED_TEXT__", html.escape(updated_text))
    html_text = html_text.replace("__ROWS_HTML__", rows_joined)

    OUT_HTML.write_text(html_text, encoding="utf-8")
    print("OK: rank_latest_view.html")


if __name__ == "__main__":
    main()
