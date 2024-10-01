from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
import os
import logging
from dotenv import load_dotenv
from math_assistant import MathAssistant
from database import DatabaseManager
from openai import OpenAI

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
os.environ["OPENAI_API_KEY"] = OPENAI_API_KEY
openai_client = OpenAI() 
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_API_KEY")
SQLITECLOUD_API_KEY = os.getenv("SQLITECLOUD_API_KEY")
DB_NAME = os.getenv("DB_NAME", "matematicas-top")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    db_manager = context.bot_data['db_manager']
    user = update.effective_user

    if context.args:
        referrer_id = context.args[0]
        db_manager.add_credits(referrer_id, 10)
        await update.message.reply_text(f"Te has registrado con el código de referencia de {referrer_id}. ¡Ellos ganaron 10 créditos!")

    db_manager.create_user(user.id, user.username, user.first_name, user.last_name)
    logger.info(f"User {user.first_name} started the bot.")
    await update.message.reply_text(f'Hola {user.first_name}! Puedes enviarme mensajes o imágenes de ecuaciones. ¿En qué puedo ayudarte hoy?')

    # Initialize conversation history
    context.user_data['history'] = []

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    math_assistant = context.bot_data['math_assistant']
    user = update.effective_user
    message = update.message.text

    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action='typing')
    # Add user message to history
    context.user_data['history'].append({"role": "user", "content": message})

    # Get response from OpenAI
    response = math_assistant.chat(context.user_data['history'], user.id)

    # Add assistant's response to history
    context.user_data['history'].append({"role": "assistant", "content": response})

    # Trim history if it gets too long
    if len(context.user_data['history']) > 10:
        context.user_data['history'] = context.user_data['history'][-10:]

    await update.message.reply_text(response)

async def handle_image(update: Update, context: ContextTypes.DEFAULT_TYPE):
    math_assistant = context.bot_data['math_assistant']
    logger.info("Received an image from the user.")
    user = update.effective_user

    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action='typing')
    
    file = await context.bot.get_file(update.message.photo[-1].file_id)
    
    image_path = 'temp_equation.jpg'
    await file.download_to_drive(image_path)
    logger.info(f"Image downloaded to {image_path}.")
    
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action='typing')
    math_problem = math_assistant.parse_image(image_path, user.id)
    
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action='typing')
    solution = math_assistant.solve_math_problem(math_problem, user.id)
    
    logger.info("Equation solved.")
    
    await update.message.reply_text(solution)
    
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action='typing')
    
    yt_video_link = math_assistant.recommend_yt_video(math_problem, user.id)
    await update.message.reply_text(yt_video_link)
    
    os.remove(image_path)
    logger.info(f"Temporary image {image_path} deleted.")

    # Add this interaction to the conversation history
    context.user_data['history'].append({"role": "user", "content": "User sent an image of a math problem."})
    context.user_data['history'].append({"role": "assistant", "content": f"I solved the math problem: {solution}\n\nHere's a relevant video: {yt_video_link}"})

async def show_usage(update: Update, context: ContextTypes.DEFAULT_TYPE):
    db_manager = context.bot_data['db_manager']
    user = update.effective_user
    usage = db_manager.get_user_usage(user.id)
    if usage:
        total_tokens, total_cost = usage
        await update.message.reply_text(f"Tu uso total de OpenAI:\nTokens: {total_tokens}\nCosto estimado: ${total_cost:.4f}")
    else:
        await update.message.reply_text("Aún no has utilizado el servicio de OpenAI.")

async def referral(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    referral_link = f"https://t.me/{context.bot.username}?start={user.id}"
    await update.message.reply_text(f'Tu enlace de referencia: {referral_link}')

def main():
    db_manager = DatabaseManager(SQLITECLOUD_API_KEY, DB_NAME)
    db_manager.initialize_database()
    math_assistant = MathAssistant(db_manager, openai_client)

    application = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()
    
    application.bot_data['db_manager'] = db_manager
    application.bot_data['math_assistant'] = math_assistant

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("usage", show_usage))
    application.add_handler(CommandHandler("referral", referral))
    application.add_handler(MessageHandler(filters.PHOTO, handle_image))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    logger.info("Bot is polling for updates.")
    application.run_polling()

if __name__ == "__main__":
    main()