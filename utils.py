from constants import Order, OrderDetail, OrderItem, OrderStatus, MenuItem

def sanitise_username(username:str) -> str:
    """Escape underscores from usernames for markdown."""
    return username.replace("_", "\\_")

def parse_status(status_str:str) -> OrderStatus:
    """Convert a human-readable string back to the corresponding OrderStatus."""
    for status in OrderStatus:
        if status.value == status_str:
            return status
    return OrderStatus.Pending

def status_transition(status:OrderStatus) -> OrderStatus:
    STATUS_TRANSITIONS = {
        OrderStatus.AwaitingPayment: [OrderStatus.InKitchen, OrderStatus.Cancelled],
        OrderStatus.InKitchen: [OrderStatus.OrderReady],
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