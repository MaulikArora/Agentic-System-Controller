import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from wakeword.custom_voice_detector import CustomVoiceWakeWordDetector


def main():
    detector = CustomVoiceWakeWordDetector()
    print("Listening for custom wake phrases. Press Ctrl+C to stop.")
    print("Say one of your configured wake phrases and watch the score.")

    try:
        last_printed_score_time = 0
        while True:
            detected = detector.listen()
            if detected:
                print(f"DETECTED: {detected}")

            if detector.last_match and detector.last_score_time != last_printed_score_time:
                last_printed_score_time = detector.last_score_time
                phrase, score, negative_score, adjusted_score = detector.last_match
                threshold = detector.phrases[phrase]["threshold"]
                print(
                    f"{phrase}: pos={score:.3f}/{threshold:.3f} "
                    f"neg={negative_score:.3f} margin={adjusted_score:.3f}/{detector.negative_margin:.3f}"
                )

    except KeyboardInterrupt:
        print("\nStopped.")
    finally:
        detector.close()


if __name__ == "__main__":
    main()
