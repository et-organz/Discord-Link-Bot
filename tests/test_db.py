import os
import sys
import unittest
from datetime import datetime, timedelta, timezone

# Add the project root to sys.path so we can import db.py
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from db import (
    get_top_posts,
    get_top_posters,
    get_top_domain,
    conn  # import psycopg2 connection for test data insertions
)


class TestDBIntegration(unittest.TestCase):
    test_guild_id = 999999  # use a clearly fake/test guild_id

    @classmethod
    def setUpClass(cls):
        with conn:
            with conn.cursor() as cur:
                # Insert mock link message
                cur.execute("""
                    INSERT INTO link_messages (
                        message_id, user_id, channel_id, guild_id, link, domain_name,
                        reactions, reactors, created_at
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s::reaction_tuple[], %s, %s)
                    ON CONFLICT (message_id) DO NOTHING;
                """, (
                    1001, 111, 222, cls.test_guild_id,
                    "http://example.com", "example.com",
                    [('👍', 111)],
                    [111],
                    datetime.now(timezone.utc)
                ))

                # Insert mock media message with cast on reactions
                cur.execute("""
                    INSERT INTO media_messages (
                        message_id, user_id, channel_id, guild_id, media_url, media_type,
                        reactions, reactors, created_at
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s::reaction_tuple[], %s, %s)
                    ON CONFLICT (message_id) DO NOTHING;
                """, (
                    1002, 222, 333, cls.test_guild_id,
                    "http://cdn.example.com/image.png", "image",
                    [('🔥', 222)],
                    [222],
                    datetime.now(timezone.utc)
                ))

    @classmethod
    def tearDownClass(cls):
        with conn:
            with conn.cursor() as cur:
                # Delete the mock data
                cur.execute("DELETE FROM link_messages WHERE guild_id = %s;", (cls.test_guild_id,))
                cur.execute("DELETE FROM media_messages WHERE guild_id = %s;", (cls.test_guild_id,))

    def test_get_top_posts_returns_list(self):
        posts = get_top_posts(self.test_guild_id)
        self.assertIsInstance(posts, list)
        self.assertGreaterEqual(len(posts), 1)

    def test_get_top_posters_returns_expected_keys(self):
        posters = get_top_posters()
        self.assertIsInstance(posters, list)
        if posters:
            self.assertIn("user_id", posters[0])
            self.assertIn("unique_reactors", posters[0])

    def test_get_top_domain_returns_expected_result(self):
        domain = get_top_domain(self.test_guild_id)
        self.assertIsInstance(domain, tuple)
        self.assertEqual(domain[0], "example.com")


if __name__ == '__main__':
    unittest.main()
