import logging
from typing import Dict, Any
from telegram import Update, constants
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from telegram.helpers import escape_markdown

from utils.stats import stats

class TelegramAPI:
    def __init__(self, bot_token: str, chat_id: str, topic_id: str = None):
        """
        Initialize the Telegram API client.
        
        Args:
            bot_token: Telegram bot token
            chat_id: Telegram chat ID
            topic_id: Telegram topic ID (optional)
        """
        self.bot_token = bot_token
        self.chat_id = chat_id
        self.topic_id = topic_id
        self.application = None
        self.logger = logging.getLogger(__name__)
    
    def build_application(self):
        """
        Build the Telegram application and add command handlers.
        
        Returns:
            The Telegram application
        """
        self.application = ApplicationBuilder().token(self.bot_token).build()
        self.application.add_handler(CommandHandler("stats", self.stats_command))
        return self.application
    
    async def stats_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        Handle the /stats command.
        
        Args:
            update: Telegram update object
            context: Telegram context object
        """
        message = (
            f"📊 *Monitoring Statistics*\n"
            f"```\n"
            f"Tweets Processed: {stats.tweets_processed}\n"
            f"Tweets Relevant: {stats.tweets_relevant}\n"
            f"News Processed: {stats.news_processed}\n"
            f"News Relevant: {stats.news_relevant}\n"
            f"Last Tweet Check: {stats.last_tweet_check.strftime('%Y-%m-%d %H:%M:%S UTC')}\n"
            f"Last News Check: {stats.last_news_check.strftime('%Y-%m-%d %H:%M:%S UTC')}\n"
            f"```"
        )
        await update.message.reply_text(
            text=message,
            parse_mode=constants.ParseMode.MARKDOWN_V2
        )
    
    async def send_tweet_alert(self, screen_name: str, tweet_text: str, tweet_id: str, analysis: Dict[str, Any]):
        """
        Send a tweet alert to Telegram.
        
        Args:
            screen_name: Twitter screen name
            tweet_text: Tweet text
            tweet_id: Tweet ID
            analysis: Analysis results
        """
        try:
            safe_screen_name = escape_markdown(screen_name, version=2)
            safe_text = escape_markdown(tweet_text, version=2)
            safe_sentiment = escape_markdown(analysis['sentiment'], version=2)
            safe_impact = escape_markdown(analysis['impact'], version=2)
            safe_direction = escape_markdown(analysis['direction'], version=2)
            safe_assets = escape_markdown(', '.join(analysis['assets']), version=2)
            tweet_url = f"https://twitter.com/{screen_name}/status/{tweet_id}"
            safe_tweet_url = escape_markdown(tweet_url, version=2)

            # Properly escape the score value with parentheses
            score_text = f"{analysis['score']}/10"
            safe_score_text = escape_markdown(score_text, version=2)

            message = (
                f"🚨 Market Alert\n"
                f"👤 {safe_screen_name}\n"
                f"💬 {safe_text}\n\n"
                f"📈 Sentiment: {safe_sentiment} \\({safe_score_text}\\)\n"
                f"💥 Impact: {safe_impact}\n"
                f"🔮 Direction: {safe_direction}\n"
                f"💰 Assets: {safe_assets}\n"
                f"🔗 View Tweet: {safe_tweet_url}"
            )
            
            await self.application.bot.send_message(
                chat_id=self.chat_id,
                text=message,
                parse_mode=constants.ParseMode.MARKDOWN_V2,
                message_thread_id=self.topic_id,
                disable_web_page_preview=True
            )
            self.logger.info(f"Market tweet alert sent: {tweet_id}")
            return True
        except Exception as e:
            self.logger.error(f"Telegram send error: {e}", exc_info=True)
            return False
    
    async def send_news_alert(self, article: Dict[str, Any], analysis: Dict[str, Any]):
        """
        Send a news alert to Telegram.
        
        Args:
            article: News article object
            analysis: Analysis results
        """
        try:
            safe_source = escape_markdown(article.get('source', 'Unknown'), version=2)
            safe_headline = escape_markdown(article.get('headline', ''), version=2)
            safe_url = escape_markdown(article.get('url', ''), version=2)
            safe_sentiment = escape_markdown(analysis['sentiment'], version=2)
            safe_impact = escape_markdown(analysis['impact'], version=2)
            safe_direction = escape_markdown(analysis['direction'], version=2)
            safe_assets = escape_markdown(', '.join(analysis['assets']), version=2)
            
            # Properly escape the score value with parentheses
            score_text = f"{analysis['score']}/10"
            safe_score_text = escape_markdown(score_text, version=2)

            message = (
                f"📰 Market News\n"
                f"📌 {safe_source}\n"
                f"🚨 {safe_headline}\n\n"
                f"📈 Sentiment: {safe_sentiment} \\({safe_score_text}\\)\n"
                f"💥 Impact: {safe_impact}\n"
                f"🔮 Direction: {safe_direction}\n"
                f"💰 Assets: {safe_assets}\n"
                f"🔗 Read more: {safe_url}"
            )
            
            await self.application.bot.send_message(
                chat_id=self.chat_id,
                text=message,
                parse_mode=constants.ParseMode.MARKDOWN_V2,
                message_thread_id=self.topic_id,
                disable_web_page_preview=True
            )
            self.logger.info(f"Market news alert sent: {article.get('url')}")
            return True
        except Exception as e:
            self.logger.error(f"Telegram send error: {e}", exc_info=True)
            return False
    
    async def test_connection(self):
        """
        Test the Telegram connection by getting bot info.
        
        Returns:
            True if connection is successful, False otherwise
        """
        try:
            # Actually test the connection by getting bot info
            bot_info = await self.application.bot.getMe()
            self.logger.info(f"Successfully connected to Telegram as @{bot_info.username}")
            return True
        except Exception as e:
            self.logger.error("Telegram connection failed. Check your credentials and chat ID.")
            self.logger.error(str(e))
            return False