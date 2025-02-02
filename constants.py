from enum import Enum
from typing import NamedTuple


class OrderStatus(Enum):
    Pending = 1
    AwaitingPayment = 2
    Processing = 3
    Completed = 4
    Cancelled = 5


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
