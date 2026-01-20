"""
Redis caching service for discount rules.

Caches active discount rules (not per-user) for scalability.
Only 2 cache entries needed regardless of number of users:
- All active discount rules
- Loyalty-only discount rules (subset)
"""
import logging
from typing import Optional, List

from django.conf import settings
from django.core.cache import cache

logger = logging.getLogger(__name__)

# Cache keys - only 2 entries needed!
ACTIVE_RULES_CACHE_KEY = 'discount_rules:active'
LOYALTY_RULES_CACHE_KEY = 'discount_rules:loyalty'

# Cache timeout: 5 minutes
CACHE_TIMEOUT = getattr(settings, 'USER_DISCOUNT_CACHE_TIMEOUT', 300)


def get_cached_active_discount_rule_ids() -> Optional[List[str]]:
    """
    Get cached IDs of all active discount rules.
    
    Returns:
        List of discount rule IDs if cached, None otherwise
    """
    try:
        cached_ids = cache.get(ACTIVE_RULES_CACHE_KEY)
        if cached_ids is not None:
            logger.debug("Cache HIT for active discount rules")
            return cached_ids
        logger.debug("Cache MISS for active discount rules")
        return None
    except Exception as e:
        logger.error(f"Cache read error: {str(e)}")
        return None


def get_cached_loyalty_discount_rule_ids() -> Optional[List[str]]:
    """
    Get cached IDs of loyalty-only discount rules.
    
    Returns:
        List of loyalty discount rule IDs if cached, None otherwise
    """
    try:
        cached_ids = cache.get(LOYALTY_RULES_CACHE_KEY)
        if cached_ids is not None:
            logger.debug("Cache HIT for loyalty discount rules")
            return cached_ids
        logger.debug("Cache MISS for loyalty discount rules")
        return None
    except Exception as e:
        logger.error(f"Cache read error: {str(e)}")
        return None


def cache_active_discount_rule_ids(rule_ids: List[str]) -> bool:
    """
    Cache IDs of all active discount rules.
    
    Args:
        rule_ids: List of active discount rule IDs
        
    Returns:
        True if cached successfully
    """
    try:
        cache.set(ACTIVE_RULES_CACHE_KEY, rule_ids, timeout=CACHE_TIMEOUT)
        logger.debug(f"Cached {len(rule_ids)} active discount rules")
        return True
    except Exception as e:
        logger.error(f"Cache write error: {str(e)}")
        return False


def cache_loyalty_discount_rule_ids(rule_ids: List[str]) -> bool:
    """
    Cache IDs of loyalty-only discount rules.
    
    Args:
        rule_ids: List of loyalty discount rule IDs
        
    Returns:
        True if cached successfully
    """
    try:
        cache.set(LOYALTY_RULES_CACHE_KEY, rule_ids, timeout=CACHE_TIMEOUT)
        logger.debug(f"Cached {len(rule_ids)} loyalty discount rules")
        return True
    except Exception as e:
        logger.error(f"Cache write error: {str(e)}")
        return False


def invalidate_discount_cache() -> bool:
    """
    Clear all discount caches.
    
    Call this when discount rules are created/updated/deleted.
    Only deletes 2 cache entries regardless of user count.
    """
    try:
        cache.delete(ACTIVE_RULES_CACHE_KEY)
        cache.delete(LOYALTY_RULES_CACHE_KEY)
        logger.info("Discount rule cache invalidated")
        return True
    except Exception as e:
        logger.error(f"Cache invalidation error: {str(e)}")
        return False


# Alias for backward compatibility
def invalidate_all_discount_caches() -> bool:
    """Alias for invalidate_discount_cache."""
    return invalidate_discount_cache()

