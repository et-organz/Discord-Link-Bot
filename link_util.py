import re
INSTAGRAM_REGEX = r"(https?://)?(www\.)?instagram\.com/[A-Za-z0-9_.]+/?"
TWITTER_REGEX = r"(https?://)?(www\.)?(twitter|x)\.com/[A-Za-z0-9_]+/status/\d+"
TIKTOK_REGEX = r"(https?://)?(www\.)?tiktok\.com/(t/[\w\d]+|@[\w\d_.]+/video/\d+)"
REDDIT_REGEX = r"(https?://)?(www\.)?reddit\.com/r/\w+/comments/\w+"
FACEBOOK_REGEX = r"(https?://)?(www\.)?facebook\.com/reel/[\w\d./?=&-]+"
YOUTUBE_REGEX = r"(?:https?://)?(?:www\.)?(?:youtube\.com/(?:watch\?v=|embed/|shorts/)|youtu\.be/)([A-Za-z0-9_-]{11})"
# Regex pattern for extracting domain
domain_pattern = r'(?:https?://)?(?:www\.)?([a-zA-Z0-9-]+\.[a-zA-Z]{2,})'

link_pattern = r'https?://[^\s]+'  # Matches http/https URLs
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

def convert_link(message):
    modified_url = None

    if re.search(INSTAGRAM_REGEX, message.content):
        modified_url = re.sub(r"instagram", "instagramez", message.content)
        return modified_url

    elif re.search(TWITTER_REGEX, message.content):
        modified_url = re.sub(r"(twitter|x)", "twitterez", message.content)
        return modified_url

    elif re.search(TIKTOK_REGEX, message.content):
        modified_url = re.sub(r"tiktok", "tiktokez", message.content)
        return modified_url

    elif re.search(REDDIT_REGEX, message.content):
        modified_url = re.sub(r"reddit", "redditez", message.content)
        return modified_url

    elif re.search(FACEBOOK_REGEX, message.content):
        modified_url = re.sub(r"facebook", "facebookez", message.content)
        return modified_url

    return modified_url
