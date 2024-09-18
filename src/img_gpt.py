import base64
import os
from openai import OpenAI
from dotenv import load_dotenv
import functools
from utils import get_embedding, retrieve_similar_vectors, get_url_and_description

# gpt-4o-mini
# $0.150 / 1M input tokens
# $0.600 / 1M output tokens

# gpt-4o
# $5.00 / 1M input tokens
# $15.00 / 1M output tokens


load_dotenv()  # Load environment variables from .env file
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
os.environ["OPENAI_API_KEY"] = OPENAI_API_KEY
client = OpenAI()

def encode_image(image_path: str) -> str:
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode("utf-8")

def query_openai(messages: list[dict]) -> str:
    response = client.chat.completions.create(
        model="gpt-4o-mini", 
        messages=messages,
    )
    usage = response.usage
    if response.choices[0].message.content:
        return response.choices[0].message.content.strip()
    return ""

@functools.lru_cache(maxsize=None) 
def parse_image(image_path):
    base64_image = encode_image(image_path)

    messages = [
        {
            "role": "user",
            "content": [
                {
                    "type": "text",
                    "text": "Eres un experto en clasificar problemás matemáticos."
                    "Dada una imagen devuelve el contenido de la imagen y el tipo de problema matemático."
                    "Ejemplo de resultado: ∫ x^(-1/3) dx - Integral inmediata"
                    "Devuelve esta estructura de resultado (equación/problema - tipo de equación/problema) y nada más."
        
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

    final_response = query_openai(messages)
    return final_response
def solve_math_problem(math_problem: str):
    messages = [
        {
            "role": "user",
            "content": [
                {
                    "type": "text",
                    "text": "Eres un experto en explicar problemas matemáticos. "
                             f"Dada la siguiente expresión matemática, resuélvela: {math_problem}. "
                             "Devuelve solo el proceso para hayar la solución y la solución. No incluyas latex solo texto plano y símbolos matemáticos."
                }
            ]
        }
    ]

    final_response = query_openai(messages)
    return final_response
def recommend_yt_video(math_problem:str):
    math_problem_embedding = get_embedding(math_problem)
    similar_vectors_in_yt_videos = retrieve_similar_vectors(math_problem_embedding, limit=5)
    descriptions_and_links = "/n".join([":".join(get_url_and_description(id)) for id, _ in similar_vectors_in_yt_videos])
  

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

    final_response = query_openai(messages)


    return final_response
    



if __name__ == "__main__":
    image_path = "data/imgs/eq_example.png"
    math_problem =parse_image(image_path)  # Replace with the actual image path
    solution = solve_math_problem(image_path)
    yt_video_link = recommend_yt_video(math_problem)
    print(math_problem," ----" ,yt_video_link)