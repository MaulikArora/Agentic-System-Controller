import subprocess


class Speaker:
    def speak(self, text: str) -> None:
        message = (text or "").strip()
        if not message:
            return

        escaped = message.replace("'", "''")
        script = (
            "Add-Type -AssemblyName System.Speech; "
            "$speaker = New-Object System.Speech.Synthesis.SpeechSynthesizer; "
            f"$speaker.Speak('{escaped}')"
        )

        try:
            subprocess.run(
                ["powershell", "-NoProfile", "-Command", script],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=True
            )
        except Exception as exc:
            print(f"TTS failed: {exc}")
