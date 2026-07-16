import webbrowser

from actions.app_launcher import AppLauncher
from actions.calculator import calculate_expression
from music.music_controller import MusicController
from system_control.system_controller import SystemController


class CommandRouter:
    def __init__(self, spotify_config, llm):
        self.llm = llm
        self.applauncher = AppLauncher()
        self.music = MusicController(**spotify_config)
        self.system_controller = SystemController()

    def handle(self, intent_data, command, recorder, transcriber, speaker):
        intent = intent_data.get("intent")
        target = intent_data.get("target", "")

        if intent == "open_app":
            result = self.applauncher.open(target)
            speaker.speak(result)
            return result

        if intent == "search_web":
            result = f"Searching web for: {target}"
            webbrowser.open(f"https://www.google.com/search?q={target.replace(' ', '+')}")
            speaker.speak(result)
            return result

        if intent == "play_music":
            speaker.speak("Opening Spotify.")
            speaker.speak("What would you like to play?")
            result = self.music.handle(recorder, transcriber, self.llm)
            speaker.speak(result)
            return result

        if intent == "system_control":
            result = self.system_controller.handle(target)
            speaker.speak(result)
            return result

        if intent == "calculate":
            result = calculate_expression(target)
            return str(result)

        speaker.speak("I couldn't understand that command.")
        return f"Unknown command: {command}"
