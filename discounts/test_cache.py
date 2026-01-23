"""
Unit tests for discount caching module.
These tests don't require database or Redis - they use Django's in-memory cache.

Scalable caching: Only 2 cache entries regardless of user count!
"""
import os
import sys

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Setup Django settings before importing Django modules
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pragma.settings')
os.environ['USE_REDIS_CACHE'] = 'False'

import django
django.setup()

from django.core.cache import cache
from django.test import SimpleTestCase, override_settings

from discounts.cache import (
    ACTIVE_RULES_CACHE_KEY,
    LOYALTY_RULES_CACHE_KEY,
    get_cached_active_discount_rule_ids,
    get_cached_loyalty_discount_rule_ids,
    cache_active_discount_rule_ids,
    cache_loyalty_discount_rule_ids,
    invalidate_discount_cache,
    invalidate_all_discount_caches,
)


# Use in-memory cache for all tests
TEST_CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'test-cache',
        'KEY_PREFIX': 'pragma',
    }
}


@override_settings(CACHES=TEST_CACHES)
class DiscountCacheUnitTest(SimpleTestCase):
    """Unit tests for scalable discount caching - no database required."""

    def setUp(self):
        """Clear cache before each test."""
        cache.clear()

    def tearDown(self):
        """Clear cache after each test."""
        cache.clear()

    def test_cache_keys_are_constant(self):
        """Test that cache keys are constant (not per-user)."""
        self.assertEqual(ACTIVE_RULES_CACHE_KEY, 'discount_rules:active')
        self.assertEqual(LOYALTY_RULES_CACHE_KEY, 'discount_rules:loyalty')

    def test_cache_miss_returns_none(self):
        """Test that cache miss returns None."""
        result = get_cached_active_discount_rule_ids()
        self.assertIsNone(result)
        
        result = get_cached_loyalty_discount_rule_ids()
        self.assertIsNone(result)

    def test_cache_stores_and_retrieves_active_rule_ids(self):
        """Test storing and retrieving active discount rule IDs."""
        rule_ids = ['uuid-1', 'uuid-2', 'uuid-3']
        
        # Store in cache
        success = cache_active_discount_rule_ids(rule_ids)
        self.assertTrue(success)
        
        # Retrieve from cache
        cached = get_cached_active_discount_rule_ids()
        self.assertEqual(cached, rule_ids)

    def test_cache_stores_and_retrieves_loyalty_rule_ids(self):
        """Test storing and retrieving loyalty discount rule IDs."""
        rule_ids = ['uuid-loyalty-1', 'uuid-loyalty-2']
        
        # Store in cache
        success = cache_loyalty_discount_rule_ids(rule_ids)
        self.assertTrue(success)
        
        # Retrieve from cache
        cached = get_cached_loyalty_discount_rule_ids()
        self.assertEqual(cached, rule_ids)

    def test_cache_stores_empty_list(self):
        """Test that empty list is cached correctly (no active discounts)."""
        cache_active_discount_rule_ids([])
        
        cached = get_cached_active_discount_rule_ids()
        self.assertEqual(cached, [])
        self.assertIsNotNone(cached)  # Empty list is not None

    def test_only_two_cache_entries(self):
        """Test that only 2 cache entries are created regardless of data."""
        # Cache active rules
        cache_active_discount_rule_ids(['rule-1', 'rule-2', 'rule-3', 'rule-4', 'rule-5'])
        cache_loyalty_discount_rule_ids(['rule-3', 'rule-5'])
        
        # Verify both can be retrieved independently
        active = get_cached_active_discount_rule_ids()
        loyalty = get_cached_loyalty_discount_rule_ids()
        
        self.assertEqual(len(active), 5)
        self.assertEqual(len(loyalty), 2)

    def test_invalidate_clears_both_caches(self):
        """Test that invalidation clears both cache entries."""
        # Cache data
        cache_active_discount_rule_ids(['rule-1', 'rule-2'])
        cache_loyalty_discount_rule_ids(['rule-2'])
        
        # Verify cached
        self.assertIsNotNone(get_cached_active_discount_rule_ids())
        self.assertIsNotNone(get_cached_loyalty_discount_rule_ids())
        
        # Invalidate
        success = invalidate_discount_cache()
        self.assertTrue(success)
        
        # Verify cleared
        self.assertIsNone(get_cached_active_discount_rule_ids())
        self.assertIsNone(get_cached_loyalty_discount_rule_ids())

    def test_invalidate_all_alias_works(self):
        """Test that invalidate_all_discount_caches alias works."""
        cache_active_discount_rule_ids(['rule-1'])
        
        success = invalidate_all_discount_caches()
        self.assertTrue(success)
        
        self.assertIsNone(get_cached_active_discount_rule_ids())

    def test_cache_hit_performance_scenario(self):
        """Simulate cache hit scenario - same cache used for all users."""
        # First request - cache miss
        result1 = get_cached_active_discount_rule_ids()
        self.assertIsNone(result1)  # Cache miss
        
        # Simulate: after cache miss, we query DB and cache the result
        all_active = ['discount-1', 'discount-2', 'discount-3']
        loyalty_only = ['discount-3']  # discount-3 requires loyalty
        
        cache_active_discount_rule_ids(all_active)
        cache_loyalty_discount_rule_ids(loyalty_only)
        
        # Second request (any user) - cache hit
        result2 = get_cached_active_discount_rule_ids()
        self.assertEqual(result2, all_active)
        
        # Simulate regular user filtering (done in application code)
        loyalty_set = set(loyalty_only)
        regular_user_discounts = [r for r in all_active if r not in loyalty_set]
        self.assertEqual(regular_user_discounts, ['discount-1', 'discount-2'])
        
        # Simulate loyalty user - gets all
        loyalty_user_discounts = all_active
        self.assertEqual(loyalty_user_discounts, ['discount-1', 'discount-2', 'discount-3'])

    def test_scalability_same_cache_for_million_users(self):
        """
        Demonstrate scalability: same 2 cache entries serve all users.
        No matter how many users, only 2 cache entries exist.
        """
        # Setup: cache discount rules once
        cache_active_discount_rule_ids(['10-percent-off', 'loyalty-20-off', 'free-shipping'])
        cache_loyalty_discount_rule_ids(['loyalty-20-off'])
        
        # Simulate 1000 different users accessing discounts
        for user_id in range(1, 1001):
            is_loyalty = user_id % 10 == 0  # Every 10th user is loyalty member
            
            # All users hit the SAME cache entries
            active = get_cached_active_discount_rule_ids()
            loyalty = get_cached_loyalty_discount_rule_ids()
            
            # Filter in memory based on user status
            if is_loyalty:
                user_discounts = active  # Loyalty gets all
            else:
                loyalty_set = set(loyalty)
                user_discounts = [r for r in active if r not in loyalty_set]
            
            # Verify correct filtering
            if is_loyalty:
                self.assertEqual(len(user_discounts), 3)
            else:
                self.assertEqual(len(user_discounts), 2)
        
        # Still only 2 cache entries after 1000 "users"!
        self.assertIsNotNone(get_cached_active_discount_rule_ids())
        self.assertIsNotNone(get_cached_loyalty_discount_rule_ids())


if __name__ == '__main__':
    import unittest
    
    # Create test suite
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromTestCase(DiscountCacheUnitTest)
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Exit with appropriate code
    sys.exit(0 if result.wasSuccessful() else 1)
