# backend/app/middleware/rate_limiter.py

import logging
import time
from functools import wraps
from flask import request, jsonify, g
from app.extensions import redis_client

logger = logging.getLogger(__name__)


# ── helpers ───────────────────────────────────────────────────────────────────

def _err(msg: str, status: int = 429):
    return jsonify({"success": False, "error": msg}), status


def _get_identifier() -> str:
    """
    Uses authenticated user ID if available (set by jwt_required_with_user),
    falls back to IP address for unauthenticated routes.
    """
    user = getattr(g, "current_user", None)
    if user:
        return f"user:{user.id}"
    return f"ip:{request.remote_addr}"


def _sliding_window_check(key: str, limit: int, window_seconds: int) -> tuple[bool, int, int]:
    """
    Sliding window rate limit using Redis sorted sets.

    Returns:
        allowed  (bool)   — whether the request should proceed
        remaining (int)   — requests left in the current window
        retry_after (int) — seconds until the oldest request expires (0 if allowed)
    """
    if redis_client is None:
        # Redis not configured — fail open
        return True, limit, 0

    now = time.time()
    window_start = now - window_seconds

    pipe = redis_client.pipeline()
    # Remove timestamps outside the window
    pipe.zremrangebyscore(key, 0, window_start)
    # Count remaining in window
    pipe.zcard(key)
    # Add current request timestamp
    pipe.zadd(key, {str(now): now})
    # Set expiry so keys clean themselves up
    pipe.expire(key, window_seconds + 10)

    results = pipe.execute()
    current_count = results[1]          # count BEFORE adding this request

    if current_count >= limit:
        # Find when the oldest entry will expire
        oldest = redis_client.zrange(key, 0, 0, withscores=True)
        retry_after = int(window_seconds - (now - oldest[0][1])) + 1 if oldest else window_seconds
        # Undo the zadd we just did — request is rejected
        redis_client.zrem(key, str(now))
        return False, 0, retry_after

    remaining = limit - current_count - 1
    return True, remaining, 0


# ── main decorator ────────────────────────────────────────────────────────────

def rate_limit(limit: int = 60, window: int = 60, scope: str = "default"):
    """
    Sliding-window rate limiter decorator.

    Args:
        limit  — max requests allowed in the window
        window — window size in seconds
        scope  — logical name for the limit bucket (e.g. "auth", "voice", "ai")

    Usage:
        @rate_limit(limit=5, window=60, scope="auth")
        def login(): ...
    """
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            identifier = _get_identifier()
            key = f"rl:{scope}:{identifier}"

            try:
                allowed, remaining, retry_after = _sliding_window_check(key, limit, window)
            except Exception as exc:
                # Redis failure → fail open (don't block legitimate traffic)
                logger.error("rate_limiter Redis error: %s — failing open", exc)
                return fn(*args, **kwargs)

            if not allowed:
                logger.warning("Rate limit hit: %s on scope=%s", identifier, scope)
                response = _err(
                    f"Too many requests. Try again in {retry_after}s."
                )
                response[0].headers["Retry-After"] = str(retry_after)
                response[0].headers["X-RateLimit-Limit"] = str(limit)
                response[0].headers["X-RateLimit-Remaining"] = "0"
                response[0].headers["X-RateLimit-Window"] = str(window)
                return response

            result = fn(*args, **kwargs)

            # Attach headers to successful responses
            try:
                result[0].headers["X-RateLimit-Limit"] = str(limit)
                result[0].headers["X-RateLimit-Remaining"] = str(remaining)
                result[0].headers["X-RateLimit-Window"] = str(window)
            except Exception:
                pass     # result may not be a tuple in all cases

            return result
        return wrapper
    return decorator


# ── preset limiters for reuse across blueprints ───────────────────────────────

def auth_limit(fn):
    """5 requests / 60s — login, register, password change."""
    return rate_limit(limit=5, window=60, scope="auth")(fn)


def voice_limit(fn):
    """30 requests / 60s — voice/STT/TTS endpoints."""
    return rate_limit(limit=30, window=60, scope="voice")(fn)


def ai_limit(fn):
    """20 requests / 60s — LLM chat endpoints."""
    return rate_limit(limit=20, window=60, scope="ai")(fn)


def memory_limit(fn):
    """40 requests / 60s — memory read/write."""
    return rate_limit(limit=40, window=60, scope="memory")(fn)


def tools_limit(fn):
    """30 requests / 60s — tools endpoints."""
    return rate_limit(limit=30, window=60, scope="tools")(fn)


def strict_limit(fn):
    """3 requests / 60s — sensitive ops like account deletion."""
    return rate_limit(limit=3, window=60, scope="strict")(fn)


# ── global rate limiter (register on app) ─────────────────────────────────────

def init_rate_limiter(app):
    """
    Registers a before_request hook for a hard global cap per IP.
    Call this inside create_app() after all blueprints are registered.

    Global cap: 200 requests / 60s per IP (DDoS baseline protection).
    """
    @app.before_request
    def global_limit():
        ip  = request.remote_addr
        key = f"rl:global:{ip}"

        try:
            allowed, _, retry_after = _sliding_window_check(key, limit=200, window_seconds=60)
        except Exception as exc:
            logger.error("global rate_limiter Redis error: %s — failing open", exc)
            return None     # allow

        if not allowed:
            logger.warning("Global rate limit hit: IP %s", ip)
            resp = _err("Global rate limit exceeded. Slow down.")
            resp[0].headers["Retry-After"] = str(retry_after)
            return resp

        return None         # allow