import logging
import finnhub
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any

class FinnhubAPI:
    def __init__(self, api_key: str):
        """
        Initialize the Finnhub API client.
        
        Args:
            api_key: Finnhub API key
        """
        self.client = finnhub.Client(api_key=api_key)
        self.logger = logging.getLogger(__name__)
    
    def get_recent_news(self, category: str, minutes: int = 5) -> List[Dict[str, Any]]:
        """
        Get recent news from Finnhub.
        
        Args:
            category: News category (e.g., 'forex', 'crypto', 'merger')
            minutes: Number of minutes to look back
            
        Returns:
            List of news article objects
        """
        try:
            # Get timestamp from specified minutes ago
            from_time = int((datetime.now(timezone.utc) - timedelta(minutes=minutes)).timestamp())
            
            self.logger.info(f"Fetching {category} news from Finnhub from the last {minutes} minutes")
            news = self.client.general_news(category)
            self.logger.debug(f"Received {len(news)} {category} news articles from Finnhub")

            if not news:
                self.logger.debug(f"No new {category} articles found")
                return []

            # Filter news to only include those from the specified time period
            recent_news = [
                article for article in news 
                if article.get('datetime', 0) >= from_time
            ]
            
            self.logger.info(f"Found {len(recent_news)} new {category} articles from the last {minutes} minutes")
            
            if not recent_news:
                return []

            # Sort news by datetime to process newest first
            recent_news.sort(key=lambda x: x.get('datetime', 0), reverse=True)
            return recent_news
            
        except Exception as e:
            self.logger.error(f"Error fetching {category} news: {e}", exc_info=True)
            return []