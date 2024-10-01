import base64
import functools
import json
from dotenv import load_dotenv


class MathAssistant:
    def __init__(self,db_manager,openai_client):
        self.db_manager = db_manager
        self.openai_client = openai_client
        
    def chat(self, messages: list[dict], user_id: int) -> str:
        system_message = {
            "role": "system",
            "content": """Eres un asistente matemático amigable y conversacional. 
            Puedes ayudar con problemas matemáticos, explicar conceptos y mantener una conversación general sobre matemáticas y temas relacionados. No uses LaTeX ni Markdown solo texto plano."""
        }
        
        full_messages = [system_message] + messages
        
        return self.query_openai(full_messages, "gpt-4o-mini", user_id)

    @staticmethod
    def encode_image(image_path: str) -> str:
        with open(image_path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode("utf-8")

    @staticmethod
    def hashable_messages(messages):
        return tuple(json.dumps(message, sort_keys=True) for message in messages)

    @functools.lru_cache(maxsize=None)
    def _cached_query_openai(self, hashed_messages: tuple, model: str, user_id: int) -> str:
        messages = [json.loads(message) for message in hashed_messages]
        response = self.openai_client.chat.completions.create(
            model=model,
            messages=messages,
        )
        usage = response.usage
        
        # TODO: move this to config file or somewhere
        if model == "gpt-4o-mini":
            input_cost = usage.prompt_tokens * 0.15 / 1000000
            output_cost = usage.completion_tokens * 0.6 / 1000000
        elif model == "gpt-4o":
            input_cost = usage.prompt_tokens * 5 / 1000000
            output_cost = usage.completion_tokens * 15 / 1000000
        else:
            input_cost = output_cost = 0
        
        total_cost = input_cost + output_cost
        total_tokens = usage.total_tokens
        
        self.db_manager.log_openai_usage(user_id, model, total_tokens, total_cost)
        
        if response.choices[0].message.content:
            return response.choices[0].message.content.strip()
        return ""

    def query_openai(self, messages: list[dict], model: str, user_id: int) -> str:
        hashed_messages = self.hashable_messages(messages)
        return self._cached_query_openai(hashed_messages, model, user_id)

    def parse_image(self, image_path, user_id):
        base64_image = self.encode_image(image_path)
        
        messages = [
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": "Eres un experto en clasificar problemás matemáticos. "
                                "Dada una imagen devuelve el contenido de la imagen y el tipo de problema matemático. "
                                "Ejemplo de resultado: ∫ x^(-1/3) dx - Integral inmediata "
                                "No modifiques la equación/problema. Devuelve esta estructura de resultado (equación/problema - tipo de equación/problema) y nada más. "
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{base64_image}"
                        }
                    }
                ]
            }
        ]
        
        return self.query_openai(messages, "gpt-4o", user_id)

    def solve_math_problem(self, math_problem: str, user_id: int):
        messages = [
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": f"Eres un experto en explicar problemas matemáticos. "
                                f"Dada la siguiente expresión matemática, resuélvela: {math_problem}. "
                                f"Devuelve solo el proceso para hayar la solución y la solución. No incluyas latex solo texto plano y símbolos matemáticos."
                    }
                ]
            }
        ]
        
        return self.query_openai(messages, "gpt-4o", user_id)
    def get_embedding(self, text):
        response = self.openai_client.embeddings.create(
            input=text,
            model="text-embedding-3-large"
        )
        return response.data[0].embedding

    def recommend_yt_video(self, math_problem: str, user_id: int):
        math_problem_embedding = self.get_embedding(math_problem)
        similar_vectors_in_yt_videos = self.db_manager.retrieve_similar_vectors(math_problem_embedding, limit=5)
        descriptions_and_links = "\n".join([":".join(self.db_manager.get_video_details(id) or ["", ""]) for id, _ in similar_vectors_in_yt_videos])
        
        messages = [
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": f"""Eres un experto en encontrar videos educativos.
                                  Dada la siguiente problema de matemáticas y la lista de videos, sugiere el video más relevante:
                                  
                                  Problema de mátematicas: {math_problem}.
                                  
                                  Lista de videos y links: {descriptions_and_links}.
                                  Devuelve el link del video. No incluyas nada más."""
                    }
                ]
            }
        ]
        
        return self.query_openai(messages, "gpt-4o-mini", user_id)

if __name__ == "__main__":
    math_assistant = MathAssistant()
    math_assistant.db_manager.initialize_database()

    # Example usage
    user_id = 12345
    math_assistant.db_manager.create_user(user_id, "test_user", "Test", "User")

    image_path = "data/imgs/eq_example.png"
    math_problem = math_assistant.parse_image(image_path, user_id)
    solution = math_assistant.solve_math_problem(math_problem, user_id)
    yt_video_link = math_assistant.recommend_yt_video(math_problem, user_id)

    print(f"Math Problem: {math_problem}")
    print(f"Solution: {solution}")
    print(f"Recommended YouTube Video: {yt_video_link}")

    # Print usage for the test user
    usage = math_assistant.db_manager.get_user_usage(user_id)
    if usage:
        total_tokens, total_cost = usage
        print(f"Test user usage - Tokens: {total_tokens}, Cost: ${total_cost:.4f}")