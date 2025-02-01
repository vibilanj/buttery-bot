import logging
import os
import signal
import sys
import telebot

from dotenv import load_dotenv
from models import Database

load_dotenv()


db = Database()
db._reset_database()
db.initialise()
db._populate_test_data()

print(db.get_menu())


bot = telebot.TeleBot(os.getenv("TOKEN"))

# Bot message handlers
@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
	bot.reply_to(message, "Hi, how are you doing?")

@bot.message_handler(func=lambda m: True)
def echo_all(message):
	bot.reply_to(message, message.text)


# Setup signal handling for graceful shutdown
def graceful_shutdown(signal, frame):
    logging.info("Gracefully shutting down the bot...")
    db.shutdown()
    bot.stop_polling()
    sys.exit(0)

signal.signal(signal.SIGINT, graceful_shutdown)  # Handle Ctrl+C
signal.signal(signal.SIGTERM, graceful_shutdown)  # Handle termination signal (e.g., for systemd)

# TODO: convert to asynchronous polling, check database feasibility
bot.infinity_polling()
