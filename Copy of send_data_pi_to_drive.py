
#!/usr/bin/python3
import os
import json
import requests
import shutil
import sys
import time
from datetime import datetime

# --- Configuration ---
UPQ_PATH = "/home/sglab/pi/CEMS/UpQ/"
HISTORIAN_ROOT = "/home/sglab/pi/CEMS/Historian/"
URL = "https://script.google.com/macros/s/AKfycbzD3Ubhl9GNZJ9ZL2DD-OfxDHxW5mKunV3aUBubfs3fedn2kYBNGCAP5qplUjQICZJ9/exec"  # replace with your URL
MAX_RETRIES = 3
RETRY_DELAY = 10  # seconds

# Define meter header in exact order expected by Apps Script
METER_HEADER = [
    "va", "vb", "vc",
    "Vab", "Vbc", "Vca",
    "Ia", "Ib", "Ic",
    "I_neutral",
    "P_a", "P_b", "P_c", "sum_of_powers",
    "Q_a", "Q_b", "Q_c", "sum_of_Qs",
    "S_a", "S_b", "S_c", "S_total",
    "pf_a", "pf_b", "pf_c", "total_PF",
    "frequency",
    "Energy_total_KWH_high", "Energy_total_KWH_low",
    "KVARH_total_high", "KVARH_total_low",
    "Export_kVAH_low", "Export_KVAH_high",
    "voltage_imbalance"
]

# Wait a few seconds before starting
time.sleep(5)

# Ensure folders exist
os.makedirs(UPQ_PATH, exist_ok=True)
os.makedirs(HISTORIAN_ROOT, exist_ok=True)

# Get list of JSON files
files = [f for f in os.listdir(UPQ_PATH) if f.startswith("data_") and f.endswith(".json")]
files.sort()  # lexicographical sort works because filename has YYYY-MM-DD HH:MM

if not files:
    print("No files to send. The folder is empty.")
    sys.exit(0)

for file_name in files:
    file_path = os.path.join(UPQ_PATH, file_name)

    # Read JSON file
    try:
        with open(file_path, 'r') as f:
            json_data = json.load(f)
    except Exception as e:
        print(f"Failed to read '{file_name}': {e}")
        continue

    # Convert each meter dict to array in METER_HEADER order
    timestamp = list(json_data.keys())[0]
    new_data = {timestamp: {}}
    for meter_id, meter_dict in json_data[timestamp].items():
        values_array = [round(meter_dict.get(h, 0), 3) for h in METER_HEADER]
        new_data[timestamp][meter_id] = values_array

    json_string = json.dumps(new_data)
    print(f"Sending data from '{file_name}'...")

    # Attempt to POST data with retries
    success = False
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            response = requests.post(
                URL,
                data=json_string,
                headers={'Content-Type': 'application/json'},
                timeout=30
            )
            print("Response status:", response.status_code)
            print("Response text:", response.text)

            if response.status_code == 200:
                success = True
                print(f"File '{file_name}' sent successfully.")
                break
            else:
                print(f"Attempt {attempt}: Error {response.status_code} - {response.text}")

        except requests.exceptions.RequestException as e:
            print(f"Attempt {attempt}: Exception occurred - {e}")

        time.sleep(RETRY_DELAY)

    if not success:
        print(f"Failed to send '{file_name}' after {MAX_RETRIES} attempts. Skipping file.")
        continue

    # Move file to Historian folder based on filename timestamp
    try:
        # Filename format: data_YYYY-MM-DD HH:MM.json
        ts_str = file_name[5:-5]  # remove "data_" prefix and ".json" suffix
        dt_obj = datetime.strptime(ts_str, "%Y-%m-%d %H:%M")
        year, month, day = dt_obj.strftime("%Y"), dt_obj.strftime("%m"), dt_obj.strftime("%d")

        target_dir = os.path.join(HISTORIAN_ROOT, year, month, day)
        os.makedirs(target_dir, exist_ok=True)
        shutil.move(file_path, os.path.join(target_dir, file_name))
        print(f"File '{file_name}' moved to '{target_dir}'")
    except Exception as e:
        print(f"Error moving file '{file_name}': {e}")
        continue

print("All files processed.")