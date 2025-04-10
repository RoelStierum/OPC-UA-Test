import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from statsmodels.nonparametric.smoothers_lowess import lowess

# === Bestanden ===
file_cycle = "cycletime.csv"
file_opcua = "opcua_latency_log.csv"

# === Cycle time inlezen ===
df_cycle = pd.read_csv(file_cycle)
df_cycle.columns = ["Sample", "unix_ns", "cycletime_ns"]
df_cycle["unix_ms"] = df_cycle["unix_ns"] / 1_000_000
df_cycle["cycletime_ms"] = df_cycle["cycletime_ns"] / 1_000_000

# === OPC UA log inlezen ===
df_opc = pd.read_csv(file_opcua)
if "echo_waarde" in df_opc.columns:
    df_opc = df_opc.dropna(subset=["round_trip_seconden"])
    df_opc["round_trip_ms"] = df_opc["round_trip_seconden"] * 1000
else:
    # Variant zonder echo
    df_opc = df_opc.dropna(subset=["round_trip_seconden"])
    df_opc["round_trip_ms"] = df_opc["round_trip_seconden"] * 1000

# === Match cycle times met OPC UA metingen (dichtstbijzijnde tijd) ===
matched = []
for _, row in df_opc.iterrows():
    opc_time = row["tijd_unix_ms"]
    closest_idx = (df_cycle["unix_ms"] - opc_time).abs().idxmin()
    matched_row = df_cycle.loc[closest_idx]
    matched.append({
        "tijd_unix_ms": opc_time,
        "round_trip_ms": row["round_trip_ms"],
        "cycletime_ms": matched_row["cycletime_ms"]
    })

df_matched = pd.DataFrame(matched)

# === Plot: Scatterplot van cycle time vs round-trip ===
plt.figure(figsize=(12, 6))
plt.scatter(df_matched["cycletime_ms"], df_matched["round_trip_ms"], alpha=0.6, label="metingen")
plt.title("Relatie tussen PLC cycletijd en OPC UA round-trip tijd", fontsize=16, weight='bold')
plt.xlabel("PLC Cycle Time (ms)", fontsize=14)
plt.ylabel("OPC UA Round-trip tijd (ms)", fontsize=14)
plt.grid(True)

# Loess smoothing toevoegen (optioneel)
smoothed = lowess(df_matched["round_trip_ms"], df_matched["cycletime_ms"], frac=0.3)
plt.plot(smoothed[:, 0], smoothed[:, 1], color="red", linewidth=2, label="trend (lowess)")

plt.legend()
plt.tight_layout()
plt.show()
