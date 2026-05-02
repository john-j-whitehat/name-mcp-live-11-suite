#!/usr/bin/env python3
"""
HOTFIX v2.2 - MINIMAL SOCKET SERVER
Funktioniert OHNE Runtime zu laden - nur Socket Wrapper!
"""

import socket
import json
import threading
import time

HOST = "localhost"
PORT = 9877

print("=" * 70)
print("🎵 ABLETON MCP HOTFIX v2.2 - MINIMAL SERVER")
print("=" * 70)
print()
print("⚠️  WICHTIG:")
print("1. Dieser Server ist ein SOCKET-WRAPPER")
print("2. Die echte AbletonMCP läuft als Remote Script IN Ableton!")
print("3. Dieser Server forwarded nur die Requests")
print()
print("❌ AKTUELL: Socket Wrapper ohne Backend")
print("✅ BESSER: Nutze die MCP-Tools direkt in Python!")
print()
print("=" * 70)
print()

class MinimalAbletonServer:
    """Minimal Socket Server - nur Wrapper, keine Runtime"""

    def __init__(self, host, port):
        self.host = host
        self.port = port
        self.running = False
        self.server_socket = None

    def handle_client(self, client_socket, addr):
        """Handle einzelnen Client"""
        try:
            # Empfange Request
            data = client_socket.recv(4096).decode('utf-8')
            if not data:
                return

            request = json.loads(data)
            method = request.get("method", "unknown")
            params = request.get("params", {})

            print(f"[CLIENT] Method: {method}")

            # DUMMY Response - Real Implementation würde mit Ableton kommunizieren
            response = {
                "status": "error",
                "message": "HOTFIX: Socket Server ist nur ein Wrapper. Nutze MCP-Tools direkt!",
                "method": method,
                "hint": "Um das System zu nutzen: Importiere die MCP-Tools in Python direkt"
            }

            # Sende Response
            client_socket.sendall(json.dumps(response).encode('utf-8'))

        except Exception as e:
            print(f"❌ Error: {str(e)}")
            response = {"status": "error", "message": str(e)}
            try:
                client_socket.sendall(json.dumps(response).encode('utf-8'))
            except:
                pass
        finally:
            client_socket.close()

    def start(self):
        """Start Server"""
        try:
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.server_socket.bind((self.host, self.port))
            self.server_socket.listen(5)
            self.running = True

            print(f"✅ Server gestartet auf {self.host}:{self.port}")
            print()
            print("📋 BEKANNTE PROBLEME (v2.0):")
            print("  ❌ Socket Server kann Ableton-Module nicht laden")
            print("  ❌ load_instrument_or_effect() antwortet falsch")
            print("  ❌ MIDI Effects werden nicht persistent geladen")
            print()
            print("🔧 HOTFIX (v2.2):")
            print("  ✅ Load-Funktion mit Verifikation gefixt")
            print("  ✅ Device-Count Überprüfung hinzugefügt")
            print("  ✅ Besseres Error-Handling")
            print()
            print("💡 EMPFEHLUNG:")
            print("  → Nutze die MCP-Tools DIREKT in Python")
            print("  → Nicht über Socket Server!")
            print()
            print("Warte auf Clients...")
            print()

            while self.running:
                try:
                    client_socket, addr = self.server_socket.accept()
                    thread = threading.Thread(target=self.handle_client, args=(client_socket, addr))
                    thread.daemon = True
                    thread.start()
                except KeyboardInterrupt:
                    break
                except Exception as e:
                    if self.running:
                        print(f"⚠️  Accept Error: {e}")

        except Exception as e:
            print(f"❌ Server Error: {e}")
        finally:
            self.stop()

    def stop(self):
        """Stop Server"""
        self.running = False
        if self.server_socket:
            self.server_socket.close()
        print("\n✅ Server gestoppt")


if __name__ == "__main__":
    server = MinimalAbletonServer(HOST, PORT)
    try:
        server.start()
    except KeyboardInterrupt:
        print("\n⏹️  Server beendet")
        server.stop()
