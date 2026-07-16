import pyaudio
import numpy as np
import wave
import time


class AudioRecorder:

    def __init__(
        self,
        sample_rate=16000,
        chunk=1024,
        silence_threshold=1000,
        silence_duration=1.2
    ):

        self.sample_rate = sample_rate
        self.chunk = chunk
        self.silence_threshold = silence_threshold
        self.silence_duration = silence_duration

        self.audio = pyaudio.PyAudio()

    def record(self, filename="command.wav"):
        print("Listening for command...")

        stream = self.audio.open(
            format=pyaudio.paInt16,
            channels=1,
            rate=self.sample_rate,
            input=True,
            frames_per_buffer=self.chunk
        )

        frames = []
        silence_start = None
        speech_started = False         

        while True:

            data = stream.read(self.chunk, exception_on_overflow=False)
            audio_data = np.frombuffer(data, dtype=np.int16)
            volume = np.abs(audio_data).mean()

            if volume >= self.silence_threshold:
                speech_started = True   
                silence_start = None
                frames.append(data)

            elif speech_started:        
                frames.append(data)

                if silence_start is None:
                    silence_start = time.time()
                elif time.time() - silence_start > self.silence_duration:
                    break


        stream.stop_stream()
        stream.close()

        wf = wave.open(filename, 'wb')

        wf.setnchannels(1)

        wf.setsampwidth(
            self.audio.get_sample_size(pyaudio.paInt16)
        )

        wf.setframerate(self.sample_rate)

        wf.writeframes(b''.join(frames))

        wf.close()

        return filename
    
    def flush_audio(self, duration = 0.3):
        stream = self.audio.open(
            format=pyaudio.paInt16,
            channels=1,
            rate=self.sample_rate,
            input=True,
            frames_per_buffer=self.chunk
        )

        start_time = time.time()

        while time.time() - start_time < duration:

            stream.read(
                self.chunk,
                exception_on_overflow=False
            )

        stream.stop_stream()
        stream.close()