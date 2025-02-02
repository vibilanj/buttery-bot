from enum import Enum

class OrderStatus(Enum):
    Pending = 1
    AwaitingPayment = 2
    Processing = 3
    Completed = 4
    Cancelled = 5
