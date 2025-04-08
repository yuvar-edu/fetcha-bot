import os
import tweepy
import time
import asyncio
from datetime import datetime
from grok_api import grok_analyze
from telegram import Bot, Update
from telegram.ext import Application, CommandHandler, ContextTypes
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from config import (
    TWITTER_BEARER_TOKEN,
    GROK_API_KEY,
    FINNHUB_API_KEY,
    TELEGRAM_BOT_TOKEN,
    TELEGRAM_CHANNEL_ID,
    TELEGRAM_TOPIC_ID
)

import finnhub
from dotenv import load_dotenv
import json
from pathlib import Path
from grok_api import grok_analyze

load_dotenv()

class BotStats:
    def __init__(self):
        self.start_time = datetime.now()
        self.tweets_processed = 0
        self.news_processed = 0
        self.messages_sent = 0
        self.errors_count = 0

    def get_uptime(self):
        delta = datetime.now() - self.start_time
        days = delta.days
        hours, remainder = divmod(delta.seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        return f"{days}d {hours}h {minutes}m {seconds}s"

    def format_stats(self):
        return (
            f"📊 Bot Statistics\n\n"
            f"⏱ Uptime: {self.get_uptime()}\n"
            f"🐦 Tweets Processed: {self.tweets_processed}\n"
            f"📰 News Processed: {self.news_processed}\n"
            f"📨 Messages Sent: {self.messages_sent}\n"
            f"⚠️ Errors: {self.errors_count}\n"
        )

bot_stats = BotStats()

INFLUENCERS = {
    'elonmusk': 'Elon Musk',
    'saylor': 'Michael Saylor',
    'CathieDWood': 'Cathie Wood',
    'brian_armstrong': 'Brian Armstrong',
    'cz_binance': 'Changpeng Zhao',
    'VitalikButerin': 'Vitalik Buterin',
    'APompliano': 'Anthony Pompliano',
    'RaoulGMI': 'Raoul Pal',
    'chamath': 'Chamath Palihapitiya',
    'garyvee': 'Gary Vaynerchuk',
    'realDonaldTrump': 'Donald Trump'
}

PROCESSED_TWEETS_FILE = Path(__file__).parent / 'processed_tweets.json'
PROCESSED_NEWS_FILE = Path(__file__).parent / 'processed_news.json'

async def fetch_news():
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Starting scheduled news check", flush=True)
    
    try:
        processed_news = set(json.loads(PROCESSED_NEWS_FILE.read_text())) if PROCESSED_NEWS_FILE.exists() else set()
    except Exception as e:
        print(f"Error loading processed news: {e}")
        processed_news = set()

    finnhub_client = finnhub.Client(api_key=FINNHUB_API_KEY)
    categories = ['general', 'forex', 'crypto', 'merger']
    new_news_found = False

    for category in categories:
        try:
            news = finnhub_client.general_news(category, min_id=0)
            print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Retrieved {len(news)} news articles in {category}", flush=True)

            for article in news:
                if str(article['id']) in processed_news:
                    continue

                print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Processing NEW news ID: {article['id']}")
                bot_stats.news_processed += 1
                analysis = grok_analyze(article['summary'], GROK_API_KEY)
                processed_news.add(str(article['id']))
                new_news_found = True

                if analysis.get('relevant', False):
                    formatted_msg = (
                        f"📰 **{analysis['headline']}**\n\n"
                        f"**{article['source']} News** ({category.title()})\n"
                        f"{article['summary']}\n\n"
                        f"📈 Sentiment: {analysis['sentiment']} ({analysis['score']}/10)\n"
                        f"📉 Impact: {analysis['impact']}\n"
                        f"🧭 Direction: {analysis['direction']}\n"
                        f"💰 Assets: {', '.join(analysis['assets'])}\n\n"
                        f"🔗 Full article: {article['url']}"
                    )
                    await send_to_telegram(formatted_msg)

        except Exception as e:
            bot_stats.errors_count += 1
            print(f"Error processing {category} news: {str(e)}")

    if new_news_found:
        try:
            PROCESSED_NEWS_FILE.write_text(json.dumps(list(processed_news)))
        except Exception as e:
            print(f"Error saving processed news: {e}")


async def fetch_tweets():
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Starting scheduled tweet check", flush=True)
    
    try:
        processed_tweets = set(json.loads(PROCESSED_TWEETS_FILE.read_text())) if PROCESSED_TWEETS_FILE.exists() else set()
    except Exception as e:
        print(f"Error loading processed tweets: {e}")
        processed_tweets = set()

    client = tweepy.Client(
        bearer_token=TWITTER_BEARER_TOKEN,
        wait_on_rate_limit=True
    )
    
    new_tweets_found = False
    for idx, (username, name) in enumerate(INFLUENCERS.items()):
        if idx > 0:
            await asyncio.sleep(60)
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Processing influencer: {username} ({name})", flush=True)
        try:
            user = client.get_user(username=username)
            if not user.data:
                print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] User not found: {username}")
                continue
                
            tweets = client.get_users_tweets(
                user.data.id,
                tweet_fields=['created_at', 'public_metrics', 'referenced_tweets'],
                exclude=['retweets', 'replies'],
                max_results=5
            )
            
            print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Retrieved {len(tweets.data) if tweets and tweets.data else 0} tweets from {username}", flush=True)
        
            if tweets and tweets.data:
                for tweet in tweets.data:
                    if str(tweet.id) in processed_tweets:
                        continue
                    
                    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Processing NEW tweet ID: {tweet.id}")
                    bot_stats.tweets_processed += 1
                    analysis = grok_analyze(tweet.text, GROK_API_KEY)
                    print(f"Grok API analysis result: {analysis}")
                    processed_tweets.add(str(tweet.id))
                    new_tweets_found = True
                    if analysis.get('relevant', False):
                        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Relevant tweet detected: {tweet.id}")
                        formatted_msg = (
                        f"🚨 **{analysis['headline']}**\n\n"
                        f"**{name} (@{username})**\n"
                        f"{tweet.text}\n\n"
                        f"📈 Sentiment: {analysis['sentiment']} ({analysis['score']}/10)\n"
                        f"📉 Impact: {analysis['impact']}\n"
                        f"🧭 Direction: {analysis['direction']}\n"
                        f"💰 Assets: {', '.join(analysis['assets'])}\n\n"
                        f"🔗 Original tweet: https://twitter.com/{username}/status/{tweet.id}"
                    )
                        await send_to_telegram(formatted_msg)
        except tweepy.HTTPException as e:
            if e.response.status_code == 429:
                retry_after = int(e.response.headers.get('Retry-After', 300))
                print(f"Rate limited - waiting {retry_after} seconds")
                await asyncio.sleep(retry_after)
                continue
            else:
                bot_stats.errors_count += 1
                print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Error processing {username}: {e}")
        except Exception as e:
            bot_stats.errors_count += 1
            print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Telegram send error: {e}")
            print(f"Failed to send message: {message}")
            print(f"Error details: {str(e)}")

    if new_tweets_found:
        try:
            PROCESSED_TWEETS_FILE.write_text(json.dumps(list(processed_tweets)))
        except Exception as e:
            print(f"Error saving processed tweets: {e}")

