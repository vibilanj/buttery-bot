# Buttery Bot

## Features

- List all available items on a particular buttery opening day.
- Allow users to select available items to make an order.
- Show total price and payment QR code.
- Show order status to customer.
- Send order and customer information to cooking team.
- Admin hidden commands to
    - set available items and quantity (?)
    - update available quantity
    - manually approve payment
    - update order status
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

- [ ] Allow users to edit their order if status is AwaitingPayment (or Pending)
- [ ] Send payment QR code and menu poster. 
- [ ] Setup script to archive database, convert database into a nice viewing format in a pinch
- [ ] Test with real users and concurrency
    - if not, consider using thread local connections or SQLachemy
- [ ] Move backend functionality to API (overkill?)

## Learning 

- load_dotenv function
- Enum type
- Dealing with decimal calculations
- Logging 
- NamedTuple vs Dataclass