import os
from dotenv import load_dotenv

class Config:
    def __init__(self):
        load_dotenv()
        self.OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
        self.TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_API_KEY")
        self.SQLITECLOUD_API_KEY = os.getenv("SQLITECLOUD_API_KEY")
        self.DB_NAME = os.getenv("DB_NAME", "matematicas-top")
        self.WEBHOOK_URL = "https://matematicas-top-bot.onrender.com"
        self.WEBHOOK_PATH = f"/webhook/{self.TELEGRAM_BOT_TOKEN}"
        self.ADMIN_CHAT_ID = os.getenv("ADMIN_CHAT_ID")

    def set_config(self):         
        os.environ["OPENAI_API_KEY"] = self.OPENAI_API_KEY
        self._validate()

    def _validate(self):
        missing = [k for k, v in self.__dict__.items() if v is None]
        if missing:
            raise ValueError(f"Missing environment variables: {', '.join(missing)}")

    def get_webhook_url(self):
        return f"{self.WEBHOOK_URL}{self.WEBHOOK_PATH}"