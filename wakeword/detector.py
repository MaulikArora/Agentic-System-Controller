import pyaudio
import numpy as np
import time
from config import get_wakeword_config
from wakeword.custom_voice_detector import CustomVoiceWakeWordDetector
from openwakeword.model import Model


class WakeWordDetector:

    def __init__(self):
        self.config = get_wakeword_config()
        if self.config["engine"] == "custom_voice":
            self.custom_detector = CustomVoiceWakeWordDetector()
            return

        self.custom_detector = None
        self.threshold = self.config["threshold"]
        self.cooldown_seconds = self.config["cooldown_seconds"]

        self.model = Model(inference_framework="onnx")

        self.CHUNK = 1280
        self.FORMAT = pyaudio.paInt16
        self.CHANNELS = 1
        self.RATE = 16000

        self.audio = pyaudio.PyAudio()

        self.stream = self.audio.open(
            format=self.FORMAT,
            channels=self.CHANNELS,
            rate=self.RATE,
            input=True,
            frames_per_buffer=self.CHUNK
        )

        self.last_detection = 0

    def listen(self):
        if self.custom_detector:
            return self.custom_detector.listen()

        audio_data = self.stream.read(
            self.CHUNK,
            exception_on_overflow=False
        )

        audio_array = np.frombuffer(audio_data, dtype=np.int16)

        prediction = self.model.predict(audio_array)

        for wakeword, score in prediction.items():

            if (
                score > self.threshold
                and time.time() - self.last_detection > self.cooldown_seconds
            ):

                self.last_detection = time.time()

                self.flush_audio()

                return wakeword

        return None
    
    def flush_audio(self, duration = 1.5):
        if self.custom_detector:
            self.custom_detector.flush_audio(duration)
            return

        for key in self.model.prediction_buffer:
            self.model.prediction_buffer[key].clear()

        start_time = time.time()

        while time.time() - start_time < duration:
            self.stream.read(
                self.CHUNK,
                exception_on_overflow=False
            )
