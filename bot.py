import argparse
import logging
import os
import signal
import sys
import telebot

from constants import QR_CODE_FILE, AVAIL_CMDS, MENU_DETAILS, OrderStatus, UpdateStatusOption
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
    parser = argparse.ArgumentParser()
    parser.add_argument("-t", "--test", help="Run in test mode", action="store_true")
    args = parser.parse_args()

    setup_logging()
    load_dotenv()

    if args.test:
        logging.info("Running bot in test mode.")
          
    admins_str = os.getenv("ADMINS")
    admins = admins_str.split(',') if admins_str else []

    admin_chat_ids_str = os.getenv("ADMIN_CHAT_IDS")
    admin_chat_ids = admin_chat_ids_str.split(',') if admin_chat_ids_str else []

    db = Database(test_mode=args.test)
    bot = telebot.TeleBot(os.getenv("TOKEN"))


    # Bot message handlers
    @bot.message_handler(commands=["start"])
    def send_welcome(message:types.Message) -> None:
        start_message = (
            "Hi, I'm the Yale-NUS Buttery Bot! 🤖\n"
            "Use /help to see what commands you can use!\n\n"
            "Please use the custom keyboards whenever they pop up.\n"
            "Lastly, I'm new so let the buttery team know if there any issues."
        )
        bot.send_message(message.chat.id, start_message)
        # bot.reply_to(message, f"Your chat_id is {message.chat.id}")

    @bot.message_handler(commands=["help"])
    def help(message: types.Message) -> None:
        formatted_message = "⚙️ *Available Commands*\n"
        for command in AVAIL_CMDS:
            if message.chat.username in admins or not command.admin_only:
                formatted_message += f"{command.command} - {command.description}\n"
        bot.send_message(message.chat.id, formatted_message)

    @bot.message_handler(commands=["menu"])
    def show_menu(message:types.Message) -> None:
        menu = db.get_menu()
        formatted_message = "📋 *Menu Items*\n"
        for item in menu:
            formatted_message += f"• {item.name}  (${item.price:.2f})\n"
        bot.send_message(message.chat.id, formatted_message, parse_mode="Markdown")

        if MENU_DETAILS:
            bot.send_message(message.chat.id, MENU_DETAILS, parse_mode="Markdown")

    @bot.message_handler(commands=["order"])
    def make_order(message:types.Message) -> None:
        username = message.chat.username
        has_order = db.check_order_for_user_exists(username)
        if has_order:
            bot.send_message(message.chat.id, "Sorry, you already have an order. Please contact buttery staff for assistance.")
            return

        formatted_message = "📋 *Menu Items*\nPlease select an item from the menu:"
        
        unselected_items = db.get_unselected_menu_item_names_by_username(username)
        final = len(unselected_items) == 1
        keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
        for item in unselected_items:
            button = types.KeyboardButton(f"{item.name} - ${item.price:.2f}")
            keyboard.add(button)

        msg = bot.send_message(
            message.chat.id,
            formatted_message,
            reply_markup=keyboard,
            parse_mode="Markdown"
        )
        bot.register_next_step_handler(msg, handle_item_selection, final)

    def handle_item_selection(message:types.Message, final:bool) -> None:
        split_message = message.text.split(" - ")
        if len(split_message) != 2:
            logging.warning(f"Should be unreachable: handle_item_selection with incorrect message text.")
            bot.send_message(message.chat.id, "Please use the custom keyboard to select the item.")
            return make_order(message)

        item_name = split_message[0]
        item = db.get_menu_item_by_name(item_name)
        if not item:
            logging.warning("Should be unreachable: handle_item_selection with no item.")
            bot.send_message(message.chat.id, "Please try again with an existing menu item.")
            return

        keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
        keyboard.add(types.KeyboardButton("1"), types.KeyboardButton("2"))

        msg = bot.send_message(
            message.chat.id,
            f"How many {item.name}(s) would you like to order? (Price per item: ${item.price:.2f})",
            reply_markup=keyboard
        )
        bot.register_next_step_handler(msg, handle_quantity_input, item.id, final)

    def handle_quantity_input(message:types.Message, item_id:int, final:bool) -> None:
        quantity = int(message.text)

        keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
        keyboard.add(types.KeyboardButton("Yes"), types.KeyboardButton("No"))

        chat_id = message.chat.id
        username = message.chat.username
        success = db.insert_single_order(username, chat_id, item_id, quantity)
        if not success:
            bot.send_message(
                chat_id,
                "Sorry, we have run out of the item you selected. Please select a smaller quantity or choose another item."
            )
            make_order(message)
            return

        if final:
            finalise_order(chat_id, username)
            return

        msg = bot.send_message(
            chat_id,
            "Would you like to add another item to your order? (Yes/No)",
            reply_markup=keyboard
        )
        bot.register_next_step_handler(msg, handle_add_another_item)

    def handle_add_another_item(message:types.Message) -> None:
        if message.text == "Yes":
            make_order(message)
        elif message.text == "No":
            finalise_order(message.chat.id, message.chat.username)
        else:
            logging.warning("Should be unreachable: handle_add_another_item with neither Yes or No.")
            finalise_order(message.chat.id, message.chat.username)

    def finalise_order(chat_id:int, username:str) -> None:
        pending_order_ids = db.get_pending_orders_for_username(username)
        if len(pending_order_ids) != 1:
            logging.warning("Should be unreachable: finalise_order with multiple pending orders.")
            return
        pending_order_id = pending_order_ids[0]

        order_items = db.get_order_items_for_order_id(pending_order_id)
        order_summary = "Your Order:\n"
        total_price = Decimal(0)

        for order_item in order_items:
            item = db.get_menu_item_by_id(order_item.menu_id)
            if not item:
                logging.warning("Should be unreachable: finalise_order with no item.")
                bot.send_message(chat_id, "Please try again with an existing menu item.")
                return

            item_price = Decimal(item.price) * Decimal(order_item.quantity)
            total_price += item_price
            order_summary += f"{item.name} x {order_item.quantity} = ${item_price:.2f}\n"
        order_summary += f"\nTotal: ${total_price:.2f}"        

        bot.send_message(chat_id, order_summary, parse_mode="Markdown")
        bot.send_message(
            chat_id,
            "Please pay the correct amount to the QR code below and send the screenshot in this chat. Thank you for your order!"
        )
        with open(QR_CODE_FILE, "rb") as photo:
            msg = bot.send_photo(chat_id, photo)
        
        db.update_order_status(pending_order_id, OrderStatus.AwaitingPayment)
        bot.register_next_step_handler(msg, send_notification_after_payment, order_item.order_id)

    def send_notification_after_payment(message:types.Message, order_id:int) -> None:
        if message.photo:
            file_id = message.photo[-1].file_id
        elif message.document:
            file_id = message.document.file_id
        else:
            msg = bot.send_message(message.chat.id, "Please send the screenshot image.")
            bot.register_next_step_handler(msg, send_notification_after_payment, order_id)
            return
        
        file_path = bot.get_file(file_id).file_path
        photo_file = bot.download_file(file_path)

        username = message.chat.username
        for chat_id in admin_chat_ids:
            bot.send_photo(chat_id, photo_file, caption=f"Payment from {username} for order {order_id}")

        bot.send_message(message.chat.id, "Your screenshot has been forwarded to the admin.")

    @bot.message_handler(commands=["status"])
    def check_status(message:types.Message) -> None:
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
        if not order_details:
            bot.send_message(message.chat.id, "There are no orders.")
            return
        
        formatted_message = "📃 *All Orders*\n"
        for order_detail in order_details:
            username = sanitise_username(order_detail.customer_name)
            status = display_status(order_detail.status)
            formatted_message += f"{order_detail.order_id}: @{username} - {status}\n"
            formatted_message += f"    {order_detail.order_contents}\n"
        bot.send_message(message.chat.id, formatted_message, parse_mode="Markdown")

    @bot.message_handler(commands=["toprocess"])
    @admin_only
    def show_processing_order_details(message:types.Message) -> None:
        processing_orders = db.get_order_details_by_status(OrderStatus.Processing)       
        if not processing_orders:
            bot.send_message(message.chat.id, "There are no orders to be processed.")
            return  

        formatted_message = "🔄 *Orders to Process*\n"
        for order in processing_orders:
            username = sanitise_username(order.customer_name)
            formatted_message += f"• @{username} - {order.order_contents}\n"
        bot.send_message(message.chat.id, formatted_message, parse_mode="Markdown")

    @bot.message_handler(commands=["updatestatus"])
    @admin_only
    def manage_orders(message:types.Message) -> None:
        keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
        for option in UpdateStatusOption:
            button = types.KeyboardButton(option.value)
            keyboard.add(button)

        msg = bot.send_message(message.chat.id, "What would you like to do?", reply_markup=keyboard)
        bot.register_next_step_handler(msg, handle_manage_order)

    def handle_manage_order(message:types.Message) -> None:
        option = message.text
        match option:
            case UpdateStatusOption.AwaitingPayment.value:
                handle_restricted_update_status(OrderStatus.AwaitingPayment, message.chat.id)

            case UpdateStatusOption.Processing.value:
                handle_restricted_update_status(OrderStatus.Processing, message.chat.id)

            case UpdateStatusOption.OrderReady.value:
                handle_restricted_update_status(OrderStatus.OrderReady, message.chat.id)

            case UpdateStatusOption.Any.value:
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

    def handle_restricted_update_status(status:OrderStatus, chat_id:int) -> None:
        orders = db.get_order_details_by_status(status)
        if not orders:
            bot.send_message(chat_id, f"There are no {display_status(status)} orders.")
            return 

        formatted_message = f"*{display_status(status)}*\n"
        order_ids = []
        for order in orders:
            username = sanitise_username(order.customer_name)
            formatted_message += f"{order.order_id}: @{username} - {order.order_contents}\n"
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
            return

    def handle_order_selection(message:types.Message, restricted:bool) -> None:
        try:
            order_id = int(message.text)
        except ValueError:
            bot.send_message(message.chat.id, "Please enter a valid order ID number.")
            return 
        
        if not db.check_order_for_id_exists(order_id):
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
            "Please select the status you want to update the order to.",
            reply_markup=keyboard
        )
        bot.register_next_step_handler(msg, handle_status_selection, init_status, order_id, restricted)

    def handle_status_selection(message:types.Message, init_status:OrderStatus, order_id:int, restricted:bool) -> None:
        status = parse_status(message.text)
        db.update_order_status(order_id, status)

        # TODO: check if order is moved to processing, then send message to cooks @rachel
        if status == OrderStatus.OrderReady:
            user_chat_id = db.get_chat_id_by_id(order_id)
            bot.send_message(user_chat_id, "Your order is ready to collect!")

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

    @bot.message_handler(commands=["updatequantity"])
    @admin_only
    def update_menu_quantity(message:types.Message) -> None:
        keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
        menu = db.get_menu()

        for item in menu:
            button = types.KeyboardButton(f"{item.name} - {item.quantity} nos")
            keyboard.add(button)

        msg = bot.send_message(
            message.chat.id,
            "Please select the menu item you want to update the quantity of.",
            reply_markup=keyboard
        )
        bot.register_next_step_handler(msg, handle_update_item_selection)

    def handle_update_item_selection(message:types.Message) -> None:
        item_name, _ = message.text.split(" - ")
        item = db.get_menu_item_by_name(item_name)
        if not item:
            logging.warning("Should be unreachable: handle_update_item_selection with no item.")
            bot.send_message(message.chat.id, "Please try again with an existing menu item.")
            return

        msg = bot.send_message(
            message.chat.id,
            f"Please enter the new quantity for {item.name}. (Integers only)"
        )
        bot.register_next_step_handler(msg, handle_update_quantity, item.id)

    def handle_update_quantity(message: types.Message, item_id: int) -> None:
        # TODO: reduce quantity instead of replace? @rachel
        try:
            quantity = int(message.text)
            if quantity <= 0:
                raise ValueError("Quantity must be a positive integer.")
        except ValueError:
            msg = bot.send_message(message.chat.id, "Please enter a valid positive integer quantity.")
            bot.register_next_step_handler(msg, handle_update_quantity, item_id)
            return

        db.update_menu_item_quantity(item_id, quantity)
        bot.send_message(message.chat.id, f"Menu item {item_id} updated to {quantity} nos.")

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
