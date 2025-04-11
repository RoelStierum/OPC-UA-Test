import os
import pandas as pd
import matplotlib.pyplot as plt
from statsmodels.nonparametric.smoothers_lowess import lowess

# === Configuratie: paden per map en scenario
base_dirs = {
    "Old PLC": "TestOldPLC",
    "Firmware V3.1": "TestTiaV20FirmwareV3.1",
    "Firmware V4.0": "TestTiaV20FirmwareV4"
}

scenario_bestanden = {
    "Zonder stresstest": {
        "latency": "opcua_latency_log_no_stress.csv",
        "cycletime": "Cycletime.csv"
    },
    "Stresstest (20%)": {
        "latency": "opcua_latency_log_with_stress_com_lvl_20.csv",
        "cycletime": "Cycletime_lvl_20.csv"
    },
    "Stresstest (50%)": {
        "latency": "opcua_latency_log_with_stress_com_lvl_50.csv",
        "cycletime": "Cycletime_lvl_50.csv"
    }
}

alle_data = []

# === Inlezen per combinatie
for systeem, map_path in base_dirs.items():
    for scenario, bestanden in scenario_bestanden.items():
        latency_path = os.path.join(map_path, bestanden["latency"])
        cycle_path = os.path.join(map_path, bestanden["cycletime"])

        if not os.path.exists(latency_path) or not os.path.exists(cycle_path):
            print(f"[⏭️] Bestand(en) ontbreken voor: {systeem} - {scenario}")
            continue

        try:
            df_lat = pd.read_csv(latency_path)
            df_lat = df_lat.dropna(subset=["tijd_unix_ms", "round_trip_seconden"])
            df_lat["round_trip_ms"] = df_lat["round_trip_seconden"] * 1000
            df_lat["tijd_unix_ms"] = df_lat["tijd_unix_ms"].astype(float)
        except Exception as e:
            print(f"[❌] Fout bij inlezen latency ({latency_path}): {e}")
            continue

        try:
            df_cyc = pd.read_csv(cycle_path, skiprows=1, header=None,
                                 names=["Sample", "tijd_unix_ms", "cycletime_ns"])
            df_cyc["tijd_unix_ms"] = df_cyc["tijd_unix_ms"].astype(float)
            df_cyc["cycletime_ms"] = df_cyc["cycletime_ns"] / 1_000_000
        except Exception as e:
            print(f"[❌] Fout bij inlezen cycletime ({cycle_path}): {e}")
            continue

        # === Match dichtstbijzijnd
        matched_rows = []
        for _, row in df_lat.iterrows():
            idx = (df_cyc["tijd_unix_ms"] - row["tijd_unix_ms"]).abs().idxmin()
            match = df_cyc.loc[idx]
            matched_rows.append({
                "round_trip_ms": row["round_trip_ms"],
                "cycletime_ms": match["cycletime_ms"],
                "Systeem": systeem,
                "Scenario": scenario
            })

        df_matched = pd.DataFrame(matched_rows)
        alle_data.append(df_matched)
        print(f"[✓] Gecombineerd: {systeem} - {scenario}")

# === Plot
if not alle_data:
    print("❌ Geen geldige combinaties gevonden.")
    exit()

df_all = pd.concat(alle_data, ignore_index=True)

plt.figure(figsize=(14, 7))
groups = df_all.groupby(["Systeem", "Scenario"])

for (systeem, scenario), group in groups:
    label = f"{systeem} - {scenario}"
    plt.scatter(group["round_trip_ms"], group["cycletime_ms"], alpha=0.6, s=20, label=label)
    if len(group) >= 5:
        smooth = lowess(group["cycletime_ms"], group["round_trip_ms"], frac=0.3)
        plt.plot(smooth[:, 0], smooth[:, 1], linewidth=2)

plt.title("Invloed van Round-trip tijd op PLC Cycletime", fontsize=16, weight='bold')
plt.xlabel("Round-trip tijd (ms)", fontsize=14)
plt.ylabel("PLC Cycletime (ms)", fontsize=14)
plt.grid(True)
plt.legend(title="Systeem + Scenario", fontsize=10)
plt.tight_layout()
plt.show()
