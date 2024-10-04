import logging
from telegram import Update, Bot
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
import os
from config import Config
from math_assistant import MathAssistant
from database import DatabaseManager
from openai import OpenAI
from fastapi import FastAPI, Request, HTTPException, BackgroundTasks
from contextlib import asynccontextmanager
import uvicorn
import asyncio
from time import time

config = Config()
config.set_config()

TELEGRAM_TOKEN = config.TELEGRAM_BOT_TOKEN
WEBHOOK_URL = config.WEBHOOK_URL  # Add this to your Config class

class MathBot:
    def __init__(self, config: Config):
   def __init__(self, config: Config):
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.openai_client = OpenAI()
        self.db_manager = DatabaseManager(self.config.SQLITECLOUD_API_KEY, self.config.DB_NAME)
        self.math_assistant = MathAssistant(self.db_manager, self.openai_client)
        self.application = ApplicationBuilder().token(self.config.TELEGRAM_BOT_TOKEN).build()
        self.running = False
        self.bot = Bot(token=self.config.TELEGRAM_BOT_TOKEN)

    async def setup(self):
        self.db_manager.initialize_database()
        self.setup_handlers()
        await self.application.initialize()
        await self.application.bot.set_webhook(url=self.config.get_webhook_url())
        self.logger.info(f"Webhook set to {self.config.get_webhook_url()}")
        self.running = True

    def setup_handlers(self):
        self.application.add_handler(CommandHandler("start", self.start))
        self.application.add_handler(CommandHandler("usage", self.show_usage))
        self.application.add_handler(CommandHandler("referral", self.referral))
        self.application.add_handler(MessageHandler(filters.PHOTO, self.handle_image))
        self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        if not self.db_manager.is_user_registered(user.id):
            self.db_manager.create_user(user.id, user.username, user.first_name, user.last_name)
            self.db_manager.log_openai_usage(user.id, "INITIAL_TOKENS", -20000, 0)
            await update.message.reply_text(f"¡Bienvenido, {user.first_name}! Tienes 1,000,000 de tokens para empezar.")

        if context.args:
            referrer_id = int(context.args[0])
            if referrer_id != user.id and self.db_manager.is_user_registered(referrer_id):
                self.db_manager.log_openai_usage(referrer_id, "REFERRAL_BONUS", -10000, 0)
                await update.message.reply_text(f"Te has registrado con un código de referencia. ¡Tu amigo ha ganado 1,000,000 de tokens extra!")

        self.logger.info(f"User {user.first_name} started the bot.")
        await update.message.reply_text(f"""
        ¡Hola, {user.first_name}! 👋 Soy Matemáticas TOP, aquí para ayudarte con todo lo de matemáticas. 📚✨ ¿Tienes dudas o problemas por resolver? Mándame tus preguntas o una foto del problema, ¡y te lo resuelvo! 📸 Y no olvides pasarte por mi canal de YouTube 🎥👉 https://www.youtube.com/@matematicastop para más trucos y ayuda. ¿Qué necesitas hoy? 😊""")

        context.user_data['history'] = []

    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        usage = self.db_manager.get_user_usage(user.id)
        if usage:
            available_tokens = max(0, -usage[0])
            if available_tokens <= 0:
                await update.message.reply_text("Lo siento, has agotado tus tokens. Invita a un amigo para obtener más tokens.")
                return
        
        if 'history' not in context.user_data:
            await self.start(update, context)
        message = update.message.text
        await context.bot.send_chat_action(chat_id=update.effective_chat.id, action='typing')
        context.user_data['history'].append({"role": "user", "content": message})

        response = self.math_assistant.chat(context.user_data['history'], user.id)
        context.user_data['history'].append({"role": "assistant", "content": response})

        if len(context.user_data['history']) > 5:
            context.user_data['history'] = context.user_data['history'][-5:]

        await context.bot.send_chat_action(chat_id=update.effective_chat.id, action='typing')
        await update.message.reply_text(response)

    async def handle_image(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        self.logger.info("Received an image from the user.")
        user = update.effective_user

        # Check if user has enough tokens
        usage = self.db_manager.get_user_usage(user.id)
        if usage:
            available_tokens = max(0, -usage[0])  # usage[0] is negative for available tokens
            if available_tokens <= 0:
                await update.message.reply_text("Lo siento, has agotado tus tokens. Invita a un amigo para obtener más tokens.")
                return

            await context.bot.send_chat_action(chat_id=update.effective_chat.id, action='typing')
            
            file = await context.bot.get_file(update.message.photo[-1].file_id)
            
            image_path = 'temp_equation.jpg'
            await file.download_to_drive(image_path)
            self.logger.info(f"Image downloaded to {image_path}.")
            
            await context.bot.send_chat_action(chat_id=update.effective_chat.id, action='typing')
            math_problem = self.math_assistant.parse_image(image_path, user.id)
            
            await context.bot.send_chat_action(chat_id=update.effective_chat.id, action='typing')
            solution = self.math_assistant.solve_math_problem(math_problem, user.id)
            
            self.logger.info("Equation solved.")
            
            await update.message.reply_text(solution)
            
            await context.bot.send_chat_action(chat_id=update.effective_chat.id, action='typing')
            
            yt_video_link = self.math_assistant.recommend_yt_video(math_problem, user.id)
            await update.message.reply_text(yt_video_link)
        
            os.remove(image_path)
            self.logger.info(f"Temporary image {image_path} deleted.")

            context.user_data['history'].append({"role": "user", "content": "El usuario envió una imagen de un problema matemático."})
            context.user_data['history'].append({"role": "assistant", "content": f"He resuelto el problema matemático: {solution}\n\nAquí hay un video relevante: {yt_video_link}"})


    async def show_usage(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        usage = self.db_manager.get_user_usage(user.id)
        if usage:
            available_tokens = max(0, -usage[0])
            await update.message.reply_text(f"Tienes {available_tokens} tokens 💰 disponibles para usar.")
        else:
            await update.message.reply_text("Tienes 20,000 de tokens disponibles para usar.")

    async def referral(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        referral_link = f"https://t.me/{context.bot.username}?start={user.id}"
        await update.message.reply_text(f'🌟 Tu enlace de referencia: {referral_link}. Invita a amigos 👥 y recibirás 10,000 de tokens extra para usar aquí 💰! ')
    async def keep_alive(self):
        while True:
            try:
                if self.config.ADMIN_CHAT_ID:
                    await self.bot.send_message(chat_id=self.config.ADMIN_CHAT_ID, text="/start")
                    self.logger.info("Sent keep-alive message")
                else:
                    self.logger.warning("ADMIN_CHAT_ID not set, skipping keep-alive message")
                await asyncio.sleep(300)  # Wait for 5 minutes
            except Exception as e:
                self.logger.error(f"Error in keep_alive: {e}")
                await asyncio.sleep(60)
config = Config()
bot = MathBot(config)

@asynccontextmanager
async def lifespan(app: FastAPI):
    config.set_config()
    await bot.setup()
    background_tasks = BackgroundTasks()
    background_tasks.add_task(bot.keep_alive)
    yield {"background_tasks": background_tasks}

app = FastAPI(lifespan=lifespan)

@app.post(config.WEBHOOK_PATH)
async def webhook_handler(request: Request):
    data = await request.json()
    update = Update.de_json(data, bot.application.bot)
    await bot.application.process_update(update)
    return {"ok": True}

@app.get("/healthz")
async def health_check():
    if not bot.running:
        raise HTTPException(status_code=503, detail="Bot is not running")
    return {"status": "healthy"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))