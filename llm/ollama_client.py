import ollama


class OllamaClient:

    def __init__(self, model="qwen2:0.5b", temperature=0, num_predict=50, keep_alive="10m"):

        self.model = model
        self.temperature = temperature
        self.num_predict = num_predict
        self.keep_alive = keep_alive

    def chat(self, system_prompt, user_prompt, temperature=None, num_predict=None):

        actual_temperature = self.temperature if temperature is None else temperature
        actual_num_predict = self.num_predict if num_predict is None else num_predict

        response = ollama.chat(
            model=self.model,
            messages=[
                {
                    "role": "system",
                    "content": system_prompt
                },
                {
                    "role": "user",
                    "content": user_prompt
                }
            ],
            options={
                "temperature": actual_temperature,
                "num_predict": actual_num_predict,
            },
            keep_alive=self.keep_alive
        )

        return response["message"]["content"]
