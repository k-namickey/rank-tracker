#!/bin/bash

cd "$(dirname "$0")"

PYTHON="/Library/Frameworks/Python.framework/Versions/3.13/bin/python3"

/usr/bin/git pull

"$PYTHON" fetch_rank.py
"$PYTHON" plot_rank_per_shop.py

/usr/bin/git add rank_latest.csv rank_history.csv rank_plots
/usr/bin/git commit -m "auto update" || true
/usr/bin/git push
