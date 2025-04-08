import os
import dotenv

# Load environment variables from .env file
dotenv.load_dotenv(".env")

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