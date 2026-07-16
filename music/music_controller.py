import subprocess
import time
import spotipy
from spotipy.exceptions import SpotifyException, SpotifyOauthError
from spotipy.oauth2 import SpotifyOAuth

class MusicController:
    def __init__(
        self,
        client_id,
        client_secret,
        redirect_uri="http://127.0.0.1:8888/callback",
    ):
        self.sp = spotipy.Spotify(
            auth_manager=SpotifyOAuth(
                client_id=client_id,
                client_secret=client_secret,
                redirect_uri=redirect_uri,
                scope="user-modify-playback-state user-read-playback-state",
            )
        )

    def handle(self, recorder, transcriber, llm):
        try:
            return self._handle(recorder, transcriber, llm)
        except SpotifyOauthError as exc:
            return f"Spotify login failed: {self._format_spotify_error(exc)}"
        except SpotifyException as exc:
            return f"Spotify request failed: {self._format_spotify_error(exc)}"
        except Exception as exc:
            return f"Music failed: {exc}"

    def _handle(self, recorder, transcriber, llm):
        self._open_spotify()

        recorder.flush_audio()
        audio_file = recorder.record()

        query = transcriber.transcribe(audio_file)

        if not query.strip():
            return "I didn't catch what to play. Please try again."

        music_intent = llm.extract_music_intent(query)

        kind = music_intent.get("kind", "song")
        target = music_intent.get("target", "").strip()

        if not target:
            return "Couldn't figure out what to play."

        if kind == "playlist":
            return self._play_playlist(target)

        return self._play_song(target)

    def _open_spotify(self):
        try:
            subprocess.Popen(["spotify"])
        except FileNotFoundError:
            try:
                subprocess.Popen(["snap", "run", "spotify"])
            except FileNotFoundError:
                pass

        time.sleep(4)

    def _get_device_id(self):
        devices = self.sp.devices()
        device_list = devices.get("devices", [])

        if not device_list:
            return None

        for d in device_list:
            if d["is_active"]:
                return d["id"]

        return device_list[0]["id"]

    def _play_song(self, song_name: str):
        print(f"Searching for song: {song_name}")
        results = self.sp.search(q=f"track:{song_name}", type="track", limit=1)
        tracks = results.get("tracks", {}).get("items", [])

        if not tracks:
            return f"Couldn't find a song called '{song_name}'."

        track = tracks[0]
        track_uri = track["uri"]
        track_display = f"{track['name']} by {track['artists'][0]['name']}"
        print(f"Playing: {track_display}")

        device_id = self._get_device_id()
        if not device_id:
            return "No active Spotify device found. Open Spotify and start playback once."

        self.sp.start_playback(device_id=device_id, uris=[track_uri])
        return f"Playing {track_display}."

    def _play_playlist(self, playlist_name: str):
        print(f"Searching for playlist: {playlist_name}")
        results = self.sp.search(q=playlist_name, type="playlist", limit=1)
        playlists = results.get("playlists", {}).get("items", [])

        if not playlists:
            return f"Couldn't find a playlist called '{playlist_name}'."

        playlist = playlists[0]
        playlist_uri = playlist["uri"]
        print(f"Playing playlist: {playlist['name']}")

        device_id = self._get_device_id()
        if not device_id:
            return "No active Spotify device found. Open Spotify and start playback once."

        self.sp.start_playback(device_id=device_id, context_uri=playlist_uri)
        return f"Playing playlist {playlist['name']}."

    def _format_spotify_error(self, exc: Exception) -> str:
        text = str(exc)
        if "invalid_client" in text:
            return "invalid Spotify client credentials. Check client_id and client_secret in config.json, then delete .cache and sign in again."

        return text
