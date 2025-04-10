from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Set

@dataclass
class Stats:
    """
    Class to track statistics about processed tweets and news.
    """
    tweets_processed: int = 0
    tweets_relevant: int = 0
    news_processed: int = 0
    news_relevant: int = 0
    last_tweet_check: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    last_news_check: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    last_news_id: int = 0
    processed_news_ids: Set[str] = field(default_factory=set)
    processed_tweet_ids: Set[str] = field(default_factory=set)

# Create a global stats instance
stats = Stats()