# Telegram Bot Response Listener

A Python script that listens to messages from a specific Telegram bot in real-time, prints all bot responses to the console, and saves filtered messages to MongoDB.

## Features

- Real-time listening to bot messages
- Console output with formatted timestamps and message content
- Automatic saving to MongoDB (localhost)
- Automatic parsing of account status information (Name, Due, Balance, Due Limit)
- Automatic session management (saves login state)
- Support for text, media, stickers, and other message types
- Duplicate message prevention

## Prerequisites

- Python 3.7 or higher
- Telegram API credentials (api_id and api_hash)
- A Telegram account
- MongoDB installed and running on localhost (optional - script works without it)

## Installation

1. Clone or download this repository

2. Install required dependencies:
```bash
pip install -r requirements.txt
```

## MongoDB Setup (Optional)

1. Install MongoDB on your system:
   - Windows: Download from [MongoDB Download Center](https://www.mongodb.com/try/download/community)
   - Or use: `choco install mongodb` (if you have Chocolatey)

2. Start MongoDB service:
   ```bash
   # Windows (if installed as service, it starts automatically)
   # Or manually:
   mongod --dbpath "C:\data\db"
   ```

3. MongoDB will run on `localhost:27017` by default

**Note:** The script will work without MongoDB - messages will still be printed to console. MongoDB is optional for data persistence.

## Configuration

Edit `config.py` to set your bot username and MongoDB settings:

```python
BOT_USERNAME = "kaiumrakibucbot"  # Change to your target bot username

# MongoDB Configuration (default: localhost)
MONGODB_HOST = "localhost"
MONGODB_PORT = 27017
MONGODB_DATABASE = "telegram_bot"
MONGODB_COLLECTION = "bot_messages"
```

The API credentials are already configured:
- API_ID: 37118739
- API_HASH: d02baf67c4f5d2e0586236c24e1248d1

## Usage

1. Run the script:
```bash
python telegram_listener.py
```

2. On first run, you'll be prompted to:
   - Enter your phone number (with country code, e.g., +1234567890)
   - Enter the verification code sent to your Telegram app
   - Enter your 2FA password (if enabled)

3. After authentication, the script will start listening to messages from the configured bot.

4. Send commands to the bot from your Telegram app, and you'll see the bot's responses printed in the console.

5. Press `Ctrl+C` to stop the listener.

## How It Works

1. The script connects to Telegram using Telethon library
2. It connects to MongoDB (if available)
3. It authenticates using your phone number and API credentials
4. It finds the target bot by username
5. It listens for all incoming messages
6. When a message from the target bot is received:
   - It prints it to the console with timestamp
   - It saves the message data to MongoDB (if connected)

## Output Format

**Console Output:**
```
[2025-01-04 23:26:45] Bot: Your message content here
[Saved to MongoDB: 507f1f77bcf86cd799439011]
--------------------------------------------------------------------------------
```

**MongoDB Document Structure:**
```json
{
  "_id": ObjectId("..."),
  "message_id": 12345,
  "date": "2025-01-04T23:26:45",
  "text": "Your message content here",
  "sender_id": 123456789,
  "chat_id": 123456789,
  "message_type": "text",
  "media_type": null,
  "raw_date": "2025-01-04T23:26:45.123456",
  "account_status": {
    "user": {
      "name": "Mohammad Robayet"
    },
    "wallet": {
      "due": 69.0,
      "balance": 0.0,
      "dueLimit": 3000
    },
    "currency": "Tk"
  }
}
```

**Note:** If a message contains account status information (Name, Due, Balance, Due Limit), it will be automatically parsed and stored in the `account_status` field.

## Notes

- The session file (`.session`) is created automatically and saves your login state
- You only need to authenticate once (unless you delete the session file)
- The script listens to all messages, but only prints messages from the configured bot
- Make sure the bot username in `config.py` is correct (without the @ symbol)

## Troubleshooting

- **Bot not found**: Check that the bot username in `config.py` is correct
- **Authentication errors**: Make sure your API credentials are correct
- **No messages appearing**: Ensure you're sending commands to the bot from your Telegram app
- **MongoDB connection failed**: 
  - Make sure MongoDB is installed and running
  - Check that MongoDB is running on `localhost:27017`
  - The script will continue working without MongoDB (console output only)
- **Duplicate messages in MongoDB**: The script automatically prevents duplicates based on message_id

## License

This project is for personal use.

