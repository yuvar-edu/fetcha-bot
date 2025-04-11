import os
import asyncio
import sys
import logging
import tweepy
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.events import EVENT_JOB_EXECUTED, EVENT_JOB_ERROR, EVENT_JOB_MISSED

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
    start_time = datetime.now(timezone.utc)
    stats.last_tweet_check = start_time
    logger.info("Starting tweet check process")
    
    # Process tweets in batches to avoid long-running operations
    processed_count = 0
    error_count = 0
    max_errors = 3  # Maximum number of consecutive errors before aborting
    rate_limit_errors = 0
    max_rate_limit_errors = 5  # Maximum number of rate limit errors before backing off
    
    try:
        # Randomize the order of influencers to distribute API calls
        import random
        influencer_items = list(user_id_map.items())
        random.shuffle(influencer_items)
        
        for screen_name, user_id in influencer_items:
            if error_count >= max_errors:
                logger.warning(f"Aborting tweet check after {error_count} consecutive errors")
                break
                
            if rate_limit_errors >= max_rate_limit_errors:
                logger.warning(f"Rate limit threshold reached ({rate_limit_errors} errors). Pausing tweet check for this cycle.")
                break
                
            try:
                # Add a variable delay between API calls to different influencers to avoid rate limiting
                # Longer delay as we process more influencers
                delay = random.uniform(3, 6)  # Random delay between 3-6 seconds
                logger.debug(f"Waiting {delay:.1f}s before checking tweets for {screen_name}")
                await asyncio.sleep(delay)
                
                logger.info(f"Checking tweets for {screen_name} (ID: {user_id})")
                tweets = twitter_api.get_recent_tweets(user_id, minutes=60)
                logger.info(f"Found {len(tweets)} tweets for {screen_name}")
                error_count = 0  # Reset error count on success

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
                    processed_count += 1
                    
                    logger.debug(f"Processing tweet {tweet['id']} from {screen_name}")
                    analysis = await analysis_api.analyze_text(tweet['text'])

                    # Only process if analysis exists and relevant flag is True
                    if analysis and analysis.get('relevant', False):
                        stats.tweets_relevant += 1
                        await telegram_api.send_tweet_alert(
                            screen_name=screen_name,
                            tweet_text=tweet['text'],
                            tweet_id=str(tweet['id']),
                            analysis=analysis
                        )
                    else:
                        logger.debug(f"Irrelevant tweet skipped: {tweet['id']} (Reason: {'No analysis' if not analysis else 'Not relevant'})")
            except tweepy.TooManyRequests:
                # Specific handling for rate limit errors
                rate_limit_errors += 1
                error_count += 1
                logger.warning(f"Rate limit error for {screen_name}. Total rate limit errors: {rate_limit_errors}/{max_rate_limit_errors}")
                # Add an additional delay after hitting rate limit
                await asyncio.sleep(random.uniform(5, 10))
            except Exception as e:
                error_count += 1
                logger.error(f"Twitter check error for {screen_name}: {e}", exc_info=True)
                
        # Save processed IDs after each tweet check
        save_processed_ids(stats.processed_news_ids, stats.processed_tweet_ids)
        
        elapsed_time = (datetime.now(timezone.utc) - start_time).total_seconds()
        logger.info(f"Tweet check completed in {elapsed_time:.2f} seconds. Processed {processed_count} tweets.")
    except Exception as e:
        logger.error(f"Critical error in tweet check process: {e}", exc_info=True)

async def check_news():
    """
    Check for new news articles and process them.
    """
    stats.last_news_check = datetime.now(timezone.utc)
    categories = ['forex', 'crypto', 'merger']
    
    try:
        for category in categories:
            recent_news = finnhub_api.get_recent_news(category, minutes=60)
            
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
        
    # Log available commands
    logger.info("Available Telegram commands: /stats")
    from telegram import BotCommand
    await application.bot.set_my_commands([BotCommand("stats", "Display monitoring statistics")])
    
    # Initialize the scheduler with misfire handling
    scheduler = AsyncIOScheduler(
        job_defaults={
            'coalesce': True,  # Combine multiple missed executions into one
            'max_instances': 1,  # Only allow one instance of each job to run at a time
            'misfire_grace_time': 60  # Allow jobs to be executed up to 60 seconds late
        }
    )
    
    # Add event listeners for scheduler events
    def job_executed_event(event):
        logger.info(f"Job '{event.job_id}' executed successfully")
        
    def job_error_event(event):
        logger.error(f"Job '{event.job_id}' raised an exception: {event.exception}")
        logger.error(f"Traceback: {event.traceback}")
        
    def job_missed_event(event):
        logger.warning(f"Job '{event.job_id}' missed its execution time")
        
    scheduler.add_listener(job_executed_event, EVENT_JOB_EXECUTED)
    scheduler.add_listener(job_error_event, EVENT_JOB_ERROR)
    scheduler.add_listener(job_missed_event, EVENT_JOB_MISSED)
    
    # Add jobs with IDs for better tracking
    scheduler.add_job(check_tweets, 'interval', minutes=30, id='check_tweets')
    scheduler.add_job(check_news, 'interval', minutes=5, id='check_news')  # Hit Finnhub API every 5 minutes
    scheduler.start()
    
    # Run jobs immediately after startup to verify they're working
    logger.info("Running initial checks...")
    asyncio.create_task(check_tweets())  # Run tweet check immediately
    asyncio.create_task(check_news())    # Run news check immediately
    
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