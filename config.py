import os
import dotenv
import sys

# Load environment variables from .env file
dotenv.load_dotenv(".env")

# Validate required environment variables
REQUIRED_KEYS = [
    'TWITTER_BEARER_TOKEN',
    'GROK_API_KEY',
    'TELEGRAM_BOT_TOKEN',
    'TELEGRAM_CHANNEL_ID',
    'FINNHUB_API_KEY'
]

missing = [key for key in REQUIRED_KEYS if not os.getenv(key)]
if missing:
    print(f"Error: Missing required environment variables: {', '.join(missing)}")
    sys.exit(1)

# Twitter/X API Configuration
TWITTER_BEARER_TOKEN = os.getenv('TWITTER_BEARER_TOKEN')

# DeepSeek AI Configuration
GROK_API_KEY = os.getenv('GROK_API_KEY')

# Telegram Configuration
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
TELEGRAM_CHANNEL_ID = os.getenv('TELEGRAM_CHANNEL_ID')
TELEGRAM_TOPIC_ID = os.getenv('TELEGRAM_TOPIC_ID')

# Finnhub Configuration
FINNHUB_API_KEY = os.getenv('FINNHUB_API_KEY')

# Scheduler Configuration
POLLING_INTERVAL_MINUTES = 1

__all__ = [
    'TWITTER_BEARER_TOKEN',
    'GROK_API_KEY',
    'TELEGRAM_BOT_TOKEN',
    'TELEGRAM_CHANNEL_ID',
    'TELEGRAM_TOPIC_ID',
    'FINNHUB_API_KEY',
    'POLLING_INTERVAL_MINUTES'
]