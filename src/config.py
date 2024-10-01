from dotenv import load_dotenv
import os
class Config:
    def __init__(self):
        load_dotenv()
        self.OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
        self.TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_API_KEY")
        self.SQLITECLOUD_API_KEY = os.getenv("SQLITECLOUD_API_KEY")
        self.DB_NAME = os.getenv("DB_NAME", "matematicas-top")

    def set_config(self):         
        os.environ["OPENAI_API_KEY"] = self.OPENAI_API_KEY
        self._validate()

    def _validate(self):
        missing = [k for k, v in self.__dict__.items() if v is None]
        if missing:
            raise ValueError(f"Missing environment variables: {', '.join(missing)}")
