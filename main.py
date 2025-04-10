import os
import asyncio
import sys
import logging
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv
from apscheduler.schedulers.asyncio import AsyncIOScheduler

# Import utility modules
from utils.logging_config import setup_logging
from utils.data import load_user_ids, save_user_ids, load_processed_ids, save_processed_ids
from utils.stats import stats

# Import API modules
from api.twitter import TwitterAPI
from api.analysis import AnalysisAPI
from api.finnhub import FinnhubAPI
from api.telegram import TelegramAPI

# Load environment variables
load_dotenv()

# Setup logging
logger = setup_logging()

# Check for required environment variables
required_env_vars = [
    'TWITTER_BEARER_TOKEN',
    'FINNHUB_API_KEY',
    'GROK_API_KEY',
    'TELEGRAM_BOT_TOKEN',
    'TELEGRAM_CHAT_ID',
    'TELEGRAM_TOPIC_ID'
]

missing_vars = [var for var in required_env_vars if not os.getenv(var)]
if missing_vars:
    logger.error(f"Missing environment variables: {', '.join(missing_vars)}")
    sys.exit(1)

# Initialize API clients
try:
    twitter_api = TwitterAPI(bearer_token=os.getenv('TWITTER_BEARER_TOKEN'))
    analysis_api = AnalysisAPI(api_key=os.getenv('GROK_API_KEY'), base_url="https://api.x.ai/v1")
    finnhub_api = FinnhubAPI(api_key=os.getenv('FINNHUB_API_KEY'))
    telegram_api = TelegramAPI(
        bot_token=os.getenv('TELEGRAM_BOT_TOKEN'),
        chat_id=os.getenv('TELEGRAM_CHAT_ID'),
        topic_id=os.getenv('TELEGRAM_TOPIC_ID')
    )
    logger.info("API clients initialized successfully")
except Exception as e:
    logger.error(f"Error initializing API clients: {e}")
    sys.exit(1)

# Define influencers
influencers = [
    'elonmusk', 'michaelsaylor', 'CathieDWood', 'brian_armstrong',
    'cz_binance', 'VitalikButerin', 'APompliano', 'RaoulGMI',
    'chamath', 'garyvee', 'realDonaldTrump'
]

# Load user IDs and processed IDs
user_id_map = load_user_ids()
processed_ids = load_processed_ids()
stats.processed_news_ids = processed_ids['news']
stats.processed_tweet_ids = processed_ids['tweets']

# Resolve user IDs for influencers
user_id_map = twitter_api.resolve_user_ids(influencers, user_id_map)

async def check_tweets():
    """
    Check for new tweets from influencers and process them.
    """
    stats.last_tweet_check = datetime.now(timezone.utc)
    
    for screen_name, user_id in user_id_map.items():
        try:
            logger.info(f"Checking tweets for {screen_name} (ID: {user_id})")
            tweets = twitter_api.get_recent_tweets(user_id, minutes=30)
            logger.info(f"Found {len(tweets)} tweets for {screen_name}")

            if not tweets:
                continue

            for tweet in tweets:
                # Skip already processed tweets
                if str(tweet['id']) in stats.processed_tweet_ids:
                    logger.debug(f"Skipping already processed tweet {tweet['id']} from {screen_name}")
                    continue
                    
                # Add to processed set
                stats.processed_tweet_ids.add(str(tweet['id']))
                stats.tweets_processed += 1
                
                logger.debug(f"Processing tweet {tweet['id']} from {screen_name}")
                analysis = await analysis_api.analyze_text(tweet['text'])

                # Only process if analysis exists and relevant flag is True
                if analysis and analysis['relevant']:
                    stats.tweets_relevant += 1
                    await telegram_api.send_tweet_alert(
                        screen_name=screen_name,
                        tweet_text=tweet['text'],
                        tweet_id=str(tweet['id']),
                        analysis=analysis
                    )
                else:
                    logger.debug(f"Irrelevant tweet skipped: {tweet['id']} (Reason: {'No analysis' if not analysis else 'Not relevant'})")
        except Exception as e:
            logger.error(f"Twitter check error for {screen_name}: {e}", exc_info=True)

async def check_news():
    """
    Check for new news articles and process them.
    """
    stats.last_news_check = datetime.now(timezone.utc)
    categories = ['forex', 'crypto', 'merger']
    
    try:
        for category in categories:
            recent_news = finnhub_api.get_recent_news(category, minutes=5)
            
            if not recent_news:
                continue

            for article in recent_news:
                # Skip already processed articles
                article_id = article.get('id')
                if article_id in stats.processed_news_ids:
                    logger.debug(f"Skipping already processed article {article_id}")
                    continue
                
                # Add the article ID to the processed set before analysis
                stats.processed_news_ids.add(article_id)
                stats.news_processed += 1
                
                # Create analysis text from headline and summary
                analysis_text = f"{article.get('headline', '')} {article.get('summary', '')}"
                analysis = await analysis_api.analyze_text(analysis_text)
                
                # Only process if analysis exists and relevant flag is True
                if analysis and analysis.get('relevant', True):
                    stats.news_relevant += 1
                    await telegram_api.send_news_alert(article, analysis)
                else:
                    logger.debug(f"Irrelevant news skipped: {article.get('headline')} (Reason: {'No analysis' if not analysis else 'Not relevant'})")
    except Exception as e:
        logger.error(f"News check error: {e}", exc_info=True)
    finally:
        # Save processed IDs after each news check
        save_processed_ids(stats.processed_news_ids, stats.processed_tweet_ids)

async def main_async():
    """
    Main async function to run the application.
    """
    # Build Telegram application
    application = telegram_api.build_application()
    
    # Test Telegram connection
    if not await telegram_api.test_connection():
        logger.error("Telegram connection test failed. Exiting.")
        return 1
    
    # Initialize the scheduler
    scheduler = AsyncIOScheduler()
    scheduler.add_job(check_tweets, 'interval', minutes=30)
    scheduler.add_job(check_news, 'interval', minutes=5)
    scheduler.start()
    
    # Start the application without blocking
    await application.initialize()
    await application.start()
    
    try:
        # Keep the application running
        while True:
            await asyncio.sleep(1)
    except (KeyboardInterrupt, SystemExit):
        logger.info("Received signal to terminate")
    finally:
        logger.info("Shutting down scheduler...")
        scheduler.shutdown()
        # Save processed IDs before shutting down
        save_processed_ids(stats.processed_news_ids, stats.processed_tweet_ids)
        # Properly shutdown the application
        await application.stop()
        await application.shutdown()
    
    return 0

def main():
    """
    Main entry point for the application.
    """
    try:
        # Create new event loop
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        # Run the async main function
        exit_code = loop.run_until_complete(main_async())
        
        # Clean up
        loop.close()
        return exit_code
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
        return 0
    except Exception as e:
        logger.error(f"Critical error: {e}", exc_info=True)
        return 1
    finally:
        logger.info("Exiting application")

if __name__ == "__main__":
    sys.exit(main())