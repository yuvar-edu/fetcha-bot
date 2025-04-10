# Fetcha Bot

Fetcha Bot is an automated financial monitoring system that tracks tweets from influential figures in the finance and crypto space, as well as financial news, analyzes their content for market relevance, and delivers real-time notifications to a Telegram channel.

## Features

- **Twitter Monitoring**: Tracks tweets from specified financial influencers
- **Financial News Tracking**: Monitors crypto and forex news from Finnhub
- **AI-Powered Analysis**: Uses AI to analyze content for market sentiment and relevance
- **Real-time Notifications**: Sends relevant updates to a configured Telegram channel
- **Scheduled Checks**: Automatically checks for new content at regular intervals
- **Statistics Tracking**: Maintains stats on processed content and relevance

## Requirements

- Python 3.10+
- Twitter API access (Bearer Token)
- Finnhub API key
- Grok API key (or compatible AI service)
- Telegram Bot Token and Channel

## Installation

1. Clone the repository:
   ```
   git clone https://github.com/yuvar-edu/fetcha-bot.git
   cd fetcha-bot
   ```

2. Create a virtual environment and activate it:
   ```
   python -m venv venv
   # On Windows
   venv\Scripts\activate
   # On macOS/Linux
   source venv/bin/activate
   ```

3. Install dependencies:
   ```
   pip install tweepy finnhub-python python-telegram-bot python-dotenv apscheduler openai
   ```

## Configuration

1. Rename `.env.example` to `.env` and fill in your API keys and Telegram Bot Token and Channel.

2. Customize the list of influencers to monitor in `main.py`

## Usage

Start the bot by running:
```
python main.py
```

The bot will:
1. Initialize connections to all required APIs
2. Resolve Twitter usernames to user IDs
3. Start scheduled checks for new tweets and news
4. Send relevant updates to your Telegram channel

## Telegram Commands

The bot supports the following commands in Telegram:
- `/stats` - Display monitoring statistics

## Project Structure

- `main.py` - Main application entry point and scheduler
- `api/` - API client modules
  - `twitter.py` - Twitter API integration
  - `finnhub.py` - Finnhub API for financial news
  - `analysis.py` - AI-powered text analysis
  - `telegram.py` - Telegram bot for notifications
- `utils/` - Utility modules
  - `logging_config.py` - Logging configuration
  - `data.py` - Data persistence utilities
  - `stats.py` - Statistics tracking
- `data/` - Data storage directory
  - `user_ids.json` - Cached Twitter user IDs
  - `processed_ids.json` - Tracking for processed content


## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.