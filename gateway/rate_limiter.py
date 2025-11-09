"""Rate limiting for Gateway."""
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from typing import Dict, Tuple
from collections import defaultdict, deque
from fastapi import HTTPException, status

from shared.config import settings
from .auth import APIKeyInfo


class RateLimiter:
    """In-memory rate limiter with sliding window."""

    def __init__(self):
        # Store request timestamps per user
        # Format: {user_id: deque([timestamp1, timestamp2, ...])}
        self.request_history: Dict[str, deque] = defaultdict(deque)

    def get_tier_limits(self, tier: str) -> Tuple[int, int]:
        """Get rate limits for a tier."""
        if tier == "premium":
            return (
                settings.rate_limit_premium_per_minute,
                settings.rate_limit_premium_per_hour,
            )
        elif tier == "standard":
            return (
                settings.rate_limit_standard_per_minute,
                settings.rate_limit_standard_per_hour,
            )
        else:  # free
            return (
                settings.rate_limit_free_per_minute,
                settings.rate_limit_free_per_hour,
            )

    def check_rate_limit(self, user_info: APIKeyInfo) -> None:
        """
        Check if user has exceeded rate limits.

        Args:
            user_info: User information including tier

        Raises:
            HTTPException: If rate limit exceeded
        """
        requests_per_minute, requests_per_hour = self.get_tier_limits(user_info.tier)
        user_id = user_info.user_id

        current_time = time.time()

        # Get user's request history
        history = self.request_history[user_id]

        # Remove old timestamps outside the hour window
        one_hour_ago = current_time - 3600
        while history and history[0] < one_hour_ago:
            history.popleft()

        # Check hourly limit
        if len(history) >= requests_per_hour:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Rate limit exceeded. Maximum {requests_per_hour} requests per hour allowed for tier '{user_info.tier}'.",
                headers={
                    "X-RateLimit-Limit-Hour": str(requests_per_hour),
                    "X-RateLimit-Remaining-Hour": "0",
                    "Retry-After": str(int(3600 - (current_time - history[0]))),
                },
            )

        # Check per-minute limit
        one_minute_ago = current_time - 60
        recent_requests = sum(1 for ts in history if ts >= one_minute_ago)

        if recent_requests >= requests_per_minute:
            # Find when the oldest request in the current minute will expire
            oldest_in_window = next(ts for ts in history if ts >= one_minute_ago)
            retry_after = int(60 - (current_time - oldest_in_window)) + 1

            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Rate limit exceeded. Maximum {requests_per_minute} requests per minute allowed for tier '{user_info.tier}'.",
                headers={
                    "X-RateLimit-Limit-Minute": str(requests_per_minute),
                    "X-RateLimit-Remaining-Minute": "0",
                    "Retry-After": str(retry_after),
                },
            )

        # Record this request
        history.append(current_time)

    def get_rate_limit_status(self, user_info: APIKeyInfo) -> Tuple[int, int, int, int]:
        """
        Get current rate limit status for a user.

        Returns:
            Tuple of (minute_limit, minute_remaining, hour_limit, hour_remaining)
        """
        requests_per_minute, requests_per_hour = self.get_tier_limits(user_info.tier)
        user_id = user_info.user_id

        current_time = time.time()
        history = self.request_history[user_id]

        # Count requests in last minute
        one_minute_ago = current_time - 60
        recent_requests = sum(1 for ts in history if ts >= one_minute_ago)

        # Count requests in last hour
        one_hour_ago = current_time - 3600
        hourly_requests = sum(1 for ts in history if ts >= one_hour_ago)

        return (
            requests_per_minute,
            max(0, requests_per_minute - recent_requests),
            requests_per_hour,
            max(0, requests_per_hour - hourly_requests),
        )
