#!/bin/zsh
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

echo "=== Matplotlib設定（日本語フォント固定） ==="

export MPLCONFIGDIR="$SCRIPT_DIR/.mplconfig"
mkdir -p "$MPLCONFIGDIR"

cat > "$MPLCONFIGDIR/matplotlibrc" << 'EOF'
font.family: sans-serif
font.sans-serif: Hiragino Sans
axes.unicode_minus: False
EOF

echo "MPLCONFIGDIR = $MPLCONFIGDIR"
echo "matplotlibrc = $MPLCONFIGDIR/matplotlibrc"

echo "=== ランキング取得 ==="
python3 fetch_rank.py

echo "=== 折れ線グラフ生成（24時間推移）==="
if [[ -f "plot_rank_per_shop.py" ]]; then
  python3 plot_rank_per_shop.py
else
  echo "plot_rank_per_shop.py が見つかりません"
fi

echo "=== 店舗別テキストPNG生成（rank_text）==="
python3 make_text_summary.py | sed '/^Using font file: /d'

echo "=== 全店HTML生成 ==="
python3 make_latest_view.py

echo "=== GitHubへ反映 ==="
git add .
git commit -m "Update ranking" || echo "(no changes to commit)"
git push

echo "=== 完了 ==="
read -n 1