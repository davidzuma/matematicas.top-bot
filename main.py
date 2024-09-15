from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
import os
import logging
from dotenv import load_dotenv
from img_gpt import main as solve_math_equation

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()  # Cargar variables de entorno desde el archivo .env
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_API_KEY")

# Función para responder al comando /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_first_name = update.effective_user.first_name
    logger.info(f"User {user_first_name} started the bot.")
    await update.message.reply_text(f'Hola {user_first_name}! Envíame una imagen de una ecuación y la resolveré para ti.')

# Función para manejar imágenes recibidas
async def handle_image(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.info("Received an image from the user.")
    # Obtener la imagen
    file = await context.bot.get_file(update.message.photo[-1].file_id)
    
    # Descargar la imagen
    image_path = 'temp_equation.jpg'
    await file.download_to_drive(image_path)
    logger.info(f"Image downloaded to {image_path}.")
    
    # Resolver la ecuación usando la función importada
    result = solve_math_equation(image_path)
    logger.info("Equation solved.")

    # Enviar el resultado
    await update.message.reply_text(result)
    
    # Eliminar la imagen temporal
    os.remove(image_path)
    logger.info(f"Temporary image {image_path} deleted.")

# Función principal para configurar el bot
def main():
    # Inicializar el bot de Telegram
    application = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()

    # Agregar manejadores
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.PHOTO, handle_image))

    # Ejecutar el bot hasta que se detenga manualmente
    logger.info("Bot is polling for updates.")
    application.run_polling()

if __name__ == "__main__":
    main()