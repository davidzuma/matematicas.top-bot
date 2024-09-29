from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
import os
import logging
from dotenv import load_dotenv
from math_assistant import MathAssistant
from database import DatabaseManager
import asyncio
from openai import OpenAI


# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
os.environ["OPENAI_API_KEY"] = OPENAI_API_KEY
openai_client = OpenAI()  # Cargar variables de entorno desde el archivo .env
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_API_KEY")
SQLITECLOUD_API_KEY = os.getenv("SQLITECLOUD_API_KEY")
DB_NAME = os.getenv("DB_NAME", "matematicas-top")

# Función para responder al comando /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    db_manager = context.bot_data['db_manager']
    user = update.effective_user
    db_manager.create_user(user.id, user.username, user.first_name, user.last_name)
    logger.info(f"User {user.first_name} started the bot.")
    await update.message.reply_text(f'Hola {user.first_name}! Envíame una imagen de una ecuación y la resolveré para ti.')

# Función para manejar imágenes recibidas
async def handle_image(update: Update, context: ContextTypes.DEFAULT_TYPE):
    
    db_manager = context.bot_data['db_manager']
    math_assistant = context.bot_data['math_assistant']
    logger.info("Received an image from the user.")
    user = update.effective_user
    
    # Mostrar "escribiendo..." mientras el bot procesa la imagen
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action='typing')
    
    # Obtener la imagen
    file = await context.bot.get_file(update.message.photo[-1].file_id)
    
    # Descargar la imagen
    image_path = 'temp_equation.jpg'
    await file.download_to_drive(image_path)
    logger.info(f"Image downloaded to {image_path}.")
    
    # Resolver la ecuación usando la función importada
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action='typing')  # Seguir mostrando escribiendo
    math_problem = math_assistant.parse_image(image_path, user.id)
    
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action='typing')  # Seguir mostrando escribiendo
    solution = math_assistant.solve_math_problem(math_problem, user.id)
    
    logger.info("Equation solved.")
    
    # Enviar el resultado
    await update.message.reply_text(solution)
    
    # Mostrar "escribiendo..." mientras busca el video de YouTube
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action='typing')
    
    yt_video_link = math_assistant.recommend_yt_video(math_problem, user.id)
    await update.message.reply_text(yt_video_link)
    
    # Eliminar la imagen temporal
    os.remove(image_path)
    logger.info(f"Temporary image {image_path} deleted.")

# Función para mostrar el uso de OpenAI
async def show_usage(update: Update, context: ContextTypes.DEFAULT_TYPE):
    db_manager = context.bot_data['db_manager']
    user = update.effective_user
    usage = db_manager.get_user_usage(user.id)
    if usage:
        total_tokens, total_cost = usage
        await update.message.reply_text(f"Tu uso total de OpenAI:\nTokens: {total_tokens}\nCosto estimado: ${total_cost:.4f}")
    else:
        await update.message.reply_text("Aún no has utilizado el servicio de OpenAI.")

# Función principal para configurar el bot
def main():
    db_manager = DatabaseManager(SQLITECLOUD_API_KEY, DB_NAME)
    db_manager.initialize_database()
    math_assistan = MathAssistant(db_manager,openai_client)
    # Inicializar el bot de Telegram
    application = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()
    
    # Store the db_manager in the bot's context
    application.bot_data['db_manager'] = db_manager
    application.bot_data['math_assistant'] = math_assistan
    # Agregar manejadores
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("usage", show_usage))
    application.add_handler(MessageHandler(filters.PHOTO, handle_image))

    # Ejecutar el bot hasta que se detenga manualmente
    logger.info("Bot is polling for updates.")
    application.run_polling()

if __name__ == "__main__":
    main()