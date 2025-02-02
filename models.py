import logging
import sqlite3

from constants import Order, OrderItem, OrderStatus, MenuItem
from typing import Optional

logger = logging.getLogger(__name__)

DB_FILE = "buttery.db"

def add_log(msg: str):
    def decorator(func):
        def wrapper(*args, **kwargs):
            logging.info(msg)
            return func(*args, **kwargs)
        return wrapper
    return decorator

class Database:
    def __init__(self, db_file:str=DB_FILE) -> None:
        self.db_file = db_file
        self.conn = sqlite3.connect(db_file, check_same_thread=False if sqlite3.threadsafety == 3 else True)
        self.cursor = self.conn.cursor()
        logging.info(f"Connected to database: {db_file}")
        # TODO: enable wal mode?
        # self._enable_wal_mode()

    # def _enable_wal_mode(self) -> None:
    #     try:
    #         self.cursor.execute("PRAGMA journal_mode=WAL;")
    #         self.conn.commit()
    #         logging.info(f"Enabled WAL mode on database: {self.db_file}")
    #     except sqlite3.Error as e:
    #         logging.error(f"Error enabling WAL mode: {e}")

    def __del__(self) -> None:
        """Close the database connection when the object is deleted."""
        if self.conn:
            self.conn.close()
            logging.info(f"Closed connection to database: {self.db_file}")

    def shutdown(self) -> None:
        """Gracefully shut down the database by committing changes and closing the connection."""
        if self.conn:
            self.conn.commit()
            self.conn.close()
            logging.info(f"Database connection to {self.db_file} has been shut down.")

    def initialise(self) -> None:
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

    # Create
    def insert_menu_item(self, name:str, quantity:int, price:float) -> None:
        """Insert a new item into the menu."""
        query = "INSERT INTO menu (name, quantity, price) VALUES (?, ?, ?)"
        self.cursor.execute(query, (name, quantity, price))

    def insert_single_order(self, username:str, item_id:int, quantity:int) -> None:
        """Insert a new single order."""
        self.cursor.execute("SELECT id FROM orders WHERE customer_name = ? AND status = ?", (username, OrderStatus.Pending.name,))
        existing_order = self.cursor.fetchone()

        if not existing_order:
            self.cursor.execute("INSERT INTO orders (customer_name, status) VALUES (?, ?)", (username, OrderStatus.Pending.name))
            order_id = self.cursor.lastrowid
            self.cursor.execute("INSERT INTO order_items (order_id, menu_id, quantity) VALUES (?, ?, ?)",
                                (order_id, item_id, quantity))
        else:
            order_id = existing_order[0]
            self.cursor.execute("SELECT * from order_items WHERE order_id = ? AND menu_id = ?", (order_id, item_id))
            existing_order_item = self.cursor.fetchone()

            if not existing_order_item:
                self.cursor.execute("INSERT INTO order_items (order_id, menu_id, quantity) VALUES (?, ?, ?)",
                                    (order_id, item_id, quantity))
            else:
                existing_quantity = existing_order_item[2]
                updated_quantity = existing_quantity + quantity
                self.cursor.execute("UPDATE order_items SET quantity = ? WHERE order_id = ? and menu_id = ?",
                                    (updated_quantity, order_id, item_id))

        self.conn.commit()
        logging.info(f"Order for {username} of {quantity}x Item {item_id} added successfully.")

    # Read
    @add_log("Fetched menu.")
    def get_menu(self) -> list[MenuItem]:
        """Fetch all items from the menu."""
        self.cursor.execute("SELECT * FROM menu")
        rows = self.cursor.fetchall()
        return [MenuItem(*row) for row in rows]
    
    def get_menu_item(self, id:int) -> Optional[MenuItem]:
        """Fetch menu item by id."""
        self.cursor.execute("SELECT * FROM menu WHERE id = ?", (id,))
        row = self.cursor.fetchone()
        return MenuItem(*row) if row else None
    
    @add_log("Fetched orders")
    def get_orders(self) -> list[Order]:
        """Fetch all orders."""
        self.cursor.execute("SELECT * FROM orders")
        rows = self.cursor.fetchall()
        return [Order(*row) for row in rows]
    
    def get_pending_orders_for_username(self, username:str) -> list[int]:
        """Fetch all pending order ids for a username."""
        query = "SELECT id FROM orders WHERE customer_name = ? AND status = ?"
        self.cursor.execute(query, (username, OrderStatus.Pending.name))
        rows = self.cursor.fetchall()
        return [row[0] for row in rows]

    def get_order_items_for_order_id(self, order_id:int) -> list[OrderItem]:
        """Fetch all order items for a particular order."""
        query = "SELECT * from order_items WHERE order_id = ?"
        self.cursor.execute(query, (order_id,))
        rows = self.cursor.fetchall()
        return [OrderItem(*row) for row in rows]

    # Update
    def update_order_status(self, order_id:int, status:OrderStatus) -> None:
        """Update order status."""
        query = "UPDATE orders SET status = ? WHERE id = ?"
        self.cursor.execute(query, (status.name, order_id))
        self.conn.commit()
        logging.info(f"Order {order_id} status updated to {status.name}.")

    # Testing 
    def _insert_bulk_order(self, customer_name:str, ordered_items: list[tuple[int, int]]) -> None:
        """Insert a new bulk order."""
        self.cursor.execute("INSERT INTO orders (customer_name, status) VALUES (?, ?)",
                            (customer_name, OrderStatus.AwaitingPayment.name))
        order_id = self.cursor.lastrowid

        for item_id, quantity in ordered_items:
            self.cursor.execute("INSERT INTO order_items (order_id, menu_id, quantity) VALUES (?, ?, ?)",
                                (order_id, item_id, quantity))
        
        self.conn.commit()
        logging.info(f"Order for {customer_name} with {len(ordered_items)} items added successfully.")


    def _populate_test_data(self) -> None:
        """Populate the database with some test data for testing purposes."""
        # Insert some items into the menu
        self.insert_menu_item("Pizza", 50, 9.99)
        self.insert_menu_item("Burger", 30, 5.99)
        self.insert_menu_item("Fries", 100, 2.49)

        # Insert some orders
        self._insert_bulk_order("Alice", [(1, 1), (3, 2)])
        self._insert_bulk_order("Bob", [(2, 2), (3, 3)])

        logging.info("Test data populated.")

    def _reset_database(self) -> None:
        """Drop all tables and reset the database."""
        # Drop the tables to reset the database
        self.cursor.execute("DROP TABLE IF EXISTS menu;")
        self.cursor.execute("DROP TABLE IF EXISTS orders;")
        self.cursor.execute("DROP TABLE IF EXISTS order_items;")

        self.conn.commit()
        logging.info("Database reset: All tables have been dropped and reset.")
