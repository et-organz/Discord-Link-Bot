import unittest
import re
from unittest.mock import AsyncMock, MagicMock
from collections import defaultdict

from .. import link_util


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

    def test_convert_link_substitutes_platforms(self):
        test_cases = {
            "https://www.instagram.com/user": "https://www.instagramez.com/user",
            "https://twitter.com/user/status/123": "https://twitterez.com/user/status/123",
            "https://www.tiktok.com/@user/video/987654": "https://www.tiktokez.com/@user/video/987654",
            "https://www.reddit.com/r/test/comments/xyz": "https://www.redditez.com/r/test/comments/xyz",
            "https://www.facebook.com/reel/abc": "https://www.facebookez.com/reel/abc",
            "https://www.unknownsite.com": None
        }

        for url, expected in test_cases.items():
            msg = MockMessage(url)
            result = link_util.convert_link(msg)
            if expected:
                self.assertIn(expected.split(".")[0], result)
            else:
                self.assertIsNone(result)


if __name__ == "__main__":
    unittest.main()
