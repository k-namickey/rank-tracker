#!/bin/zsh
set -euo pipefail

cd ~/ranktracker/xiaoxiao

echo "=== Git状態リセット・GitHub最新版へ同期 ==="
git rebase --abort || true
git merge --abort || true
git reset --hard HEAD
git fetch origin
git reset --hard origin/main

echo "=== 最新スプレッドシート内容でランキング再取得・再生成・push ==="
./update_rank.command

echo "=== force update 完了 ==="