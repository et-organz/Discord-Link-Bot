import re
import asyncio
from collections import defaultdict
from urllib.parse import urlsplit, urlunsplit

import aiohttp

INSTAGRAM_REGEX = r"(https?://)?(www\.)?instagram\.com/[A-Za-z0-9_.]+/?"
TWITTER_REGEX = r"(https?://)?(www\.)?(twitter|x)\.com/[A-Za-z0-9_]+/status/\d+"
TIKTOK_REGEX = r"(https?://)?(www\.)?tiktok\.com/(t/[\w\d]+|@[\w\d_.]+/video/\d+)"
REDDIT_REGEX = r"(https?://)?(www\.)?reddit\.com/r/\w+/comments/\w+"
FACEBOOK_REGEX = r"(https?://)?(www\.)?facebook\.com/reel/[\w\d./?=&-]+"
YOUTUBE_REGEX = r"(?:https?://)?(?:www\.)?(?:youtube\.com/(?:watch\?v=|embed/|shorts/)|youtu\.be/)([A-Za-z0-9_-]{11})"
# Regex pattern for extracting domain
domain_pattern = r'(?:https?://)?(?:www\.)?([a-zA-Z0-9-]+\.[a-zA-Z]{2,})'
url_pattern = re.compile(r'https?://[^\s]+')
link_pattern = r'https?://[^\s]+'  # Matches http/https URLs

# Dictionary to store how many times a user has posted a link
user_link_count = defaultdict(int)
web_link_count = defaultdict(int)
async def url_posted(message):
    match = re.search(domain_pattern, message.content)
    if match:
        domain = match.group(1)
        web_link_count[domain] += 1

    user_link_count[message.author.id] += 1
async def count_links_in_channel(channel):
    async for message in channel.history(limit=100):  # Adjust limit as needed
        if url_pattern.search(message.content):
            await url_posted(message)
def get_link_from_message(message):
    match = re.search(link_pattern, message.content)
    if match:
        first_url = match.group() # Get the first URL found
        return first_url
    else:
        return None

def get_url_type(message):
    modified_url = "unknown"

    if re.search(INSTAGRAM_REGEX, message.content):
        modified_url = "instagram"

    elif re.search(TWITTER_REGEX, message.content):
        modified_url = "twitter"

    elif re.search(TIKTOK_REGEX, message.content):
        modified_url = "tiktok"

    elif re.search(REDDIT_REGEX, message.content):
        modified_url = "reddit"

    elif re.search(FACEBOOK_REGEX, message.content):
        modified_url = "facebook"

    elif re.search(YOUTUBE_REGEX, message.content):
        modified_url = "youtube"
    return modified_url

# Ordered by reliability; the first backup that actually responds wins.
# Verified 2026-07-25 - these embed-fix services change ownership/behavior over
# time (e.g. instagramez.com now redirects to an ad domain, twitterez/tiktokez/
# redditez.com now redirect to a generic landing page instead of embedding
# directly, facebookez.com is dead, ddinstagram.com blocks Discord's bot UA) so
# don't assume this list stays accurate forever.
EMBED_FIX_DOMAINS = {
    "instagram": ["toinstagram.com"],
    "twitter": ["fxtwitter.com", "vxtwitter.com", "fixupx.com"],
    "tiktok": ["tnktok.com", "vxtiktok.com"],
    "reddit": ["rxddit.com", "vxreddit.com"],
    "facebook": ["facebed.com"],
}

PLATFORM_REGEXES = {
    "instagram": INSTAGRAM_REGEX,
    "twitter": TWITTER_REGEX,
    "tiktok": TIKTOK_REGEX,
    "reddit": REDDIT_REGEX,
    "facebook": FACEBOOK_REGEX,
}

# Discord's own crawler UA - some of these services (e.g. ddinstagram.com)
# specifically block it while working fine for browsers, so checking with a
# generic UA would give a false "it's up" reading.
_DISCORDBOT_USER_AGENT = "Mozilla/5.0 (compatible; Discordbot/2.0; +https://discordapp.com)"
_LINK_CHECK_TIMEOUT = aiohttp.ClientTimeout(total=5)

_session = None


async def _get_session():
    global _session
    if _session is None or _session.closed:
        _session = aiohttp.ClientSession(headers={"User-Agent": _DISCORDBOT_USER_AGENT})
    return _session


def _with_host(url: str, new_host: str) -> str:
    parts = urlsplit(url if "://" in url else f"https://{url}")
    return urlunsplit(("https", new_host, parts.path, parts.query, parts.fragment))


async def _domain_is_up(url: str) -> bool:
    try:
        session = await _get_session()
        async with session.get(url, timeout=_LINK_CHECK_TIMEOUT, allow_redirects=True) as resp:
            return resp.status < 500
    except (aiohttp.ClientError, asyncio.TimeoutError):
        return False


async def convert_link(content: str):
    """
    Finds the first recognized social-media link in `content` and returns just
    the embed-friendly mirror URL (not the surrounding text). Tries each
    platform's backup domains in order and returns the first one that actually
    responds; if every backup for that platform is down, or no recognized
    link is found at all, returns None.
    """
    for platform, pattern in PLATFORM_REGEXES.items():
        match = re.search(pattern, content)
        if not match:
            continue

        original_url = match.group(0)
        for domain in EMBED_FIX_DOMAINS[platform]:
            candidate_url = _with_host(original_url, domain)
            if await _domain_is_up(candidate_url):
                return candidate_url

        print(f"All embed-fix backups for {platform} are down; not posting a converted link.")
        return None

    return None
