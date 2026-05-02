# 🎵 Ableton Live 11 MCP Suite - Setup Guide

## Quick Start (5 Minuten)

### 1️⃣ Clone Repository

```bash
git clone https://github.com/john-j-whitehat/name-mcp-live-11-suite.git
cd name-mcp-live-11-suite
```

### 2️⃣ Start Ableton Live 11

**WICHTIG:** Ableton Live 11 muss LAUFEN!

- Öffne Ableton Live 11
- Öffne irgendein Live Set
- Der MCP Server connectet automatisch

### 3️⃣ Start MCP Server

```powershell
# Windows PowerShell
cd "name-mcp-live-11-suite"
py standalone_ableton_server.py
```

**Expected Output:**
```
🎵 STANDALONE ABLETON MCP SERVER - STARTUP
✅ Runtime Script geladen
✅ Runtime Code ausgeführt
✅ AbletonMCP Klasse gefunden

[1] Initialisiere Socket Server...
✅ Socket Server gestartet auf localhost:9877

ABLETON MCP SERVER - READY!
Warte auf Verbindungen...
```

---

## Was ist das?

**Ableton Live 11 MCP Suite** ist ein Remote Control Server für Ableton Live 11.

Du kannst damit:
- 🎚️ **Alle Parameter ändern** (Operator, Sampler, Effects)
- 🎵 **MIDI Clips erstellen** und bearbeiten
- 🎼 **Tracks verwalten** (erstellen, löschen, umbenennen)
- ⏱️ **Transport steuern** (Play, Stop, Tempo)
- 🎯 **Live Session auslesen** (alle Daten)

---

## Installation (Detailliert)

### Anforderungen

- ✅ **Windows OS** (Server läuft auf localhost:9877)
- ✅ **Python 3.8+** (with pip)
- ✅ **Ableton Live 11 Suite** (installed + running!)

### Schritt 1: Repository klonen

```bash
git clone https://github.com/john-j-whitehat/name-mcp-live-11-suite.git
cd name-mcp-live-11-suite
```

### Schritt 2: Dependencies installieren (Optional)

```bash
pip install -r requirements.txt
```

*Hinweis: Server verwendet nur Standard-Bibliotheken, daher optional!*

### Schritt 3: Ableton Live starten

**WICHTIG:**
1. Öffne Ableton Live 11
2. Öffne oder erstelle ein Live Set
3. Der Remote Script muss geladen sein (automatisch)

### Schritt 4: Server starten

```powershell
py standalone_ableton_server.py
```

**Server läuft wenn du das siehst:**
```
✅ Socket Server gestartet auf localhost:9877
ABLETON MCP SERVER - READY!
```

---

## Erste Befehle

### Im PowerShell (Neues Fenster!)

```powershell
cd "name-mcp-live-11-suite"
python read_clips_socket.py
```

**Output (Beispiel):**
```
📋 CLIPNAMEN AUSLESEN - ALLE TRACKS
======================================================

[1] Session Info...
[LOG] Verbinde zu localhost:9877
[LOG] Sende: get_session_info mit params None
✅ 5 Tracks gefunden

[2] Lese Clips von ALLEN Tracks...

Track 0 (Track 1):
  (Keine Clips)

Track 4 (Fucker):
  Slot 0: ✅ 'Test_Melody'
  Slot 1: ✅ 'Test_Notes_2'
  Slot 2: ✅ 'Copilot ist Dumm!'
```

---

## Test: Device Parameters

```powershell
python TEST_DEVICE_PARAMETERS.py
```

**Das testet:**
- ✅ Operator Parameter auslesen (195 params!)
- ✅ Parameter ändern (#0 = Waveform)
- ✅ Filter Cutoff ändern (#50)

**Höre die Änderungen LIVE in Ableton!** 🎵

---

## API Dokumentation

### Alle verfügbaren APIs

**Siehe DEVICE_PARAMETERS_API.md für:**
- Get Device Parameters
- Set Device Parameter
- Get Track Devices
- Load Instruments
- MIDI Operations
- Transport Control

### Beispiel: Parameter ändern

```python
import socket, json

def cmd(method, params):
    sock = socket.socket()
    sock.connect(("localhost", 9877))
    sock.sendall(json.dumps({"method": method, "params": params}).encode())
    return json.loads(sock.recv(16384).decode())

# Operator Waveform auf 75% setzen
result = cmd("set_device_parameter", {
    "track_kind": "track",
    "track_index": 4,      # Track "Fucker"
    "device_index": 0,     # Operator
    "parameter_index": 0,  # Waveform
    "value": 0.75
})

print(f"✅ Changed: {result['result']['parameter']['name']}")
```

---

## Troubleshooting

### Problem: "Connection refused"

**Lösung:**
1. ✅ Ist Ableton Live 11 offen?
2. ✅ Ist Server gestartet? (`py standalone_ableton_server.py`)
3. ✅ Port 9877 nicht blockiert?

```powershell
# Port checken
netstat -ano | findstr :9877
```

### Problem: "Unknown command"

**Lösung:**
- Server nutzt neues JSON-RPC Format
- Siehe README.md für korrekte API Calls

### Problem: Parameter ändern hat keine Wirkung

**Lösung:**
1. Ist Operator wirklich auf Track 5?
2. Device Index korrekt? (0 = first device)
3. Parameter Index valide? (0-194 für Operator)

Siehe `read_clips_socket.py` für Beispiele!

---

## Architecture

```
┌─────────────────────────────────────────┐
│  Dein Python Script / Client             │
│  (Socket Port 9877)                     │
└──────────────┬──────────────────────────┘
               │ JSON-RPC
┌──────────────▼──────────────────────────┐
│  standalone_ableton_server.py            │
│  (Socket Server auf localhost:9877)     │
└──────────────┬──────────────────────────┘
               │ Python API
┌──────────────▼──────────────────────────┐
│  AbletonMCP_RemoteScript_runtime.py      │
│  (Ableton Live Object Model Access)     │
└──────────────┬──────────────────────────┘
               │ Live API
┌──────────────▼──────────────────────────┐
│  Ableton Live 11 Suite                   │
│  (Running on your Computer)              │
└──────────────────────────────────────────┘
```

---

## Nächste Schritte

### Anfänger
1. ✅ Server starten
2. ✅ `read_clips_socket.py` laufen
3. ✅ Clipnamen sehen!
4. ✅ Sounds in Ableton ändern

### Fortgeschrittene
1. Eigen Scripts schreiben
2. Parameter automatisieren
3. MIDI Clips generieren
4. Session automatisiert bauen

### Professionelle Integration
- Live Set Daten in Datenbank speichern
- Parameter Learning Systeme
- Automatische Sound Generierung
- Live Performance Tools

---

## Support & Docs

- 📖 **API Docs:** `DEVICE_PARAMETERS_API.md`
- 🧪 **Test Scripts:** `TEST_DEVICE_PARAMETERS.py`
- 📝 **Code Examples:** `read_clips_socket.py`
- 🔧 **Server Logs:** Console während Server läuft

---

## Status

✅ **Production Ready**
✅ **Fully Documented**
✅ **Test Suite Included**
✅ **Ready to Deploy**

---

**Version:** 2.0  
**Last Updated:** 2026-05-02  
**Author:** Claude (Master Builder)  
**GitHub:** https://github.com/john-j-whitehat/name-mcp-live-11-suite
