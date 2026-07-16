import re
import sys
import threading
import tkinter as tk
import wave
import winsound
from pathlib import Path
from tkinter import messagebox, ttk

import pyaudio

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from config import get_wakeword_config


class NegativeSampleRecorder:
    RATE = 16000
    CHANNELS = 1
    FORMAT = pyaudio.paInt16
    CHUNK = 1024
    RECORD_SECONDS = 2
    DEFAULT_TARGET_SAMPLES = 50

    def __init__(self, root):
        self.root = root
        self.root.title("Negative Wakeword Samples")
        self.root.geometry("560x320")
        self.root.resizable(False, False)

        self.config = get_wakeword_config()
        self.profile_dir = (
            Path(__file__).resolve().parent
            / "profiles"
            / self.config["name"]
        )
        self.negative_dir = self.profile_dir / "negatives"
        self.preview_path = self.profile_dir / ".negative_preview.wav"

        self.audio = pyaudio.PyAudio()
        self.current_frames = None

        self._build_ui()
        self._refresh()

    def _build_ui(self):
        main = ttk.Frame(self.root, padding=18)
        main.pack(fill="both", expand=True)

        ttk.Label(main, text="Record Negative Samples", font=("Segoe UI", 16, "bold")).pack(anchor="w")
        ttk.Label(
            main,
            text="Record clips where you do NOT say the wake word: TV, silence, normal speech, typing, room noise.",
            wraplength=500,
        ).pack(anchor="w", pady=(12, 16))

        self.progress_label = ttk.Label(main, text="")
        self.progress_label.pack(anchor="w")

        row = ttk.Frame(main)
        row.pack(fill="x", pady=(12, 16))

        ttk.Label(row, text="Target samples").pack(side="left")
        self.target_count = tk.IntVar(value=self.DEFAULT_TARGET_SAMPLES)
        ttk.Spinbox(row, from_=10, to=300, textvariable=self.target_count, width=6, command=self._refresh).pack(
            side="left",
            padx=10,
        )

        self.status_label = ttk.Label(main, text="")
        self.status_label.pack(anchor="center", pady=(0, 16))

        buttons = ttk.Frame(main)
        buttons.pack(anchor="center")

        self.record_button = ttk.Button(buttons, text="Record", command=self.record)
        self.record_button.grid(row=0, column=0, padx=6)

        self.play_button = ttk.Button(buttons, text="Playback", command=self.playback, state="disabled")
        self.play_button.grid(row=0, column=1, padx=6)

        self.rerecord_button = ttk.Button(buttons, text="Re-record", command=self.rerecord, state="disabled")
        self.rerecord_button.grid(row=0, column=2, padx=6)

        self.save_button = ttk.Button(buttons, text="Save", command=self.save, state="disabled")
        self.save_button.grid(row=0, column=3, padx=6)

    def _refresh(self):
        saved = self._saved_count()
        self.progress_label.config(text=f"Saved {saved}/{int(self.target_count.get())}")
        self.status_label.config(text="Press Record and capture a non-wake-word sound.")
        self._set_buttons(record=True, review=self.current_frames is not None)

    def record(self):
        self.current_frames = None
        self._set_buttons(record=False, review=False)
        self.status_label.config(text=f"Recording for {self.RECORD_SECONDS} seconds...")
        threading.Thread(target=self._record_worker, daemon=True).start()

    def _record_worker(self):
        try:
            stream = self.audio.open(
                format=self.FORMAT,
                channels=self.CHANNELS,
                rate=self.RATE,
                input=True,
                frames_per_buffer=self.CHUNK,
            )

            frames = []
            total_chunks = int(self.RATE / self.CHUNK * self.RECORD_SECONDS)
            for _ in range(total_chunks):
                frames.append(stream.read(self.CHUNK, exception_on_overflow=False))

            stream.stop_stream()
            stream.close()

            self.current_frames = frames
            self._write_wav(self.preview_path, frames)
            self.root.after(0, self._recording_finished)
        except Exception as exc:
            self.root.after(0, lambda: self._recording_failed(exc))

    def _recording_finished(self):
        self.status_label.config(text="Recording complete. Play it back, then Save or Re-record.")
        self._set_buttons(record=False, review=True)

    def _recording_failed(self, exc):
        self.status_label.config(text=f"Recording failed: {exc}")
        self._set_buttons(record=True, review=False)

    def playback(self):
        if not self.preview_path.exists():
            messagebox.showerror("Playback", "No recording is available yet.")
            return

        threading.Thread(
            target=lambda: winsound.PlaySound(str(self.preview_path), winsound.SND_FILENAME),
            daemon=True,
        ).start()

    def rerecord(self):
        self.current_frames = None
        self._set_buttons(record=True, review=False)
        self.status_label.config(text="Ready to re-record this negative sample.")

    def save(self):
        if self.current_frames is None:
            messagebox.showerror("Save", "Record a sample before saving.")
            return

        self.negative_dir.mkdir(parents=True, exist_ok=True)
        sample_path = self.negative_dir / f"negative_{self._next_sample_number():03d}.wav"
        self._write_wav(sample_path, self.current_frames)
        self.current_frames = None
        self.status_label.config(text=f"Saved {sample_path.name}")
        self._refresh()

    def _set_buttons(self, record, review):
        self.record_button.config(state="normal" if record else "disabled")
        review_state = "normal" if review else "disabled"
        self.play_button.config(state=review_state)
        self.rerecord_button.config(state=review_state)
        self.save_button.config(state=review_state)

    def _saved_count(self):
        if not self.negative_dir.exists():
            return 0

        return len(list(self.negative_dir.glob("*.wav")))

    def _next_sample_number(self):
        if not self.negative_dir.exists():
            return 1

        sample_numbers = []
        for path in self.negative_dir.glob("negative_*.wav"):
            match = re.fullmatch(r"negative_(\d+)\.wav", path.name)
            if match:
                sample_numbers.append(int(match.group(1)))

        if not sample_numbers:
            return 1

        return max(sample_numbers) + 1

    def _write_wav(self, path, frames):
        path.parent.mkdir(parents=True, exist_ok=True)
        with wave.open(str(path), "wb") as wav_file:
            wav_file.setnchannels(self.CHANNELS)
            wav_file.setsampwidth(self.audio.get_sample_size(self.FORMAT))
            wav_file.setframerate(self.RATE)
            wav_file.writeframes(b"".join(frames))

    def close(self):
        self.audio.terminate()
        self.root.destroy()


def main():
    root = tk.Tk()
    app = NegativeSampleRecorder(root)
    root.protocol("WM_DELETE_WINDOW", app.close)
    root.mainloop()


if __name__ == "__main__":
    main()
