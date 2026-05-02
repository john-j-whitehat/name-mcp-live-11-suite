#!/usr/bin/env python3
"""
TEST SCRIPT - Device Parameters API v2.0
Testet Operator Parameter auslesen + ändern
"""

import socket
import json
import time

HOST = "localhost"
PORT = 9877

def send_command(method, params=None):
    """Sende Befehl zu MCP Server"""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5)
        sock.connect((HOST, PORT))

        command = {
            "method": method,
            "params": params or {}
        }

        json_str = json.dumps(command)
        sock.sendall(json_str.encode('utf-8'))
        response = sock.recv(16384).decode('utf-8')
        sock.close()

        return json.loads(response)
    except Exception as e:
        return {"error": str(e)}

print("=" * 70)
print("🎚️ DEVICE PARAMETERS TEST - OPERATOR")
print("=" * 70)
print()

# Test 1: Get Track Devices
print("[1] Lese Devices von Track 5...")
result = send_command("get_track_devices", {"track_index": 4})
if "error" in result:
    print(f"   ❌ ERROR: {result['error']}")
else:
    devices = result.get("result", {}).get("devices", [])
    print(f"   ✅ {len(devices)} Device(s) gefunden")
    for dev in devices:
        print(f"      - {dev.get('name')} ({dev.get('parameter_count')} params)")
print()

# Test 2: Get Device Parameters
print("[2] Lese Operator Parameter (Device 0)...")
result = send_command("get_device_parameters", {
    "track_kind": "track",
    "track_index": 4,
    "device_index": 0
})

if "error" in result:
    print(f"   ❌ ERROR: {result['error']}")
else:
    params = result.get("result", {}).get("parameters", [])
    print(f"   ✅ {len(params)} Parameter gelesen!")
    print()
    print("   Erste 15 Parameter:")
    for i, param in enumerate(params[:15]):
        name = param.get("name", "?")
        value = param.get("value", "?")
        min_val = param.get("min", "?")
        max_val = param.get("max", "?")
        print(f"      [{i:2d}] {name:30s} = {value:6.2f} ({min_val} - {max_val})")
print()

# Test 3: Set Parameter (z.B. Filter Cutoff)
print("[3] Ändere Parameter #50 (Filter?)...")
result = send_command("set_device_parameter", {
    "track_kind": "track",
    "track_index": 4,
    "device_index": 0,
    "parameter_index": 50,
    "value": 0.75  # 75% des Range
})

if "error" in result:
    print(f"   ❌ ERROR: {result['error']}")
else:
    param = result.get("result", {}).get("parameter", {})
    name = param.get("name", "?")
    value = param.get("value", "?")
    print(f"   ✅ Parameter geändert!")
    print(f"      Name: {name}")
    print(f"      Neuer Wert: {value}")
print()

# Test 4: Set Parameter (Waveform - Index 0)
print("[4] Ändere Waveform (Parameter #0)...")
result = send_command("set_device_parameter", {
    "track_kind": "track",
    "track_index": 4,
    "device_index": 0,
    "parameter_index": 0,
    "value": 0.5  # Mittlere Position
})

if "error" in result:
    print(f"   ❌ ERROR: {result['error']}")
else:
    param = result.get("result", {}).get("parameter", {})
    name = param.get("name", "?")
    value = param.get("value", "?")
    print(f"   ✅ Waveform geändert!")
    print(f"      Name: {name}")
    print(f"      Neuer Wert: {value}")
print()

print("=" * 70)
print("✅ TEST ABGESCHLOSSEN!")
print("=" * 70)
print()
print("📋 NEXT STEPS:")
print("1. Start Server: py standalone_ableton_server.py")
print("2. Run Test: python TEST_DEVICE_PARAMETERS.py")
print("3. Überprüfe Operator Sound in Ableton!")
print()
