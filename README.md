# Fetcha Bot

A Twitter monitoring bot that tracks crypto influencers and sends analyzed updates to Telegram.

## Features
- 🐦 Monitors 10+ influencers on Twitter/X
- 🔍 Uses Grok AI for tweet analysis
- 📊 Tracks bot statistics including uptime and message metrics
- ⏰ Automated checks every 5 minutes
- 📨 Telegram notifications for relevant updates

## Requirements
- Python 3.10+
- Twitter Developer Account
- Grok API Key
- Telegram Bot Token

## Installation
1. Clone repository
```bash
git clone https://github.com/yourusername/fetcha-bot.git
cd fetcha-bot
```
2. Install dependencies
```bash
pip install -r requirements.txt
```

## Configuration
Create `.env` file with these variables:
```ini
TWITTER_CONSUMER_KEY=your_key
TWITTER_CONSUMER_SECRET=your_secret
TWITTER_ACCESS_TOKEN=your_token
TWITTER_ACCESS_TOKEN_SECRET=your_token_secret
TWITTER_BEARER_TOKEN=your_bearer_token
GROK_API_KEY=your_grok_key
TELEGRAM_BOT_TOKEN=your_bot_token
TELEGRAM_CHANNEL_ID=your_channel_id
TELEGRAM_TOPIC_ID=your_topic_id
```

## Usage
```bash
python main.py
```

📊 View statistics in Telegram with `/stats` command

🔧 The bot automatically checks for new tweets every 5 minutes

## Supported Influencers
- Elon Musk
- Michael Saylor
- Cathie Wood
- Brian Armstrong
- Changpeng Zhao
- Vitalik Buterin
- Anthony Pompliano
- Raoul Pal
- Chamath Palihapitiya
- Gary Vaynerchuk