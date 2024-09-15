import base64
import os
from openai import OpenAI
from dotenv import load_dotenv
import functools

# gpt-4o-mini
# $0.150 / 1M input tokens
# $0.600 / 1M output tokens

# gpt-4o
# $5.00 / 1M input tokens
# $15.00 / 1M output tokens


load_dotenv()  # Load environment variables from .env file
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
client = OpenAI(api_key=OPENAI_API_KEY)

def encode_image(image_path: str) -> str:
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode("utf-8")

def query_openai(messages: list[dict]) -> str:
    response = client.chat.completions.create(
        model="gpt-4o-mini",  # Updated model name
        messages=messages,
        max_tokens=300,
    )
    usage = response.usage
    if response.choices[0].message.content:
        return response.choices[0].message.content.strip()
    return ""

@functools.lru_cache(maxsize=None) 
def main(image_path):
    base64_image = encode_image(image_path)

    messages = [
        {
            "role": "user",
            "content": [
                {
                    "type": "text",
                    "text": "Resuelve el siguiente problema. Da una explicación paso por paso. No uses latext"
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

if __name__ == "__main__":
    image_path = "image.png"  # Replace with the actual image path
    main(image_path)