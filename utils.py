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
        status=getattr(OrderStatus, row[2], None),
        created_at=row[3]
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