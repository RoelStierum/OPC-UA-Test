import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
import numpy as np

# Configuratie voor de verschillende test scenarios
scenarios = {
    "Old PLC - No Stress": {
        "file": "TestOldPLC/opcua_latency_log_no_stress.csv",
        "color": "#FF0000",  # Fel rood
        "stress_level": "No Stress",
        "plc_type": "Old PLC"
    },
    "Old PLC - Stress 20%": {
        "file": "TestOldPLC/opcua_latency_log_with_stress_com_lvl_20.csv",
        "color": "#FF4D4D",  # Middel rood
        "stress_level": "20%",
        "plc_type": "Old PLC"
    },
    "Old PLC - Stress 50%": {
        "file": "TestOldPLC/opcua_latency_log_with_stress_com_lvl_50.csv",
        "color": "#FF9999",  # Licht rood
        "stress_level": "50%",
        "plc_type": "Old PLC"
    },
    "New PLC V3.1 - No Stress": {
        "file": "TestTiaV20FirmwareV3.1/opcua_latency_log_no_stress.csv",
        "color": "#008000",  # Donker groen
        "stress_level": "No Stress",
        "plc_type": "New PLC V3.1"
    },
    "New PLC V3.1 - Stress 20%": {
        "file": "TestTiaV20FirmwareV3.1/opcua_latency_log_with_stress_com_lvl_20.csv",
        "color": "#00CC00",  # Helder groen
        "stress_level": "20%",
        "plc_type": "New PLC V3.1"
    },
    "New PLC V3.1 - Stress 50%": {
        "file": "TestTiaV20FirmwareV3.1/opcua_latency_log_with_stress_com_lvl_50.csv",
        "color": "#90EE90",  # Licht groen
        "stress_level": "50%",
        "plc_type": "New PLC V3.1"
    },
    "New PLC V4.0 - No Stress": {
        "file": "TestTiaV20FirmwareV4/opcua_latency_log_no_stress.csv",
        "color": "#000080",  # Marine blauw
        "stress_level": "No Stress",
        "plc_type": "New PLC V4.0"
    },
    "New PLC V4.0 - Stress 20%": {
        "file": "TestTiaV20FirmwareV4/opcua_latency_log_with_stress_com_lvl_20.csv",
        "color": "#0000FF",  # Fel blauw
        "stress_level": "20%",
        "plc_type": "New PLC V4.0"
    },
    "New PLC V4.0 - Stress 50%": {
        "file": "TestTiaV20FirmwareV4/opcua_latency_log_with_stress_com_lvl_50.csv",
        "color": "#6495ED",  # Korenbloem blauw
        "stress_level": "50%",
        "plc_type": "New PLC V4.0"
    }
}

# Dictionary voor het opslaan van de round-trip tijden per PLC en stress level
results = {}

# Maak een figuur aan
plt.figure(figsize=(15, 8))

# Voor elk scenario
for name, config in scenarios.items():
    try:
        # Lees de data
        file_path = Path(config["file"])
        if not file_path.exists():
            print(f"Waarschuwing: Bestand niet gevonden: {file_path}")
            continue
            
        df = pd.read_csv(file_path)
        
        # Converteer round trip tijd naar milliseconden als het in seconden staat
        if "round_trip_seconden" in df.columns:
            df["round_trip_ms"] = df["round_trip_seconden"] * 1000
        
        # Sla de resultaten op per PLC type en stress level
        plc_type = config["plc_type"]
        stress_level = config["stress_level"]
        
        if plc_type not in results:
            results[plc_type] = {}
        
        # Bereken statistieken voor dit scenario
        round_trip_times = df["round_trip_ms"].dropna()
        results[plc_type][stress_level] = {
            "mean": round_trip_times.mean(),
            "std": round_trip_times.std(),
            "min": round_trip_times.min(),
            "max": round_trip_times.max()
        }
        
        # Bereken voortschrijdend gemiddelde voor een gladdere lijn
        window_size = 5
        rolling_mean = df["round_trip_ms"].rolling(window=window_size, center=True).mean()
        
        # Plot de lijn met verhoogde lijndikte
        plt.plot(rolling_mean, 
                 color=config["color"], 
                 label=name,
                 linewidth=3)

    except Exception as e:
        print(f"Fout bij verwerken van {name}: {e}")

# Print de tabel in markdown formaat
print("\n## Round-trip tijd statistieken (ms)\n")
print("| PLC Type | Belasting | Gemiddelde | Std Dev | Minimum | Maximum |")
print("|----------|-----------|------------|----------|----------|----------|")

for plc_type in ["Old PLC", "New PLC V3.1", "New PLC V4.0"]:
    if plc_type in results:
        for stress_level in ["No Stress", "20%", "50%"]:
            if stress_level in results[plc_type]:
                stats = results[plc_type][stress_level]
                print(f"| {plc_type} | {stress_level} | {stats['mean']:.2f} | {stats['std']:.2f} | {stats['min']:.2f} | {stats['max']:.2f} |")

# Configureer de plot
plt.title("Vergelijking van PLC versies - Round-trip tijd per meting",
          fontsize=14, pad=20)
plt.xlabel("Meting nummer", fontsize=12)
plt.ylabel("Round-trip tijd (ms)", fontsize=12)
plt.grid(True, alpha=0.3)

# Verplaats de legend naar de rechterkant van de plot
plt.legend(bbox_to_anchor=(1.05, 1), loc='upper left', fontsize=10)

# Maak de plot wat compacter
plt.tight_layout()

# Toon de plot
plt.show() 