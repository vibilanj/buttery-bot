# Buttery Bot

## Features

- List all available items on a particular buttery opening day.
- Allow users to select available items to make an order.
- Show total price and payment QR code.
- Send message when order is ready.
- Show order status to customer.
- Send order and customer information to cooking team.
- Admin hidden commands to
    - update available quantity
    - receive screenshots and approve payment 
    - update order status

### Future
- Store sales statistics
- Allow people to make suggestions/vote on menu items

## Implementation

- Use framework eternnoir/pyTelegramBotAPI
- Data storage using SQLite
- Authentication using hardcoded user IDs for admin features
- Manage secrets with environment file

### Order flow

0. Pending (only transient)
1. AwaitingPayment
2. Processing
3. OrderReady
4. OrderCollected / Cancelled

## Possible changes
 
- [ ] Allow users to make more orders after they are fulfilled
- [ ] Allow users to view their current order and edit it if they have not paid yet
- [ ] Use asynchronous polling?

## Notes

- load_dotenv function
- Enum type
- Dealing with decimal calculations
- Proper logging in Python 
- NamedTuple vs Dataclass

- If concurrency issue, then consider using thread local connections or ORM like SQLAlchemy
- Move backend functionality to API
