#!/bin/bash

# 環境を明示
export HOME="/Users/koichi"
export PATH="/usr/local/bin:/usr/bin:/bin:/Library/Frameworks/Python.framework/Versions/3.13/bin"

cd "$HOME/ranktracker/xiaoxiao" || exit 1

# GitHub SSH を使えるようにする
eval "$(ssh-agent -s)"
ssh-add "$HOME/.ssh/id_ed25519"

# 実行
python3 fetch_rank.py
python3 plot_rank_per_shop.py

# GitHubへ反映
git add rank_history.csv rank_latest.csv rank_plots
git commit -m "auto update" || true
git push

