import logging
import sqlite3

from decimal import Decimal
from enum import Enum


logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(message)s")

DB_FILE = "buttery.db"

class OrderStatus(Enum):
    AwaitingPayment = 1
    Processing = 2
    Completed = 3
    Cancelled = 4


class Database:
    def __init__(self, db_file=DB_FILE):
        self.db_file = db_file
        self.conn = sqlite3.connect(db_file)
        self.cursor = self.conn.cursor()
        logging.info(f"Connected to database: {db_file}")

    def __del__(self):
        """Close the database connection when the object is deleted."""
        if self.conn:
            self.conn.close()
            logging.info(f"Closed connection to database: {self.db_file}")

    def shutdown(self):
        """Gracefully shut down the database by committing changes and closing the connection."""
        if self.conn:
            self.conn.commit()
            self.conn.close()
            logging.info(f"Database connection to {self.db_file} has been shut down.")

    def initialise(self):
        """Create necessary tables if they don't already exist."""

        CREATE_MENU_TABLE = """
            CREATE TABLE IF NOT EXISTS menu (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                quantity INTEGER NOT NULL,
                price DECIMAL NOT NULL
            );
            """
        CREATE_ORDERS_TABLE = """
            CREATE TABLE IF NOT EXISTS orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                customer_name TEXT NOT NULL,
                total_price DECIMAL NOT NULL,
                status TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            """
        CREATE_ORDER_ITEMS_TABLE = """
            CREATE TABLE IF NOT EXISTS order_items (
                order_id INTEGER,
                menu_id INTEGER,
                quantity INTEGER NOT NULL,
                FOREIGN KEY (order_id) REFERENCES orders (id) ON DELETE CASCADE,
                FOREIGN KEY (menu_id) REFERENCES menu (id) ON DELETE CASCADE,
                PRIMARY KEY (order_id, menu_id)
            );
            """

        self.cursor.execute(CREATE_MENU_TABLE)
        self.cursor.execute(CREATE_ORDERS_TABLE)
        self.cursor.execute(CREATE_ORDER_ITEMS_TABLE)
        self.conn.commit()
        logging.info("Initialised database and created tables.")

    def insert_menu_item(self, name, quantity, price):
        """Insert a new item into the menu."""
        query = "INSERT INTO menu (name, quantity, price) VALUES (?, ?, ?)"
        self.cursor.execute(query, (name, quantity, price))

    def insert_order(self, customer_name, ordered_items):
        """Insert a new order."""

        # First, calculate the total price for the order
        total_price = Decimal(0)
        for item_name, quantity in ordered_items:
            self.cursor.execute("SELECT price FROM menu WHERE name = ?", (item_name,))
            result = self.cursor.fetchone()
            if result:
                price = Decimal(result[0])
                total_price += price * Decimal(quantity)
            else:
                # TODO: log error here
                raise ValueError(f"Item '{item_name}' not found in menu.")

        # Insert the order into the orders table
        self.cursor.execute("INSERT INTO orders (customer_name, total_price, status) VALUES (?, ?, ?)",
                            (customer_name, str(total_price), OrderStatus.AwaitingPayment.name))
        order_id = self.cursor.lastrowid

        # Insert each item into the order_items table
        for item_name, quantity in ordered_items:
            self.cursor.execute("SELECT id FROM menu WHERE name = ?", (item_name,))
            result = self.cursor.fetchone()
            if result:
                menu_id = result[0]
                # Insert the order item into the order_items table
                self.cursor.execute("INSERT INTO order_items (order_id, menu_id, quantity) VALUES (?, ?, ?)",
                                    (order_id, menu_id, quantity))
            else:
                # TODO: log error here
                raise ValueError(f"Item '{item_name}' not found in menu.")
        
        self.conn.commit()
        logging.info(f"Order for {customer_name} with {len(ordered_items)} items added successfully.")

    def get_menu(self):
        """Fetch all items from the menu."""
        query = "SELECT * FROM menu"
        self.cursor.execute(query)
        return self.cursor.fetchall()
    
    def get_orders(self):
        """Fetch all orders."""
        query = "SELECT * FROM orders"
        self.cursor.execute(query)
        return self.cursor.fetchall()

    def _populate_test_data(self):
        """Populate the database with some test data for testing purposes."""
        # Insert some items into the menu
        self.insert_menu_item("Pizza", 50, 9.99)
        self.insert_menu_item("Burger", 30, 5.99)
        self.insert_menu_item("Fries", 100, 2.49)

        # Insert some orders
        self.insert_order("Alice", [("Pizza", 1), ("Fries", 2)])
        self.insert_order("Bob", [("Burger", 2), ("Fries", 3)])

        logging.info("Test data populated.")

    def _reset_database(self):
        """Drop all tables and reset the database."""
        # Drop the tables to reset the database
        self.cursor.execute("DROP TABLE IF EXISTS menu;")
        self.cursor.execute("DROP TABLE IF EXISTS orders;")
        self.cursor.execute("DROP TABLE IF EXISTS order_items;")

        self.conn.commit()
        logging.info("Database reset: All tables have been dropped and reset.")
