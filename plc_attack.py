import time
import random
import threading
import csv
import os
import signal
from opcua import Client, ua

# === OPC UA instellingen ===
OPC_SERVER = "opc.tcp://172.16.0.1:4840"
client = Client(OPC_SERVER)

# === CSV-bestand ===
CSV_FILE = "opcua_results.csv"
csv_headers = ["Timestamp", "Variable", "Operation", "Value", "Response Time (s)", "Status"]
if not os.path.exists(CSV_FILE):
    with open(CSV_FILE, mode="w", newline="") as file:
        csv.writer(file).writerow(csv_headers)

# === Configuratie ===
stop_event = threading.Event()
TEST_DURATION = 500  # seconden
ARRAY_BASE_NODEID_START = 17  # TestArray2[0] = i=17, TestArray2[1] = i=18, ..., TestArray2[99] = i=116

# === Loggingfunctie ===
def log_to_csv(variable, operation, value, response_time, status):
    if isinstance(value, list):
        value = f"Array({len(value)} items)"
    with open(CSV_FILE, mode="a", newline="") as file:
        writer = csv.writer(file)
        writer.writerow([
            time.strftime("%Y-%m-%d %H:%M:%S"),
            variable,
            operation,
            value,
            f"{response_time:.4f}",
            status
        ])

# === Connectiebeheer ===
def connect_opc():
    try:
        print("Verbinden met OPC UA server...")
        client.connect()
        print("Verbonden!")
        return True
    except Exception as e:
        print(f"Verbindingsfout: {e}")
        return False

def disconnect_opc():
    try:
        print("Verbinding verbreken...")
        client.disconnect()
        print("Verbinding verbroken.")
    except Exception as e:
        print(f"Disconnect fout: {e}")

# === Lezen en schrijven ===
def read_variable(nodeid):
    try:
        start = time.time()
        value = client.get_node(nodeid).get_value()
        duration = time.time() - start
        print(f"Read {nodeid}: {value}")
        log_to_csv(nodeid, "Read", value, duration, "Success")
        return value
    except Exception as e:
        print(f"Read error: {e}")
        log_to_csv(nodeid, "Read", "N/A", 0, "Failed")
        return None

def write_variable(nodeid, value, varianttype=ua.VariantType.Int16):
    try:
        start = time.time()
        node = client.get_node(nodeid)
        val = ua.DataValue(ua.Variant(value, varianttype))
        node.set_value(val)
        duration = time.time() - start
        print(f"Wrote {value} to {nodeid}")
        log_to_csv(nodeid, "Write", value, duration, "Success")
    except Exception as e:
        print(f"Write error: {e}")
        log_to_csv(nodeid, "Write", value, 0, "Failed")

# === Simuleer HMI-belasting ===
def simulate_hmi_load():
    print("Start HMI-simulatie")

    def poll_thread():
        while not stop_event.is_set():
            read_variable('ns=4;i=1110') # TestBool1
            time.sleep(0.5)

    def interaction_thread():
        while not stop_event.is_set():
            write_variable('ns=4;i=1120', random.choice([True, False]), ua.VariantType.Boolean)  # TestBool2
            time.sleep(random.uniform(1, 5))

    threading.Thread(target=poll_thread, daemon=True).start()
    threading.Thread(target=interaction_thread, daemon=True).start()

# === Stress test (schrijft naar arrayelementen) ===
def stress_test():
    print("Start stress test (5 schrijvers, elk 100 array-elementen)")

    def stress_writer():
        while not stop_event.is_set():
            for index in range(100):
                nodeid_int = ARRAY_BASE_NODEID_START + index  # i = 17 + 0..99
                nodeid = f"ns=4;i={nodeid_int}"
                write_variable(nodeid, random.randint(0, 32767))
            time.sleep(0.01)

    for _ in range(5):
        threading.Thread(target=stress_writer, daemon=True).start()

# === Timer en afhandeling ===
def test_timer():
    print(f"Test loopt voor {TEST_DURATION} seconden...")
    time.sleep(TEST_DURATION)
    print("Tijd verstreken! Stoppen van de test...")
    stop_event.set()

def signal_handler(sig, frame):
    print("\nCtrl+C ontvangen. Stoppen...")
    stop_event.set()

signal.signal(signal.SIGINT, signal_handler)

# === Main loop ===
if __name__ == "__main__":
    print("Start OPC UA Performance Test")

    if connect_opc():
        simulate_hmi_load()
        stress_test()
        threading.Thread(target=test_timer, daemon=True).start()

        try:
            while not stop_event.is_set():
                time.sleep(1)
        except KeyboardInterrupt:
            signal_handler(None, None)

        disconnect_opc()
        print(f"Resultaten opgeslagen in: {CSV_FILE}")
        print("Test volledig afgerond.")
    else:
        print("Kan niet verbinden met OPC UA server.")
