import logging
import tweepy
import time
import random
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, List, Optional, Deque
from collections import deque

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
        
        # Initialize request tracking for rate limiting
        self._request_timestamps: Deque[float] = deque(maxlen=100)  # Track last 100 requests
        self._window_size = 15 * 60  # 15 minutes in seconds (Twitter's standard window)
        self._max_requests_per_window = 300  # Default limit for most Twitter endpoints
        self._min_request_interval = 1.0  # Minimum seconds between requests
    
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
    
    # Store rate limit information per endpoint
    _rate_limits = {}
    
    def _update_rate_limit_info(self, response):
        """
        Update rate limit information from response headers.
        
        Args:
            response: Tweepy response object with headers
        """
        if not hasattr(response, '_headers') or not response._headers:
            return
            
        headers = response._headers
        endpoint = 'users_tweets'  # Default endpoint name
        
        # Extract rate limit information from headers
        limit = headers.get('x-rate-limit-limit')
        remaining = headers.get('x-rate-limit-remaining')
        reset = headers.get('x-rate-limit-reset')
        
        if limit and remaining and reset:
            self._rate_limits[endpoint] = {
                'limit': int(limit),
                'remaining': int(remaining),
                'reset': int(reset),
                'reset_time': datetime.fromtimestamp(int(reset), tz=timezone.utc)
            }
            
            # Log rate limit information
            reset_time = datetime.fromtimestamp(int(reset), tz=timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')
            self.logger.debug(f"Rate limit for {endpoint}: {remaining}/{limit} remaining, resets at {reset_time}")
            
            # Update max requests per window based on actual limit
            if int(limit) > 0:
                self._max_requests_per_window = int(limit)
    
    def _track_request(self):
        """
        Track a new API request and enforce rate limiting if needed.
        
        Returns:
            float: Time slept in seconds to respect rate limits (0 if no sleep needed)
        """
        now = time.time()
        
        # Clean up old timestamps outside the window
        window_start = now - self._window_size
        while self._request_timestamps and self._request_timestamps[0] < window_start:
            self._request_timestamps.popleft()
        
        # Check if we're approaching the rate limit
        if len(self._request_timestamps) >= self._max_requests_per_window * 0.9:  # 90% of limit
            # Calculate time until oldest request falls out of window
            if self._request_timestamps:
                sleep_time = max(0, self._window_size - (now - self._request_timestamps[0]))
                if sleep_time > 0:
                    self.logger.warning(f"Approaching rate limit, sleeping for {sleep_time:.2f}s")
                    time.sleep(sleep_time)
                    now = time.time()  # Update current time after sleep
        
        # Enforce minimum interval between requests
        if self._request_timestamps:
            last_request = self._request_timestamps[-1]
            elapsed = now - last_request
            if elapsed < self._min_request_interval:
                sleep_time = self._min_request_interval - elapsed
                time.sleep(sleep_time)
                now = time.time()  # Update current time after sleep
        
        # Add current timestamp to the queue
        self._request_timestamps.append(now)
        return now
    
    def get_recent_tweets(self, user_id: int, minutes: int = 30) -> List[Dict[str, Any]]:
        """
        Get recent tweets from a user with improved rate limit handling.
        
        Args:
            user_id: Twitter user ID
            minutes: Number of minutes to look back
            
        Returns:
            List of tweet objects
        """
        max_retries = 3
        base_delay = 2  # Initial delay in seconds
        attempt = 0
        endpoint = 'users_tweets'
        
        # Check if we're already at the rate limit
        if endpoint in self._rate_limits:
            rate_info = self._rate_limits[endpoint]
            if rate_info['remaining'] == 0:
                now = datetime.now(timezone.utc)
                if now < rate_info['reset_time']:
                    wait_seconds = (rate_info['reset_time'] - now).total_seconds() + 1  # Add 1 second buffer
                    self.logger.warning(f"Rate limit already exhausted for user ID {user_id}, waiting until reset: {rate_info['reset_time'].strftime('%H:%M:%S')} ({wait_seconds:.1f}s)")
                    time.sleep(wait_seconds)
        
        while attempt < max_retries:
            try:
                # Track this request and potentially wait to respect rate limits
                self._track_request()
                
                # Format the start_time in RFC3339 format without the extra Z
                start_time = (datetime.now(timezone.utc) - timedelta(minutes=minutes)).isoformat(timespec='seconds')
                
                self.logger.debug(f"Making Twitter API request for user_id={user_id}, window_requests={len(self._request_timestamps)}")
                tweets = self.client.get_users_tweets(
                    id=user_id,
                    max_results=5,
                    start_time=start_time,
                    tweet_fields=['created_at', 'id', 'text']
                )
                
                # Update rate limit information from response
                self._update_rate_limit_info(tweets)
                
                if not tweets.data:
                    return []
                    
                return [{
                    'id': tweet.id,
                    'text': tweet.text,
                    'created_at': tweet.created_at
                } for tweet in tweets.data]
                
            except tweepy.TooManyRequests as e:
                attempt += 1
                
                # Try to extract rate limit reset time from the exception
                reset_time = None
                if hasattr(e, 'response') and hasattr(e.response, 'headers'):
                    reset_timestamp = e.response.headers.get('x-rate-limit-reset')
                    if reset_timestamp:
                        reset_time = datetime.fromtimestamp(int(reset_timestamp), tz=timezone.utc)
                        
                        # Update our rate limit tracking
                        if endpoint not in self._rate_limits:
                            self._rate_limits[endpoint] = {}
                        self._rate_limits[endpoint]['remaining'] = 0
                        self._rate_limits[endpoint]['reset_time'] = reset_time
                
                if attempt >= max_retries:
                    if reset_time:
                        self.logger.error(f"Rate limit exceeded for user ID {user_id}. Reset at {reset_time.strftime('%Y-%m-%d %H:%M:%S UTC')}")
                    else:
                        self.logger.error(f"Rate limit exceeded for user ID {user_id} after {max_retries} attempts")
                    return []
                
                # Calculate wait time with exponential backoff and jitter
                wait_time = base_delay * (2 ** (attempt - 1))
                jitter = random.uniform(0.5, 1.5)  # Add 50% jitter in either direction
                wait_time = wait_time * jitter
                
                # If we have reset time information, use that instead if it's sooner
                if reset_time:
                    seconds_until_reset = (reset_time - datetime.now(timezone.utc)).total_seconds() + 1
                    wait_time = min(wait_time, max(1, seconds_until_reset))  # At least 1 second wait
                    self.logger.warning(f"Rate limit hit for user ID {user_id}, waiting {wait_time:.1f}s until reset at {reset_time.strftime('%H:%M:%S')} (attempt {attempt}/{max_retries})")
                else:
                    self.logger.warning(f"Rate limit hit for user ID {user_id}, retrying in {wait_time:.1f}s (attempt {attempt}/{max_retries})")
                
                time.sleep(wait_time)
                
            except Exception as e:
                self.logger.error(f"Error fetching tweets for user ID {user_id}: {e}")
                return []