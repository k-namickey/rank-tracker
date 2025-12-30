#!/bin/bash

cd "$(dirname "$0")"

PYTHON="/Library/Frameworks/Python.framework/Versions/3.13/bin/python3"

"$PYTHON" fetch_rank.py
"$PYTHON" plot_rank_per_shop.py