def analyze_tweet(tweet):
    # AI analysis implementation
    analysis = grok_analyze(
        text=tweet.text,
        api_key=GROK_API_KEY
    )
    return analysis

async def send_to_telegram(message):
    try:
        print(f'Attempting to send message to channel: {TELEGRAM_CHANNEL_ID}')
        bot = Bot(token=TELEGRAM_BOT_TOKEN)

        if not TELEGRAM_CHANNEL_ID.startswith('-'):
            raise ValueError('Invalid Telegram channel ID format')

        message_obj = await bot.send_message(
            chat_id=TELEGRAM_CHANNEL_ID,
            message_thread_id=int(TELEGRAM_TOPIC_ID),
            text=message,
            disable_notification=False
        )
        print(f'Message sent successfully. Message ID: {message_obj.message_id}')
        bot_stats.messages_sent += 1
    except Exception as e:
        bot_stats.errors_count += 1
        print(f'Telegram send error: {str(e)}')

async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    stats_text = (
        f"📊 Bot Statistics\n\n"
        f"Tweets processed: {bot_stats.tweets_processed}\n"
        f"Errors encountered: {bot_stats.errors_count}\n"
        f"Uptime: {str(datetime.now() - bot_stats.start_time).split('.')[0]}"
    )
    await context.bot.send_message(chat_id=update.effective_chat.id, text=stats_text)

if __name__ == '__main__':
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    application.add_handler(CommandHandler("stats", stats_command))
    # Initialize scheduler before starting polling
    scheduler = AsyncIOScheduler()
    scheduler.add_job(
        fetch_tweets, 
        'interval', 
        minutes=1,
        next_run_time=datetime.now(),
        misfire_grace_time=300
    )
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Starting scheduler with 1-minute intervals")
    scheduler.start()
    
        # Start Telegram polling after scheduler
    # Initial immediate checks before starting polling
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Performing initial tweet check")
    fetch_tweets()
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Performing initial news check")
    fetch_news()
    
    # Remove direct fetch_tweets() call
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Starting Telegram polling")
    application.run_polling()