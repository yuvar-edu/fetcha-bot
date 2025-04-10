import logging
import tweepy
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, List, Optional

from utils.stats import stats
from utils.data import save_user_ids

class TwitterAPI:
    def __init__(self, bearer_token: str):
        """
        Initialize the Twitter API client.
        
        Args:
            bearer_token: Twitter API bearer token
        """
        self.client = tweepy.Client(bearer_token=bearer_token)
        self.logger = logging.getLogger(__name__)
    
    def get_user_id(self, screen_name: str) -> Optional[int]:
        """
        Get the user ID for a Twitter screen name.
        
        Args:
            screen_name: Twitter screen name/handle
            
        Returns:
            User ID as an integer, or None if not found
        """
        try:
            user = self.client.get_user(username=screen_name)
            if user and user.data:
                self.logger.info(f"Resolved {screen_name} to user ID {user.data.id}")
                return user.data.id
            return None
        except Exception as e:
            self.logger.error(f"Error fetching user ID for {screen_name}: {e}")
            return None
    
    def resolve_user_ids(self, screen_names: List[str], user_id_map: Dict[str, int]) -> Dict[str, int]:
        """
        Resolve Twitter screen names to user IDs and update the mapping.
        
        Args:
            screen_names: List of Twitter screen names
            user_id_map: Existing mapping of screen names to user IDs
            
        Returns:
            Updated mapping of screen names to user IDs
        """
        for screen_name in screen_names:
            if screen_name not in user_id_map:
                user_id = self.get_user_id(screen_name)
                if user_id:
                    user_id_map[screen_name] = user_id
        
        # Save the updated mapping
        save_user_ids(user_id_map)
        return user_id_map
    
    def get_recent_tweets(self, user_id: int, minutes: int = 30) -> List[Dict[str, Any]]:
        """
        Get recent tweets from a user.
        
        Args:
            user_id: Twitter user ID
            minutes: Number of minutes to look back
            
        Returns:
            List of tweet objects
        """
        try:
            start_time = (datetime.now(timezone.utc) - timedelta(minutes=minutes)).isoformat(timespec='seconds') + "Z"
            
            tweets = self.client.get_users_tweets(
                id=user_id,
                max_results=5,
                start_time=start_time,
                tweet_fields=['created_at', 'id', 'text']
            )
            
            if not tweets.data:
                return []
                
            return [{
                'id': tweet.id,
                'text': tweet.text,
                'created_at': tweet.created_at
            } for tweet in tweets.data]
            
        except Exception as e:
            self.logger.error(f"Error fetching tweets for user ID {user_id}: {e}")
            return []