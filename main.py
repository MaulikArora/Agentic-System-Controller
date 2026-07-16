import threading
import time

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config import get_assistant_name, get_spotify_config
from actions.command_router import CommandRouter
from llm.interface import LLMInterface
from speech.recorder import AudioRecorder
from speech.speaker import Speaker
from speech.transcriber import Transcriber
from llm.intent_classifier import IntentClassifier
from wakeword.detector import WakeWordDetector


app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

detector = WakeWordDetector()
recorder = AudioRecorder()
transcriber = Transcriber()
assistant_name = get_assistant_name().strip() or "Koro"
assistant_label = assistant_name.title()
llm = LLMInterface(assistant_name=assistant_name)
classifier = IntentClassifier()
router = CommandRouter(get_spotify_config(), llm)
speaker = Speaker()

assistant_running = False
stop_event = threading.Event()
assistant_state = "Offline"
latest_log = "System Ready"
latest_answer = ""


def assistant_logic_loop():
    global assistant_running, assistant_state, latest_log, latest_answer

    assistant_running = True
    stop_event.clear()
    assistant_state = "Online"

    while not stop_event.is_set():
        wakeword = detector.listen()
        if stop_event.is_set():
            break

        if wakeword:
            assistant_state = "Listening"
            latest_log = f"Detected: {wakeword}"
            recorder.flush_audio()

            audio_file = recorder.record()
            command = transcriber.transcribe(audio_file)
            latest_log = f"Command: {command}"

            if not command.strip() or len(command.split()) < 2:
                assistant_state = "Online"
                continue

            intent_data = classifier.classify(command)
            input_type = intent_data.get("type")
            intent = intent_data.get("intent")
            target = intent_data.get("target", "")

            if input_type == "question":
                assistant_state = "Thinking"
                latest_log = f"Question: {command}"
                answer = llm.answer_question(command)
                latest_answer = answer
                latest_log = f"{assistant_label}: {answer}"
                speaker.speak(answer)

            elif input_type == "command":
                assistant_state = intent.replace("_", " ").title()
                if intent == "calculate":
                    try:
                        result = router.handle(intent_data, command, recorder, transcriber, speaker)
                        latest_answer = result
                        latest_log = f"{assistant_label}: {result}"
                        speaker.speak(f"The answer is {result}.")
                    except Exception as exc:
                        latest_log = f"Calculation failed: {exc}"
                        speaker.speak("I could not calculate that.")
                else:
                    latest_log = router.handle(intent_data, command, recorder, transcriber, speaker)

            else:
                latest_log = f"Could not understand: {command}"
                speaker.speak("I couldn't understand that request.")

            time.sleep(2)
            detector.flush_audio()
            recorder.flush_audio()
            assistant_state = "Online"

        time.sleep(0.1)

    assistant_running = False
    assistant_state = "Offline"


@app.get("/start-koro")
def start_koro():
    global assistant_running

    if not assistant_running:
        threading.Thread(target=assistant_logic_loop, daemon=True).start()
        return {"status": "running"}

    return {"status": "already_running"}


@app.get("/stop-koro")
def stop_koro():
    stop_event.set()
    return {"status": "stopped"}


@app.get("/start-jarvis")
def start_jarvis():
    return start_koro()


@app.get("/stop-jarvis")
def stop_jarvis():
    return stop_koro()


@app.get("/status")
def get_status():
    return {
        "running": assistant_running,
        "state": assistant_state,
        "log": latest_log,
        "answer": latest_answer,
    }


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)
