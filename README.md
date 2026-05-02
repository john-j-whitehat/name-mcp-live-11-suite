# ⚠️ UNSTABIL - NUR FÜR ERFAHRENE ANWENDER ⚠️

**WICHTIG:** Dieses Projekt befindet sich in der Entwicklung. Die Basis-Funktionalität arbeitet, aber Setup, Deployment und Integration haben erhebliche Probleme. Verwende diesen Code nur wenn du Python, Ableton Live und Socket-Kommunikation verstehst.

---

# 🎵 Ableton Live 11 MCP Remote Server

Standalone Socket Server für Ableton Live 11 Remote Control via Model Context Protocol (MCP).

## ⚠️ Bekannte Probleme

### 🔴 NICHT FUNKTIONIEREND:
- **MIDI Effects Loading** - Scale, Arpeggiator und andere MIDI Effects können nicht über die API geladen werden
- - **Server-Setup** - Standalone-Server startet, verbindet sich aber nicht zuverlässig mit Live 11
  - - **Remote Scripts Deployment** - Komplizierte Pfadverwaltung und Integrationsprobleme
   
    - ### 🟡 TEILWEISE FUNKTIONIEREND:
    - - **Track/Clip Management** - Erstellen und Steuern funktioniert über MCP-Tools
      - - **Instrument Loading** - Operator, Sampler, Wavetable und andere funktionieren teilweise
        - - **MIDI Note Input** - Funktioniert, aber mit Limitations
          - - **Transport Control** - Play/Stop funktionieren über MCP-Tools
           
            - ### 🟢 FUNKTIONIEREND:
            - - **Session Info** - Tempo, Track Count und Basis-Parameter abrufen
              - - **Core MCP API** - Direkter Zugriff auf Ableton Live über MCP-Tools (wenn Live läuft)
               
                - ## 📋 Anforderungen
               
                - - **Windows OS**
                  - - **Python 3.8+**
                    - - **Ableton Live 11 Suite** (muss laufen)
                     
                      - ## 🚀 Setup
                     
                      - 1. Ableton Live 11 muss GEÖFFNET sein
                        2. 2. Remote Scripts in: `C:\Users\[USERNAME]\AppData\Roaming\Ableton\Live 11 Suite\Preferences\Remote Scripts\`
                           3. 3. Server startet auf `localhost:9877`
                             
                              4. ```bash
                                 python standalone_ableton_server_v2.py
                                 ```

                                 ## 📡 API

                                 ### Funktionierend:
                                 - `get_session_info()` - Tempo, Tracks, Play-Status
                                 - - `create_midi_track()` - MIDI Track erstellen
                                   - - `create_clip()` - Clip erstellen
                                     - - `add_notes_to_clip()` - MIDI Notes hinzufügen
                                       - - `set_tempo()` - BPM ändern
                                         - - `start_playback()` / `stop_playback()` - Transport Control
                                           - - `load_instrument_or_effect()` - Instrumente laden
                                            
                                             - ### NICHT Funktionierend:
                                             - - ❌ MIDI Effects Loading
                                               - - ❌ Zuverlässiger Standalone-Server Betrieb
                                                
                                                 - ---

                                                 **Status:** 🔴 In Development - Nicht für Production Use
                                                 **Version:** 2.0.0 (Unstable)
