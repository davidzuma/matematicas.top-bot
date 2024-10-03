import contextlib
from datetime import datetime
import os
import sqlitecloud
from dotenv import load_dotenv
from openai import OpenAI
from utils import get_embedding
import pandas as pd


 # TODO: add config here
# Load environment variables from .env file
load_dotenv()
SQLITECLOUD_API_KEY = os.getenv("SQLITECLOUD_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
os.environ["OPENAI_API_KEY"] = OPENAI_API_KEY
client = OpenAI()

class DatabaseManager:
    def __init__(self, api_key, db_name):
        self.api_key = api_key
        self.db_name = db_name

    @contextlib.contextmanager
    def get_connection(self):
        conn = sqlitecloud.connect(f"sqlitecloud://ctemvrrusk.sqlite.cloud:8860?apikey={self.api_key}")
        conn.execute(f"USE DATABASE {self.db_name}")
        try:
            yield conn
        finally:
            conn.close()

    def initialize_database(self):
        self._create_users_table()
        self._create_openai_usage_table()
        self._create_yt_videos_table()
        self._create_yt_videos_embeddings_table()

    def is_user_registered(self, user_id):
        with self.get_connection() as conn:
            cursor = conn.execute('SELECT 1 FROM users WHERE user_id = ?', (user_id,))
            return cursor.fetchone() is not None

    def _create_users_table(self):
        with self.get_connection() as conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY,
                    username TEXT,
                    first_name TEXT,
                    last_name TEXT
                )
            ''')
            conn.commit()

    def _create_openai_usage_table(self):
        with self.get_connection() as conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS openai_usage (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    timestamp DATETIME,
                    model TEXT,
                    tokens_used INTEGER,
                    estimated_cost REAL,
                    FOREIGN KEY (user_id) REFERENCES users(user_id)
                )
            ''')
            conn.commit()

    def _create_yt_videos_table(self):
        with self.get_connection() as conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS yt_videos (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    url TEXT NOT NULL,
                    description TEXT NOT NULL
                )
            ''')
            conn.commit()

    def _create_yt_videos_embeddings_table(self):
        with self.get_connection() as conn:
            conn.execute('''
                CREATE VIRTUAL TABLE IF NOT EXISTS yt_videos_embeddings USING vec0(
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    embedding FLOAT[3072]
                )
            ''')
            conn.commit()

    def create_user(self, user_id, username, first_name, last_name):
        with self.get_connection() as conn:
            conn.execute('''
                INSERT OR REPLACE INTO users (user_id, username, first_name, last_name)
                VALUES (?, ?, ?, ?)
            ''', (user_id, username, first_name, last_name))
            conn.commit()

    def log_openai_usage(self, user_id, model, tokens_used, estimated_cost):
        with self.get_connection() as conn:
            conn.execute('''
                INSERT INTO openai_usage (user_id, timestamp, model, tokens_used, estimated_cost)
                VALUES (?, ?, ?, ?, ?)
            ''', (user_id, datetime.now(), model, tokens_used, estimated_cost))
            conn.commit()

    def get_user_usage(self, user_id):
        with self.get_connection() as conn:
            cursor = conn.execute('''
                SELECT SUM(tokens_used) as total_tokens, SUM(estimated_cost) as total_cost
                FROM openai_usage
                WHERE user_id = ?
            ''', (user_id,))
            return cursor.fetchone()

    

    def insert_yt_data_csv(self, csv_file):
        df = pd.read_csv(csv_file, names=['url', 'description'])
        for _, row in df.iterrows():
            self._insert_video_data(row['url'], row['description'])
            embedding = get_embedding(row['description'])
            self._insert_video_embedding(embedding)

    def retrieve_similar_vectors(self, sample_embedding, limit=4):
        with self.get_connection() as conn:
            cursor = conn.execute(f"""
                SELECT id, distance
                FROM yt_videos_embeddings
                WHERE embedding MATCH '{sample_embedding}'
                ORDER BY distance
                LIMIT {limit}
            """)
            return cursor.fetchall()

    def get_video_details(self, video_id):
        with self.get_connection() as conn:
            cursor = conn.execute("""
                SELECT url, description
                FROM yt_videos
                WHERE id = ?
            """, (video_id,))
            result = cursor.fetchone()
            return result if result else (None, None)


    def _insert_video_embedding(self, embedding):
        with self.get_connection() as conn:
            embedding_str = ', '.join(map(str, embedding))
            conn.execute(f"""
                INSERT INTO yt_videos_embeddings (embedding)
                VALUES ('[{embedding_str}]')
            """)
            conn.commit()

    def _insert_video_data(self, url, description):
        with self.get_connection() as conn:
            conn.execute("""
                INSERT INTO yt_videos (url, description)
                VALUES (?, ?)
            """, (url, description))
            conn.commit()

if __name__ == "__main__":
    db_manager = DatabaseManager(os.getenv("SQLITECLOUD_API_KEY"), os.getenv("DB_NAME", "matematicas-top"))
    db_manager.initialize_database()
     # Assuming clear_database is a method to clear the database

# Usage example:
# db_manager = DatabaseManager(SQLITECLOUD_API_KEY, "matematicas-top")
# db_manager.initialize_database()
# db_manager.insert_("your_csv_file.csv")
    
    # create_yt_videos_table()
    # Create the yt_videos table if it doesn't exist
    # create_yt_videos_table()
    
    # Process and insert data from the CSV
    # embedding_example = str(get_embedding("ECUACIÓN LOGARITMICA"))
    # retrieve_similar_vectors(embedding_example)
    #insert__and_insert_data('data/yt/videos.csv')
    # Initialize the database when this module is imported
