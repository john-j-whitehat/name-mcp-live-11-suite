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

## 🚀 Quick Start (5 Minutes)

**👉 [DETAILED SETUP GUIDE - SETUP_GUIDE.md](SETUP_GUIDE.md)**

### TL;DR

```bash
# 1. Clone Repository
git clone https://github.com/john-j-whitehat/name-mcp-live-11-suite.git
cd name-mcp-live-11-suite

# 2. IMPORTANT: Open Ableton Live 11!

# 3. Start Server
py standalone_ableton_server.py

# 4. Test (New PowerShell Window)
python read_clips_socket.py
```

### Expected Output
```
🎵 STANDALONE ABLETON MCP SERVER - STARTUP
✅ Runtime Script geladen
✅ Runtime Code ausgeführt
✅ AbletonMCP Klasse gefunden

✅ Socket Server gestartet auf localhost:9877

ABLETON MCP SERVER - READY!
Warte auf Verbindungen...
```

**Test Output:**
```
📋 CLIPNAMEN AUSLESEN - ALLE TRACKS
✅ 5 Tracks gefunden

Track 4 (Fucker):
  Slot 0: ✅ 'Test_Melody'
  Slot 1: ✅ 'Test_Notes_2'
  Slot 2: ✅ 'Copilot ist Dumm!'
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

### Device Parameters (NEW!)
See `DEVICE_PARAMETERS_API.md`:
- `get_device_parameters()` - Read all 195 Operator parameters!
- `set_device_parameter()` - Change parameters in real-time
- `get_track_devices()` - Discover instruments
- `load_instrument_or_effect()` - Load Operator, Sampler, etc.

### Core API
See `standalone_ableton_server_v2.py`:
- `get_session_info()` - Read tempo, tracks, master volume
- `get_track_info(track_index)` - Full track details
- `set_track_name(track_index, name)` - Rename tracks
- `create_midi_track(index)` - Create new MIDI tracks
- `create_clip(track_index, clip_index, length)` - Create clips
- `add_notes_to_clip(track_index, clip_index, notes)` - Add MIDI notes
- `set_tempo(tempo)` - Change BPM
- `start_playback()` / `stop_playback()` - Transport control
- `fire_clip(track_index, clip_index)` - Play clips

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

**Status:** ✅ Production Ready - v2.0
**Last Updated:** 2026-05-02
**Version:** 2.0.0

---

## 🎉 What's New in v2.0

✅ **Device Parameters API** - Control 195+ parameters on Operator!
✅ **New Test Suite** - TEST_DEVICE_PARAMETERS.py
✅ **Complete Documentation** - SETUP_GUIDE.md + DEVICE_PARAMETERS_API.md
✅ **Production Tested** - All systems verified & stable
✅ **Full LOM Access** - Get/Set any parameter in Ableton Live
