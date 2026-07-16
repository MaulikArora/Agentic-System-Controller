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


class WakewordEnrollmentApp:
    RATE = 16000
    CHANNELS = 1
    FORMAT = pyaudio.paInt16
    CHUNK = 1024
    RECORD_SECONDS = 2
    DEFAULT_SAMPLES_PER_PHRASE = 20

    def __init__(self, root):
        self.root = root
        self.root.title("Wakeword Enrollment")
        self.root.geometry("560x360")
        self.root.resizable(False, False)

        self.config = get_wakeword_config()
        self.phrases = [phrase["text"] for phrase in self.config["phrases"]]
        self.profile_dir = (
            Path(__file__).resolve().parent
            / "profiles"
            / self.config["name"]
        )
        self.preview_path = self.profile_dir / ".preview.wav"

        self.audio = pyaudio.PyAudio()
        self.current_frames = None
        self.current_phrase_index = 0
        self.target_samples = self.DEFAULT_SAMPLES_PER_PHRASE
        self.starting_counts = {}

        self._build_ui()
        self.starting_counts = {
            phrase: self._saved_count(phrase)
            for phrase in self.phrases
        }
        self._refresh_phrase()

    def _build_ui(self):
        main = ttk.Frame(self.root, padding=18)
        main.pack(fill="both", expand=True)

        title = ttk.Label(main, text="Record Wakeword Samples", font=("Segoe UI", 16, "bold"))
        title.pack(anchor="w")

        self.progress_label = ttk.Label(main, text="")
        self.progress_label.pack(anchor="w", pady=(12, 0))

        self.phrase_label = ttk.Label(main, text="", font=("Segoe UI", 22, "bold"))
        self.phrase_label.pack(anchor="center", pady=(18, 8))

        self.status_label = ttk.Label(main, text="Press Record, say the phrase once, then review it.")
        self.status_label.pack(anchor="center", pady=(0, 16))

        sample_row = ttk.Frame(main)
        sample_row.pack(fill="x", pady=(0, 16))

        ttk.Label(sample_row, text="Add samples per phrase").pack(side="left")
        self.sample_count = tk.IntVar(value=self.DEFAULT_SAMPLES_PER_PHRASE)
        sample_spinbox = ttk.Spinbox(
            sample_row,
            from_=5,
            to=100,
            textvariable=self.sample_count,
            width=6,
            command=self._refresh_phrase,
        )
        sample_spinbox.pack(side="left", padx=10)

        buttons = ttk.Frame(main)
        buttons.pack(anchor="center", pady=8)

        self.record_button = ttk.Button(buttons, text="Record", command=self.record)
        self.record_button.grid(row=0, column=0, padx=6)

        self.play_button = ttk.Button(buttons, text="Playback", command=self.playback, state="disabled")
        self.play_button.grid(row=0, column=1, padx=6)

        self.rerecord_button = ttk.Button(buttons, text="Re-record", command=self.rerecord, state="disabled")
        self.rerecord_button.grid(row=0, column=2, padx=6)

        self.save_button = ttk.Button(buttons, text="Save", command=self.save, state="disabled")
        self.save_button.grid(row=0, column=3, padx=6)

        nav = ttk.Frame(main)
        nav.pack(anchor="center", pady=(18, 0))

        self.skip_button = ttk.Button(nav, text="Skip Phrase", command=self.next_phrase)
        self.skip_button.grid(row=0, column=0, padx=6)

        self.open_folder_button = ttk.Button(nav, text="Show Save Path", command=self.show_save_path)
        self.open_folder_button.grid(row=0, column=1, padx=6)

    def _refresh_phrase(self):
        if not self.phrases:
            self.phrase_label.config(text="No phrases configured")
            self.status_label.config(text="Add wakeword phrases in config.json first.")
            self._set_buttons(record=False, review=False)
            return

        self.target_samples = int(self.sample_count.get())
        phrase = self.current_phrase
        saved_count = self._saved_count(phrase)
        target_total = self._target_total(phrase)

        self.progress_label.config(
            text=f"Phrase {self.current_phrase_index + 1} of {len(self.phrases)} | "
            f"Saved {saved_count}/{target_total}"
        )
        self.phrase_label.config(text=phrase)

        if saved_count >= target_total:
            self.status_label.config(text="Target reached for this phrase. Move to the next phrase.")
        else:
            self.status_label.config(text="Press Record and say the phrase naturally.")

        self._set_buttons(record=True, review=self.current_frames is not None)

    @property
    def current_phrase(self):
        return self.phrases[self.current_phrase_index]

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

        self.status_label.config(text="Playing recording...")
        threading.Thread(target=self._playback_worker, daemon=True).start()

    def _playback_worker(self):
        winsound.PlaySound(str(self.preview_path), winsound.SND_FILENAME)
        self.root.after(0, lambda: self.status_label.config(text="Playback finished."))

    def rerecord(self):
        self.current_frames = None
        self._set_buttons(record=True, review=False)
        self.status_label.config(text="Ready to re-record this sample.")

    def save(self):
        if self.current_frames is None:
            messagebox.showerror("Save", "Record a sample before saving.")
            return

        phrase_dir = self.profile_dir / "positives" / self._slug(self.current_phrase)
        phrase_dir.mkdir(parents=True, exist_ok=True)
        sample_path = phrase_dir / f"{self._slug(self.current_phrase)}_{self._saved_count(self.current_phrase) + 1:03d}.wav"

        self._write_wav(sample_path, self.current_frames)
        self.current_frames = None
        self.status_label.config(text=f"Saved {sample_path.name}")

        if self._saved_count(self.current_phrase) >= self._target_total(self.current_phrase):
            self.next_phrase()
        else:
            self._refresh_phrase()

    def next_phrase(self):
        self.current_frames = None
        self.current_phrase_index = (self.current_phrase_index + 1) % len(self.phrases)
        self._refresh_phrase()

    def show_save_path(self):
        messagebox.showinfo("Save Path", str(self.profile_dir))

    def _set_buttons(self, record, review):
        self.record_button.config(state="normal" if record else "disabled")
        self.skip_button.config(state="normal" if record else "disabled")
        review_state = "normal" if review else "disabled"
        self.play_button.config(state=review_state)
        self.rerecord_button.config(state=review_state)
        self.save_button.config(state=review_state)

    def _saved_count(self, phrase):
        phrase_dir = self.profile_dir / "positives" / self._slug(phrase)
        if not phrase_dir.exists():
            return 0

        return len(list(phrase_dir.glob("*.wav")))

    def _target_total(self, phrase):
        return self.starting_counts.get(phrase, self._saved_count(phrase)) + self.target_samples

    def _write_wav(self, path, frames):
        path.parent.mkdir(parents=True, exist_ok=True)
        with wave.open(str(path), "wb") as wav_file:
            wav_file.setnchannels(self.CHANNELS)
            wav_file.setsampwidth(self.audio.get_sample_size(self.FORMAT))
            wav_file.setframerate(self.RATE)
            wav_file.writeframes(b"".join(frames))

    def _slug(self, phrase):
        slug = re.sub(r"[^a-z0-9]+", "_", phrase.lower()).strip("_")
        return slug or "phrase"

    def close(self):
        self.audio.terminate()
        self.root.destroy()


def main():
    root = tk.Tk()
    app = WakewordEnrollmentApp(root)
    root.protocol("WM_DELETE_WINDOW", app.close)
    root.mainloop()


if __name__ == "__main__":
    main()
