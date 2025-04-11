from opcua import Client, ua
import time
import csv
import matplotlib.pyplot as plt

# === OPC UA instellingen ===
OPC_SERVER = "opc.tcp://172.16.0.1:4840"
TEST_NODE_ID = 'ns=4; i=15'     #i=2'    # TestInt1
ECHO_NODE_ID = 'ns=4; i=1637'   #i=3'    # EchoInt1

# === Testinstellingen ===
AANTAL_METINGEN = 150
SLEEP_TUSSEN_METINGEN = 0.05 #seconden
MAX_POGINGEN = 10
SLEEP_TUSSEN_POLL = 0.001    # 1 ms tussen polling

# === CSV-bestand ===
CSV_BESTAND = "opcua_latency_log.csv"

# === Verbinden ===
client = Client(OPC_SERVER)

try:
    client.connect()
    print(f"[✓] Verbonden met {OPC_SERVER}")

    test_node = client.get_node(TEST_NODE_ID)
    echo_node = client.get_node(ECHO_NODE_ID)
    print(f"[✓] Nodes opgehaald")

    results = []

    for meting in range(1, AANTAL_METINGEN + 1):
        test_value = meting
        expected_echo = test_value
        unix_ms = int(time.time() * 1000)

        # Reset echo naar -1
        echo_node.set_value(ua.DataValue(ua.Variant(-1, ua.VariantType.Int16)))

        # Wacht tot echo daadwerkelijk -1 is (PLC bevestigt reset)
        for _ in range(20):  # max 20 tries
            if echo_node.get_value() == -1:
                break
            time.sleep(0.005)
        else:
            print(f"[{meting:03}] ⚠️ Reset niet bevestigd (echo ≠ -1), skipping")
            results.append([meting, unix_ms, test_value, "ResetFail", None, None])
            continue  # sla deze meting over

        # Schrijf testwaarde
        start = time.time()
        test_node.set_value(ua.DataValue(ua.Variant(test_value, ua.VariantType.Int16)))

        # Wachten op juiste echo van PLC
        for i in range(MAX_POGINGEN):
            echoed = echo_node.get_value()
            if echoed == expected_echo:
                end = time.time()
                round_trip = end - start
                print(f"[{meting:03}] Echo = {echoed} (✓) in {i+1}x: {round_trip:.4f} s")
                results.append([meting, unix_ms, test_value, echoed, echoed - test_value, round_trip])
                time.sleep(SLEEP_TUSSEN_METINGEN)
                break
            time.sleep(SLEEP_TUSSEN_POLL)
        else:
            print(f"[{meting:03}] Timeout! Laatste echo = {echoed}, verwacht {expected_echo}")
            results.append([meting, unix_ms, test_value, echoed, None, None])


        time.sleep(SLEEP_TUSSEN_METINGEN)

    # Wegschrijven naar CSV
    with open(CSV_BESTAND, mode='w', newline='') as file:
        writer = csv.writer(file)
        writer.writerow(["meting_nummer", "tijd_unix_ms", "testwaarde", "echo_waarde", "verschil", "round_trip_seconden"])
        writer.writerows(results)

    print(f"[✓] {AANTAL_METINGEN} metingen opgeslagen in '{CSV_BESTAND}'")

    # Plotten
    latency_values = [r[5] for r in results if r[5] is not None]
    plt.plot(latency_values, marker='o')
    plt.title("OPC UA Reactietijd per meting")
    plt.xlabel("Meting nummer")
    plt.ylabel("Round-trip tijd (s)")
    plt.grid(True)
    plt.tight_layout()
    plt.show()

except Exception as e:
    print(f"[✗] Fout opgetreden: {e}")

finally:
    client.disconnect()
    print("[→] Verbinding gesloten.")
