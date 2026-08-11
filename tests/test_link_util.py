import unittest
import os
import sys
import re
from unittest.mock import AsyncMock, MagicMock, patch
from collections import defaultdict

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import link_util


class MockMessage:
    def __init__(self, content, author_id=123):
        self.content = content
        self.author = MagicMock()
        self.author.id = author_id


class AsyncIterator:
    """A helper class to support async iteration over a list."""
    def __init__(self, items):
        self._items = items

    def __aiter__(self):
        self._iter = iter(self._items)
        return self

    async def __anext__(self):
        try:
            return next(self._iter)
        except StopIteration:
            raise StopAsyncIteration


class TestUtilFunctions(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        link_util.user_link_count = defaultdict(int)
        link_util.web_link_count = defaultdict(int)

    async def test_url_posted_counts_correctly(self):
        msg = MockMessage("https://www.reddit.com/r/test/comments/xyz/test_post")
        await link_util.url_posted(msg)

        self.assertEqual(link_util.web_link_count['reddit.com'], 1)
        self.assertEqual(link_util.user_link_count[msg.author.id], 1)

    async def test_count_links_in_channel(self):
        mock_channel = MagicMock()
        mock_messages = [
            MockMessage("https://www.tiktok.com/@user/video/123456"),
            MockMessage("no link here"),
            MockMessage("https://youtube.com/watch?v=dQw4w9WgXcQ"),
        ]

        mock_channel.history.return_value = AsyncIterator(mock_messages)

        await link_util.count_links_in_channel(mock_channel)
        self.assertEqual(link_util.user_link_count[123], 2)

    def test_get_link_from_message_valid(self):
        msg = MockMessage("Check this out: https://example.com/page")
        self.assertEqual(link_util.get_link_from_message(msg), "https://example.com/page")

    def test_get_link_from_message_none(self):
        msg = MockMessage("No link here")
        self.assertIsNone(link_util.get_link_from_message(msg))

    def test_get_url_type_all_platforms(self):
        urls = {
            "https://www.instagram.com/username/": "instagram",
            "https://twitter.com/user/status/123456": "twitter",
            "https://www.tiktok.com/@user/video/987654": "tiktok",
            "https://www.reddit.com/r/funny/comments/abc123": "reddit",
            "https://www.facebook.com/reel/xyz": "facebook",
            "https://www.youtube.com/watch?v=dQw4w9WgXcQ": "youtube",
            "https://someother.com/page": "unknown"
        }

        for url, expected_type in urls.items():
            msg = MockMessage(url)
            self.assertEqual(link_util.get_url_type(msg), expected_type)

    async def test_convert_link_uses_primary_backup_when_up(self):
        test_cases = {
            "https://www.instagram.com/user": "toinstagram.com",
            "https://twitter.com/user/status/123": "fxtwitter.com",
            "https://www.tiktok.com/@user/video/987654": "tnktok.com",
            "https://www.reddit.com/r/test/comments/xyz": "rxddit.com",
            "https://www.facebook.com/reel/abc": "facebed.com",
        }

        with patch("link_util._domain_is_up", new=AsyncMock(return_value=True)):
            for url, expected_domain in test_cases.items():
                result = await link_util.convert_link(url)
                self.assertIn(expected_domain, result)

    async def test_convert_link_returns_bare_url_not_surrounding_text(self):
        content = "check this out https://twitter.com/user/status/123 pretty cool right"
        with patch("link_util._domain_is_up", new=AsyncMock(return_value=True)):
            result = await link_util.convert_link(content)

        self.assertEqual(result, "https://fxtwitter.com/user/status/123")

    async def test_convert_link_returns_none_for_unrecognized_url(self):
        with patch("link_util._domain_is_up", new=AsyncMock(return_value=True)):
            result = await link_util.convert_link("https://www.unknownsite.com")
        self.assertIsNone(result)

    async def test_convert_link_falls_back_to_next_domain_when_primary_down(self):
        async def fake_domain_is_up(url):
            return "vxtwitter.com" in url  # fxtwitter.com (primary) reports down

        with patch("link_util._domain_is_up", new=fake_domain_is_up):
            result = await link_util.convert_link("https://twitter.com/user/status/123")

        self.assertIn("vxtwitter.com", result)
        self.assertNotIn("fxtwitter.com", result)

    async def test_convert_link_returns_none_when_all_backups_down(self):
        with patch("link_util._domain_is_up", new=AsyncMock(return_value=False)):
            result = await link_util.convert_link("https://twitter.com/user/status/123")

        self.assertIsNone(result)


if __name__ == "__main__":
    unittest.main()
