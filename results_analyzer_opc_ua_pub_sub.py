import os
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

RESULT_DIR = "multi_client_results"

# Inlezen alle client-bestanden
all_data = []
for fname in os.listdir(RESULT_DIR):
    if fname.startswith("client_") and fname.endswith(".csv"):
        client_id = int(fname.split("_")[1])
        df = pd.read_csv(os.path.join(RESULT_DIR, fname))
        df["Client"] = client_id
        all_data.append(df)

if not all_data:
    print("❌ Geen clientresultaten gevonden.")
    exit()

df_all = pd.concat(all_data, ignore_index=True)

# Plot per client: scatter round-trip
plt.figure(figsize=(12, 6))
for client_id in sorted(df_all["Client"].unique()):
    subset = df_all[df_all["Client"] == client_id]
    plt.plot(subset["meting_nummer"], subset["round_trip_s"] * 1000, label=f"Client {client_id}", alpha=0.8)

plt.title("OPC UA round-trip tijd per meting")
plt.xlabel("Meting nummer")
plt.ylabel("Round-trip tijd (ms)")
plt.grid(True)
plt.legend()
plt.tight_layout()
plt.show()

# Boxplot vergelijking tussen clients
plt.figure(figsize=(10, 6))
sns.boxplot(data=df_all, x="Client", y="round_trip_s", palette="Set2")
plt.title("Vergelijking round-trip tijd per client")
plt.ylabel("Round-trip tijd (s)")
plt.xlabel("Client")
plt.grid(True, axis='y')
plt.tight_layout()
plt.show()

# Gemiddelde/Min/Max tabel
stat = df_all.groupby("Client")["round_trip_s"].agg(["mean", "min", "max", "std"])
print("\n📊 Statistieken per client (tijden in seconden):")
print(stat.round(4))

# === Cycletime toevoegen? ===
cycletime_path = os.path.join(RESULT_DIR, "cycletime.csv")
if os.path.exists(cycletime_path):
    df_cycle = pd.read_csv(cycletime_path, header=None, skiprows=1, names=["Sample", "unix_ns", "cycletime_ns"])
    df_cycle["unix_ms"] = df_cycle["unix_ns"] / 1_000_000
    df_cycle["cycletime_ms"] = df_cycle["cycletime_ns"] / 1_000_000

    # Match op tijd
    matched = []
    for _, row in df_all.iterrows():
        opc_time = row["tijd_unix_ms"]
        idx = (df_cycle["unix_ms"] - opc_time).abs().idxmin()
        match = df_cycle.loc[idx]
        matched.append({
            "Client": row["Client"],
            "round_trip_ms": row["round_trip_s"] * 1000,
            "cycletime_ms": match["cycletime_ms"]
        })

    df_matched = pd.DataFrame(matched)

    # Scatterplot latency vs cycletime
    plt.figure(figsize=(12, 6))
    sns.scatterplot(data=df_matched, x="cycletime_ms", y="round_trip_ms", hue="Client", palette="tab10", alpha=0.6)
    plt.title("Round-trip tijd vs PLC cycletijd")
    plt.xlabel("Cycle time (ms)")
    plt.ylabel("Round-trip tijd (ms)")
    plt.grid(True)
    plt.tight_layout()
    plt.show()
else:
    print("Geen cycletime-log gevonden. Alleen latency geanalyseerd.")
