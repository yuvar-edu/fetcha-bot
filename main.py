import os
import random
import tweepy
import time
import asyncio
import traceback
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
from rate_limiter import RateLimiter
from telegram.helpers import escape_markdown

# Initialize rate limiter
rate_limiter = RateLimiter()

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
        
    # Check Finnhub rate limit before making request
    can_request, wait_time = await rate_limiter.check_rate_limit('finnhub')
    if not can_request:
        print(f"Rate limit reached for Finnhub API. Waiting {wait_time:.2f} seconds")
        await asyncio.sleep(wait_time)

    finnhub_client = finnhub.Client(api_key=FINNHUB_API_KEY)
    categories = ['general', 'forex', 'crypto', 'merger']
    new_news_found = False

    for category in categories:
        try:
            response = await asyncio.to_thread(finnhub_client.general_news, category, 0)
            rate_limiter.update_from_headers('finnhub', {
                'x-rate-limit-remaining': response.headers.get('x-ratelimit-remaining'),
                'x-rate-limit-reset': response.headers.get('x-ratelimit-reset')
            } if hasattr(response, 'headers') else {})
            news = response
            print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Retrieved {len(news)} news articles in {category}", flush=True)

            for article in news:
                if str(article['id']) in processed_news:
                    continue

                print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Processing NEW news ID: {article['id']}")
                bot_stats.news_processed += 1
                # Check Grok API rate limit
                can_request, wait_time = await rate_limiter.check_rate_limit('grok')
                if not can_request:
                    print(f"Rate limit reached for Grok API. Waiting {wait_time:.2f} seconds")
                    jitter = wait_time * random.uniform(0.1, 0.3)
                    await asyncio.sleep(wait_time + jitter)
                
                analysis = grok_analyze(article['summary'], GROK_API_KEY)
                rate_limiter.log_request('grok')
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
    
    # Check Twitter rate limit before starting
    can_request, wait_time = await rate_limiter.check_rate_limit('twitter')
    if not can_request:
        print(f"Rate limit reached for Twitter API. Waiting {wait_time:.2f} seconds")
        await asyncio.sleep(wait_time)
    
    try:
        processed_tweets = set(json.loads(PROCESSED_TWEETS_FILE.read_text())) if PROCESSED_TWEETS_FILE.exists() else set()
    except Exception as e:
        print(f"Error loading processed tweets: {e}")
        processed_tweets = set()

    client = tweepy.Client(
        bearer_token=TWITTER_BEARER_TOKEN,
        wait_on_rate_limit=True
    )
    
    batch_tweets = []  # Initialize empty list
    
    # Add near top with other constants
    CRITICAL_INFLUENCERS = ['elonmusk', 'saylor', 'CathieDWood', 'brian_armstrong', 'cz_binance', 'VitalikButerin', 'APompliano', 'RaoulGMI', 'chamath', 'garyvee', 'realDonaldTrump']
    MAX_RETRIES = 3
    BASE_DELAY = 1.5
    CIRCUIT_BREAKER_THRESHOLD = 5

    influencer_last_ids = {}
    new_tweets_found = False
    # Add near other initializations
    error_counts = {}
    
    # Update API call blocks with full retry wrapping
    for idx, (username, name) in enumerate(INFLUENCERS.items()):
        # Add progressive delay between influencers
        base_delay = idx * 1.2
        jitter = random.uniform(0.8, 1.2)
        await asyncio.sleep(base_delay * jitter)
        
        if error_counts.get(username, 0) >= CIRCUIT_BREAKER_THRESHOLD:
            print(f"Skipping {username} due to circuit breaker")
            continue
        
        try:
            retries = 0
            while retries < MAX_RETRIES:
                jitter = random.uniform(0.5, 1.5)
                delay = BASE_DELAY * (2 ** retries) * jitter
                
                try:
                    user = await asyncio.to_thread(client.get_user, username=username)
                    if not user or not user.data:
                        print(f"Failed to retrieve user data for {username}")
                        continue

                    # Get last processed tweet ID for pagination
                    since_id = max((int(t) for t in processed_tweets if t.isdigit()), default=None)
                    
                    response = await asyncio.to_thread(
                        client.get_users_tweets,
                        id=user.data.id,
                        tweet_fields=['created_at', 'public_metrics', 'referenced_tweets'],
                        max_results=50,
                        since_id=since_id,
                        exclude=['retweets', 'replies']
                    )
                    rate_limiter.update_from_headers('twitter', {
                        'x-rate-limit-remaining': response.headers.get('x-rate-limit-remaining'),
                        'x-rate-limit-reset': response.headers.get('x-rate-limit-reset')
                    })
                    tweets = response.data
                    
                    # Update error tracking
                    error_counts[username] = error_counts.get(username, 0)
                    
                    if not tweets or not tweets.data:
                        print(f"No tweets found for {username}")
                        continue
                    
                    users = {u.id: u for u in tweets.includes.get('users', [])} if tweets.includes else {}
                    
                    for tweet in tweets.data:
                        user = users.get(tweet.author_id)
                        if not user or user.username not in INFLUENCERS:
                            continue
                        
                        username = user.username
                        name = INFLUENCERS[username]
                    break
                except tweepy.HTTPException as inner_e:
                    rate_limiter.update_from_headers('twitter', {
                        'x-rate-limit-remaining': inner_e.response.headers.get('x-rate-limit-remaining'),
                        'x-rate-limit-reset': inner_e.response.headers.get('x-rate-limit-reset')
                    })
                    remaining = rate_limiter.get_remaining_requests('twitter')
                    reset = rate_limiter.last_reset['twitter'] + rate_limiter.rate_limits['twitter']['window'] - time.time()
                    
                    if remaining == 0:
                        wait_time = max(reset - time.time(), 60)
                        print(f"Rate limit exhausted. Waiting {wait_time} seconds")
                        jitter = wait_time * random.uniform(0.1, 0.3)
                        await asyncio.sleep(wait_time + jitter)
                    else:
                        retries += 1
                        print(f"Attempt {retries}/{MAX_RETRIES} - waiting {delay:.2f}s")
                        await asyncio.sleep(delay)
            
            # Reset error count on success
            error_counts[username] = 0
            
            if user is None or not user.data:
                continue
            
            print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Retrieved {len(tweets.data) if tweets and tweets.data else 0} tweets from {username}", flush=True)
            
            if tweets and tweets.data:
                influencer_last_ids[username] = tweets.data[0].id  # Store most recent ID
                for tweet in tweets.data:
                    if str(tweet.id) in processed_tweets:
                        continue
                    
                    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Processing NEW tweet ID: {tweet.id}")
                    bot_stats.tweets_processed += 1
                    # Check Grok API rate limit
                    can_request, wait_time = await rate_limiter.check_rate_limit('grok')
                    if not can_request:
                        print(f"Rate limit reached for Grok API. Waiting {wait_time:.2f} seconds")
                        jitter = wait_time * random.uniform(0.1, 0.3)
                    await asyncio.sleep(wait_time + jitter)
                    
                    batch_tweets.append({'id': str(tweet.id), 'text': tweet.text, 'username': username, 'name': name})

            # Process batch after collecting all new tweets
            if batch_tweets:
                try:
                    tweet_texts = [{'id': t['id'], 'text': t['text']} for t in batch_tweets]
                    analyses = grok_analyze([t['text'] for t in batch_tweets], GROK_API_KEY)
                    rate_limiter.log_request('grok')

                    for i, analysis in enumerate(analyses):
                        tweet_data = batch_tweets[i]
                        print(f"Grok API analysis result for {tweet_data['id']}: {analysis}")
                        processed_tweets.add(tweet_data['id'])
                        new_tweets_found = True

                        if analysis.get('relevant', False):
                            print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Relevant tweet detected: {tweet_data['id']}")
                            formatted_msg = (
                                f"🚨 **{analysis['headline']}**\n\n"
                                f"**{tweet_data['name']} (@{tweet_data['username']})**\n"
                                f"{tweet_data['text']}\n\n"
                                f"📈 Sentiment: {analysis['sentiment']} ({analysis['score']}/10)\n"
                                f"📉 Impact: {analysis['impact']}\n"
                                f"🧭 Direction: {analysis['direction']}\n"
                                f"💰 Assets: {', '.join(analysis['assets'])}\n\n"
                                f"🔗 Original tweet: https://twitter.com/{tweet_data['username']}/status/{tweet_data['id']}"
                            )
                            await send_to_telegram(formatted_msg)

                except Exception as e:
                    bot_stats.errors_count += 1
                    print(f"Batch processing error: {str(e)}")
        
        except tweepy.HTTPException as e:
            if e.response.status_code == 429:
                retry_after = int(e.response.headers.get('Retry-After', 300))
                print(f"Rate limited - waiting {retry_after} seconds")
                await asyncio.sleep(retry_after)
                continue
            else:
                bot_stats.errors_count += 1
                error_counts[username] = error_counts.get(username, 0) + 1
                print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Error processing {username}: {e} (Error count: {error_counts[username]}/{CIRCUIT_BREAKER_THRESHOLD})")
                if username == 'cz_binance':
                    print(f"Error processing {username}: {e}\nTraceback: {traceback.format_exc()}")
                    if username == 'cz_binance':
                        print(f"DEBUG: cz_binance API error - Status: {e.response.status_code}")
        except Exception as e:
            bot_stats.errors_count += 1
            print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Telegram send error: {e}\n{traceback.format_exc()}")
            print(f"Error details: {str(e)}")

    # Add cooldown after processing batch
    await asyncio.sleep(random.uniform(2.0, 4.0))

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
        # Initialize static bot instance
        if not hasattr(send_to_telegram, 'bot'):
            send_to_telegram.bot = Bot(token=TELEGRAM_BOT_TOKEN)
            
            # Validate and format channel ID
            channel_id = str(TELEGRAM_CHANNEL_ID)
            if channel_id.isdigit() and not channel_id.startswith('-100'):
                channel_id = f'-100{channel_id}'
            send_to_telegram.channel_id = channel_id
        
        escaped_message = escape_markdown(message, version=2)
        message_obj = await send_to_telegram.bot.send_message(
            chat_id=send_to_telegram.channel_id,
            message_thread_id=int(TELEGRAM_TOPIC_ID) if TELEGRAM_TOPIC_ID else None,
            text=escaped_message,
            parse_mode='MarkdownV2'
        )
        bot_stats.messages_sent += 1
    except Exception as e:
        print(f'Telegram error: {repr(e)}')
        if 'Forbidden: bot is not a member' in str(e):
            print('Error: Bot needs to be added to channel as admin with post permissions')

