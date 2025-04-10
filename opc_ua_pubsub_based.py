from opcua import Client, ua
import time
import csv
import matplotlib.pyplot as plt
import threading

# === OPC UA instellingen ===
OPC_SERVER = "opc.tcp://172.16.0.1:4840"
TEST_NODE_ID = 'ns=4;i=2'     # schrijf node: TestInt1
ECHO_NODE_ID = 'ns=4;i=3'     # echo node: EchoInt1

# === Testinstellingen ===
AANTAL_METINGEN = 100
CSV_BESTAND = "opcua_sync_latency_log.csv"

# === Globale variabelen ===
echo_lock = threading.Condition()
latest_echo = None
current_test_value = None
current_start_time = None
results = []

# === Subscription handler ===
class EchoHandler:
    def datachange_notification(self, node, val, data):
        global latest_echo, current_test_value, current_start_time

        if current_test_value is None:
            return  # nog geen write gestart

        if val == current_test_value:
            latency = time.time() - current_start_time
            with echo_lock:
                latest_echo = (val, latency)
                echo_lock.notify()

# === Verbinding en subscription opzetten ===
client = Client(OPC_SERVER)
client.connect()
print(f"[✓] Verbonden met {OPC_SERVER}")

test_node = client.get_node(TEST_NODE_ID)
echo_node = client.get_node(ECHO_NODE_ID)

handler = EchoHandler()
sub = client.create_subscription(50, handler)
sub_handle = sub.subscribe_data_change(echo_node)

print("[✓] Subscription actief")

# === Testloop met synchronisatie op echo ===
for meting in range(1, AANTAL_METINGEN + 1):
    test_value = meting
    current_test_value = test_value
    current_start_time = time.time()
    unix_ms = int(current_start_time * 1000)

    # Schrijf waarde naar PLC
    test_node.set_value(ua.DataValue(ua.Variant(test_value, ua.VariantType.Int16)))

    # Wacht op echo via subscription
    with echo_lock:
        success = echo_lock.wait(timeout=1.0)

    if success and latest_echo and latest_echo[0] == test_value:
        latency = latest_echo[1]
        print(f"[{meting:03}] Echo = {test_value} (✓) na {latency:.4f} s")
        results.append([meting, unix_ms, test_value, test_value, 0, latency])
    else:
        print(f"[{meting:03}] Timeout! Geen bevestiging van {test_value}")
        results.append([meting, unix_ms, test_value, latest_echo[0] if latest_echo else None, None, None])

    # Reset voor volgende meting
    latest_echo = None
    current_test_value = None
    current_start_time = None

# === Opruimen ===
sub.unsubscribe(sub_handle)
sub.delete()
client.disconnect()
print("[→] Verbinding gesloten")

# === Resultaten opslaan ===
with open(CSV_BESTAND, mode='w', newline='') as file:
    writer = csv.writer(file)
    writer.writerow(["meting_nummer", "tijd_unix_ms", "testwaarde", "echo_waarde", "verschil", "round_trip_seconden"])
    writer.writerows(results)

print(f"[✓] Resultaten opgeslagen in '{CSV_BESTAND}'")

# === Plot ===
latency_values = [r[5] for r in results if r[5] is not None]
plt.plot(latency_values, marker='o')
plt.title("OPC UA Round-trip tijd per meting (Subscription, echo == input)")
plt.xlabel("Meting nummer")
plt.ylabel("Round-trip tijd (s)")
plt.grid(True)
plt.tight_layout()
plt.show()
