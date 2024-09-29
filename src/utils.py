import subprocess
import contextlib
import os
import random

import pandas as pd
import sqlitecloud
from dotenv import load_dotenv

import base64
import os
from openai import OpenAI
# Load environment variables from .env file
load_dotenv()
SQLITECLOUD_API_KEY = os.getenv("SQLITECLOUD_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
os.environ["OPENAI_API_KEY"] = OPENAI_API_KEY
client = OpenAI()

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


def get_playlists():
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


def get_embedding(text):
    response = client.embeddings.create(
        input=text,
        model="text-embedding-3-large"
    )
    embedding = response.data[0].embedding
    return embedding
