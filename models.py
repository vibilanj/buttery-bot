import logging
import sqlite3

from constants import DB_FILE, MENU_ITEMS, Order, OrderDetail, OrderItem, OrderStatus, MenuItem
from typing import Optional
from utils import cast_to_menu_item, cast_to_order, cast_to_order_item, cast_to_order_detail

logger = logging.getLogger(__name__)

def add_log(msg: str):
    def decorator(func):
        def wrapper(*args, **kwargs):
            logging.info(msg)
            return func(*args, **kwargs)
        return wrapper
    return decorator


class Database:
    def __init__(self, db_file:str = DB_FILE, test_mode:bool = False) -> None:
        self.db_file = db_file
        self.test_mode = test_mode

        self.conn = sqlite3.connect(db_file, check_same_thread=False if sqlite3.threadsafety == 3 else True)
        self.cursor = self.conn.cursor()
        logging.info(f"Connected to database: {db_file}")
        self._enable_wal_mode()

        if test_mode:
            self._reset_database()
            self.initialise()
            self._populate_test_data()
        else:
            self.initialise()
            self.init_menu_items() # TODO: do this once incase of restart
        

    def _enable_wal_mode(self) -> None:
        try:
            self.cursor.execute("PRAGMA journal_mode=WAL;")
            self.conn.commit()
            logging.info(f"Enabled WAL mode on database: {self.db_file}")
        except sqlite3.Error as e:
            logging.error(f"Error enabling WAL mode: {e}")

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
                customer_chat_id TEXT NOT NULL,
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

        CREATE_ORDER_DETAILS_VIEW = """
            CREATE VIEW IF NOT EXISTS order_details AS
            SELECT 
                o.id AS order_id,
                o.customer_name,
                o.status,
                GROUP_CONCAT(m.name || ' (' || oi.quantity || ')', ', ') AS order_contents
            FROM 
                orders o
            JOIN 
                order_items oi ON o.id = oi.order_id
            JOIN 
                menu m ON oi.menu_id = m.id
            GROUP BY 
                o.id, o.customer_name, o.status;
        """

        self.cursor.execute(CREATE_MENU_TABLE)
        self.cursor.execute(CREATE_ORDERS_TABLE)
        self.cursor.execute(CREATE_ORDER_ITEMS_TABLE)
        self.cursor.execute(CREATE_ORDER_DETAILS_VIEW)
        self.conn.commit()
        logging.info("Initialised database and created tables and views.")

    def init_menu_items(self) -> None:
        """Add menu items to the database."""
        for name, quantity, price in MENU_ITEMS:
            self.insert_menu_item(name, quantity, price)
        logging.info("Menu items added to database.")

    # Create
    def insert_menu_item(self, name:str, quantity:int, price:float) -> None:
        """Insert a new item into the menu."""
        query = "INSERT INTO menu (name, quantity, price) VALUES (?, ?, ?)"
        self.cursor.execute(query, (name, quantity, price))

    def insert_single_order(self, username:str, chat_id:str, item_id:int, quantity:int) -> bool:
        """Insert a new single order."""
        # TODO: need try-catch here?

        self.cursor.execute("SELECT quantity FROM menu WHERE id = ?", (item_id,))
        row = self.cursor.fetchone()
        available_quantity = int(row[0]) if row else None

        if quantity > available_quantity:
            logging.warning(f"Not enough stock for item {item_id}. Requested: {quantity}, Available: {available_quantity}")
            return False

        self.cursor.execute("SELECT id FROM orders WHERE customer_name = ? AND status = ?", (username, OrderStatus.Pending.name,))
        existing_order = self.cursor.fetchone()

        if not existing_order:
            self.cursor.execute("INSERT INTO orders (customer_name, customer_chat_id, status) VALUES (?, ?, ?)", (username, chat_id, OrderStatus.Pending.name))
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

        new_quantity = available_quantity - quantity
        self.cursor.execute("UPDATE menu SET quantity = ? WHERE id = ?", (new_quantity, item_id))

        self.conn.commit()
        logging.info(f"Order for {username} of {quantity}x Item {item_id} added successfully.")
        return True


    # Read
    ## menu
    def get_menu(self) -> list[MenuItem]:
        """Fetch all items from the menu."""
        self.cursor.execute("SELECT * FROM menu")
        rows = self.cursor.fetchall()
        return [cast_to_menu_item(row) for row in rows]
    
    def get_menu_item_by_id(self, id:int) -> Optional[MenuItem]:
        """Fetch menu item by id."""
        self.cursor.execute("SELECT * FROM menu WHERE id = ?", (id,))
        row = self.cursor.fetchone()
        return cast_to_menu_item(row) if row else None
    
    def get_menu_item_by_name(self, name:str) -> Optional[MenuItem]:
        """Fetch menu item by name."""
        self.cursor.execute("SELECT * FROM menu WHERE name = ?", (name,))
        row = self.cursor.fetchone()
        return cast_to_menu_item(row) if row else None
    
    def get_unselected_menu_item_names_by_username(self, username:str) -> list[MenuItem]:
        """Fetch menu item names that have not been selected by the user."""
        query = """
            SELECT mi.id, mi.name, mi.quantity, mi.price 
            FROM order_items oi
            JOIN orders o ON oi.order_id = o.id
            JOIN menu mi ON oi.menu_id = mi.id
            WHERE o.customer_name = ?
        """
        self.cursor.execute(query, (username,))
        rows = self.cursor.fetchall()

        selected_items = {cast_to_menu_item(row) for row in rows}
        menu_items = self.get_menu()
        unselected_items = [item for item in menu_items if item not in selected_items]
        return unselected_items
    
    ## orders
    def get_orders(self) -> list[Order]:
        """Fetch all orders."""
        self.cursor.execute("SELECT * FROM orders")
        rows = self.cursor.fetchall()
        return [cast_to_order(row) for row in rows]

    def get_order_ids(self) -> list[int]:
        """Fetch all order ids."""
        self.cursor.execute("SELECT id FROM orders")
        rows = self.cursor.fetchall()
        return [int(row[0]) for row in rows]

    def get_order_ids_by_status(self, status:OrderStatus) -> list[int]:
        """Fetch order ids by status."""
        query = "SELECT * FROM orders WHERE status = ?" 
        self.cursor.execute(query, (status.name,))
        rows = self.cursor.fetchall()
        return [int(row[0]) for row in rows]

    def get_pending_orders_for_username(self, username:str) -> list[int]:
        """Fetch all pending order ids for a username."""
        query = "SELECT id FROM orders WHERE customer_name = ? AND status = ?"
        self.cursor.execute(query, (username, OrderStatus.Pending.name))
        rows = self.cursor.fetchall()
        return [int(row[0]) for row in rows]

    def get_status_by_customer_name(self, username:str) -> Optional[OrderStatus]:
        """Fetch the order status by cusomter_name."""
        self.cursor.execute("SELECT status FROM orders WHERE customer_name = ?", (username,))
        row = self.cursor.fetchone()
        return getattr(OrderStatus, row[0], None) if row else None

    def get_status_by_id(self, order_id:int) -> Optional[OrderStatus]:
        """Fetch the order status by id."""
        self.cursor.execute("SELECT status FROM orders WHERE id = ?", (order_id,))
        row = self.cursor.fetchone()
        return getattr(OrderStatus, row[0], None) if row else None
    
    def get_chat_id_by_id(self, order_id:int) -> Optional[str]:
        """Fetch the customer chat id by id."""
        self.cursor.execute("SELECT customer_chat_id FROM orders WHERE id = ?", (order_id,))
        row = self.cursor.fetchone()
        return row[0] if row else None
    
    ## order_items
    def get_order_items_for_order_id(self, order_id:int) -> list[OrderItem]:
        """Fetch all order items for a particular order."""
        query = "SELECT * from order_items WHERE order_id = ?"
        self.cursor.execute(query, (order_id,))
        rows = self.cursor.fetchall()
        return [cast_to_order_item(row) for row in rows]
    
    ## order_details
    def get_order_details(self) -> list[OrderDetail]:
        """Fetch full order details from view."""
        self.cursor.execute("SELECT * FROM order_details")
        rows = self.cursor.fetchall()
        return [cast_to_order_detail(row) for row in rows]
        
    def get_order_details_by_status(self, status:OrderStatus) -> list[OrderDetail]:
        """Fetch full order details from view by status."""
        query = "SELECT * FROM order_details WHERE status = ?" 
        self.cursor.execute(query, (status.name,))
        rows = self.cursor.fetchall()
        return [cast_to_order_detail(row) for row in rows]

    # Check
    def check_order_for_id_exists(self, order_id:int) -> bool:
        """Check that order id exists."""
        query = "SELECT COUNT(1) FROM orders WHERE id = ?"
        self.cursor.execute(query, (order_id,))
        row = self.cursor.fetchone()
        return row[0] > 0
    
    def check_order_for_user_exists(self, username:str) -> bool:
        """Check that order for user exists."""
        query = "SELECT COUNT(1) FROM orders WHERE customer_name = ? AND status != ?"
        self.cursor.execute(query, (username,OrderStatus.Pending.name))
        row = self.cursor.fetchone()
        return row[0] > 0
    
    # Update
    def reduce_menu_item_quantity(self, item_id:int, quantity:int) -> None:
        """Reduce menu item quantity."""
        self.cursor.execute("SELECT quantity FROM menu WHERE id = ?", (item_id,))
        row = self.cursor.fetchone()
        current_quantity = row[0] if row else None
        
        new_quantity = max(current_quantity - quantity, 0)
        self.cursor.execute("UPDATE menu SET quantity = ? WHERE id = ?", (new_quantity, item_id))
        self.conn.commit()
        logging.info(f"Menu item {item_id} quantity reduced to {new_quantity}.")

    def update_order_status(self, order_id:int, status:OrderStatus) -> None:
        """Update order status."""
        query = "UPDATE orders SET status = ? WHERE id = ?"
        self.cursor.execute(query, (status.name, order_id))
        self.conn.commit()
        logging.info(f"Order {order_id} status updated to {status.name}.")

    # Testing 
    def _insert_bulk_order(self, customer_name:str, ordered_items: list[tuple[int, int]]) -> None:
        """Insert a new bulk order."""
        self.cursor.execute("INSERT INTO orders (customer_name, customer_chat_id, status) VALUES (?, ?, ?)",
                            (customer_name, "", OrderStatus.AwaitingPayment.name))
        order_id = self.cursor.lastrowid

        for item_id, quantity in ordered_items:
            self.cursor.execute("INSERT INTO order_items (order_id, menu_id, quantity) VALUES (?, ?, ?)",
                                (order_id, item_id, quantity))
        
        self.conn.commit()
        logging.info(f"Order for {customer_name} with {len(ordered_items)} items added successfully.")


    def _populate_test_data(self) -> None:
        """Populate the database with some test data for testing purposes."""
        # Insert some items into the menu
        self.insert_menu_item("Chili Oil Dumplings", 20, 3)
        self.insert_menu_item("Scallion Oil Noodles", 15, 2)
        self.insert_menu_item("Egg (for noodles)", 15, 0.5)
        self.insert_menu_item("Mandarin Fresh Cream Roll", 10, 2.5)

        # Insert some orders
        self._insert_bulk_order("Alice", [(1, 1), (4, 1)])
        self._insert_bulk_order("Bob", [(2, 1), (3, 1)])
        self._insert_bulk_order("Charl_ie", [(1, 2), (2, 1), (4, 1)])

        logging.info("Test data populated.")

    def _reset_database(self) -> None:
        """Drop all tables and reset the database."""
        # Drop the tables to reset the database
        self.cursor.execute("DROP TABLE IF EXISTS menu;")
        self.cursor.execute("DROP TABLE IF EXISTS orders;")
        self.cursor.execute("DROP TABLE IF EXISTS order_items;")

        self.conn.commit()
        logging.info("Database reset: All tables have been dropped and reset.")
