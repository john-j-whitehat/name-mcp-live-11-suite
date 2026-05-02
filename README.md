# 🎵 Ableton Live 11 MCP Remote Server

Standalone Socket Server für Ableton Live 11 Remote Control via Model Context Protocol (MCP).

## ✨ Features

- 🎚️ Full Ableton Live 11 Control (Tracks, Clips, Tempo, Transport)
- 🔌 Socket Server (localhost:9877)
- 📡 JSON-RPC Interface
- ⚡ Real-time Synchronization
- 🚀 Production Ready

## 📋 Requirements

### System Requirements
- **Windows OS** (Server läuft auf localhost:9877)
- **Python 3.8+** (with pip)
- **Ableton Live 11 Suite** (installed and running)

### Python Dependencies
- **NONE!** Der Server nutzt nur Standard-Bibliotheken
  - socket, json, threading, time, os, pathlib

## 🚀 Quick Start

### 1. Clone Repository
```bash
git clone https://github.com/john-j-whitehat/name-mcp-live-11-suite.git
cd name-mcp-live-11-suite
```

### 2. Install (Optional - nur zur Validierung)
```bash
pip install -r requirements.txt
```

### 3. Start Server
```bash
py standalone_ableton_server.py
```

### Expected Output
```
🎵 STANDALONE ABLETON MCP SERVER - STARTUP
✅ Runtime Script geladen (100912 bytes)
✅ Runtime Code ausgeführt
✅ AbletonMCP Klasse gefunden

[1] Initialisiere Socket Server...
✅ Socket Server gestartet auf localhost:9877

ABLETON MCP SERVER - READY!
Warte auf Verbindungen...
```

## 🔧 Server Details

- **Host:** localhost
- **Port:** 9877
- **Protocol:** JSON-RPC over Socket
- **Encoding:** UTF-8

## 📡 API Examples

### Get Session Info
```json
{"method": "get_session_info"}
→ {"tempo": 120.0, "tracks": 4, "is_playing": false}
```

### Set Tempo
```json
{"method": "set_tempo", "params": {"tempo": 140}}
→ {"status": "ok", "tempo": 140}
```

### Create MIDI Track
```json
{"method": "create_midi_track", "params": {"index": -1}}
→ {"status": "ok", "track_index": 4}
```

## 📚 Full API Reference

See `standalone_ableton_server.py` for complete method list:
- `get_session_info()`
- `get_track_info(track_index)`
- `set_track_name(track_index, name)`
- `create_midi_track(index)`
- `create_clip(track_index, clip_index, length)`
- `add_notes_to_clip(track_index, clip_index, notes)`
- `set_tempo(tempo)`
- `start_playback()`
- `stop_playback()`
- `fire_clip(track_index, clip_index)`
- `stop_clip(track_index, clip_index)`

## 🧪 Testing

Server responds with live Ableton data:
- Real-time Tempo
- Track Count & Details
- Clip Information
- Transport Status
- Master Volume

All functions tested and production-ready ✅

## 📄 License

[Your License Here]

## 👤 Author

Oliver (Meister)
- GitHub: john-j-whitehat
- Project: Fabrik - AI-assisted Development System

## 🔗 Related Projects

- FABRIK Master System (Central AI Coordination)
- Layer 8 Philosophy (Human-AI Hierarchy)
- Ableton Live 11 Integration Suite

---

**Status:** ✅ Production Ready
**Last Updated:** 2026-05-02
**Version:** 1.0.0
