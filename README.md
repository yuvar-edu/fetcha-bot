# Fetcha Bot

A Twitter monitoring bot that tracks crypto influencers and sends analyzed updates to Telegram.

## Features
- 🐦 Monitors 10+ influencers on Twitter/X
- 📰 Gets and updates latest market headlines
- 🔍 Uses Grok AI for tweet analysis
- 📊 Tracks bot statistics including uptime and message metrics
- ⏰ Automated checks every 1 minute
- 📨 Telegram notifications for relevant updates

## Requirements
- Python 3.10+
- Twitter Developer Account
- Finnhub API Key
- Grok API Key
- Telegram Bot Token

## Installation
1. Clone repository
```bash
git clone https://github.com/yuvar-edu/fetcha-bot.git
cd fetcha-bot
```
2. Install dependencies
```bash
pip install -r requirements.txt
```

## Configuration
Use `.env.example` file to configure the bot:

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
- Donald Trump