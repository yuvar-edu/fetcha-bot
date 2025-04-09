import time
from datetime import datetime
from typing import Dict, Optional

class RateLimiter:
    def __init__(self):
        self.requests: Dict[str, list] = {}
        self.rate_limits: Dict[str, Dict] = {
            'twitter': {
                'window': 900,  # 15 minutes in seconds
                'max_requests': 180,  # Twitter's standard rate limit
                'remaining': 180
            },
            'finnhub': {
                'window': 60,  # 1 minute in seconds
                'max_requests': 60,  # Finnhub's actual API limit (60/min)
                'remaining': 30
            },
            'grok': {
                'window': 60,  # 1 minute in seconds
                'max_requests': 60,  # Adjust based on your Grok API limits
                'remaining': 60
            }
        }
        self.last_reset: Dict[str, float] = {}

    def _cleanup_old_requests(self, api: str) -> None:
        """Remove requests outside the current window."""
        now = time.time()
        window = self.rate_limits[api]['window']
        self.requests[api] = [req for req in self.requests.get(api, []) if now - req < window]

    def _should_reset_window(self, api: str) -> bool:
        """Check if the rate limit window should be reset."""
        now = time.time()
        if api not in self.last_reset:
            self.last_reset[api] = now
            return True
        
        window = self.rate_limits[api]['window']
        if now - self.last_reset[api] >= window:
            self.last_reset[api] = now
            return True
        return False

    def update_rate_limit(self, api: str, remaining: Optional[int] = None, reset_time: Optional[int] = None) -> None:
        """Update rate limit information from API responses."""
        if api in self.rate_limits:
            if remaining is not None:
                self.rate_limits[api]['remaining'] = remaining
            if reset_time is not None:
                self.last_reset[api] = reset_time

    async def check_rate_limit(self, api: str) -> tuple[bool, float]:
        """Check if we can make a request to the specified API.
        
        Returns:
            tuple: (can_request, wait_time)
            - can_request: bool indicating if request can be made
            - wait_time: seconds to wait if can_request is False
        """
        now = time.time()
        if api not in self.requests:
            self.requests[api] = []

        # Reset window if expired
        window_end = self.last_reset.get(api, 0) + self.rate_limits[api]['window']
        if now > window_end:
            self.rate_limits[api]['remaining'] = self.rate_limits[api]['max_requests']
            self.last_reset[api] = now

        if self.rate_limits[api]['remaining'] <= 0:
            base_wait = window_end - now
            jitter = base_wait * random.uniform(0.1, 0.3)
            return False, max(base_wait + jitter, 0)

        # Log successful check
        self.requests[api].append(now)
        self.rate_limits[api]['remaining'] -= 1
        return True, 0

    def update_from_headers(self, api: str, headers: dict) -> None:
        """Update rate limits from API response headers"""
        if 'x-rate-limit-remaining' in headers:
            self.rate_limits[api]['remaining'] = int(headers['x-rate-limit-remaining'])
        if 'x-rate-limit-reset' in headers:
            self.last_reset[api] = int(headers['x-rate-limit-reset'])

    def get_remaining_requests(self, api: str) -> int:
        """Get remaining requests for the specified API."""
        return self.rate_limits[api]['remaining']

    def log_request(self, api: str) -> None:
        """Log a request to the specified API."""
        now = time.time()
        if api not in self.requests:
            self.requests[api] = []
        self.requests[api].append(now)
        self.rate_limits[api]['remaining'] = max(0, self.rate_limits[api]['remaining'] - 1)

    def print_status(self, api: str) -> None:
        """Print current rate limit status for debugging."""
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] "
              f"{api.title()} API Status: "
              f"Remaining: {self.get_remaining_requests(api)}, "
              f"Requests in window: {len(self.requests.get(api, []))}\n"
              f"Next reset timestamp: {self.last_reset.get(api, 0) + self.rate_limits[api]['window']}")