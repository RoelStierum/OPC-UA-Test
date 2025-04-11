import os
import csv
import time
import threading
from opcua import Client, ua

# === OPC UA instellingen ===
OPC_SERVER = "opc.tcp://172.16.0.1:4840"

# Node mapping per client (TestInt, EchoInt)
CLIENT_NODE_IDS = {
    1: ("ns=4;i=15",   "ns=4;i=1637"),
    2: ("ns=4;i=16",   "ns=4;i=1661"),
    3: ("ns=4;i=17",   "ns=4;i=1662"),
    4: ("ns=4;i=1650", "ns=4;i=1663"),
    5: ("ns=4;i=1649", "ns=4;i=1664"),
}

# === Testinstellingen ===
AANTAL_METINGEN = 250
OUTPUT_DIR = "multi_client_results"
os.makedirs(OUTPUT_DIR, exist_ok=True)

stop_event = threading.Event()

def run_client(client_id):
    print(f"[Client {client_id}] Start")

    results = []
    echo_lock = threading.Lock()
    latest_echo = {"value": None, "latency": None}
    current_test_value = None
    current_start_time = None

    class EchoHandler:
        def datachange_notification(self, node, val, data):
            nonlocal latest_echo, current_test_value, current_start_time
            if current_test_value is not None and val == current_test_value:
                latency = time.time() - current_start_time
                with echo_lock:
                    latest_echo["value"] = val
                    latest_echo["latency"] = latency

    client = None
    sub = None

    try:
        test_node_id, echo_node_id = CLIENT_NODE_IDS[client_id]
        client = Client(OPC_SERVER)
        client.session_timeout = 60000
        client.connect()
        test_node = client.get_node(test_node_id)
        echo_node = client.get_node(echo_node_id)

        handler = EchoHandler()
        sub = client.create_subscription(50, handler)
        sub_handle = sub.subscribe_data_change(echo_node)

        for meting in range(1, AANTAL_METINGEN + 1):
            if stop_event.is_set():
                print(f"[Client {client_id}] ❌ Stop-signaal ontvangen, breekt af.")
                break

            test_value = meting
            current_test_value = test_value
            current_start_time = time.time()
            unix_ms = int(current_start_time * 1000)
            with echo_lock:
                latest_echo["value"] = None

            try:
                test_node.set_value(ua.DataValue(ua.Variant(test_value, ua.VariantType.Int16)))
            except Exception as e:
                print(f"[Client {client_id}] ⚠️ Fout bij write: {e}")
                continue

            timeout = 5
            start = time.time()
            while not stop_event.is_set() and time.time() - start < timeout:
                with echo_lock:
                    if latest_echo["value"] == test_value:
                        latency = latest_echo["latency"]
                        print(f"[Client {client_id}] Echo {test_value} ✓ {latency:.4f}s")
                        results.append([meting, unix_ms, test_value, latency])
                        break
                time.sleep(0.1)
            else:
                print(f"[Client {client_id}] ❌ Geen echo voor {test_value} binnen tijd")


            current_test_value = None
            current_start_time = None

    except Exception as e:
        print(f"[Client {client_id}] ❌ Fout: {e}")

    finally:
        if sub:
            try:
                sub.delete()
            except:
                pass
        if client:
            try:
                client.disconnect()
            except:
                pass

        # CSV wegschrijven
        file_path = os.path.join(OUTPUT_DIR, f"client_{client_id}_result.csv")
        with open(file_path, 'w', newline='') as file:
            writer = csv.writer(file)
            writer.writerow(["meting_nummer", "tijd_unix_ms", "testwaarde", "round_trip_s", "pogingen"])
            writer.writerows(results)

        print(f"[Client {client_id}] ✅ Klaar – log: {file_path}")

# === Start alle clients parallel
threads = []

try:
    for client_id in CLIENT_NODE_IDS:
        t = threading.Thread(target=run_client, args=(client_id,))
        t.daemon = True
        t.start()
        threads.append(t)

    while any(t.is_alive() for t in threads):
        time.sleep(0.2)

except KeyboardInterrupt:
    print("\n[⛔] Ctrl+C ontvangen – stop alle clients...")
    stop_event.set()
    for t in threads:
        t.join(timeout=2.0)

print("[🧹] Alles afgesloten.")
