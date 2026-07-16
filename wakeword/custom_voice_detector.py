import re
import time
import wave
from collections import deque
from pathlib import Path

import numpy as np
import pyaudio

from config import get_wakeword_config


class CustomVoiceWakeWordDetector:
    RATE = 16000
    CHANNELS = 1
    FORMAT = pyaudio.paInt16
    CHUNK = 1280
    WINDOW_SECONDS = 2
    MIN_SCORE_INTERVAL_SECONDS = 0.24

    def __init__(self, open_stream=True):
        self.config = get_wakeword_config()
        self.cooldown_seconds = self.config["cooldown_seconds"]
        self.consecutive_matches = max(1, int(self.config["consecutive_matches"]))
        self.negative_margin = self.config["negative_margin"]
        self.profile_dir = (
            Path(__file__).resolve().parent
            / "profiles"
            / self.config["name"]
        )
        self.phrases = self._load_phrases()
        self.templates = self._load_templates()
        self.negative_templates = self._load_negative_templates()

        if not self.templates:
            raise RuntimeError(f"No wakeword samples found in {self.profile_dir}")

        self.audio = None
        self.stream = None
        if open_stream:
            self.audio = pyaudio.PyAudio()
            self.stream = self.audio.open(
                format=self.FORMAT,
                channels=self.CHANNELS,
                rate=self.RATE,
                input=True,
                frames_per_buffer=self.CHUNK,
            )

        self.window_samples = self.RATE * self.WINDOW_SECONDS
        self.audio_buffer = deque(maxlen=self.window_samples)
        self.last_detection = 0
        self.last_score_time = 0
        self.last_match = None
        self.candidate_phrase = None
        self.candidate_count = 0

    def listen(self):
        audio_data = self.stream.read(self.CHUNK, exception_on_overflow=False)
        audio_array = np.frombuffer(audio_data, dtype=np.int16)
        self.audio_buffer.extend(audio_array)

        now = time.time()
        if len(self.audio_buffer) < self.window_samples:
            return None

        if now - self.last_score_time < self.MIN_SCORE_INTERVAL_SECONDS:
            return None

        self.last_score_time = now
        window = np.asarray(self.audio_buffer, dtype=np.int16)
        feature = self._extract_feature(window)
        phrase, score = self._best_match(feature)
        negative_score = self._negative_match(feature)
        adjusted_score = score - negative_score
        self.last_match = (phrase, score, negative_score, adjusted_score)

        if not phrase:
            return None

        threshold = self.phrases[phrase]["threshold"]
        if (
            score >= threshold
            and adjusted_score >= self.negative_margin
            and now - self.last_detection > self.cooldown_seconds
        ):
            if phrase == self.candidate_phrase:
                self.candidate_count += 1
            else:
                self.candidate_phrase = phrase
                self.candidate_count = 1

            if self.candidate_count < self.consecutive_matches:
                return None

            self.last_detection = now
            self.candidate_phrase = None
            self.candidate_count = 0
            self.flush_audio()
            return phrase

        self.candidate_phrase = None
        self.candidate_count = 0
        return None

    def flush_audio(self, duration=0.3):
        self.audio_buffer.clear()

        start_time = time.time()
        while time.time() - start_time < duration:
            self.stream.read(self.CHUNK, exception_on_overflow=False)

    def close(self):
        if not self.stream or not self.audio:
            return

        self.stream.stop_stream()
        self.stream.close()
        self.audio.terminate()

    def _load_phrases(self):
        phrases = {}
        for phrase in self.config["phrases"]:
            text = phrase["text"]
            phrases[text] = {
                "slug": self._slug(text),
                "threshold": phrase["threshold"],
            }

        return phrases

    def _load_templates(self):
        templates = {}
        for phrase, phrase_config in self.phrases.items():
            phrase_dir = self.profile_dir / "positives" / phrase_config["slug"]
            if not phrase_dir.exists():
                continue

            phrase_templates = []
            for wav_path in sorted(phrase_dir.glob("*.wav")):
                phrase_templates.append(self._extract_feature(self._read_wav(wav_path)))

            if phrase_templates:
                templates[phrase] = np.vstack(phrase_templates)

        return templates

    def _load_negative_templates(self):
        negative_dir = self.profile_dir / "negatives"
        if not negative_dir.exists():
            return None

        templates = []
        for wav_path in sorted(negative_dir.glob("*.wav")):
            templates.append(self._extract_feature(self._read_wav(wav_path)))

        if not templates:
            return None

        return np.vstack(templates)

    def _best_match(self, feature):
        best_phrase = None
        best_score = -1.0

        for phrase, phrase_templates in self.templates.items():
            scores = phrase_templates @ feature
            top_scores = np.sort(scores)[-3:]
            score = float(np.mean(top_scores))

            if score > best_score:
                best_phrase = phrase
                best_score = score

        return best_phrase, best_score

    def _negative_match(self, feature):
        if self.negative_templates is None:
            return 0.0

        scores = self.negative_templates @ feature
        top_scores = np.sort(scores)[-3:]
        return float(np.mean(top_scores))

    def _extract_feature(self, audio):
        samples = audio.astype(np.float32) / 32768.0
        samples = samples - np.mean(samples)

        peak = np.max(np.abs(samples))
        if peak > 0:
            samples = samples / peak

        frame_length = 400
        hop_length = 160
        if len(samples) < frame_length:
            samples = np.pad(samples, (0, frame_length - len(samples)))

        frame_count = 1 + (len(samples) - frame_length) // hop_length
        frames = np.lib.stride_tricks.sliding_window_view(samples, frame_length)[::hop_length]
        frames = frames[:frame_count] * np.hanning(frame_length)

        spectrum = np.abs(np.fft.rfft(frames, n=512)) ** 2
        mel_energies = spectrum @ self._mel_filterbank().T
        log_mel = np.log(mel_energies + 1e-6)

        delta = np.diff(log_mel, axis=0)
        if len(delta) == 0:
            delta = np.zeros_like(log_mel)

        feature = np.concatenate([
            log_mel.mean(axis=0),
            log_mel.std(axis=0),
            delta.mean(axis=0),
            delta.std(axis=0),
        ])

        norm = np.linalg.norm(feature)
        if norm == 0:
            return feature

        return feature / norm

    def _mel_filterbank(self, bands=40, fft_size=512):
        if hasattr(self, "_cached_mel_filterbank"):
            return self._cached_mel_filterbank

        min_mel = self._hz_to_mel(80)
        max_mel = self._hz_to_mel(7600)
        mel_points = np.linspace(min_mel, max_mel, bands + 2)
        hz_points = self._mel_to_hz(mel_points)
        bins = np.floor((fft_size + 1) * hz_points / self.RATE).astype(int)

        filters = np.zeros((bands, fft_size // 2 + 1))
        for index in range(1, bands + 1):
            left = bins[index - 1]
            center = bins[index]
            right = bins[index + 1]

            if center > left:
                filters[index - 1, left:center] = (
                    np.arange(left, center) - left
                ) / (center - left)

            if right > center:
                filters[index - 1, center:right] = (
                    right - np.arange(center, right)
                ) / (right - center)

        self._cached_mel_filterbank = filters
        return filters

    def _read_wav(self, path):
        with wave.open(str(path), "rb") as wav_file:
            if wav_file.getframerate() != self.RATE:
                raise ValueError(f"{path} must be {self.RATE} Hz")
            if wav_file.getnchannels() != self.CHANNELS:
                raise ValueError(f"{path} must be mono")

            audio = wav_file.readframes(wav_file.getnframes())
            return np.frombuffer(audio, dtype=np.int16)

    def _slug(self, phrase):
        slug = re.sub(r"[^a-z0-9]+", "_", phrase.lower()).strip("_")
        return slug or "phrase"

    def _hz_to_mel(self, hz):
        return 2595 * np.log10(1 + hz / 700)

    def _mel_to_hz(self, mel):
        return 700 * (10 ** (mel / 2595) - 1)
