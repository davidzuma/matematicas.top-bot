import logging
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
import os
from config import Config
from math_assistant import MathAssistant
from database import DatabaseManager
from openai import OpenAI

class MathBot:
    def __init__(self, config: Config):
        self.config = config
        self.config.set_config()

        # Configure logging
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)

        self.openai_client = OpenAI()

        # Initialize database manager and math assistant
        self.db_manager = DatabaseManager(self.config.SQLITECLOUD_API_KEY, self.config.DB_NAME)
        self.math_assistant = MathAssistant(self.db_manager, self.openai_client)

        # Initialize the application
        self.application = ApplicationBuilder().token(self.config.TELEGRAM_BOT_TOKEN).build()
        self.application.bot_data['db_manager'] = self.db_manager
        self.application.bot_data['math_assistant'] = self.math_assistant

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user

        if context.args:
            # TODO: finish this funcionality
            referrer_id = context.args[0]
            self.db_manager.add_credits(referrer_id, 10)
            await update.message.reply_text(f"Te has registrado con el código de referencia de {referrer_id}. ¡Ellos ganaron 10 créditos!")

        self.db_manager.create_user(user.id, user.username, user.first_name, user.last_name)
        self.logger.info(f"User {user.first_name} started the bot.")
        await update.message.reply_text(f'Hola {user.first_name}! Puedes enviarme mensajes o imágenes de ecuaciones. ¿En qué puedo ayudarte hoy?')

        # Initialize conversation history
        context.user_data['history'] = []

    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        message = update.message.text

        await context.bot.send_chat_action(chat_id=update.effective_chat.id, action='typing')
        context.user_data['history'].append({"role": "user", "content": message})

        response = self.math_assistant.chat(context.user_data['history'], user.id)

        context.user_data['history'].append({"role": "assistant", "content": response})

        if len(context.user_data['history']) > 10:
            context.user_data['history'] = context.user_data['history'][-10:]

        await context.bot.send_chat_action(chat_id=update.effective_chat.id, action='typing')
        await update.message.reply_text(response)

    async def handle_image(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        self.logger.info("Received an image from the user.")
        user = update.effective_user

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

        context.user_data['history'].append({"role": "user", "content": "User sent an image of a math problem."})
        context.user_data['history'].append({"role": "assistant", "content": f"I solved the math problem: {solution}\n\nHere's a relevant video: {yt_video_link}"})

    async def show_usage(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        usage = self.db_manager.get_user_usage(user.id)
        if usage:
            total_tokens, total_cost = usage
            await update.message.reply_text(f"Tu uso total de OpenAI:\nTokens: {total_tokens}\nCosto estimado: ${total_cost:.4f}")
        else:
            await update.message.reply_text("Aún no has utilizado el servicio de OpenAI.")

    async def referral(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        referral_link = f"https://t.me/{context.bot.username}?start={user.id}"
        await update.message.reply_text(f'Tu enlace de referencia: {referral_link}')

    def setup_handlers(self):
        self.application.add_handler(CommandHandler("start", self.start))
        self.application.add_handler(CommandHandler("usage", self.show_usage))
        self.application.add_handler(CommandHandler("referral", self.referral))
        self.application.add_handler(MessageHandler(filters.PHOTO, self.handle_image))
        self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))

    def run(self):
        self.db_manager.initialize_database()
        self.setup_handlers()
        self.logger.info("Bot is polling for updates.")
        self.application.run_polling()

if __name__ == "__main__":
    config = Config()
    bot = MathBot(config)
    bot.run()