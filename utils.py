from constants import *

def sanitise_username(username:str) -> str:
    """Escape underscores from usernames for markdown."""
    return username.replace("_", "\\_")

def display_status(status:OrderStatus) -> str:
    """Convert order status to a human-readable string with an emoji."""
    match status:
        case OrderStatus.Pending:
            return "⏳ Pending"
        case OrderStatus.AwaitingPayment:
            return "💳 Awaiting Payment"
        case OrderStatus.Processing:
            return "🔄 Processing"
        case OrderStatus.OrderReady:
            return "🍽️ Order Ready"
        case OrderStatus.OrderCollected:
            return "✅ Order Collected"
        case OrderStatus.Cancelled:
            return "❌ Cancelled"
        case _:
            return "Unknown Status"

def parse_status(status_str:str) -> OrderStatus:
    """Convert a human-readable string back to the corresponding OrderStatus."""
    match status_str:
        case "⏳ Pending":
            return OrderStatus.Pending
        case "💳 Awaiting Payment":
            return OrderStatus.AwaitingPayment
        case "🔄 Processing":
            return OrderStatus.Processing
        case "🍽️ Order Ready":
            return OrderStatus.OrderReady
        case "✅ Order Collected":
            return OrderStatus.OrderCollected
        case "❌ Cancelled":
            return OrderStatus.Cancelled
        case _:
            return OrderStatus.Pending

def status_transition(status:OrderStatus) -> OrderStatus:
    STATUS_TRANSITIONS = {
        OrderStatus.AwaitingPayment: [OrderStatus.Processing, OrderStatus.Cancelled],
        OrderStatus.Processing: [OrderStatus.OrderReady],
        OrderStatus.OrderReady: [OrderStatus.OrderCollected],
    }
    return STATUS_TRANSITIONS.get(status, [])

# Type casting functions
def cast_to_menu_item(row) -> MenuItem:
    return MenuItem(
        id=int(row[0]),
        name=row[1],
        quantity=int(row[2]),
        price=float(row[3])
    )

def cast_to_order(row) -> Order:
    return Order(
        id=int(row[0]),
        customer_name=row[1],
        customer_chat_id=row[2],
        status=getattr(OrderStatus, row[3], None),
        created_at=row[4]
    )

def cast_to_order_item(row) -> OrderItem:
    return OrderItem(
        order_id=int(row[0]),
        menu_id=int(row[1]),
        quantity=int(row[2])
    )

def cast_to_order_detail(row) -> OrderDetail:
    return OrderDetail(
        order_id=int(row[0]),
        customer_name=row[1],
        status=getattr(OrderStatus, row[2], None),
        order_contents=row[3]
    )