async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Get API rate limit information
    twitter_remaining = rate_limiter.get_remaining_requests('twitter')
    grok_remaining = rate_limiter.get_remaining_requests('grok')
    
    stats_text = (
        f"📊 Bot Statistics\n\n"
        f"🤖 Performance\n"
        f"- Uptime: {bot_stats.get_uptime()}\n"
        f"- Tweets processed: {bot_stats.tweets_processed}\n"
        f"- Messages sent: {bot_stats.messages_sent}\n"
        f"- Errors encountered: {bot_stats.errors_count}\n"
        f"- Uptime: {str(datetime.now() - bot_stats.start_time).split('.')[0]}\n\n"
        f"📈 API Status\n"
        f"- Twitter API: {twitter_remaining}/180 requests remaining\n"
        f"- Grok API: {grok_remaining}/60 requests remaining\n"
    )
    await context.bot.send_message(chat_id=update.effective_chat.id, text=stats_text)

async def main():
    # Initialize scheduler
    scheduler = AsyncIOScheduler()
    scheduler.add_job(
        fetch_tweets,
        'interval',
        minutes=15,
        jitter=60,
        next_run_time=datetime.now(),
        misfire_grace_time=120
    )
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Starting scheduler with 1-minute intervals")
    scheduler.start()

    # Create single Telegram application instance
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    application.add_handler(CommandHandler("stats", stats_command))

    # Initial checks
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Performing initial tweet check")
    await fetch_tweets()
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Performing initial news check")
    await fetch_news()

    # Start polling
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Starting Telegram polling")
    await application.run_polling()

if __name__ == '__main__':
    asyncio.run(main())