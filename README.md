# Buttery Bot

## Features

- List all available items on a particular buttery opening day.
- Allow users to select available items to make an order.
- Show total price and payment QR code.
- Show order status to customer.
- Send order and customer information to cooking team.
- Admin hidden commands to
    - update available quantity
    - manually approve payment
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

## Todo
 
- [ ] Setup script to archive database
- [ ] Setup script to read from database and make summaries and plots 
- [ ] Allow users to make more orders after they are fulfilled
- [ ] Allow users to view their current order and edit it if they have not paid yet

## Testing

- [ ] Usability without database WAL mode
- [ ] CHECK insert_single_order, error handling, whether commit does the transaction handling as expected
- [ ] Test if asynchronous polling is possible

## Learning 

- load_dotenv function
- Enum type
- Dealing with decimal calculations
- Logging 
- NamedTuple vs Dataclass

- If concurrency issue, then consider using thread local connections or ORM like SQLAlchemy
- Move backend functionality to API
