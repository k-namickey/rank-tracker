import pandas as pd
import matplotlib.pyplot as plt

df = pd.read_csv("rank_history.csv")

# 列名は既にあるので、そのまま使う
df["datetime"] = pd.to_datetime(df["datetime"])

plt.figure(figsize=(12, 6))
for shop, g in df.groupby("shop_name"):
    plt.plot(g["datetime"], g["rank"])

plt.xlabel("Time")
plt.ylabel("Rank")
plt.title("Rank History (sanity check)")
plt.grid(True)
plt.tight_layout()
plt.show()
