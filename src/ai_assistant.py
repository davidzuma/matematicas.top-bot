import base64
import functools
import json
from typing import List, Dict, Tuple, Optional

from openai import OpenAI
from config import Config
from database import DatabaseManager

class AIAssistant:
    def __init__(self, db_manager, config: Dict):
        self.db_manager = db_manager
        self.openai_client = OpenAI()
        self.config = config

    def chat(self, messages: List[Dict], user_id: int) -> str:
        system_message = {
            "role": "system",
            "content": self.config.get("system_message", "")
        }
        
        full_messages = [system_message] + messages
        
        return self.query_openai(full_messages, self.config.get("chat_model", "gpt-4o-mini"), user_id)

    @staticmethod
    def encode_image(image_path: str) -> str:
        with open(image_path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode("utf-8")

    @staticmethod
    def hashable_messages(messages):
        return tuple(json.dumps(message, sort_keys=True) for message in messages)

    @functools.lru_cache(maxsize=None)
    def _cached_query_openai(self, hashed_messages: Tuple, model: str, user_id: int) -> str:
        messages = [json.loads(message) for message in hashed_messages]
        response = self.openai_client.chat.completions.create(
            model=model,
            messages=messages,
        )
        usage = response.usage
        
        cost_config = self.config.get("model_costs", {}).get(model, {"input": 0, "output": 0})
        input_cost = usage.prompt_tokens * cost_config["input"] / 1000000
        output_cost = usage.completion_tokens * cost_config["output"] / 1000000
        
        total_cost = input_cost + output_cost
        total_tokens = usage.total_tokens
        
        self.db_manager.log_openai_usage(user_id, model, total_tokens, total_cost)
        
        if response.choices[0].message.content:
            return response.choices[0].message.content.strip()
        return ""

    def query_openai(self, messages: List[Dict], model: str, user_id: int) -> str:
        hashed_messages = self.hashable_messages(messages)
        return self._cached_query_openai(hashed_messages, model, user_id)

    def parse_image(self, image_path: str, user_id: int) -> str:
        base64_image = self.encode_image(image_path)
        
        messages = [
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": self.config.get("image_parse_prompt", "Describe the content of this image.")
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
        
        return self.query_openai(messages, self.config.get("image_model", "gpt-4o"), user_id)

    def solve_problem(self, problem: str, user_id: int) -> str:
        messages = [
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": f"{self.config.get('problem_solve_prompt', '')} {problem}"
                    }
                ]
            }
        ]
        
        return self.query_openai(messages, self.config.get("problem_solve_model", "gpt-4o-mini"), user_id)

    def get_embedding(self, text: str) -> List[float]:
        response = self.openai_client.embeddings.create(
            input=text,
            model=self.config.get("embedding_model", "text-embedding-3-small")
        )
        return response.data[0].embedding

    def recommend_content(self, query: str, user_id: int) -> str:
        query_embedding = self.get_embedding(query)
        similar_vectors = self.db_manager.retrieve_similar_vectors(query_embedding, limit=self.config.get("recommendation_limit", 5))
        content_details = "\n".join([":".join(self.db_manager.get_content_details(id) or ["", ""]) for id, _ in similar_vectors])
        
        messages = [
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": f"{self.config.get('recommendation_prompt', '')}\n\nQuery: {query}\n\nContent: {content_details}"
                    }
                ]
            }
        ]
        
        return self.query_openai(messages, self.config.get("recommendation_model", "gpt-4o-mini"), user_id)

def create_math_assistant(db_manager) -> AIAssistant:
    math_config = {
        "system_message": """Eres Matemáticas TOP un asistente matemático amigable y conversacional. Este es tu canal youtube: https://www.youtube.com/@matematicastop. 
        Ya te has presentado y has mandado tu canal una vez y no tienes que presentarte de nuevo pero puedes mandar tu canal cuando veas oportuno.
        Puedes ayudar con problemas matemáticos, explicar conceptos y mantener una conversación general sobre matemáticas y temas relacionados. También eres capaz de entender imágenes. 
        No uses LaTeX ni Markdown solo texto plano.
        No respondas a temas no relacionados con las Matemáticas.""",
        "chat_model": "gpt-4o-mini",
        "image_model": "gpt-4o",
        "problem_solve_model": "gpt-4o",
        "recommendation_model": "gpt-4o-mini",
        "embedding_model": "text-embedding-3-large",
        "model_costs": {
            "gpt-4o-mini": {"input": 0.15, "output": 0.6},
            "gpt-4o": {"input": 5, "output": 15}
        },
        "image_parse_prompt": """Eres un experto en clasificar problemas matemáticos. 
        Dada una imagen devuelve el contenido de la imagen y el tipo de problema matemático. 
        Ejemplo de resultado: ∫ x^(-1/3) dx - Integral inmediata 
        No modifiques la ecuación/problema. Devuelve esta estructura de resultado (ecuación/problema - tipo de ecuación/problema) y nada más.""",
        "problem_solve_prompt": """Eres un experto en explicar problemas matemáticos. 
        Dada la siguiente expresión matemática, resuélvela: {problem}. 
        Devuelve solo el proceso para hallar la solución y la solución. No incluyas latex solo texto plano y símbolos matemáticos.""",
        "recommendation_prompt": """Eres un experto en encontrar videos educativos.
        Dada la siguiente problema de matemáticas y la lista de videos, sugiere el video más relevante:
        Si los videos no están relacionados, responde: "No encontré ningún video relacionado".
        Devuelve el link del video o No encontré ningún video relacionado.
        No incluyas nada más.""",
        "recommendation_limit": 5
    }
    return AIAssistant(db_manager, math_config)

if __name__ == "__main__":
    # Example usage
    config = Config()
    config.set_config()
    db_manager = DatabaseManager(config)
    db_manager.initialize_database()

      # Initialize your database manager here # Initialize your OpenAI client here
    
    math_assistant = create_math_assistant(db_manager)
    
    user_id = 12345
    math_assistant.db_manager.create_user(user_id, "test_user", "Test", "User")

    image_path = "data/imgs/Matematicas Top.jpg"
    math_problem = math_assistant.parse_image(image_path, user_id)
    solution = math_assistant.solve_problem(math_problem, user_id)
    yt_video_link = math_assistant.recommend_content(math_problem, user_id)

    print(f"Math Problem: {math_problem}")
    print(f"Solution: {solution}")
    print(f"Recommended YouTube Video: {yt_video_link}")

    # Print usage for the test user
    usage = math_assistant.db_manager.get_user_usage(user_id)
    if usage:
        total_tokens, total_cost = usage
        print(f"Test user usage - Tokens: {total_tokens}, Cost: ${total_cost:.4f}")