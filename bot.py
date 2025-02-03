import logging
import os
import signal
import sys
import telebot

from constants import OrderStatus
from datetime import datetime
from decimal import Decimal
from dotenv import load_dotenv
from functools import wraps
from models import Database
from telebot import types
from utils import display_status, parse_status, sanitise_username, status_transition

def setup_logging(log_dir:str="logs") -> None:
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

    admins_str = os.getenv("ADMINS")
    admins = admins_str.split(',') if admins_str else []

    db = Database()
    db._reset_database()
    db.initialise()
    db._populate_test_data()

    bot = telebot.TeleBot(os.getenv("TOKEN"))


    # Bot message handlers
    @bot.message_handler(commands=["start"])
    def send_welcome(message:types.Message) -> None:
        bot.reply_to(message, "Hi, I'm the Yale-NUS Buttery Bot!")

    @bot.message_handler(commands=["help"])
    def help(message:types.Message) -> None:
        # TODO: write a helpful message
        commands = [
            ("/menu", ""),
            ("/order", ""),
        ]
        pass

    @bot.message_handler(commands=["menu"])
    def show_menu(message:types.Message) -> None:
        menu = db.get_menu()
        formatted_message = "📋 *Menu Items*\n"
        for item in menu:
            formatted_message += f"• {item.name}  (${item.price:.2f})\n"
        bot.send_message(message.chat.id, formatted_message, parse_mode="Markdown")

    @bot.message_handler(commands=["order"])
    def make_order(message:types.Message) -> None:
        # TODO: allow only one order per username
        menu = db.get_menu()
        formatted_message = "📋 *Menu Items*\nPlease select an item from the menu:"
        
        keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
        for item in menu:
            button = types.KeyboardButton(f"{item.name} - ${item.price:.2f}")
            keyboard.add(button)

        msg = bot.send_message(
            message.chat.id,
            formatted_message,
            reply_markup=keyboard,
            parse_mode="Markdown"
        )
        bot.register_next_step_handler(msg, handle_item_selection)

    def handle_item_selection(message:types.Message) -> None:
        item_name, _ = message.text.split(" - ")
        item = db.get_menu_item_by_name(item_name)
        if not item:
            pass # TODO: throw error

        keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
        keyboard.add(types.KeyboardButton("1"), types.KeyboardButton("2"))

        msg = bot.send_message(
            message.chat.id,
            f"How many {item.name}(s) would you like to order? (Price per item: ${item.price:.2f})",
            reply_markup=keyboard
        )
        bot.register_next_step_handler(msg, handle_quantity_input, item.id)

    def handle_quantity_input(message:types.Message, item_id:int) -> None:
        quantity = int(message.text)
        # TODO: do proper error checking
        # TODO: check that they have not made an order for that item already 

        keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
        keyboard.add(types.KeyboardButton("Yes"), types.KeyboardButton("No"))

        db.insert_single_order(message.chat.username, item_id, quantity)
        msg = bot.send_message(
            message.chat.id,
            "Would you like to add another item to your order? (Yes/No)",
            reply_markup=keyboard
        )
        bot.register_next_step_handler(msg, handle_add_another_item)

    def handle_add_another_item(message:types.Message) -> None:
        if message.text == "Yes":
            make_order(message)
        elif message.text == "No":
            finalise_order(message.chat.id, message.chat.username)

    def finalise_order(chat_id:int, username:str) -> None:
        pending_order_ids = db.get_pending_orders_for_username(username)
        # TODO: handle if multiple pending orders
        pending_order_id = pending_order_ids[0]

        order_items = db.get_order_items_for_order_id(pending_order_id)
        order_summary = "Your Order:\n"
        total_price = Decimal(0)

        for order_item in order_items:
            item = db.get_menu_item_by_id(order_item.menu_id)
            if not item:
                pass # TODO: throw error

            item_price = Decimal(item.price) * Decimal(order_item.quantity)
            total_price += item_price
            order_summary += f"{item.name} x {order_item.quantity} = ${item_price:.2f}\n"
        order_summary += f"\nTotal: ${total_price:.2f}"        
        # TODO: add payment details QR code here and thank you for your order

        db.update_order_status(pending_order_id, OrderStatus.AwaitingPayment)
        bot.send_message(chat_id, order_summary, parse_mode="Markdown")

    @bot.message_handler(commands=["status"])
    def check_status(message:types.Message) -> None:
        # TODO: show order details too?
        status = db.get_status_by_customer_name(message.chat.username)
        if not status:
            message_text = "You do not have an active order."
        else:
            status = display_status(status)
            message_text = f"The status of your order is {status}."
        bot.send_message(message.chat.id, message_text)

    # Admin only message handlers
    def admin_only(f):
        @wraps(f)
        def wrapper(message:types.Message, *args, **kwargs):
            if message.chat.username not in admins:
                bot.send_message(message.chat.id, "You are not authorised to run this command.")
            else:
                return f(message, *args, **kwargs)
        return wrapper

    @bot.message_handler(commands=["listorders"])
    @admin_only
    def show_order_details(message:types.Message) -> None:
        order_details = db.get_order_details()
        formatted_message = "📃 *All Orders*\n"
        for order_detail in order_details:
            # TODO: make username easy to click with @ to message them?
            username = sanitise_username(order_detail.customer_name)
            status = display_status(order_detail.status)
            formatted_message += f"{order_detail.order_id}: {username} - {status}\n"
            formatted_message += f"    {order_detail.order_contents}\n"
        bot.send_message(message.chat.id, formatted_message, parse_mode="Markdown")

    @bot.message_handler(commands=["manageorders"])
    @admin_only
    def manage_orders(message:types.Message) -> None:
        # TODO: add additional views/options
        # TODO: change this to an enum
        options = [
            "View Processing Orders",
            "Update AwaitingPayment Orders",
            "Update Processing Orders",
            "Update OrderReady Orders",
            "Update Any Order Status"
        ]

        keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
        for option in options:
            button = types.KeyboardButton(option)
            keyboard.add(button)

        msg = bot.send_message(message.chat.id, "What would you like to do?", reply_markup=keyboard)
        bot.register_next_step_handler(msg, handle_manage_order)

    def update_order_status(status:OrderStatus, chat_id:int) -> None:
        orders = db.get_order_details_by_status(status)
        if not orders:
            bot.send_message(chat_id, f"There are no {display_status(status)} orders.")
            return 

        formatted_message = f"*{display_status(status)}*\n"
        order_ids = []
        for order in orders:
            # TODO: make username easy to click with @ to message them?
            username = sanitise_username(order.customer_name)
            formatted_message += f"{order.order_id}: {username} - {order.order_contents}\n"
            order_ids.append(order.order_id)
        bot.send_message(chat_id, formatted_message, parse_mode="Markdown")

        keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
        keyboard.add(types.KeyboardButton("Yes"), types.KeyboardButton("No"))
        msg = bot.send_message(
            chat_id,
            "Would you like to update the status for any of these orders?",
            reply_markup=keyboard    
        )
        bot.register_next_step_handler(msg, handle_update_status, order_ids, True)

    def handle_manage_order(message:types.Message) -> None:
        # TODO: update when changed to enum
        option = message.text
        match option:
            case "View Processing Orders":
                processing_orders = db.get_order_details_by_status(OrderStatus.Processing)       
                if not processing_orders:
                    bot.send_message(message.chat.id, "There are no orders to be processed.")
                    return  
        
                formatted_message = "🔄 *Orders Processing*\n"
                for order in processing_orders:
                    # TODO: make username easy to click with @ to message them?
                    username = sanitise_username(order.customer_name)
                    formatted_message += f"• {username} - {order.order_contents}\n"
                bot.send_message(message.chat.id, formatted_message, parse_mode="Markdown")
            
            case "Update AwaitingPayment Orders":
                update_order_status(OrderStatus.AwaitingPayment, message.chat.id)

            case "Update Processing Orders":
                update_order_status(OrderStatus.Processing, message.chat.id)

            case "Update OrderReady Orders":
                update_order_status(OrderStatus.OrderReady, message.chat.id)

            case "Update Any Order Status":
                order_ids = db.get_order_ids()

                keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
                keyboard.add(types.KeyboardButton("Yes"), types.KeyboardButton("No"))
                msg = bot.send_message(
                    message.chat.id,
                    "Would you like to update the status for an order?",
                    reply_markup=keyboard    
                )
                bot.register_next_step_handler(msg, handle_update_status, order_ids, False)

            case _:
                bot.send_message(message.chat.id, "Nothing to do.")
     
    def handle_update_status(message:types.Message, order_ids:list[int], restricted:bool) -> None:
        if not order_ids:
            bot.send_message(message.chat.id, "There are no orders of the current status to update.")
            return

        keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
        for id in order_ids:
            button = types.KeyboardButton(str(id))
            keyboard.add(button)

        if message.text == "Yes":
            msg = bot.send_message(
                message.chat.id,
                "Please select the ID of the order you want to update.",
                reply_markup=keyboard
            )
            bot.register_next_step_handler(msg, handle_order_selection, restricted)
        elif message.text == "No":
            pass

    def handle_order_selection(message:types.Message, restricted:bool) -> None:
        try:
            order_id = int(message.text)
        except ValueError:
            bot.send_message(message.chat.id, "Please enter a valid order ID number.")
            return 
        
        if not db.check_order_id_exists(order_id):
            bot.send_message(message.chat.id, f"Order ID {order_id} does not exist in the database.")
            return

        init_status = db.get_status_by_id(order_id)
        if restricted:
            allowed_statuses = status_transition(init_status)
        else:
            allowed_statuses = OrderStatus

        keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
        for status in allowed_statuses:
            button = types.KeyboardButton(display_status(status))
            keyboard.add(button)

        msg = bot.send_message(
            message.chat.id,
            "Which order would you like to update?",
            reply_markup=keyboard
        )
        bot.register_next_step_handler(msg, handle_status_selection, init_status, order_id, restricted)

    def handle_status_selection(message:types.Message, init_status:OrderStatus, order_id:int, restricted:bool) -> None:
        status = parse_status(message.text)
        db.update_order_status(order_id, status)

        bot.send_message(message.chat.id, f"Order ID {order_id} updated to {display_status(status)}")

        order_ids = db.get_order_ids_by_status(init_status)

        keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
        keyboard.add(types.KeyboardButton("Yes"), types.KeyboardButton("No"))
        msg = bot.send_message(
            message.chat.id,
            "Would you like to update the status for another order?",
            reply_markup=keyboard    
        )
        bot.register_next_step_handler(msg, handle_update_status, order_ids, restricted)

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
