import logging
import os
import signal
import sys
import telebot

from constants import OrderStatus
from datetime import datetime
from decimal import Decimal
from dotenv import load_dotenv
from models import Database
from telebot import types

def setup_logging(log_dir="logs"):
    """Set up logging to capture logs in a file and to the console."""

    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    log_filename = f"{log_dir}/buttery_{timestamp}.log"

    log_format = "%(asctime)s [%(levelname)s] @ %(threadName)s - %(message)s"
    
    logging.basicConfig(
        level = logging.INFO,
        format = log_format,
        handlers = [
            logging.FileHandler(log_filename),
            logging.StreamHandler()
        ]
    )
    logging.info("Logging is set up.")


if __name__ == "__main__":
    setup_logging()
    load_dotenv()

    db = Database()
    db._reset_database()
    db.initialise()
    db._populate_test_data()

    bot = telebot.TeleBot(os.getenv("TOKEN"))

    # Bot message handlers

    @bot.message_handler(commands=["start"])
    def send_welcome(message):
        bot.reply_to(message, "Hi, I'm the Yale-NUS Buttery Bot!")

    @bot.message_handler(commands=["help"])
    def help(message):
        # TODO: write a helpful message
        commands = [
            ("/menu", ""),
            ("/order", ""),
        ]
        pass

    @bot.message_handler(commands=["menu"])
    def show_menu(message):
        menu = db.get_menu()
        formatted_message = "📋 *Menu Items*\n"
        for item in menu:
            _, name, _, price = item
            formatted_message += f"• {name}  (${price:.2f})\n"
        bot.send_message(message.chat.id, formatted_message, parse_mode="Markdown")

    @bot.message_handler(commands=["order"])
    def make_order(message):
        menu = db.get_menu()
        formatted_message = "📋 *Menu Items*\n"
        
        keyboard = types.InlineKeyboardMarkup()
        for item in menu:
            id, name, _, price = item
            button = types.InlineKeyboardButton(
                text=f"{name} - ${price:.2f}",
                callback_data=f"item_{id}"
            )
            keyboard.add(button)

        bot.send_message(message.chat.id, formatted_message, reply_markup=keyboard, parse_mode="Markdown")

    # Bot query handlers

    @bot.callback_query_handler(func=lambda call: call.data.startswith("item_"))
    def handle_item_selection(call):
        data = call.data.split('_')
        item_id = data[1]
        _, item_name, _, item_price = db.get_menu_item(item_id)

        msg = bot.send_message(
            call.message.chat.id,
            f"How many {item_name}s would you like to order? (Price per item: ${item_price:.2f})"
        )
        username = call.message.chat.username
        bot.register_next_step_handler(msg, handle_quantity_input, item_id, username)


    # Bot Callback Handlers
    def handle_quantity_input(message, item_id, username):
        chat_id = message.chat.id
        try:
            quantity = int(message.text)
            if quantity <= 0:
                raise ValueError("Quantity must be greater than 0.")
            # TODO: handle when exceeding max quantity

            db.insert_single_order(username, item_id, quantity)

            msg = bot.send_message(
                chat_id,
                "Would you like to add another item to your order? (yes/no)"
            )
            bot.register_next_step_handler(msg, handle_add_another_item)
        except ValueError:
            bot.send_message(
                chat_id,
                "Invalid quantity. Please enter a valid number greater than 0."
            )
            _, item_name, _, item_price = db.get_menu_item(item_id)
            msg = bot.send_message(
                chat_id,
                f"How many {item_name}s would you like to order? (Price per item: ${item_price:.2f})"
            )
            bot.register_next_step_handler(msg, handle_quantity_input, item_id, username)

    def handle_add_another_item(message):
        if message.text.lower() == "yes":
            make_order(message)
        elif message.text.lower() == "no":
            finalise_order(message.chat.id, message.chat.username)
        else:
            bot.send_message(message.chat.id, "Please answer with yes/no.")
            msg = bot.send_message(message.chat.id, "Would you like to add another item to your order? (yes/no)")
            bot.register_next_step_handler(msg, handle_add_another_item)


    def finalise_order(chat_id, username):
        pending_order_ids = db.get_pending_orders_for_username(username)
        # TODO: handle if multiple pending orders
        pending_order_id = pending_order_ids[0][0]

        # Get full order information
        order_items = db.get_order_items_for_order_id(pending_order_id)
        order_summary = "Your Order:\n"
        total_price = Decimal(0)

        for _, menu_id, quantity in order_items:
            _, name, _, price = db.get_menu_item(menu_id)
            item_price = Decimal(price) * Decimal(quantity)
            total_price += item_price
            order_summary += f"{name} x {quantity} = ${item_price:.2f}\n"
        order_summary += f"\nTotal: ${total_price:.2f}"        
        # TODO: add payment details QR code here and thank you for your order

        db.update_order_status(pending_order_id, OrderStatus.AwaitingPayment)
        bot.send_message(chat_id, order_summary, parse_mode="Markdown")


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
