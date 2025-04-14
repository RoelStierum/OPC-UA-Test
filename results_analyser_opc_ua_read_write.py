import os
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
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

# === Data inlezen en koppelen
for systeem, map_path in base_dirs.items():
    for scenario, bestanden in scenario_bestanden.items():
        latency_path = os.path.join(map_path, bestanden["latency"])
        cycle_path = os.path.join(map_path, bestanden["cycletime"])

        if not os.path.exists(latency_path) or not os.path.exists(cycle_path):
            print(f"[⏭️] Bestanden ontbreken: {systeem} - {scenario}")
            continue

        try:
            df_lat = pd.read_csv(latency_path)
            df_lat = df_lat.dropna(subset=["tijd_unix_ms", "round_trip_seconden"])
            df_lat["round_trip_ms"] = df_lat["round_trip_seconden"] * 1000
            df_lat["tijd_unix_ms"] = df_lat["tijd_unix_ms"].astype(float)
        except Exception as e:
            print(f"[❌] Fout bij inlezen latency: {latency_path}\n{e}")
            continue

        try:
            df_cyc = pd.read_csv(cycle_path, skiprows=1, header=None,
                                 names=["Sample", "tijd_unix_ms", "cycletime_ns"])
            df_cyc["tijd_unix_ms"] = df_cyc["tijd_unix_ms"].astype(float)
            df_cyc["cycletime_ms"] = df_cyc["cycletime_ns"] / 1_000_000
        except Exception as e:
            print(f"[❌] Fout bij inlezen cycletime: {cycle_path}\n{e}")
            continue

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

# === Visualisatie
if not alle_data:
    print("❌ Geen geldige combinaties gevonden.")
else:
    df_all = pd.concat(alle_data, ignore_index=True)
    unique_scenarios = df_all["Scenario"].unique()
    nrows = len(unique_scenarios)
    fig, axes = plt.subplots(nrows=nrows, ncols=1, figsize=(14, 5 * nrows), sharex=True)

    if nrows == 1:
        axes = [axes]

    for ax, scenario in zip(axes, unique_scenarios):
        df_scenario = df_all[df_all["Scenario"] == scenario]

        sns.scatterplot(
            data=df_scenario,
            x="round_trip_ms",
            y="cycletime_ms",
            hue="Systeem",
            style="Systeem",
            ax=ax,
            s=40,
            alpha=0.6
        )

        # Trendlijnen toevoegen
        for systeem in df_scenario["Systeem"].unique():
            subset = df_scenario[df_scenario["Systeem"] == systeem]
            if len(subset) > 5:
                smooth = lowess(subset["cycletime_ms"], subset["round_trip_ms"], frac=0.3)
                ax.plot(smooth[:, 0], smooth[:, 1], label=f"{systeem} trend")

        ax.set_title(f"Scenario: {scenario}", fontsize=14, weight="bold")
        ax.set_xlabel("Round-trip tijd (ms)")
        ax.set_ylabel("PLC Cycletime (ms)")
        ax.grid(True)
        ax.legend(title="Systeem")

    plt.suptitle("Round-trip tijd vs PLC Cycletime per Scenario", fontsize=18, weight="bold")
    plt.tight_layout(rect=[0, 0.03, 1, 0.97])
    plt.show()
