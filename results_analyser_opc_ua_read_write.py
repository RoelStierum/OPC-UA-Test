import os
import pandas as pd
import matplotlib.pyplot as plt
from statsmodels.nonparametric.smoothers_lowess import lowess

# === Bestandspaden: latency + (optionele) cycletime per PLC en scenario ===
files = {
    "Nieuwe PLC": {
        "Zonder stresstest": {
            "latency": "TestNewPLC/opcua_latency_log_no_stress.csv",
            "cycletime": "TestNewPLC/cycletime.csv"
        },
        "Met stresstest (com. lvl 20%)": {
            "latency": "TestNewPLC/opcua_latency_log_with_stress_com_lvl_20.csv",
            "cycletime": "TestNewPLC/cycletime_lvl_20.csv"
        },
        "Met stresstest (com. lvl 50%)": {
            "latency": "TestNewPLC/opcua_latency_log_with_stress_com_lvl_50.csv",
            "cycletime": "TestNewPLC/cycletime_lvl_50.csv"
        }
    },
    "Oude PLC": {
        "Zonder stresstest": {
            "latency": "TestOldPLC/opcua_latency_log_no_stress.csv",
            "cycletime": "TestOldPLC/cycletime.csv"
        },
        "Met stresstest (com. lvl 20%)": {
            "latency": "TestOldPLC/opcua_latency_log_with_stress_com_lvl_20.csv",
            "cycletime": "TestOldPLC/cycletime_lvl_20.csv"
        },
        "Met stresstest (com. lvl 50%)": {
            "latency": "TestOldPLC/opcua_latency_log_with_stress_com_lvl_50.csv",
            "cycletime": "TestOldPLC/cycletime_lvl_50.csv"
        }
    },
    "TIA Portal V20 Firmware V3.1": {
        "Zonder stresstest": {
            "latency": "TestTIAV20FirmwareV3.1/opcua_latency_log_no_stress.csv",
            "cycletime": "TestTIAV20FirmwareV3.1/cycletime.csv"
        },
        "Met stresstest (com. lvl 20%)": {
            "latency": "TestTIAV20FirmwareV3.1/opcua_latency_log_with_stress_com_lvl_20.csv",
            "cycletime": "TestTIAV20FirmwareV3.1/cycletime_lvl_20.csv"
        },
        "Met stresstest (com. lvl 50%)": {
            "latency": "TestTIAV20FirmwareV3.1/opcua_latency_log_with_stress_com_lvl_50.csv",
            "cycletime": "TestTIAV20FirmwareV3.1/cycletime_lvl_50.csv"
        }
    },
    "TIA Portal V20 Firmware V4": {
        "Zonder stresstest": {
            "latency": "TestTIAV20FirmwareV4/opcua_latency_log_no_stress.csv",
            "cycletime": "TestTIAV20FirmwareV4/cycletime.csv"
        },
        "Met stresstest (com. lvl 20%)": {
            "latency": "TestTIAV20FirmwareV4/opcua_latency_log_with_stress_com_lvl_20.csv",
            "cycletime": "TestTIAV20FirmwareV4/cycletime_lvl_20.csv"
        },
        "Met stresstest (com. lvl 50%)": {
            "latency": "TestTIAV20FirmwareV4/opcua_latency_log_with_stress_com_lvl_50.csv",
            "cycletime": "TestTIAV20FirmwareV4/cycletime_lvl_50.csv"
        }
    },
}

# === Alle gematchte data verzamelen
all_matched = []

for plc, scenarios in files.items():
    for scenario, paths in scenarios.items():
        latency_path = paths["latency"]
        cycle_path = paths["cycletime"]

        if not os.path.exists(latency_path) or not os.path.exists(cycle_path):
            print(f"[⚠️] Sla over: ontbrekend bestand voor {plc} - {scenario}")
            continue

        # Latency-log
        df_opc = pd.read_csv(latency_path)
        if "round_trip_seconden" not in df_opc.columns or "tijd_unix_ms" not in df_opc.columns:
            print(f"[⚠️] Ongeldig latency-bestand: {latency_path}")
            continue

        df_opc = df_opc.dropna(subset=["round_trip_seconden"])
        df_opc["round_trip_ms"] = df_opc["round_trip_seconden"] * 1000

        # Cycle time log (custom format)
        df_cycle = pd.read_csv(cycle_path, header=None, skiprows=1, names=["Sample", "unix_ns", "cycletime_ns"])
        df_cycle["unix_ms"] = df_cycle["unix_ns"] / 1_000_000
        df_cycle["cycletime_ms"] = df_cycle["cycletime_ns"] / 1_000_000

        # Match op tijd
        matched = []
        for _, row in df_opc.iterrows():
            opc_time = row["tijd_unix_ms"]
            idx = (df_cycle["unix_ms"] - opc_time).abs().idxmin()
            matched_row = df_cycle.loc[idx]
            matched.append({
                "PLC": plc,
                "Scenario": scenario,
                "cycletime_ms": matched_row["cycletime_ms"],
                "round_trip_ms": row["round_trip_ms"]
            })

        df_matched = pd.DataFrame(matched)
        all_matched.append(df_matched)

# === Alles samenvoegen
if not all_matched:
    print("❌ Geen data beschikbaar om te plotten.")
    exit()

df_all = pd.concat(all_matched, ignore_index=True)

# === Plot alles samen ===
plt.figure(figsize=(14, 7))

# Kleuren per PLC + Scenario
groups = df_all.groupby(["PLC", "Scenario"])

for (plc, scenario), group in groups:
    label = f"{plc} - {scenario}"
    plt.scatter(group["cycletime_ms"], group["round_trip_ms"], alpha=0.5, label=label)
    if len(group) > 5:
        smooth = lowess(group["round_trip_ms"], group["cycletime_ms"], frac=0.3)
        plt.plot(smooth[:, 0], smooth[:, 1], linewidth=2)

plt.title("OPC UA Round-trip tijd vs PLC Cycle Time", fontsize=16, weight='bold')
plt.xlabel("PLC Cycle Time (ms)", fontsize=14)
plt.ylabel("Round-trip tijd (ms)", fontsize=14)
plt.grid(True)
plt.legend(title="PLC + Scenario", fontsize=10)
plt.tight_layout()
plt.show()