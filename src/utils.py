import subprocess
import pandas as pd
from openai import OpenAI
from config import Config

config = Config()
config.set_config()
client = OpenAI()

# TODO: This maybe belongs outside src or in databaseManage with an UPSERT
def get_videos():
    command = [
        "yt-dlp",
        "--flat-playlist",
        "--print", "%(url)s,%(title)s",
        "--ignore-errors",
        "--no-warnings",
        "https://www.youtube.com/@matematicastop/videos"
    ]
    with open("videos.csv", "w") as output_file:
        subprocess.run(command, stdout=output_file)


# TODO: create a class to be used in databaseManager and mathAssistant OpenAIUtils with raw funcionalities openAI
def get_embedding(text):
    response = client.embeddings.create(
        input=text,
        model="text-embedding-3-large"
    )
    embedding = response.data[0].embedding
    return embedding
