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



@contextlib.contextmanager
def get_db_connection():
    conn = sqlitecloud.connect(
        f"sqlitecloud://ctemvrrusk.sqlite.cloud:8860?apikey={SQLITECLOUD_API_KEY}"
    )
    db_name = "matematicas-top"
    conn.execute(f"USE DATABASE {db_name}")
    try:
        yield conn
    finally:
        conn.close()
def create_yt_videos_table():
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
        """
        CREATE TABLE yt_videos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            url TEXT NOT NULL,
            description TEXT NOT NULL
        )
        """
        )
        conn.commit()

def create_yt_videos_embedding_table():
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
        """
        create virtual table yt_videos_embeddings using vec0(
        id integer primary key autoincrement,
        embedding float[3072])
        """
        )
        conn.commit()


def get_embedding(text):
    response = client.embeddings.create(
        input=text,
        model="text-embedding-3-large"
    )
    embedding = response.data[0].embedding
    return embedding


# Function to insert data into yt_videos table
def insert_video_data_embedding(embedding):
    with get_db_connection() as conn:
        cursor = conn.cursor()
        values = ', '.join(f"('{embedding}')" for embedding in embedding)
        cursor.execute(f"""
            INSERT INTO yt_videos_embeddings (embedding)
            VALUES {values}
        """)
        conn.commit()

# Function to read the CSV file and process it
def process_csv_and_insert_embeddings(csv_file):
    # Read the CSV file into a pandas DataFrame
    df = pd.read_csv(csv_file, names=['url', 'title'])
    
    embeddings = []
    
    # Iterate over the rows and get embeddings
    for index, row in df.iterrows():
        title = row['title']
        
        # Get the embedding for the title
        embedding = get_embedding(title)
        # Format embedding as a string
        embedding_str = ', '.join(map(str, embedding))  # Convert to a string format suitable for insertion
        embeddings.append(f"[{embedding_str}]")
    insert_video_data_embedding(embeddings)

def process_csv_and_insert_data(csv_file):
    # Read the CSV file into a pandas DataFrame
    df = pd.read_csv(csv_file, names=['url', 'description'])
    
    # Iterate over the rows and insert data into yt_videos table
    for index, row in df.iterrows():
        url = row['url']
        title = row['description']
        
        # Insert the video data into the yt_videos table
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO yt_videos (url, description)
                VALUES (?, ?)
            """, (url, title))
            conn.commit()
def retrieve_similar_vectors(sample_embedding, limit=4):
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(f"""
            SELECT id, distance
            FROM yt_videos_embeddings
            WHERE embedding MATCH '{sample_embedding}'
            ORDER BY distance
            LIMIT {limit}
        """)
        results = cursor.fetchall()
    return results

def get_url_and_description(id):
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT url, description
            FROM yt_videos
            WHERE id = ?
        """, (id,))
        result = cursor.fetchone()
    return result if result else (None, None)

# Main function
if __name__ == "__main__":
    # create_yt_videos_table()
    # Create the yt_videos table if it doesn't exist
    # create_yt_videos_table()
    
    # Process and insert data from the CSV
    embedding_example = str(get_embedding("ECUACIÓN LOGARITMICA"))
    retrieve_similar_vectors(embedding_example)
    #process_csv_and_insert_data('data/yt/videos.csv')