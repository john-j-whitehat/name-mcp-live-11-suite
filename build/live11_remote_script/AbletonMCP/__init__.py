from __future__ import absolute_import, print_function, unicode_literals

# Try new Ableton Live 12 framework first, fall back to old _Framework
try:
    from ableton.v2.control_surface import ControlSurface
except ImportError:
    try:
        from _Framework.ControlSurface import ControlSurface
    except ImportError:
        from ableton.v3.control_surface import ControlSurface

try:
    import Live
except ImportError:
    Live = None

import socket
import json
import threading
import time
import random
import traceback
import os

try:
    import Queue as queue
except ImportError:
    import queue

DEFAULT_PORT = 9877
HOST = "localhost"


def create_instance(c_instance):
    return AbletonMCP(c_instance)


class AbletonMCP(ControlSurface):

    def log_message(self, *args, **kwargs):
        """Compatibility shim - ableton.v2.ControlSurface lacks log_message in some Live 12 builds."""
        try:
            self.c_instance.log_message(*args, **kwargs)
        except Exception:
            pass

    @property
    def _song(self):
        """Resolve the Song object lazily. In Live 12.3.7+, `song` is a property (not a method)."""
        return self.song

    @property
    def _app(self):
        """Resolve the Application object. Handles both callable (older Live) and property (12.3.7+) styles."""
        a = self.application
        try:
            return a() if callable(a) else a
        except Exception:
            return a

    def __init__(self, c_instance):
        try:
            ControlSurface.__init__(self, c_instance)
        except Exception as e:
            self.log_message("AbletonMCP: ControlSurface.__init__ failed: " + repr(e))
            raise
        self.log_message("AbletonMCP initializing (v2-compat)...")
        self.midi_runtime_target = str(os.environ.get("ABLETON_MCP_MIDI_TARGET", "live11")).strip().lower()
        if self.midi_runtime_target not in ["live11", "live12", "auto"]:
            self.midi_runtime_target = "live11"
        self.allow_legacy_midi_fallback = str(os.environ.get("ABLETON_MCP_ALLOW_LEGACY_FALLBACK", "0")).strip().lower() in ["1", "true", "yes", "on"]
        self.server = None
        self.client_threads = []
        self.server_thread = None
        self.running = False
        self.start_server()
        self.log_message(
            "AbletonMCP MIDI policy: target=" + str(self.midi_runtime_target) +
            ", allow_legacy_fallback=" + str(self.allow_legacy_midi_fallback)
        )
        self.log_message("AbletonMCP ready on port " + str(DEFAULT_PORT))
        self.show_message("AbletonMCP: Ready on port " + str(DEFAULT_PORT))

    def disconnect(self):
        self.running = False
        if self.server:
            try:
                self.server.close()
            except:
                pass
        if self.server_thread and self.server_thread.is_alive():
            self.server_thread.join(1.0)
        ControlSurface.disconnect(self)

    def start_server(self):
        try:
            self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.server.bind((HOST, DEFAULT_PORT))
            self.server.listen(5)
            self.running = True
            self.server_thread = threading.Thread(target=self._server_thread)
            self.server_thread.daemon = True
            self.server_thread.start()
        except Exception as e:
            self.log_message("Error starting server: " + str(e))
            self.show_message("AbletonMCP Error: " + str(e))

    def _server_thread(self):
        self.server.settimeout(1.0)
        while self.running:
            try:
                client, address = self.server.accept()
                self.show_message("AbletonMCP: Client connected")
                t = threading.Thread(target=self._handle_client, args=(client,))
                t.daemon = True
                t.start()
                self.client_threads.append(t)
                self.client_threads = [x for x in self.client_threads if x.is_alive()]
            except socket.timeout:
                continue
            except Exception as e:
                if self.running:
                    self.log_message("Accept error: " + str(e))
                time.sleep(0.5)

    def _handle_client(self, client):
        client.settimeout(None)
        buf = ''
        try:
            while self.running:
                data = client.recv(8192)
                if not data:
                    break
                try:
                    buf += data.decode('utf-8')
                except AttributeError:
                    buf += data
                try:
                    cmd = json.loads(buf)
                    buf = ''
                    resp = self._process_command(cmd)
                    try:
                        client.sendall(json.dumps(resp).encode('utf-8'))
                    except AttributeError:
                        client.sendall(json.dumps(resp))
                except ValueError:
                    continue
                except Exception as e:
                    err = {"status": "error", "message": str(e)}
                    try:
                        client.sendall(json.dumps(err).encode('utf-8'))
                    except:
                        break
                    break
        except Exception as e:
            self.log_message("Client error: " + str(e))
        finally:
            try:
                client.close()
            except:
                pass

    def _process_command(self, command):
        t = command.get("type", "")
        p = command.get("params", {})
        resp = {"status": "success", "result": {}}
        try:
            if t == "get_session_info":
                resp["result"] = self._get_session_info()
            elif t == "get_transport_info":
                resp["result"] = self._get_transport_info()
            elif t == "get_scenes_info":
                resp["result"] = self._get_scenes_info()
            elif t == "get_scene_info":
                resp["result"] = self._get_scene_info(p.get("scene_index", 0))
            elif t == "get_tracks_info":
                resp["result"] = self._get_tracks_info()
            elif t == "get_return_tracks_info":
                resp["result"] = self._get_return_tracks_info()
            elif t == "get_track_info":
                resp["result"] = self._get_track_info(p.get("track_index", 0))
            elif t == "get_track_clip_slots":
                resp["result"] = self._get_track_clip_slots(p.get("track_index", 0))
            elif t == "get_clip_info":
                resp["result"] = self._get_clip_info(p.get("track_index", 0), p.get("clip_index", 0))
            elif t == "get_clip_notes":
                resp["result"] = self._get_clip_notes(p.get("track_index", 0), p.get("clip_index", 0))
            elif t == "get_return_track_info":
                resp["result"] = self._get_return_track_info(p.get("return_track_index", 0))
            elif t == "get_return_track_clip_slots":
                resp["result"] = self._get_return_track_clip_slots(p.get("return_track_index", 0))
            elif t == "get_master_track_info":
                resp["result"] = self._get_master_track_info()
            elif t == "get_selected_track_info":
                resp["result"] = self._get_selected_track_info()
            elif t == "get_selected_scene_info":
                resp["result"] = self._get_selected_scene_info()
            elif t == "get_selected_clip_info":
                resp["result"] = self._get_selected_clip_info()
            elif t == "get_track_devices":
                resp["result"] = self._get_track_devices(p.get("track_index", 0))
            elif t == "get_return_track_devices":
                resp["result"] = self._get_return_track_devices(p.get("return_track_index", 0))
            elif t == "get_master_track_devices":
                resp["result"] = self._get_master_track_devices()
            elif t == "get_device_parameters":
                resp["result"] = self._get_device_parameters(p.get("track_kind", "track"), p.get("device_index", 0), p.get("track_index", 0))
            elif t in ["create_midi_track", "create_audio_track", "create_scene", "duplicate_scene", "fire_scene", "fire_selected_scene", "delete_scene", "delete_track", "duplicate_track",
                       "set_track_name", "set_track_arm", "set_track_mute", "set_track_solo", "set_track_volume", "set_track_panning", "set_track_color", "set_scene_name", "rename_selected_track", "rename_selected_scene", "select_track", "select_scene",
                       "create_clip", "delete_clip", "duplicate_clip", "duplicate_selected_clip", "delete_selected_clip", "select_clip_slot", "set_clip_color", "add_notes_to_clip", "transform_midi_clip", "generate_midi_clip",
                       "set_clip_name", "set_tempo", "fire_clip", "fire_selected_clip", "stop_clip", "start_playback", "stop_playback",
                       "stop_all_clips", "select_device", "get_selected_device", "set_device_parameter", "set_selected_device_parameter", "load_browser_item", "load_instrument_or_effect", "load_drum_kit"]:
                q = queue.Queue()
                def task():
                    try:
                        r = None
                        if t == "create_midi_track":
                            r = self._create_midi_track(p.get("index", -1))
                        elif t == "create_audio_track":
                            r = self._create_audio_track(p.get("index", -1))
                        elif t == "create_scene":
                            r = self._create_scene(p.get("index", -1))
                        elif t == "duplicate_scene":
                            r = self._duplicate_scene(p.get("scene_index", 0))
                        elif t == "fire_scene":
                            r = self._fire_scene(p.get("scene_index", 0))
                        elif t == "fire_selected_scene":
                            r = self._fire_selected_scene()
                        elif t == "delete_scene":
                            r = self._delete_scene(p.get("scene_index", 0))
                        elif t == "delete_track":
                            r = self._delete_track(p.get("track_index", 0))
                        elif t == "duplicate_track":
                            r = self._duplicate_track(p.get("track_index", 0))
                        elif t == "set_track_name":
                            r = self._set_track_name(p.get("track_index", 0), p.get("name", ""))
                        elif t == "set_track_arm":
                            r = self._set_track_arm(p.get("track_index", 0), p.get("armed", False))
                        elif t == "set_track_mute":
                            r = self._set_track_mute(p.get("track_index", 0), p.get("muted", False))
                        elif t == "set_track_solo":
                            r = self._set_track_solo(p.get("track_index", 0), p.get("solo", False))
                        elif t == "set_track_volume":
                            r = self._set_track_volume(p.get("track_index", 0), p.get("volume", 0.85))
                        elif t == "set_track_panning":
                            r = self._set_track_panning(p.get("track_index", 0), p.get("panning", 0.0))
                        elif t == "set_track_color":
                            r = self._set_track_color(p.get("track_index", 0), p.get("color", None), p.get("color_index", None))
                        elif t == "set_scene_name":
                            r = self._set_scene_name(p.get("scene_index", 0), p.get("name", ""))
                        elif t == "rename_selected_track":
                            r = self._rename_selected_track(p.get("name", ""))
                        elif t == "rename_selected_scene":
                            r = self._rename_selected_scene(p.get("name", ""))
                        elif t == "select_track":
                            r = self._select_track(p.get("track_kind", "track"), p.get("track_index", 0))
                        elif t == "select_scene":
                            r = self._select_scene(p.get("scene_index", 0))
                        elif t == "create_clip":
                            r = self._create_clip(p.get("track_index", 0), p.get("clip_index", 0), p.get("length", 4.0))
                        elif t == "delete_clip":
                            r = self._delete_clip(p.get("track_kind", "track"), p.get("track_index", 0), p.get("clip_index", 0))
                        elif t == "duplicate_clip":
                            r = self._duplicate_clip(p.get("track_kind", "track"), p.get("track_index", 0), p.get("source_clip_index", 0), p.get("target_clip_index", 1))
                        elif t == "duplicate_selected_clip":
                            r = self._duplicate_selected_clip(p.get("target_clip_index", 1))
                        elif t == "delete_selected_clip":
                            r = self._delete_selected_clip()
                        elif t == "select_clip_slot":
                            r = self._select_clip_slot(p.get("track_kind", "track"), p.get("track_index", 0), p.get("clip_index", 0))
                        elif t == "set_clip_color":
                            r = self._set_clip_color(p.get("track_index", 0), p.get("clip_index", 0), p.get("color", None), p.get("color_index", None))
                        elif t == "add_notes_to_clip":
                            r = self._add_notes_to_clip(p.get("track_index", 0), p.get("clip_index", 0), p.get("notes", []))
                        elif t == "transform_midi_clip":
                            r = self._transform_midi_clip(
                                p.get("track_index", 0), p.get("clip_index", 0), p.get("operation", "transpose"),
                                p.get("semitones", 0), p.get("velocity_delta", 0), p.get("velocity_scale", 1.0),
                                p.get("grid", 0.25), p.get("strength", 1.0), p.get("time_amount", 0.0),
                                p.get("velocity_amount", 0), p.get("axis_pitch", 60), p.get("device_name", ""),
                                p.get("seed", None)
                            )
                        elif t == "generate_midi_clip":
                            r = self._generate_midi_clip(
                                p.get("track_index", 0), p.get("clip_index", 0), p.get("generator", "arpeggio"),
                                p.get("root_note", 60), p.get("scale", "major"), p.get("clip_length", 4.0),
                                p.get("step", 0.25), p.get("note_length", 0.25), p.get("octave_span", 1),
                                p.get("chord_type", "triad"), p.get("pattern", "up"), p.get("pulses", 8),
                                p.get("rotation", 0), p.get("device_name", ""), p.get("seed", None),
                                p.get("replace_existing", True)
                            )
                        elif t == "set_clip_name":
                            r = self._set_clip_name(p.get("track_index", 0), p.get("clip_index", 0), p.get("name", ""))
                        elif t == "set_tempo":
                            r = self._set_tempo(p.get("tempo", 120.0))
                        elif t == "fire_clip":
                            r = self._fire_clip(p.get("track_index", 0), p.get("clip_index", 0))
                        elif t == "fire_selected_clip":
                            r = self._fire_selected_clip()
                        elif t == "stop_clip":
                            r = self._stop_clip(p.get("track_index", 0), p.get("clip_index", 0))
                        elif t == "start_playback":
                            r = self._start_playback()
                        elif t == "stop_playback":
                            r = self._stop_playback()
                        elif t == "stop_all_clips":
                            r = self._stop_all_clips(p.get("quantized", True))
                        elif t == "select_device":
                            r = self._select_device(p.get("track_kind", "track"), p.get("track_index", 0), p.get("device_index", 0))
                        elif t == "get_selected_device":
                            r = self._get_selected_device()
                        elif t == "set_device_parameter":
                            r = self._set_device_parameter(p.get("track_kind", "track"), p.get("track_index", 0), p.get("device_index", 0), p.get("parameter_index", 0), p.get("value", 0.0))
                        elif t == "set_selected_device_parameter":
                            r = self._set_selected_device_parameter(p.get("parameter_index", 0), p.get("value", 0.0))
                        elif t == "load_browser_item":
                            r = self._load_browser_item(p.get("track_index", 0), p.get("item_uri", ""))
                        elif t == "load_instrument_or_effect":
                            r = self._load_instrument_or_effect(p.get("track_index", 0), p.get("uri", ""))
                        elif t == "load_drum_kit":
                            r = self._load_drum_kit(p.get("track_index", 0), p.get("rack_uri", ""), p.get("kit_path", ""))
                        q.put({"status": "success", "result": r})
                    except Exception as e:
                        q.put({"status": "error", "message": str(e)})
                try:
                    self.schedule_message(0, task)
                except AssertionError:
                    task()
                try:
                    tr = q.get(timeout=10.0)
                    if tr.get("status") == "error":
                        resp["status"] = "error"
                        resp["message"] = tr.get("message", "")
                    else:
                        resp["result"] = tr.get("result", {})
                except queue.Empty:
                    resp["status"] = "error"
                    resp["message"] = "Timeout"
            elif t == "get_browser_tree":
                resp["result"] = self.get_browser_tree(p.get("category_type", "all"))
            elif t == "get_browser_categories":
                resp["result"] = self.get_browser_categories(p.get("category_type", "all"))
            elif t == "get_browser_item_info":
                resp["result"] = self.get_browser_item_info(p.get("path", ""), p.get("uri", ""))
            elif t == "get_browser_items_at_path":
                resp["result"] = self.get_browser_items_at_path(p.get("path", ""))
            elif t == "get_browser_items_at_uri":
                resp["result"] = self.get_browser_items_at_uri(p.get("uri", ""))
            elif t == "get_browser_subtree":
                resp["result"] = self.get_browser_subtree(p.get("path", ""), p.get("uri", ""), p.get("max_depth", 2))
            elif t == "get_browser_item_path":
                resp["result"] = self.get_browser_item_path(p.get("path", ""), p.get("uri", ""))
            elif t == "get_browser_stats":
                resp["result"] = self.get_browser_stats(p.get("category_type", "all"), p.get("path", ""), p.get("uri", ""), p.get("max_depth", 10))
            elif t == "search_browser_items":
                resp["result"] = self.search_browser_items(p.get("query", ""), p.get("category_type", "all"), p.get("max_results", 25))
            else:
                resp["status"] = "error"
                resp["message"] = "Unknown command: " + t
        except Exception as e:
            resp["status"] = "error"
            resp["message"] = str(e)
        return resp

    def _get_session_info(self):
        return {
            "tempo": self._song.tempo,
            "signature_numerator": self._song.signature_numerator,
            "signature_denominator": self._song.signature_denominator,
            "track_count": len(self._song.tracks),
            "return_track_count": len(self._song.return_tracks),
            "master_track": {
                "name": "Master",
                "volume": self._song.master_track.mixer_device.volume.value,
                "panning": self._song.master_track.mixer_device.panning.value
            }
        }

    def _get_transport_info(self):
        return {
            "is_playing": self._song.is_playing,
            "current_song_time": self._song.current_song_time,
            "loop": self._song.loop,
            "loop_start": self._song.loop_start,
            "loop_length": self._song.loop_length,
            "overdub": self._song.overdub,
            "metronome": self._song.metronome,
            "record_mode": self._song.record_mode,
        }

    def _get_scenes_info(self):
        selected_scene = self._safe_view_attr(self._song.view, "selected_scene", None)
        scenes = []
        for i, scene in enumerate(self._song.scenes):
            scenes.append(self._serialize_scene(scene, i, scene == selected_scene))
        return {
            "scene_count": len(scenes),
            "scenes": scenes,
        }

    def _get_scene_info(self, scene_index):
        if scene_index < 0 or scene_index >= len(self._song.scenes):
            raise IndexError("Scene index out of range")
        selected_scene = self._safe_view_attr(self._song.view, "selected_scene", None)
        return self._serialize_scene_detail(self._song.scenes[scene_index], scene_index, self._song.scenes[scene_index] == selected_scene)

    def _get_tracks_info(self):
        tracks = []
        for i, track in enumerate(self._song.tracks):
            tracks.append(self._serialize_track_summary(track, i, "track"))
        return {
            "track_count": len(tracks),
            "tracks": tracks,
        }

    def _get_return_tracks_info(self):
        tracks = []
        for i, track in enumerate(self._song.return_tracks):
            tracks.append(self._serialize_track_summary(track, i, "return"))
        return {
            "return_track_count": len(tracks),
            "tracks": tracks,
        }

    def _get_track_info(self, track_index):
        if track_index < 0 or track_index >= len(self._song.tracks):
            raise IndexError("Track index out of range")
        return self._serialize_track(self._song.tracks[track_index], track_index, "track")

    def _get_track_clip_slots(self, track_index):
        if track_index < 0 or track_index >= len(self._song.tracks):
            raise IndexError("Track index out of range")
        track = self._song.tracks[track_index]
        clip_slots = []
        filled_slot_count = 0
        for i, slot in enumerate(track.clip_slots):
            slot_info = self._serialize_clip_slot(slot, i)
            if slot_info["has_clip"]:
                filled_slot_count += 1
            clip_slots.append(slot_info)
        return {"track_kind": "track", "track_index": track_index, "track_name": track.name, "clip_slot_count": len(clip_slots), "filled_slot_count": filled_slot_count, "clip_slots": clip_slots}

    def _get_clip_info(self, track_index, clip_index):
        if track_index < 0 or track_index >= len(self._song.tracks):
            raise IndexError("Track index out of range")
        track = self._song.tracks[track_index]
        if clip_index < 0 or clip_index >= len(track.clip_slots):
            raise IndexError("Clip index out of range")
        return self._serialize_clip_slot(track.clip_slots[clip_index], clip_index)

    def _get_clip_notes(self, track_index, clip_index):
        if track_index < 0 or track_index >= len(self._song.tracks):
            raise IndexError("Track index out of range")
        track = self._song.tracks[track_index]
        if not track.has_midi_input:
            raise ValueError("Clip notes are only available for MIDI tracks")
        if clip_index < 0 or clip_index >= len(track.clip_slots):
            raise IndexError("Clip index out of range")
        slot = track.clip_slots[clip_index]
        if not slot.has_clip:
            return {"track_index": track_index, "clip_index": clip_index, "has_clip": False, "notes": [], "note_count": 0}
        clip = slot.clip
        try:
            notes = clip.get_notes(0.0, 0, clip.length, 128)
        except Exception:
            raise ValueError("Clip notes are only available for MIDI clips")
        serialized_notes = []
        for note in notes:
            serialized_notes.append({
                "pitch": note[0],
                "start_time": note[1],
                "duration": note[2],
                "velocity": note[3],
                "mute": note[4],
            })
        return {
            "track_index": track_index,
            "clip_index": clip_index,
            "has_clip": True,
            "clip_name": clip.name,
            "clip_length": clip.length,
            "note_count": len(serialized_notes),
            "notes": serialized_notes,
        }

    def _create_midi_track(self, index):
        self._song.create_midi_track(index)
        i = len(self._song.tracks) - 1 if index == -1 else index
        return {"index": i, "name": self._song.tracks[i].name}

    def _create_audio_track(self, index):
        if not hasattr(self._song, "create_audio_track"):
            raise ValueError("Audio track creation is not supported in this Live build")
        self._song.create_audio_track(index)
        i = len(self._song.tracks) - 1 if index == -1 else int(index)
        return self._serialize_track(self._song.tracks[i], i, "track")

    def _create_scene(self, index):
        self._song.create_scene(index)
        scene_index = len(self._song.scenes) - 1 if index == -1 else int(index)
        return self._serialize_scene_detail(self._song.scenes[scene_index], scene_index, False)

    def _duplicate_scene(self, scene_index):
        if scene_index < 0 or scene_index >= len(self._song.scenes):
            raise IndexError("Scene index out of range")
        self._song.duplicate_scene(scene_index)
        duplicated_index = min(scene_index + 1, len(self._song.scenes) - 1)
        return self._serialize_scene_detail(self._song.scenes[duplicated_index], duplicated_index, False)

    def _fire_scene(self, scene_index):
        if scene_index < 0 or scene_index >= len(self._song.scenes):
            raise IndexError("Scene index out of range")
        self._song.scenes[scene_index].fire()
        return {"scene_index": scene_index, "fired": True}

    def _fire_selected_scene(self):
        scene = self._safe_view_attr(self._song.view, "selected_scene", None)
        if scene is None:
            raise ValueError("No selected scene")
        scene_index = self._find_scene_index(scene)
        scene.fire()
        return {"scene_index": scene_index, "scene_name": scene.name, "fired": True, "is_selected": True}

    def _delete_scene(self, scene_index):
        if scene_index < 0 or scene_index >= len(self._song.scenes):
            raise IndexError("Scene index out of range")
        scene_name = self._song.scenes[scene_index].name
        self._song.delete_scene(scene_index)
        return {"deleted_scene_index": scene_index, "deleted_scene_name": scene_name}

    def _delete_track(self, track_index):
        if track_index < 0 or track_index >= len(self._song.tracks):
            raise IndexError("Track index out of range")
        name = self._song.tracks[track_index].name
        self._song.delete_track(track_index)
        return {"deleted_index": track_index, "deleted_name": name}

    def _duplicate_track(self, track_index):
        if track_index < 0 or track_index >= len(self._song.tracks):
            raise IndexError("Track index out of range")
        if not hasattr(self._song, "duplicate_track"):
            raise ValueError("Track duplication is not supported in this Live build")
        self._song.duplicate_track(track_index)
        duplicated_index = min(track_index + 1, len(self._song.tracks) - 1)
        return self._serialize_track(self._song.tracks[duplicated_index], duplicated_index, "track")

    def _set_track_name(self, track_index, name):
        if track_index < 0 or track_index >= len(self._song.tracks):
            raise IndexError("Track index out of range")
        self._song.tracks[track_index].name = name
        return {"name": self._song.tracks[track_index].name}

    def _set_track_arm(self, track_index, armed):
        if track_index < 0 or track_index >= len(self._song.tracks):
            raise IndexError("Track index out of range")
        track = self._song.tracks[track_index]
        if hasattr(track, "can_be_armed") and not track.can_be_armed:
            raise ValueError("Track cannot be armed")
        if not hasattr(track, "arm"):
            raise ValueError("Track does not support arming")
        track.arm = bool(armed)
        return {"track_index": track_index, "armed": bool(track.arm)}

    def _set_track_mute(self, track_index, muted):
        if track_index < 0 or track_index >= len(self._song.tracks):
            raise IndexError("Track index out of range")
        track = self._song.tracks[track_index]
        track.mute = bool(muted)
        return {"track_index": track_index, "muted": bool(track.mute)}

    def _set_track_solo(self, track_index, solo):
        if track_index < 0 or track_index >= len(self._song.tracks):
            raise IndexError("Track index out of range")
        track = self._song.tracks[track_index]
        track.solo = bool(solo)
        return {"track_index": track_index, "solo": bool(track.solo)}

    def _set_track_volume(self, track_index, volume):
        if track_index < 0 or track_index >= len(self._song.tracks):
            raise IndexError("Track index out of range")
        track = self._song.tracks[track_index]
        clamped_volume = float(self._clamp(float(volume), 0.0, 1.0))
        track.mixer_device.volume.value = clamped_volume
        return {"track_index": track_index, "volume": float(track.mixer_device.volume.value)}

    def _set_track_panning(self, track_index, panning):
        if track_index < 0 or track_index >= len(self._song.tracks):
            raise IndexError("Track index out of range")
        track = self._song.tracks[track_index]
        clamped_panning = float(self._clamp(float(panning), -1.0, 1.0))
        track.mixer_device.panning.value = clamped_panning
        return {"track_index": track_index, "panning": float(track.mixer_device.panning.value)}

    def _apply_color_fields(self, target, color, color_index):
        if color is not None:
            target.color = int(color)
        if color_index is not None:
            target.color_index = int(color_index)

    def _set_track_color(self, track_index, color=None, color_index=None):
        if track_index < 0 or track_index >= len(self._song.tracks):
            raise IndexError("Track index out of range")
        if color is None and color_index is None:
            raise ValueError("Either color or color_index is required")
        track = self._song.tracks[track_index]
        self._apply_color_fields(track, color, color_index)
        return self._serialize_track(track, track_index, "track")

    def _set_scene_name(self, scene_index, name):
        if scene_index < 0 or scene_index >= len(self._song.scenes):
            raise IndexError("Scene index out of range")
        scene = self._song.scenes[scene_index]
        scene.name = name
        return self._serialize_scene_detail(scene, scene_index, scene == self._safe_view_attr(self._song.view, "selected_scene", None))

    def _rename_selected_track(self, name):
        track = self._safe_view_attr(self._song.view, "selected_track", None)
        if track is None:
            raise ValueError("No selected track")
        if track == self._song.master_track:
            track.name = name
            return self._serialize_track(track, None, "master")
        for i, current_track in enumerate(self._song.tracks):
            if current_track == track:
                current_track.name = name
                return self._serialize_track(current_track, i, "track")
        for i, current_track in enumerate(self._song.return_tracks):
            if current_track == track:
                current_track.name = name
                return self._serialize_track(current_track, i, "return")
        raise ValueError("Selected track could not be resolved")

    def _rename_selected_scene(self, name):
        scene = self._safe_view_attr(self._song.view, "selected_scene", None)
        if scene is None:
            raise ValueError("No selected scene")
        scene_index = self._find_scene_index(scene)
        scene.name = name
        return self._serialize_scene_detail(scene, scene_index, True)

    def _select_track(self, track_kind, track_index):
        track = self._resolve_track_reference(track_kind, track_index)
        self._song.view.selected_track = track
        return self._serialize_selected_track(track)

    def _select_scene(self, scene_index):
        if scene_index < 0 or scene_index >= len(self._song.scenes):
            raise IndexError("Scene index out of range")
        scene = self._song.scenes[scene_index]
        self._song.view.selected_scene = scene
        return self._serialize_scene_detail(scene, scene_index, True)

    def _get_clip_slot_reference(self, track_kind, track_index, clip_index):
        if clip_index < 0:
            raise IndexError("Clip index out of range")
        track = self._resolve_track_reference(track_kind, track_index)
        if not hasattr(track, "clip_slots"):
            raise ValueError("Track kind does not support clip slots")
        if clip_index >= len(track.clip_slots):
            raise IndexError("Clip index out of range")
        return track, track.clip_slots[clip_index]

    def _delete_clip(self, track_kind, track_index, clip_index):
        track, slot = self._get_clip_slot_reference(track_kind, track_index, clip_index)
        if not slot.has_clip:
            raise ValueError("No clip in slot")
        clip_name = slot.clip.name
        slot.delete_clip()
        return {
            "track_kind": track_kind,
            "track_index": track_index,
            "track_name": track.name,
            "clip_index": clip_index,
            "deleted_clip_name": clip_name,
            "has_clip": bool(slot.has_clip),
        }

    def _duplicate_clip(self, track_kind, track_index, source_clip_index, target_clip_index):
        track, source_slot = self._get_clip_slot_reference(track_kind, track_index, source_clip_index)
        _, target_slot = self._get_clip_slot_reference(track_kind, track_index, target_clip_index)
        if not source_slot.has_clip:
            raise ValueError("No clip in source slot")
        if target_slot.has_clip:
            raise ValueError("Target clip slot already has a clip")
        source_slot.duplicate_clip_to(target_slot)
        result = self._serialize_clip_slot(target_slot, target_clip_index)
        result.update({
            "track_kind": track_kind,
            "track_index": track_index,
            "track_name": track.name,
            "source_clip_index": source_clip_index,
            "target_clip_index": target_clip_index,
        })
        return result

    def _duplicate_selected_clip(self, target_clip_index):
        clip_slot = self._safe_view_attr(self._song.view, "highlighted_clip_slot", None)
        if clip_slot is None:
            raise ValueError("No selected clip slot")
        location = self._find_clip_slot_location(clip_slot)
        if location is None:
            raise ValueError("Selected clip slot could not be resolved")
        return self._duplicate_clip(location["track_kind"], location["track_index"], location["clip_index"], target_clip_index)

    def _delete_selected_clip(self):
        clip_slot = self._safe_view_attr(self._song.view, "highlighted_clip_slot", None)
        if clip_slot is None:
            raise ValueError("No selected clip slot")
        location = self._find_clip_slot_location(clip_slot)
        if location is None:
            raise ValueError("Selected clip slot could not be resolved")
        return self._delete_clip(location["track_kind"], location["track_index"], location["clip_index"])

    def _select_clip_slot(self, track_kind, track_index, clip_index):
        track, slot = self._get_clip_slot_reference(track_kind, track_index, clip_index)
        if track_kind == "master":
            raise ValueError("Master track does not support clip slot selection")
        self._song.view.selected_track = track
        if clip_index < len(self._song.scenes):
            self._song.view.selected_scene = self._song.scenes[clip_index]
        if hasattr(self._song.view, "highlighted_clip_slot"):
            self._song.view.highlighted_clip_slot = slot
        result = self._serialize_clip_slot(slot, clip_index)
        result.update({
            "track_kind": track_kind,
            "track_index": track_index,
            "track_name": track.name,
            "clip_index": clip_index,
            "is_selected": True,
        })
        return result

    def _set_clip_color(self, track_index, clip_index, color=None, color_index=None):
        if color is None and color_index is None:
            raise ValueError("Either color or color_index is required")
        track, slot, clip = self._get_midi_clip_for_edit(track_index, clip_index, allow_create=False)
        self._apply_color_fields(clip, color, color_index)
        return {
            "track_index": track_index,
            "track_name": track.name,
            "clip_index": clip_index,
            "clip_name": clip.name,
            "color": self._safe_view_attr(clip, "color", None),
            "color_index": self._safe_view_attr(clip, "color_index", None),
        }

    def _create_clip(self, track_index, clip_index, length):
        if track_index < 0 or track_index >= len(self._song.tracks):
            raise IndexError("Track index out of range")
        track = self._song.tracks[track_index]
        if not track.has_midi_input:
            raise ValueError("create_clip is only available for MIDI tracks")
        if clip_index < 0 or clip_index >= len(track.clip_slots):
            raise IndexError("Clip index out of range")
        clip_length = max(0.03125, float(length))
        slot = track.clip_slots[clip_index]
        if slot.has_clip:
            raise ValueError("Clip slot already has a clip")
        slot.create_clip(clip_length)
        return {
            "track_index": track_index,
            "clip_index": clip_index,
            "length": clip_length,
            "has_clip": bool(slot.has_clip),
            "clip_name": slot.clip.name if slot.has_clip else "",
        }

    def _add_notes_to_clip(self, track_index, clip_index, notes):
        track, slot, clip = self._get_midi_clip_for_edit(track_index, clip_index, allow_create=False)
        clip_length = float(clip.length)
        normalized_notes = self._normalize_notes(notes or [], clip_length)
        if not normalized_notes:
            return {
                "track_index": track_index,
                "clip_index": clip_index,
                "clip_name": clip.name,
                "clip_length": clip_length,
                "note_count": 0,
                "note_ids": [],
            }

        note_ids = []
        if hasattr(clip, "add_new_notes"):
            note_ids = clip.add_new_notes(self._prepare_add_new_notes_payload(normalized_notes)) or []
        else:
            existing_notes = self._read_clip_notes(clip)
            combined_notes = self._normalize_notes(existing_notes + normalized_notes, clip_length)
            self._replace_clip_notes(clip, combined_notes, replace_existing=True)

        return {
            "track_index": track_index,
            "clip_index": clip_index,
            "clip_name": clip.name,
            "clip_length": clip_length,
            "note_count": len(normalized_notes),
            "note_ids": note_ids,
        }

    def _get_return_track_info(self, return_track_index):
        if return_track_index < 0 or return_track_index >= len(self._song.return_tracks):
            raise IndexError("Return track index out of range")
        track = self._song.return_tracks[return_track_index]
        return self._serialize_track(track, return_track_index, "return")

    def _get_return_track_clip_slots(self, return_track_index):
        if return_track_index < 0 or return_track_index >= len(self._song.return_tracks):
            raise IndexError("Return track index out of range")
        track = self._song.return_tracks[return_track_index]
        clip_slots = []
        filled_slot_count = 0
        for i, slot in enumerate(track.clip_slots):
            slot_info = self._serialize_clip_slot(slot, i)
            if slot_info["has_clip"]:
                filled_slot_count += 1
            clip_slots.append(slot_info)
        return {"track_kind": "return", "track_index": return_track_index, "track_name": track.name, "clip_slot_count": len(clip_slots), "filled_slot_count": filled_slot_count, "clip_slots": clip_slots}

    def _get_master_track_info(self):
        return self._serialize_track(self._song.master_track, None, "master")

    def _get_selected_track_info(self):
        selected_track = self._safe_view_attr(self._song.view, "selected_track", None)
        if selected_track is None:
            raise ValueError("No selected track")
        return self._serialize_selected_track(selected_track)

    def _get_selected_scene_info(self):
        scene = self._safe_view_attr(self._song.view, "selected_scene", None)
        if scene is None:
            raise ValueError("No selected scene")
        return self._serialize_scene(scene, self._find_scene_index(scene), True)

    def _get_selected_clip_info(self):
        clip_slot = self._safe_view_attr(self._song.view, "highlighted_clip_slot", None)
        if clip_slot is None:
            raise ValueError("No selected clip slot")
        location = self._find_clip_slot_location(clip_slot)
        if location is None:
            raise ValueError("Selected clip slot could not be resolved")
        result = self._serialize_clip_slot(clip_slot, location["clip_index"])
        result.update(location)
        result["is_selected"] = True
        return result

    def _get_track_devices(self, track_index):
        track = self._resolve_track_reference("track", track_index)
        return self._serialize_track_devices(track, track_index, "track")

    def _get_return_track_devices(self, return_track_index):
        track = self._resolve_track_reference("return", return_track_index)
        return self._serialize_track_devices(track, return_track_index, "return")

    def _get_master_track_devices(self):
        track = self._resolve_track_reference("master", 0)
        return self._serialize_track_devices(track, None, "master")

    def _get_device_parameters(self, track_kind, device_index, track_index):
        track = self._resolve_track_reference(track_kind, track_index)
        if device_index < 0 or device_index >= len(track.devices):
            raise IndexError("Device index out of range")
        device = track.devices[device_index]
        return self._serialize_device_parameters(device, device_index, track_kind, track_index)

    def _resolve_device_reference(self, track_kind, track_index, device_index):
        track = self._resolve_track_reference(track_kind, track_index)
        if device_index < 0 or device_index >= len(track.devices):
            raise IndexError("Device index out of range")
        return track, track.devices[device_index]

    def _find_device_location(self, device):
        if device is None:
            return None
        for track_index, track in enumerate(self._song.tracks):
            for device_index, current_device in enumerate(track.devices):
                if current_device == device:
                    return {"track_kind": "track", "track_index": track_index, "track_name": track.name, "device_index": device_index}
        for track_index, track in enumerate(self._song.return_tracks):
            for device_index, current_device in enumerate(track.devices):
                if current_device == device:
                    return {"track_kind": "return", "track_index": track_index, "track_name": track.name, "device_index": device_index}
        for device_index, current_device in enumerate(self._song.master_track.devices):
            if current_device == device:
                return {"track_kind": "master", "track_index": None, "track_name": self._song.master_track.name, "device_index": device_index}
        return None

    def _select_device(self, track_kind, track_index, device_index):
        track, device = self._resolve_device_reference(track_kind, track_index, device_index)
        if hasattr(self._song, "appointed_device"):
            self._song.appointed_device = device
        if self._safe_view_attr(self._song.view, "selected_track", None) != track and track_kind != "master":
            self._song.view.selected_track = track
        result = self._serialize_device_parameters(device, device_index, track_kind, track_index)
        result["is_selected"] = True
        return result

    def _get_selected_device(self):
        device = self._safe_view_attr(self._song, "appointed_device", None)
        if device is None:
            raise ValueError("No selected device")
        location = self._find_device_location(device)
        if location is None:
            raise ValueError("Selected device could not be resolved")
        result = self._serialize_device_parameters(device, location["device_index"], location["track_kind"], 0 if location["track_index"] is None else location["track_index"])
        result["track_index"] = location["track_index"]
        result["track_name"] = location["track_name"]
        result["is_selected"] = True
        return result

    def _set_device_parameter(self, track_kind, track_index, device_index, parameter_index, value):
        track, device = self._resolve_device_reference(track_kind, track_index, device_index)
        if parameter_index < 0 or parameter_index >= len(device.parameters):
            raise IndexError("Parameter index out of range")
        parameter = device.parameters[parameter_index]
        target_value = float(value)
        minimum = self._safe_view_attr(parameter, "min", None)
        maximum = self._safe_view_attr(parameter, "max", None)
        if minimum is not None and maximum is not None:
            target_value = float(self._clamp(target_value, minimum, maximum))
        parameter.value = target_value
        return {
            "track_kind": track_kind,
            "track_index": track_index,
            "track_name": track.name,
            "device": self._serialize_device(device, device_index),
            "parameter": {
                "index": parameter_index,
                "name": parameter.name,
                "value": parameter.value,
                "min": minimum,
                "max": maximum,
                "is_quantized": self._safe_view_attr(parameter, "is_quantized", None),
            },
        }

    def _set_selected_device_parameter(self, parameter_index, value):
        device = self._safe_view_attr(self._song, "appointed_device", None)
        if device is None:
            raise ValueError("No selected device")
        location = self._find_device_location(device)
        if location is None:
            raise ValueError("Selected device could not be resolved")
        return self._set_device_parameter(location["track_kind"], 0 if location["track_index"] is None else location["track_index"], location["device_index"], parameter_index, value)

    def _safe_track_attr(self, track, attr_name, default):
        try:
            return getattr(track, attr_name)
        except Exception:
            return default

    def _safe_view_attr(self, obj, attr_name, default):
        try:
            return getattr(obj, attr_name)
        except Exception:
            return default

    def _serialize_clip_slot(self, slot, clip_index):
        clip_info = None
        if slot.has_clip:
            c = slot.clip
            clip_info = {
                "name": c.name,
                "length": c.length,
                "is_playing": c.is_playing,
                "is_recording": c.is_recording,
                "is_triggered": c.is_triggered,
                "color": self._safe_view_attr(c, "color", None)
            }
        return {"index": clip_index, "has_clip": slot.has_clip, "clip": clip_info}

    def _serialize_scene(self, scene, scene_index, is_selected):
        return {
            "index": scene_index,
            "name": scene.name,
            "is_empty": self._scene_is_empty(scene),
            "is_selected": is_selected,
        }

    def _serialize_scene_detail(self, scene, scene_index, is_selected):
        clip_slots = []
        filled_slot_count = 0
        for i, slot in enumerate(scene.clip_slots):
            slot_info = self._serialize_clip_slot(slot, i)
            if slot_info["has_clip"]:
                filled_slot_count += 1
            clip_slots.append(slot_info)
        result = self._serialize_scene(scene, scene_index, is_selected)
        result["clip_slot_count"] = len(clip_slots)
        result["filled_slot_count"] = filled_slot_count
        result["clip_slots"] = clip_slots
        return result

    def _scene_is_empty(self, scene):
        try:
            return not any(slot.has_clip for slot in scene.clip_slots)
        except Exception:
            return False

    def _find_scene_index(self, scene):
        for i, current_scene in enumerate(self._song.scenes):
            if current_scene == scene:
                return i
        return None

    def _find_clip_slot_location(self, clip_slot):
        for track_index, track in enumerate(self._song.tracks):
            for slot_index, current_slot in enumerate(track.clip_slots):
                if current_slot == clip_slot:
                    return {"track_kind": "track", "track_index": track_index, "track_name": track.name, "clip_index": slot_index}
        for track_index, track in enumerate(self._song.return_tracks):
            for slot_index, current_slot in enumerate(track.clip_slots):
                if current_slot == clip_slot:
                    return {"track_kind": "return", "track_index": track_index, "track_name": track.name, "clip_index": slot_index}
        return None

    def _serialize_selected_track(self, track):
        if track == self._song.master_track:
            return self._serialize_track(track, None, "master")
        for i, current_track in enumerate(self._song.return_tracks):
            if current_track == track:
                return self._serialize_track(track, i, "return")
        for i, current_track in enumerate(self._song.tracks):
            if current_track == track:
                return self._serialize_track(track, i, "track")
        return self._serialize_track(track, None, "unknown")

    def _serialize_track_summary(self, track, track_index, track_kind):
        clip_slot_count = len(track.clip_slots) if hasattr(track, "clip_slots") else 0
        return {
            "track_kind": track_kind,
            "index": track_index,
            "name": track.name,
            "is_audio_track": track.has_audio_input,
            "is_midi_track": track.has_midi_input,
            "mute": self._safe_track_attr(track, "mute", False),
            "solo": self._safe_track_attr(track, "solo", False),
            "arm": self._safe_track_attr(track, "arm", False),
            "clip_slot_count": clip_slot_count,
            "device_count": len(track.devices),
            "volume": track.mixer_device.volume.value,
            "panning": track.mixer_device.panning.value,
        }

    def _resolve_track_reference(self, track_kind, track_index):
        if track_kind == "track":
            if track_index < 0 or track_index >= len(self._song.tracks):
                raise IndexError("Track index out of range")
            return self._song.tracks[track_index]
        if track_kind == "return":
            if track_index < 0 or track_index >= len(self._song.return_tracks):
                raise IndexError("Return track index out of range")
            return self._song.return_tracks[track_index]
        if track_kind == "master":
            return self._song.master_track
        raise ValueError("Unknown track kind: " + str(track_kind))

    def _serialize_track_devices(self, track, track_index, track_kind):
        devices = []
        for i, device in enumerate(track.devices):
            devices.append(self._serialize_device(device, i))
        return {
            "track_kind": track_kind,
            "track_index": track_index,
            "track_name": track.name,
            "device_count": len(devices),
            "devices": devices,
        }

    def _serialize_device(self, device, device_index):
        return {
            "index": device_index,
            "name": device.name,
            "class_name": device.class_name,
            "class_display_name": self._safe_view_attr(device, "class_display_name", None),
            "type": self._get_device_type(device),
            "can_have_chains": self._safe_view_attr(device, "can_have_chains", False),
            "can_have_drum_pads": self._safe_view_attr(device, "can_have_drum_pads", False),
            "parameter_count": len(device.parameters) if hasattr(device, "parameters") else 0,
        }

    def _serialize_device_parameters(self, device, device_index, track_kind, track_index):
        parameters = []
        if hasattr(device, "parameters"):
            for i, parameter in enumerate(device.parameters):
                parameters.append({
                    "index": i,
                    "name": parameter.name,
                    "value": parameter.value,
                    "min": self._safe_view_attr(parameter, "min", None),
                    "max": self._safe_view_attr(parameter, "max", None),
                    "is_enabled": self._safe_view_attr(parameter, "is_enabled", None),
                    "is_quantized": self._safe_view_attr(parameter, "is_quantized", None),
                })
        return {
            "track_kind": track_kind,
            "track_index": track_index,
            "device": self._serialize_device(device, device_index),
            "parameters": parameters,
        }

    def _serialize_track(self, track, track_index, track_kind):
        clip_slots = []
        if hasattr(track, "clip_slots"):
            for i, slot in enumerate(track.clip_slots):
                clip_slots.append(self._serialize_clip_slot(slot, i))
        devices = [self._serialize_device(d, i) for i, d in enumerate(track.devices)]
        return {
            "track_kind": track_kind,
            "index": track_index,
            "name": track.name,
            "is_audio_track": track.has_audio_input,
            "is_midi_track": track.has_midi_input,
            "mute": self._safe_track_attr(track, "mute", False),
            "solo": self._safe_track_attr(track, "solo", False),
            "arm": self._safe_track_attr(track, "arm", False),
            "volume": track.mixer_device.volume.value,
            "panning": track.mixer_device.panning.value,
            "clip_slots": clip_slots,
            "devices": devices
        }

    def _clamp(self, value, minimum, maximum):
        return max(minimum, min(maximum, value))

    def _find_matching_track_device(self, track, device_name):
        if not device_name:
            return None
        needle = str(device_name).lower()
        for device in track.devices:
            candidates = [
                getattr(device, "name", None),
                getattr(device, "class_name", None),
                self._safe_view_attr(device, "class_display_name", None),
            ]
            for candidate in candidates:
                if candidate and needle in str(candidate).lower():
                    return getattr(device, "name", candidate)
        raise ValueError("Required device not found on track: " + str(device_name))

    def _get_midi_clip_for_edit(self, track_index, clip_index, allow_create=False, clip_length=4.0):
        if track_index < 0 or track_index >= len(self._song.tracks):
            raise IndexError("Track index out of range")
        track = self._song.tracks[track_index]
        if not track.has_midi_input:
            raise ValueError("Transform/Generate are only available for MIDI tracks")
        if clip_index < 0 or clip_index >= len(track.clip_slots):
            raise IndexError("Clip index out of range")
        slot = track.clip_slots[clip_index]
        if not slot.has_clip:
            if not allow_create:
                raise ValueError("No clip in slot")
            slot.create_clip(max(0.25, float(clip_length)))
        clip = slot.clip
        try:
            self._read_clip_notes(clip)
        except Exception:
            raise ValueError("Transform/Generate are only available for MIDI clips")
        return track, slot, clip

    def _serialize_note_dict(self, note):
        if isinstance(note, (list, tuple)):
            serialized = {
                "pitch": int(note[0]) if len(note) > 0 else 60,
                "start_time": float(note[1]) if len(note) > 1 else 0.0,
                "duration": float(note[2]) if len(note) > 2 else 0.25,
                "velocity": int(note[3]) if len(note) > 3 else 100,
                "mute": bool(note[4]) if len(note) > 4 else False,
            }
            if len(note) > 5:
                serialized["note_id"] = note[5]
            if len(note) > 6:
                serialized["probability"] = float(note[6])
            if len(note) > 7:
                serialized["velocity_deviation"] = float(note[7])
            if len(note) > 8:
                serialized["release_velocity"] = float(note[8])
            return serialized
        serialized = {
            "pitch": int(note.get("pitch", 60)),
            "start_time": float(note.get("start_time", 0.0)),
            "duration": float(note.get("duration", 0.25)),
            "velocity": int(note.get("velocity", 100)),
            "mute": bool(note.get("mute", False)),
        }
        if "note_id" in note:
            serialized["note_id"] = note["note_id"]
        if "probability" in note:
            serialized["probability"] = float(note.get("probability", 1.0))
        if "velocity_deviation" in note:
            serialized["velocity_deviation"] = float(note.get("velocity_deviation", 0.0))
        if "release_velocity" in note:
            serialized["release_velocity"] = float(note.get("release_velocity", 64.0))
        return serialized

    def _get_clip_notes_extended(self, clip):
        if not hasattr(clip, "get_notes_extended"):
            return None
        clip_length = float(clip.length)
        try:
            payload = clip.get_notes_extended({
                "from_pitch": 0,
                "pitch_span": 128,
                "from_time": 0.0,
                "time_span": clip_length,
            })
        except Exception:
            try:
                payload = clip.get_notes_extended(0, 128, 0.0, clip_length)
            except Exception:
                return None
        if isinstance(payload, dict):
            notes = payload.get("notes", [])
        else:
            notes = payload or []
        try:
            return [self._serialize_note_dict(note) for note in notes]
        except Exception:
            return None

    def _read_clip_notes(self, clip):
        extended_notes = self._get_clip_notes_extended(clip)
        if extended_notes is not None:
            return extended_notes
        notes = clip.get_notes(0.0, 0, clip.length, 128)
        return [{
            "pitch": note[0],
            "start_time": note[1],
            "duration": note[2],
            "velocity": note[3],
            "mute": note[4],
        } for note in notes]

    def _normalize_notes(self, notes, clip_length):
        normalized = []
        for note in notes:
            start_time = max(0.0, float(note.get("start_time", 0.0)))
            duration = max(0.03125, float(note.get("duration", 0.25)))
            if start_time >= clip_length:
                continue
            duration = min(duration, max(0.03125, clip_length - start_time))
            normalized_note = {
                "pitch": int(self._clamp(int(round(note.get("pitch", 60))), 0, 127)),
                "start_time": start_time,
                "duration": duration,
                "velocity": int(self._clamp(int(round(note.get("velocity", 100))), 1, 127)),
                "mute": bool(note.get("mute", False)),
            }
            if "note_id" in note:
                normalized_note["note_id"] = note["note_id"]
            if "probability" in note:
                normalized_note["probability"] = float(self._clamp(float(note.get("probability", 1.0)), 0.0, 1.0))
            if "velocity_deviation" in note:
                normalized_note["velocity_deviation"] = float(self._clamp(float(note.get("velocity_deviation", 0.0)), -127.0, 127.0))
            if "release_velocity" in note:
                normalized_note["release_velocity"] = float(self._clamp(float(note.get("release_velocity", 64.0)), 0.0, 127.0))
            normalized.append(normalized_note)
        normalized.sort(key=lambda note: (note["start_time"], note["pitch"], note["duration"]))
        return normalized

    def _build_note_specification(self, note, include_id=False):
        spec = {
            "pitch": int(note["pitch"]),
            "start_time": float(note["start_time"]),
            "duration": float(note["duration"]),
            "velocity": int(note.get("velocity", 100)),
            "mute": bool(note.get("mute", False)),
        }
        if "probability" in note:
            spec["probability"] = float(note.get("probability", 1.0))
        if "velocity_deviation" in note:
            spec["velocity_deviation"] = float(note.get("velocity_deviation", 0.0))
        if "release_velocity" in note:
            spec["release_velocity"] = float(note.get("release_velocity", 64.0))
        if include_id and "note_id" in note:
            spec["note_id"] = int(note["note_id"])
        return spec

    def _build_strict_note_dict(self, note, include_id=False):
        strict_note = {
            "pitch": int(note["pitch"]),
            "start_time": float(note["start_time"]),
            "duration": float(note["duration"]),
            "velocity": float(int(note.get("velocity", 100))),
            "mute": bool(note.get("mute", False)),
        }
        if include_id and "note_id" in note:
            strict_note["note_id"] = int(note["note_id"])
        if "probability" in note:
            strict_note["probability"] = float(note["probability"])
        if "velocity_deviation" in note:
            strict_note["velocity_deviation"] = float(note["velocity_deviation"])
        if "release_velocity" in note:
            strict_note["release_velocity"] = float(note["release_velocity"])
        return strict_note

    def _build_live_midi_note_specification(self, note):
        if Live is None or not hasattr(Live, "Clip") or not hasattr(Live.Clip, "MidiNoteSpecification"):
            raise RuntimeError("Live.Clip.MidiNoteSpecification unavailable")
        note_class = Live.Clip.MidiNoteSpecification
        pitch = int(note["pitch"])
        start_time = float(note["start_time"])
        duration = float(note["duration"])
        velocity = float(int(note.get("velocity", 100)))
        mute = bool(note.get("mute", False))
        attempts = [
            lambda: note_class(pitch=pitch, start_time=start_time, duration=duration, velocity=velocity, mute=mute),
            lambda: note_class(pitch, start_time, duration, velocity, mute),
        ]
        last_error = None
        for attempt in attempts:
            try:
                return attempt()
            except Exception as exc:
                last_error = exc
        raise RuntimeError("MidiNoteSpecification construction failed: " + str(last_error))

    def _call_add_new_notes_modern(self, clip, notes):
        errors = []
        if hasattr(clip, "add_new_notes"):
            try:
                midi_specs = [self._build_live_midi_note_specification(note) for note in notes]
                sequence_payloads = [midi_specs, tuple(midi_specs), {"notes": midi_specs}]
                last_error = None
                for payload in sequence_payloads:
                    try:
                        return {
                            "mode": "modern_midi_note_specification",
                            "note_ids": clip.add_new_notes(payload),
                        }
                    except Exception as exc:
                        last_error = exc
                return {
                    "mode": "modern_midi_note_specification",
                    "note_ids": clip.add_new_notes(midi_specs),
                }
            except Exception as exc:
                if 'last_error' in locals() and last_error is not None:
                    exc = last_error
                errors.append("MidiNoteSpecification: " + str(exc))
            try:
                strict_notes = [self._build_strict_note_dict(note) for note in notes]
                sequence_payloads = [strict_notes, tuple(strict_notes), {"notes": strict_notes}]
                last_error = None
                for payload in sequence_payloads:
                    try:
                        return {
                            "mode": "modern_strict_dict",
                            "note_ids": clip.add_new_notes(payload),
                        }
                    except Exception as exc:
                        last_error = exc
                return {
                    "mode": "modern_strict_dict",
                    "note_ids": clip.add_new_notes(strict_notes),
                }
            except Exception as exc:
                if 'last_error' in locals() and last_error is not None:
                    exc = last_error
                errors.append("strict_dict: " + str(exc))
        raise RuntimeError("Modern MIDI note API failed: " + " | ".join(errors))

    def _coerce_note_ids(self, raw_note_ids):
        if raw_note_ids is None:
            return []
        if isinstance(raw_note_ids, (list, tuple)):
            values = raw_note_ids
        else:
            try:
                values = list(raw_note_ids)
            except Exception:
                return []
        coerced = []
        for value in values:
            try:
                coerced.append(int(value))
            except Exception:
                continue
        return coerced

    def _write_clip_notes_legacy(self, clip, notes, replace_existing=True):
        if replace_existing:
            try:
                clip.remove_notes(0.0, 0, clip.length, 128)
            except Exception:
                pass
        if notes:
            clip.set_notes(tuple((
                note["pitch"],
                note["start_time"],
                note["duration"],
                note.get("velocity", 100),
                note.get("mute", False),
            ) for note in notes))

    def _is_legacy_fallback_allowed(self, allow_legacy_fallback=None):
        if allow_legacy_fallback is None:
            return bool(self.allow_legacy_midi_fallback)
        return bool(allow_legacy_fallback)

    def _replace_clip_notes(self, slot, clip, notes, replace_existing=True, allow_legacy_fallback=None):
        fallback_allowed = self._is_legacy_fallback_allowed(allow_legacy_fallback)
        try:
            if replace_existing:
                removed_existing = False
                existing_notes = self._read_clip_notes(clip) or []
                note_ids = [note.get("note_id") for note in existing_notes if note.get("note_id") is not None]
                if note_ids and hasattr(clip, "remove_notes_by_id"):
                    try:
                        clip.remove_notes_by_id(note_ids)
                        removed_existing = True
                    except Exception:
                        removed_existing = False
                if not removed_existing and hasattr(clip, "remove_notes_extended"):
                    try:
                        clip.remove_notes_extended(0, 128, 0.0, clip.length)
                        removed_existing = True
                    except Exception:
                        removed_existing = False
                if replace_existing and existing_notes and not removed_existing:
                    raise RuntimeError("Unable to clear existing MIDI notes with modern APIs")
            if notes:
                modern_result = self._call_add_new_notes_modern(clip, notes)
                return clip, modern_result.get("mode", "modern_unknown")
            return clip, "noop"
        except Exception as exc:
            if not fallback_allowed:
                raise RuntimeError("Modern MIDI write failed and legacy fallback is disabled: " + str(exc))
        self._write_clip_notes_legacy(clip, notes, replace_existing)
        return clip, "legacy_set_notes"

    def _get_scale_intervals(self, scale_name):
        scales = {
            "major": [0, 2, 4, 5, 7, 9, 11],
            "minor": [0, 2, 3, 5, 7, 8, 10],
            "dorian": [0, 2, 3, 5, 7, 9, 10],
            "mixolydian": [0, 2, 4, 5, 7, 9, 10],
            "pentatonic": [0, 2, 4, 7, 9],
        }
        return scales.get(str(scale_name).lower(), scales["major"])

    def _build_scale_pitches(self, root_note, scale_name, octave_span):
        intervals = self._get_scale_intervals(scale_name)
        pitches = []
        for octave in range(max(1, int(octave_span))):
            for interval in intervals:
                pitches.append(int(self._clamp(root_note + interval + (12 * octave), 0, 127)))
        return pitches or [int(self._clamp(root_note, 0, 127))]

    def _get_chord_intervals(self, chord_type):
        chord_map = {
            "triad": [0, 4, 7],
            "minor": [0, 3, 7],
            "seventh": [0, 4, 7, 10],
            "minor_seventh": [0, 3, 7, 10],
            "sus2": [0, 2, 7],
            "sus4": [0, 5, 7],
        }
        return chord_map.get(str(chord_type).lower(), chord_map["triad"])

    def _build_euclidean_pattern(self, steps, pulses, rotation):
        steps = max(1, int(steps))
        pulses = max(0, min(int(pulses), steps))
        if pulses == 0:
            return [0] * steps
        pattern = []
        for step_index in range(steps):
            current = int((step_index * pulses) / float(steps))
            following = int(((step_index + 1) * pulses) / float(steps))
            pattern.append(1 if following > current else 0)
        if rotation:
            rotation = int(rotation) % steps
            pattern = pattern[-rotation:] + pattern[:-rotation]
        return pattern

    def _transform_midi_clip(self, track_index, clip_index, operation, semitones=0,
                              velocity_delta=0, velocity_scale=1.0, grid=0.25,
                              strength=1.0, time_amount=0.0, velocity_amount=0,
                              axis_pitch=60, device_name="", seed=None):
        track, slot, clip = self._get_midi_clip_for_edit(track_index, clip_index)
        matched_device = self._find_matching_track_device(track, device_name)
        notes = self._read_clip_notes(clip)
        if not notes:
            return {"track_index": track_index, "clip_index": clip_index, "operation": operation, "matched_device": matched_device, "note_count_before": 0, "note_count_after": 0, "notes": []}
        rng = random.Random(seed)
        transformed = []
        clip_length = float(clip.length)
        operation_name = str(operation).lower()
        for note in notes:
            updated = dict(note)
            if operation_name == "transpose":
                updated["pitch"] = self._clamp(note["pitch"] + int(semitones), 0, 127)
            elif operation_name == "velocity":
                updated["velocity"] = self._clamp(int(round((note["velocity"] + int(velocity_delta)) * float(velocity_scale))), 1, 127)
            elif operation_name == "quantize":
                quantize_grid = max(0.03125, float(grid))
                quantize_strength = self._clamp(float(strength), 0.0, 1.0)
                target = round(note["start_time"] / quantize_grid) * quantize_grid
                updated["start_time"] = note["start_time"] + ((target - note["start_time"]) * quantize_strength)
            elif operation_name == "humanize":
                updated["start_time"] = note["start_time"] + rng.uniform(-abs(float(time_amount)), abs(float(time_amount)))
                updated["velocity"] = self._clamp(note["velocity"] + rng.randint(-abs(int(velocity_amount)), abs(int(velocity_amount))), 1, 127)
            elif operation_name == "reverse":
                updated["start_time"] = clip_length - (note["start_time"] + note["duration"])
            elif operation_name == "invert":
                updated["pitch"] = self._clamp(int((2 * int(axis_pitch)) - note["pitch"]), 0, 127)
            else:
                raise ValueError("Unknown transform operation: " + str(operation))
            transformed.append(updated)
        normalized = self._normalize_notes(transformed, clip_length)
        write_mode = "noop"
        if hasattr(clip, "apply_note_modifications") and normalized and all("note_id" in note for note in normalized):
            try:
                clip.apply_note_modifications({"notes": [self._build_strict_note_dict(note, True) for note in normalized]})
                write_mode = "apply_note_modifications"
            except Exception:
                clip, write_mode = self._replace_clip_notes(slot, clip, normalized, True)
        else:
            clip, write_mode = self._replace_clip_notes(slot, clip, normalized, True)
        return {"track_index": track_index, "clip_index": clip_index, "clip_name": clip.name, "clip_length": clip.length, "operation": operation_name, "matched_device": matched_device, "write_mode": write_mode, "note_count_before": len(notes), "note_count_after": len(normalized), "notes": normalized[:16]}

    def _generate_midi_clip(self, track_index, clip_index, generator, root_note=60,
                             scale="major", clip_length=4.0, step=0.25,
                             note_length=0.25, octave_span=1, chord_type="triad",
                             pattern="up", pulses=8, rotation=0,
                             device_name="", seed=None, replace_existing=True):
        track, slot, clip = self._get_midi_clip_for_edit(track_index, clip_index, True, clip_length)
        matched_device = self._find_matching_track_device(track, device_name)
        rng = random.Random(seed)
        generator_name = str(generator).lower()
        effective_clip_length = float(clip.length)
        step_size = max(0.03125, float(step))
        generated = []
        if generator_name == "chord":
            intervals = self._get_chord_intervals(chord_type)
            position = 0.0
            while position < effective_clip_length:
                for interval in intervals:
                    generated.append({"pitch": root_note + interval, "start_time": position, "duration": note_length, "velocity": 100, "mute": False})
                position += step_size
        elif generator_name == "arpeggio":
            sequence = []
            intervals = self._get_chord_intervals(chord_type)
            for octave in range(max(1, int(octave_span))):
                for interval in intervals:
                    sequence.append(root_note + interval + (12 * octave))
            if not sequence:
                sequence = [root_note]
            pattern_name = str(pattern).lower()
            if pattern_name == "down":
                sequence = list(reversed(sequence))
            elif pattern_name == "updown" and len(sequence) > 1:
                sequence = sequence + list(reversed(sequence[1:-1]))
            step_index = 0
            position = 0.0
            while position < effective_clip_length:
                generated.append({"pitch": sequence[step_index % len(sequence)], "start_time": position, "duration": note_length, "velocity": 100, "mute": False})
                step_index += 1
                position += step_size
        elif generator_name == "euclidean":
            total_steps = max(1, int(round(effective_clip_length / step_size)))
            euclidean_pattern = self._build_euclidean_pattern(total_steps, pulses, rotation)
            scale_pitches = self._build_scale_pitches(int(root_note), scale, octave_span)
            for step_index, is_active in enumerate(euclidean_pattern):
                if not is_active:
                    continue
                generated.append({"pitch": scale_pitches[step_index % len(scale_pitches)], "start_time": step_index * step_size, "duration": note_length, "velocity": 100, "mute": False})
        elif generator_name == "melody":
            scale_pitches = self._build_scale_pitches(int(root_note), scale, octave_span)
            position = 0.0
            while position < effective_clip_length:
                generated.append({"pitch": scale_pitches[rng.randrange(len(scale_pitches))], "start_time": position, "duration": note_length, "velocity": 100, "mute": False})
                position += step_size
        else:
            raise ValueError("Unknown clip generator: " + str(generator))
        normalized = self._normalize_notes(generated, effective_clip_length)
        clip, write_mode = self._replace_clip_notes(slot, clip, normalized, bool(replace_existing))
        return {"track_index": track_index, "clip_index": clip_index, "clip_name": clip.name, "clip_length": clip.length, "generator": generator_name, "matched_device": matched_device, "write_mode": write_mode, "note_count": len(normalized), "notes": normalized[:16]}

    def _add_notes_to_clip(self, track_index, clip_index, notes):
        track, slot, clip = self._get_midi_clip_for_edit(track_index, clip_index, allow_create=False)
        clip_length = float(clip.length)
        normalized = self._normalize_notes(notes or [], clip_length)
        if not normalized:
            return {
                "track_index": track_index,
                "clip_index": clip_index,
                "clip_name": clip.name,
                "clip_length": clip_length,
                "note_count": 0,
                "note_ids": [],
            }
        note_ids = []
        write_mode = "noop"
        try:
            result = self._call_add_new_notes_modern(clip, normalized)
            note_ids = self._coerce_note_ids(result.get("note_ids"))
            write_mode = result.get("mode", "modern_unknown")
        except Exception as exc:
            if self._is_legacy_fallback_allowed():
                existing_notes = self._read_clip_notes(clip)
                combined = self._normalize_notes(existing_notes + normalized, clip_length)
                self._write_clip_notes_legacy(clip, combined, replace_existing=True)
                write_mode = "legacy_set_notes"
            else:
                raise RuntimeError("add_notes_to_clip failed in modern mode (legacy fallback disabled): " + str(exc))
        return {
            "track_index": track_index,
            "clip_index": clip_index,
            "clip_name": clip.name,
            "clip_length": clip_length,
            "write_mode": write_mode,
            "note_count": len(normalized),
            "note_ids": note_ids,
        }

    def _set_clip_name(self, track_index, clip_index, name):
        slot = self._song.tracks[track_index].clip_slots[clip_index]
        if not slot.has_clip:
            raise Exception("No clip in slot")
        slot.clip.name = name
        return {"name": slot.clip.name}

    def _set_tempo(self, tempo):
        self._song.tempo = tempo
        return {"tempo": self._song.tempo}

    def _fire_clip(self, track_index, clip_index):
        slot = self._song.tracks[track_index].clip_slots[clip_index]
        if not slot.has_clip:
            raise Exception("No clip in slot")
        slot.fire()
        return {"fired": True}

    def _fire_selected_clip(self):
        clip_slot = self._safe_view_attr(self._song.view, "highlighted_clip_slot", None)
        if clip_slot is None:
            raise ValueError("No selected clip slot")
        if not clip_slot.has_clip:
            raise ValueError("Selected clip slot has no clip")
        location = self._find_clip_slot_location(clip_slot)
        if location is None:
            raise ValueError("Selected clip slot could not be resolved")
        clip_slot.fire()
        return {
            "track_kind": location["track_kind"],
            "track_index": location["track_index"],
            "track_name": location["track_name"],
            "clip_index": location["clip_index"],
            "clip_name": clip_slot.clip.name,
            "fired": True,
            "is_selected": True,
        }

    def _stop_clip(self, track_index, clip_index):
        self._song.tracks[track_index].clip_slots[clip_index].stop()
        return {"stopped": True}

    def _start_playback(self):
        self._song.start_playing()
        return {"playing": True, "observed_is_playing": bool(self._song.is_playing)}

    def _stop_playback(self):
        self._song.stop_playing()
        return {"playing": False, "observed_is_playing": bool(self._song.is_playing)}

    def _stop_all_clips(self, quantized=True):
        try:
            self._song.stop_all_clips(bool(quantized))
        except TypeError:
            self._song.stop_all_clips()
        return {"stopped": True, "quantized": bool(quantized)}

    def _load_browser_item(self, track_index, item_uri):
        track = self._song.tracks[track_index]
        app = self._app
        item = self._find_browser_item_by_uri(app.browser, item_uri)
        if not item:
            raise ValueError("Item not found: " + item_uri)
        self._song.view.selected_track = track
        app.browser.load_item(item)
        return {"loaded": True, "item_name": item.name, "track_name": track.name}

    def _select_device_on_track(self, track, device):
        self._song.view.selected_track = track
        try:
            self._song.view.select_device(device)
            return True
        except Exception:
            pass
        try:
            self._song.view.selected_device = device
            return True
        except Exception:
            return False

    def _find_drum_rack_device(self, track):
        for device in reversed(track.devices):
            if self._safe_view_attr(device, "can_have_drum_pads", False):
                return device
        return None

    def _load_instrument_or_effect(self, track_index, uri):
        if not uri:
            raise ValueError("Browser URI is required")
        return self._load_browser_item(track_index, uri)

    def _load_drum_kit(self, track_index, rack_uri, kit_path):
        if not rack_uri:
            raise ValueError("Drum rack URI is required")
        track = self._song.tracks[track_index]
        app = self._app
        result = {
            "track_index": track_index,
            "rack_uri": rack_uri,
            "kit_path": kit_path,
        }
        rack_result = self._load_browser_item(track_index, rack_uri)
        drum_rack = self._find_drum_rack_device(track)
        result.update({
            "loaded": rack_result.get("loaded", False),
            "rack_name": rack_result.get("item_name"),
            "track_name": rack_result.get("track_name"),
            "drum_rack_found": bool(drum_rack),
        })
        if kit_path:
            kit_item = self._find_browser_item_by_uri(app.browser, kit_path)
            if not kit_item:
                raise ValueError("Kit item not found: " + str(kit_path))
            if drum_rack is None:
                result["kit_path_loaded"] = False
                result["warning"] = "Drum Rack device could not be resolved after loading"
                return result
            result["device_selected"] = self._select_device_on_track(track, drum_rack)
            device_count_before = len(track.devices)
            app.browser.load_item(kit_item)
            result["kit_path_loaded"] = True
            result["kit_item_name"] = kit_item.name if hasattr(kit_item, "name") else None
            result["device_count_before_kit"] = device_count_before
            result["device_count_after_kit"] = len(track.devices)
            result["drum_rack_name_after_kit"] = self._find_drum_rack_device(track).name if self._find_drum_rack_device(track) else None
        else:
            result["kit_path_loaded"] = True
        return result

    def _find_browser_item_by_uri(self, node, uri, depth=0):
        if depth > 10:
            return None
        if hasattr(node, 'uri') and node.uri == uri:
            return node
        if hasattr(node, 'instruments'):
            for cat in [node.instruments, node.sounds, node.drums, node.audio_effects, node.midi_effects]:
                r = self._find_browser_item_by_uri(cat, uri, depth + 1)
                if r:
                    return r
            return None
        if hasattr(node, 'children'):
            for child in node.children:
                r = self._find_browser_item_by_uri(child, uri, depth + 1)
                if r:
                    return r
        return None

    def _get_browser_root_uri_aliases(self):
        return {
            "instruments": ["query:synths", "query:instruments", "/synths", "/instruments"],
            "sounds": ["query:sounds", "/sounds"],
            "drums": ["query:drums", "/drums"],
            "audio_effects": ["query:audiofx", "query:audio_effects", "/audiofx"],
            "midi_effects": ["query:midifx", "query:midi_effects", "/midifx"],
        }

    def _get_browser_root_item_by_uri(self, browser, uri):
        normalized_uri = str(uri or "").strip().lower()
        if not normalized_uri:
            return None

        for attr, _label in self._get_browser_root_categories():
            if not hasattr(browser, attr):
                continue

            root_item = getattr(browser, attr)
            root_uri = str(getattr(root_item, 'uri', '') or '').strip().lower()
            aliases = self._get_browser_root_uri_aliases().get(attr, [])

            if normalized_uri == root_uri:
                return root_item
            if any(normalized_uri.startswith(alias) for alias in aliases):
                return root_item
            if root_uri and (normalized_uri.startswith(root_uri + '#') or normalized_uri.startswith(root_uri + '/')):
                return root_item

        return None

    def _get_device_type(self, device):
        try:
            if device.can_have_drum_pads:
                return "drum_machine"
            elif device.can_have_chains:
                return "rack"
            elif "instrument" in device.class_display_name.lower():
                return "instrument"
            elif "audio_effect" in device.class_name.lower():
                return "audio_effect"
            elif "midi_effect" in device.class_name.lower():
                return "midi_effect"
        except:
            pass
        return "unknown"

    def get_browser_tree(self, category_type="all"):
        app = self._app
        result = {"type": category_type, "categories": []}
        for attr, label in [("instruments", "Instruments"), ("sounds", "Sounds"), ("drums", "Drums"), ("audio_effects", "Audio Effects"), ("midi_effects", "MIDI Effects")]:
            if (category_type == "all" or category_type == attr) and hasattr(app.browser, attr):
                try:
                    item = getattr(app.browser, attr)
                    result["categories"].append({"name": label, "uri": item.uri if hasattr(item, 'uri') else None, "children": []})
                except Exception as e:
                    self.log_message("Browser error: " + str(e))
        return result

    def get_browser_categories(self, category_type="all"):
        app = self._app
        categories = []
        for attr, label in self._get_browser_root_categories():
            if (category_type == "all" or category_type == attr) and hasattr(app.browser, attr):
                try:
                    categories.append(self._serialize_browser_item(getattr(app.browser, attr), label, attr))
                except Exception as e:
                    self.log_message("Browser category error: " + str(e))
        return {"type": category_type, "category_count": len(categories), "categories": categories}

    def get_browser_item_info(self, path="", uri=""):
        item = self._resolve_browser_item(path, uri)
        result = self._serialize_browser_item(item)
        result["children"] = self._serialize_browser_children(item)
        result["child_count"] = len(result["children"])
        result["path"] = path or None
        return result

    def get_browser_items_at_path(self, path):
        app = self._app
        parts = path.split("/")
        attr_map = {"instruments": "instruments", "sounds": "sounds", "drums": "drums", "audio_effects": "audio_effects", "midi_effects": "midi_effects"}
        root = parts[0].lower()
        if root not in attr_map or not hasattr(app.browser, attr_map[root]):
            return {"path": path, "error": "Unknown category", "items": []}
        current = getattr(app.browser, attr_map[root])
        for part in parts[1:]:
            if not part:
                continue
            found = False
            for child in current.children:
                if hasattr(child, 'name') and child.name.lower() == part.lower():
                    current = child
                    found = True
                    break
            if not found:
                return {"path": path, "error": "Not found: " + part, "items": []}
        items = []
        if hasattr(current, 'children'):
            for child in current.children:
                items.append({"name": child.name if hasattr(child, 'name') else "?", "is_folder": hasattr(child, 'children') and bool(child.children), "is_loadable": hasattr(child, 'is_loadable') and child.is_loadable, "uri": child.uri if hasattr(child, 'uri') else None})
        return {"path": path, "name": current.name if hasattr(current, 'name') else "?", "items": items}

    def get_browser_items_at_uri(self, uri):
        if not uri:
            raise ValueError("Browser URI is required")
        item = self._resolve_browser_item("", uri)
        return {
            "uri": uri,
            "name": item.name if hasattr(item, 'name') else "?",
            "items": self._serialize_browser_children(item),
        }

    def get_browser_subtree(self, path="", uri="", max_depth=2):
        item = self._resolve_browser_item(path, uri)
        resolved = self._find_browser_item_path(item)
        return {
            "path": resolved["path"],
            "uri": item.uri if hasattr(item, 'uri') else uri or None,
            "max_depth": max(0, int(max_depth)),
            "tree": self._serialize_browser_tree_node(item, max(0, int(max_depth))),
        }

    def get_browser_item_path(self, path="", uri=""):
        item = self._resolve_browser_item(path, uri)
        resolved = self._find_browser_item_path(item)
        result = self._serialize_browser_item(item)
        result["path"] = resolved["path"]
        result["path_parts"] = resolved["path_parts"]
        result["category"] = resolved["category"]
        result["resolved_via"] = "uri" if uri else "path"
        return result

    def get_browser_stats(self, category_type="all", path="", uri="", max_depth=10):
        depth_limit = max(0, int(max_depth))
        if path or uri:
            item = self._resolve_browser_item(path, uri)
            resolved = self._find_browser_item_path(item)
            stats = self._collect_browser_stats(item, depth_limit)
            stats["path"] = resolved["path"]
            stats["category"] = resolved["category"]
            stats["max_depth"] = depth_limit
            return stats
        category_stats = []
        total_nodes = 0
        total_folders = 0
        total_loadable = 0
        total_devices = 0
        for attr, _label in self._get_browser_root_categories():
            if category_type != "all" and category_type != attr:
                continue
            if not hasattr(self._app.browser, attr):
                continue
            item = getattr(self._app.browser, attr)
            stats = self._collect_browser_stats(item, depth_limit)
            stats["category"] = attr
            stats["path"] = self._find_browser_item_path(item)["path"]
            category_stats.append(stats)
            total_nodes += stats["node_count"]
            total_folders += stats["folder_count"]
            total_loadable += stats["loadable_count"]
            total_devices += stats["device_count"]
        return {"category_type": category_type, "max_depth": depth_limit, "category_count": len(category_stats), "node_count": total_nodes, "folder_count": total_folders, "loadable_count": total_loadable, "device_count": total_devices, "categories": category_stats}

    def search_browser_items(self, query, category_type="all", max_results=25):
        if not query:
            raise ValueError("Browser search query is required")
        app = self._app
        results = []
        query_lower = query.lower()
        limit = max(1, int(max_results))
        for attr, label in self._get_browser_root_categories():
            if category_type != "all" and category_type != attr:
                continue
            if not hasattr(app.browser, attr):
                continue
            self._search_browser_item_tree(getattr(app.browser, attr), query_lower, limit, results, [label], attr)
            if len(results) >= limit:
                break
        return {"query": query, "category_type": category_type, "result_count": len(results), "results": results}

    def _get_browser_root_categories(self):
        return [("instruments", "Instruments"), ("sounds", "Sounds"), ("drums", "Drums"), ("audio_effects", "Audio Effects"), ("midi_effects", "MIDI Effects")]

    def _resolve_browser_item(self, path, uri):
        app = self._app
        if uri:
            root_item = self._get_browser_root_item_by_uri(app.browser, uri)
            if root_item is not None:
                root_uri = str(getattr(root_item, 'uri', '') or '').strip().lower()
                normalized_uri = str(uri or '').strip().lower()
                if normalized_uri == root_uri:
                    return root_item
                item = self._find_browser_item_by_uri(root_item, uri)
            else:
                item = self._find_browser_item_by_uri(app.browser, uri)
            if item:
                return item
            raise ValueError("Item not found: " + uri)
        if not path:
            raise ValueError("Either path or uri is required")
        parts = [part for part in path.split("/") if part]
        if not parts:
            raise ValueError("Invalid browser path")
        current = self._get_browser_root_item(app.browser, parts[0])
        if current is None:
            raise ValueError("Unknown category: " + parts[0])
        for part in parts[1:]:
            found = None
            if hasattr(current, 'children'):
                for child in current.children:
                    if hasattr(child, 'name') and child.name.lower() == part.lower():
                        found = child
                        break
            if found is None:
                raise ValueError("Not found: " + part)
            current = found
        return current

    def _get_browser_root_item(self, browser, root_name):
        root = root_name.lower()
        for attr, _label in self._get_browser_root_categories():
            if attr == root and hasattr(browser, attr):
                return getattr(browser, attr)
        return None

    def _serialize_browser_item(self, item, display_name=None, category_key=None):
        children = getattr(item, 'children', None)
        return {
            "name": display_name or (item.name if hasattr(item, 'name') else "?"),
            "category": category_key,
            "uri": item.uri if hasattr(item, 'uri') else None,
            "is_folder": bool(children),
            "is_loadable": hasattr(item, 'is_loadable') and item.is_loadable,
            "is_device": hasattr(item, 'is_device') and item.is_device,
            "child_count": len(children) if children else 0,
        }

    def _serialize_browser_children(self, item):
        items = []
        if hasattr(item, 'children') and item.children:
            for child in item.children:
                items.append(self._serialize_browser_item(child))
        return items

    def _serialize_browser_tree_node(self, item, remaining_depth):
        result = self._serialize_browser_item(item)
        result["children"] = []
        if remaining_depth <= 0:
            return result
        if hasattr(item, 'children') and item.children:
            for child in item.children:
                result["children"].append(self._serialize_browser_tree_node(child, remaining_depth - 1))
        return result

    def _find_browser_item_path(self, target):
        for attr, label in self._get_browser_root_categories():
            if hasattr(self._app.browser, attr):
                root = getattr(self._app.browser, attr)
                match = self._find_browser_item_path_recursive(root, target, [label], attr)
                if match:
                    return match
        name = target.name if hasattr(target, 'name') else "?"
        return {"path": name, "path_parts": [name], "category": None}

    def _find_browser_item_path_recursive(self, current, target, path_parts, category_key):
        current_name = current.name if hasattr(current, 'name') else None
        current_path = path_parts
        if current_name and current_name != path_parts[-1]:
            current_path = path_parts + [current_name]
        if current == target:
            return {"path": "/".join(current_path), "path_parts": current_path, "category": category_key}
        if hasattr(current, 'children') and current.children:
            for child in current.children:
                match = self._find_browser_item_path_recursive(child, target, current_path, category_key)
                if match:
                    return match
        return None

    def _collect_browser_stats(self, item, remaining_depth):
        node_count = 1
        folder_count = 1 if hasattr(item, 'children') and bool(item.children) else 0
        loadable_count = 1 if hasattr(item, 'is_loadable') and item.is_loadable else 0
        device_count = 1 if hasattr(item, 'is_device') and item.is_device else 0
        if remaining_depth > 0 and hasattr(item, 'children') and item.children:
            for child in item.children:
                child_stats = self._collect_browser_stats(child, remaining_depth - 1)
                node_count += child_stats["node_count"]
                folder_count += child_stats["folder_count"]
                loadable_count += child_stats["loadable_count"]
                device_count += child_stats["device_count"]
        return {"name": item.name if hasattr(item, 'name') else "?", "uri": item.uri if hasattr(item, 'uri') else None, "node_count": node_count, "folder_count": folder_count, "loadable_count": loadable_count, "device_count": device_count}

    def _search_browser_item_tree(self, item, query_lower, limit, results, path_parts, category_key):
        if len(results) >= limit:
            return
        item_name = item.name if hasattr(item, 'name') else ""
        current_path = path_parts + ([item_name] if item_name and (not path_parts or item_name != path_parts[-1]) else [])
        if item_name and query_lower in item_name.lower():
            entry = self._serialize_browser_item(item)
            entry["path"] = "/".join(current_path)
            entry["category"] = category_key
            results.append(entry)
            if len(results) >= limit:
                return
        if hasattr(item, 'children') and item.children:
            for child in item.children:
                self._search_browser_item_tree(child, query_lower, limit, results, current_path, category_key)
                if len(results) >= limit:
                    return
