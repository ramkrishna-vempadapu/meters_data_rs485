#!/usr/bin/python3
import time
import struct
import minimalmodbus
import serial
import datetime
import os
import json

# ---------------------------------
# CONFIG
# ---------------------------------
decimal_places = 3
UPQ_PATH = "/home/sglab/pi/CEMS/UpQ/"

par_dict = {
    "va": [5, 6, decimal_places],
    "vb": [7, 8, decimal_places],
    "vc": [9, 10, decimal_places],
    "Vab": [11, 12, decimal_places],
    "Vbc": [13, 14, decimal_places],
    "Vca": [15, 16, decimal_places],
    "Ia": [17, 18, decimal_places],
    "Ib": [19, 20, decimal_places],
    "Ic": [21, 22, decimal_places],
    "I_neutral": [55, 56, decimal_places],
    "P_a": [23, 24, decimal_places],
    "P_b": [25, 26, decimal_places],
    "P_c": [27, 28, decimal_places],
    "sum_of_powers": [29, 30, decimal_places],
    "Q_a": [31, 32, decimal_places],
    "Q_b": [33, 34, decimal_places],
    "Q_c": [35, 36, decimal_places],
    "sum_of_Qs": [37, 38, decimal_places],
    "S_a": [57, 58, decimal_places],
    "S_b": [59, 60, decimal_places],
    "S_c": [61, 62, decimal_places],
    "S_total": [39, 40, decimal_places],
    "pf_a": [63, 64, decimal_places],
    "pf_b": [65, 66, decimal_places],
    "pf_c": [67, 68, decimal_places],
    "total_PF": [41, 42, decimal_places],
    "frequency": [43, 44, 3],
    "Energy_total_KWH_high": [45, 46, decimal_places],
    "Energy_total_KWH_low": [47, 48, decimal_places],
    "KVARH_total_high": [49, 50, decimal_places],
    "KVARH_total_low": [51, 52, decimal_places],
    "Export_kVAH_low": [71, 72, decimal_places],
    "Export_KVAH_high": [75, 76, decimal_places],
    "voltage_imbalance": [773, 774, decimal_places],
}

BLOCKS = [0, 6]

# ---------------------------------
# HELPERS
# ---------------------------------
def unpack_meter_data(x, y):
    return struct.unpack("<f", struct.pack("<HH", x, y))[0]

def map_reg(data_blocks, reg):
    block = reg // 125
    block_start = block * 125
    local_index = reg - block_start
    if block == 0:
        return data_blocks[local_index]
    elif block == 6:
        return data_blocks[125 + local_index]
    else:
        return 0

# ---------------------------------
# MODBUS SETUP
# ---------------------------------
inst = minimalmodbus.Instrument("/dev/ttyUSB0", 1)
inst.serial.baudrate = 9600
inst.serial.bytesize = 8
inst.serial.parity = serial.PARITY_EVEN
inst.serial.stopbits = 1
inst.serial.timeout = 1
inst.mode = minimalmodbus.MODE_RTU

# ---------------------------------
# MAIN
# ---------------------------------
def main():
    os.makedirs(UPQ_PATH, exist_ok=True)
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    filename = f"data_{timestamp}.json"
    file_path = os.path.join(UPQ_PATH, filename)

    print("Starting meter read:", timestamp)

    all_data = {}

    for meter_id in range(1, 15):
        print(f"\n--- Meter {meter_id} ---")
        inst.address = meter_id
        data = []

        # Read blocks
        for blk in BLOCKS:
            start = blk * 125
            try:
                data.extend(inst.read_registers(start, 125, 3))
            except Exception as e:
                print(f"Block {blk} read error: {e}")
                data.extend([0]*125)

        meter_data = {}
        for par, vals in par_dict.items():
            r1, r2 = vals[0], vals[1]
            try:
                x = map_reg(data, r1)
                y = map_reg(data, r2)
                value = unpack_meter_data(x, y)
                meter_data[par] = round(value, decimal_places)
            except Exception as e:
                meter_data[par] = None
                print(f"{par}: ERROR ({e})")

        all_data[str(meter_id)] = meter_data

    # Save JSON
    with open(file_path, "w") as f:
        json.dump({timestamp: all_data}, f, indent=4)

    print(f"\nData saved to {file_path}")
    print("Completed.")

if __name__ == "__main__":
    main()
