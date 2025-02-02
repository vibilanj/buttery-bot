# Buttery Bot

## Features

- List all available items on a particular buttery opening day.
- Allow users to select available items to make an order.
- Show total price and payment QR code.
- Send order and customer information to cooking team.
- Show order status to customer.
- Admin hidden commands to
    - set available items and quantity
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

### Models

- Menu
    - Name
    - Quantity
    - Price
    - Picture (?)
- Order
    - Name
    - Items (list of items)
    - Total Price
    - Status (enum)


## Todo

- [x] How to capture and store logs
- [ ] Update commands in BotFather
- [ ] Test with real users and concurrency
    - if not, consider using thread local connections or SQLachemy

## Learning 

- load_dotenv function
- Enum type
- Dealing with decimal calculations
- Logging 