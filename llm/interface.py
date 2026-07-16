import json
import re

from config import get_assistant_name, get_llm_config
from llm.intent_classifier import IntentClassifier
from llm.ollama_client import OllamaClient


class LLMInterface:
    def __init__(self, assistant_name=None):

        llm_config = get_llm_config()
        self.client = OllamaClient(
            model=llm_config["response_model"],
            temperature=llm_config["response_temperature"],
            num_predict=llm_config["response_max_tokens"],
            keep_alive=llm_config["keep_alive"],
        )
        self.intent_classifier = IntentClassifier()
        self.assistant_name = (assistant_name or get_assistant_name()).strip() or "Koro"

    def extract_intent(self, command):
        return self.intent_classifier.classify(command)
    
    def extract_music_intent(self, command):
        system_prompt = """
        You are a music intent parser.
 
        The user will say something like:
          - "play Blinding Lights"
          - "play the song Levitating"
          - "play from playlist Chill Vibes"
          - "play my playlist Workout Mix"
          - "shuffle playlist Lo-Fi Beats"
 
        Return ONLY a JSON object with two keys:
          "kind"   -> either "song" or "playlist"
          "target" -> the exact song or playlist name the user mentioned
 
        Rules:
        - If the user says "playlist", "from playlist", "my playlist", or "shuffle playlist", set kind to "playlist".
        - Otherwise set kind to "song".
        - Never include any explanation or extra text — only the JSON.
 
        Examples:
          Input:  play blinding lights
          Output: {"kind":"song","target":"Blinding Lights"}
 
          Input:  play from playlist chill vibes
          Output: {"kind":"playlist","target":"Chill Vibes"}
 
          Input:  play my playlist workout mix
          Output: {"kind":"playlist","target":"Workout Mix"}
        """
 
        response = self.client.chat(system_prompt, command)
 
        try:
            match = re.search(r'\{[^{}]*\}', response, re.DOTALL)
            if match:
                return json.loads(match.group())
 
        except Exception as e:
            print("JSON Error (music intent):", e)
 
        return {
            "kind": "song",
            "target": command
        }

    def answer_question(self, question):
        system_prompt = (
            f"You are {self.assistant_name}, a fast, natural voice assistant.\n"
            "Reply like a person talking to a person.\n"
            "Be concise, direct, and conversational.\n"
            "Avoid sounding formal, scripted, or like a manual.\n"
            "Do not use markdown, bullet points, or long lists.\n"
            "Keep the answer under 3 sentences unless detail is clearly needed."
        )

        response = self.client.chat(
            system_prompt,
            question,
            temperature=None,
            num_predict=None,
        )
        return response.strip()
  
