from enum import Enum
from typing import NamedTuple

DB_FILE = "buttery.db"

QR_CODE_FILE = "qr_code.jpg"

MENU_ITEMS = [
    ("Mini Sliders (Beef Burgers)", 12, 2.5),
    ("Roast Chicken w/ Veggies & Yorkshire Pudding", 6, 3.5),
    ("Duck Fat Roasted Potatoes", 6, 1.5),
    ("Sticky Date Pudding w/ Ice Cream", 13, 2)
]
MENU_DETAILS = None # None or "additional details"
MENU_FLYER = None # None or "image_path.jpg"

LOGS_DIR = "logs"
ARCHIVE_DIR = "archive"

class OrderStatus(Enum):
    Pending = "⏳ Pending"
    AwaitingPayment = "💳 Awaiting Payment"
    InKitchen = "👨‍🍳 In the Kitchen"
    OrderReady = "🍽️ Order Ready"
    OrderCollected = "✅ Order Collected"
    Cancelled = "❌ Cancelled"

    def display(self) -> str:
        return self.value


class UpdateStatusOption(Enum):
    AwaitingPayment = "Update AwaitingPayment Orders"
    InKitchen = "Update InKitchen Orders"
    OrderReady = "Update OrderReady Orders"
    Any = "Update Any Order"
    

class MenuItem(NamedTuple):
    id: int
    name: str
    quantity: int
    price: float


class Order(NamedTuple):
    id: int
    customer_name: str
    customer_chat_id: str
    status: OrderStatus
    created_at: str 


class OrderItem(NamedTuple):
    order_id: int
    menu_id: int
    quantity: int


class OrderDetail(NamedTuple):
    order_id: int
    customer_name: str
    status : OrderStatus
    order_contents: str


class Command(NamedTuple):
    command: str
    description: str
    admin_only: bool

AVAIL_CMDS : list[Command] = [
    Command(command="/start", description="Start the bot", admin_only=False),
    Command(command="/help", description="View commands", admin_only=False),
    Command(command="/menu", description="See the menu", admin_only=False),
    Command(command="/order", description="Place your order", admin_only=False),
    Command(command="/status", description="Check your order status", admin_only=False),
    
    Command(command="/listorders", description="List all orders", admin_only=True),
    Command(command="/toprocess", description="List orders to process", admin_only=True),
    Command(command="/updatestatus", description="Update order status", admin_only=True),
    Command(command="/reducequantity", description="Reduce menu item quantity", admin_only=True),
]

