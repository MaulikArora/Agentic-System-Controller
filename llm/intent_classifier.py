import json
import re

from config import get_llm_config
from llm.ollama_client import OllamaClient


class IntentClassifier:
    COMMAND_CUES = (
        "open ", "launch ", "search ", "play ", "start ", "stop ",
        "close ", "turn ", "increase ", "decrease ", "raise ", "lower ",
        "mute ", "unmute ", "lock ", "unlock ", "shutdown ", "restart ",
        "calculate ", "compute ", "solve ", "what is ", "what's ", "whats ",
    )

    SUPPORTED_COMMAND_INTENTS = {
        "open_app",
        "search_web",
        "play_music",
        "system_control",
        "calculate",
    }

    def __init__(self):
        llm_config = get_llm_config()
        self.client = OllamaClient(
            model=llm_config["intent_model"],
            temperature=llm_config["intent_temperature"],
            num_predict=llm_config["intent_max_tokens"],
            keep_alive=llm_config["keep_alive"],
        )

    def classify(self, command):
        local_intent = self._extract_local_command_intent(command)
        if local_intent:
            return local_intent

        system_prompt = """
        You are the intent classifier for Koro, a local voice assistant.

        Return ONLY one compact JSON object. Do not use markdown.
        The JSON object must always contain exactly these keys:
        {"type":"...","intent":"...","target":"..."}

        Types:
        - "command": the user wants Koro to do something
        - "question": the user wants Koro to answer something

        Command intents:
        - "open_app": open or launch an app, website, utility, or tool
        - "search_web": search the web
        - "play_music": play music, a song, artist, album, or playlist
        - "system_control": change volume, mute, lock, shutdown, restart
        - "calculate": calculate a math expression
        - "unknown": command intent is unclear

        Rules:
        - For questions, use {"type":"question","intent":"answer","target":""}.
        - For commands, target must be the app name, search query, music name, system action, or expression.
        - Never return only {"type":"command"}.

        Examples:
        open calculator -> {"type":"command","intent":"open_app","target":"calculator"}
        open chrome -> {"type":"command","intent":"open_app","target":"chrome"}
        search for pizza near me -> {"type":"command","intent":"search_web","target":"pizza near me"}
        play blinding lights -> {"type":"command","intent":"play_music","target":"blinding lights"}
        volume up -> {"type":"command","intent":"system_control","target":"volume up"}
        what is the capital of India -> {"type":"question","intent":"answer","target":""}
        """

        response = self.client.chat(system_prompt, command)

        try:
            match = re.search(r'\{[^{}]*\}', response, re.DOTALL)
            if match:
                intent_data = json.loads(match.group())
                return self._normalize_intent(command, intent_data)
        except Exception as exc:
            print("JSON Error:", exc)

        if self._looks_like_question(command):
            return {
                "type": "question",
                "intent": "answer",
                "target": ""
            }

        return {
            "type": "unknown",
            "intent": "unknown",
            "target": ""
        }

    def _extract_local_command_intent(self, command):
        command_clean = command.strip().lower()
        compact_command = re.sub(r"\s+", " ", command_clean)

        calculation_target = self._extract_calculation_target(compact_command)
        if calculation_target:
            return {
                "type": "command",
                "intent": "calculate",
                "target": calculation_target
            }

        volume_level_match = re.search(
            r"\bvolume\s+(?:to\s+|at\s+)?(\d{1,3})\b",
            compact_command
        )
        if volume_level_match:
            level = max(0, min(100, int(volume_level_match.group(1))))
            return {
                "type": "command",
                "intent": "system_control",
                "target": f"volume {level}"
            }

        system_control_phrases = {
            "volume up": (
                "increase volume", "volume up", "raise volume",
                "turn up volume", "turn the volume up"
            ),
            "volume down": (
                "decrease volume", "volume down", "lower volume",
                "turn down volume", "turn the volume down"
            ),
            "volume mute": (
                "mute volume", "mute the volume", "mute audio",
                "unmute volume", "unmute the volume"
            ),
        }

        for target, phrases in system_control_phrases.items():
            if any(phrase in compact_command for phrase in phrases):
                return {
                    "type": "command",
                    "intent": "system_control",
                    "target": target
                }

        return None

    def _normalize_intent(self, command, intent_data):
        input_type = intent_data.get("type")
        intent = intent_data.get("intent")
        target = intent_data.get("target", "")

        if input_type in self.SUPPORTED_COMMAND_INTENTS and intent in (None, "", "unknown"):
            intent = input_type
            input_type = "command"

        if input_type == "question" or intent == "answer":
            return {
                "type": "question",
                "intent": "answer",
                "target": ""
            }

        if self._looks_like_question(command):
            return {
                "type": "question",
                "intent": "answer",
                "target": ""
            }

        if intent in (None, "unknown") and not self._looks_like_command(command):
            return {
                "type": "question",
                "intent": "answer",
                "target": ""
            }

        if input_type == "command" and intent in (None, "", "unknown"):
            guessed_intent, guessed_target = self._infer_command_from_text(command)
            if guessed_intent:
                return {
                    "type": "command",
                    "intent": guessed_intent,
                    "target": guessed_target
                }

        if input_type == "command" and intent not in self.SUPPORTED_COMMAND_INTENTS:
            return {
                "type": "unknown",
                "intent": "unknown",
                "target": target
            }

        return {
            "type": input_type or "unknown",
            "intent": intent or "unknown",
            "target": target
        }

    def _infer_command_from_text(self, command):
        command_clean = re.sub(r"\s+", " ", command.strip().lower())

        command_patterns = (
            (r"^(?:open|launch|start)\s+(.+)$", "open_app"),
            (r"^(?:search|google|look up|find)\s+(?:for\s+)?(.+)$", "search_web"),
            (r"^(?:play|shuffle)\s+(.+)$", "play_music"),
        )

        for pattern, intent in command_patterns:
            match = re.match(pattern, command_clean)
            if match:
                return intent, match.group(1).strip()

        return "", ""

    def _extract_calculation_target(self, command):
        command_clean = re.sub(r"\s+", " ", command.strip().lower())
        prefixes = (
            "calculate ",
            "compute ",
            "solve ",
            "what is ",
            "what's ",
            "whats ",
            "how much is ",
        )

        prefix = next((item for item in prefixes if command_clean.startswith(item)), None)
        if not prefix:
            return ""

        expression = command_clean[len(prefix):].strip()
        expression = re.sub(
            r"\b(please|now|equals?|equal to|result|answer)\b",
            "",
            expression
        )
        expression = re.sub(r"\bplus\b", "+", expression)
        expression = re.sub(r"\bminus\b", "-", expression)
        expression = re.sub(r"\btimes\b", "*", expression)
        expression = re.sub(r"\bmultiplied by\b", "*", expression)
        expression = re.sub(r"\bdivided by\b", "/", expression)
        expression = re.sub(r"\bover\b", "/", expression)
        expression = re.sub(r"\s+", " ", expression).strip()

        if not expression:
            return ""

        if not re.search(r"\d", expression):
            return ""

        if not re.search(r"[+\-*/()]|\*\*", expression):
            return ""

        return expression

    def _looks_like_question(self, command):
        command_clean = command.strip().lower()
        question_starters = (
            "what", "why", "how", "when", "where", "who", "which",
            "is", "are", "can", "could", "would", "should", "do", "does",
            "did", "tell me", "explain", "define"
        )

        question_phrases = (
            "capital of", "meaning of", "definition of", "weather in",
            "time in", "date of", "population of", "distance between",
            "price of", "who is", "what is", "what are", "how many",
            "how much"
        )

        return (
            command_clean.endswith("?")
            or command_clean.startswith(question_starters)
            or any(phrase in command_clean for phrase in question_phrases)
        )

    def _looks_like_command(self, command):
        command_clean = re.sub(r"\s+", " ", command.strip().lower())
        return any(
            command_clean.startswith(cue) or f" {cue.strip()} " in f" {command_clean} "
            for cue in self.COMMAND_CUES
        )
