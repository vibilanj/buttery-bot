from enum import Enum
from typing import NamedTuple


class OrderStatus(Enum):
    Pending = 1
    AwaitingPayment = 2
    Processing = 3
    OrderReady = 4
    OrderCollected = 5
    Cancelled = 6


class MenuItem(NamedTuple):
    id: int
    name: str
    quantity: int
    price: float


class Order(NamedTuple):
    id: int
    customer_name: str
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
