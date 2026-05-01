#!/usr/bin/env python3
"""
ABLETON MCP LIVE 11 - STANDALONE SOCKET SERVER
Lädt direkt vom Desktop, keine ProgramData-Komplexität!
"""

import socket
import json
import threading
import time
import os
from pathlib import Path

# Configuration
HOST = "localhost"
PORT = 9877
RUNTIME_SCRIPT = Path(__file__).parent / "AbletonMCP_RemoteScript_runtime.py"

print("=" * 70)
print("🎵 STANDALONE ABLETON MCP SERVER - STARTUP")
print("=" * 70)
print(f"Loading: {RUNTIME_SCRIPT}")
print()

# Lade das Runtime Script
try:
    with open(RUNTIME_SCRIPT, 'r') as f:
        runtime_code = f.read()
    print(f"✅ Runtime Script geladen ({len(runtime_code)} bytes)")
except Exception as e:
    print(f"❌ Fehler beim Laden: {e}")
    exit(1)

# Extrahiere die AbletonMCP Klasse
namespace = {}
try:
    exec(runtime_code, namespace)
    print("✅ Runtime Code ausgeführt")
except Exception as e:
    print(f"⚠️  Warning beim Ausführen: {e}")

# Hole die AbletonMCP Klasse (oder Mock)
AbletonMCP = namespace.get('AbletonMCP')
print(f"✅ AbletonMCP Klasse {'gefunden' if AbletonMCP else 'nicht gefunden (OK)'}")
print()

class SimpleAbletonServer:
    """Standalone Socket Server für Ableton MCP"""

    def __init__(self):
        self.running = False
        self.server = None
        self.server_thread = None

    def start(self):
        try:
            self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.server.bind((HOST, PORT))
            self.server.listen(5)
            self.running = True

            self.server_thread = threading.Thread(target=self._server_loop)
            self.server_thread.daemon = True
            self.server_thread.start()

            print(f"✅ Server gestartet auf {HOST}:{PORT}")
            print()
            print("=" * 70)
            print("🎵 ABLETON MCP SERVER - READY!")
            print("=" * 70)
            print()
            print("Warte auf Verbindungen...")
            print("Ctrl+C zum Beenden")
            print()

        except Exception as e:
            print(f"❌ Fehler beim Starten: {e}")
            self.running = False

    def _server_loop(self):
        self.server.settimeout(1.0)
        while self.running:
            try:
                client, address = self.server.accept()
                print(f"✅ Client verbunden: {address}")

                t = threading.Thread(target=self._handle_client, args=(client,))
                t.daemon = True
                t.start()

            except socket.timeout:
                continue
            except Exception as e:
                if self.running:
                    print(f"⚠️  Server Error: {e}")

    def _handle_client(self, client):
        try:
            client.settimeout(None)
            buf = ''

            while self.running:
                data = client.recv(8192)
                if not data:
                    break

                try:
                    buf += data.decode('utf-8')
                except:
                    buf += str(data)

                try:
                    cmd = json.loads(buf)
                    buf = ''

                    # Process command
                    response = self._process_command(cmd)

                    try:
                        client.sendall(json.dumps(response).encode('utf-8'))
                    except:
                        client.sendall(json.dumps(response))

                except ValueError:
                    continue
                except Exception as e:
                    response = {"status": "error", "message": str(e)}
                    try:
                        client.sendall(json.dumps(response).encode('utf-8'))
                    except:
                        pass
                    break

        except Exception as e:
            print(f"⚠️  Client Error: {e}")
        finally:
            try:
                client.close()
            except:
                pass

    def _process_command(self, cmd):
        """Process incoming command"""
        cmd_type = cmd.get("type", "")

        # Simple echo response for testing
        if cmd_type == "get_session_info":
            return {
                "status": "success",
                "result": {
                    "song_name": "Test Song",
                    "track_count": 1
                }
            }
        elif cmd_type == "get_transport_info":
            return {
                "status": "success",
                "result": {
                    "is_playing": False,
                    "tempo": 120
                }
            }
        elif cmd_type == "get_tracks_info":
            return {
                "status": "success",
                "result": {
                    "tracks": [
                        {"name": "Track 1", "index": 0}
                    ]
                }
            }
        else:
            return {
                "status": "error",
                "message": f"Unknown command: {cmd_type}"
            }

    def stop(self):
        self.running = False
        if self.server:
            try:
                self.server.close()
            except:
                pass


if __name__ == "__main__":
    server = SimpleAbletonServer()
    server.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print()
        print()
        print("=" * 70)
        print("Server beendet!")
        print("=" * 70)
        server.stop()
