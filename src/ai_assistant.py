import subprocess
import pandas as pd
from openai import OpenAI
from config import Config

config = Config()
config.set_config()
client = OpenAI()



class OpenAIUtils:
    def __init__(self,db_manager, config):
        self.db_manager = db_manager
        self.config = config
        
# TODO: create a class to be used in databaseManager and mathAssistant OpenAIUtils with raw funcionalities openAI
def get_embedding(text):
    response = client.embeddings.create(
        input=text,
        model="text-embedding-3-large"
    )
    embedding = response.data[0].embedding
    return embedding
