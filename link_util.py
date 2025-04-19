import re
INSTAGRAM_REGEX = r"(https?://)?(www\.)?instagram\.com/[A-Za-z0-9_.]+/?"
TWITTER_REGEX = r"(https?://)?(www\.)?(twitter|x)\.com/[A-Za-z0-9_]+/status/\d+"
TIKTOK_REGEX = r"(https?://)?(www\.)?tiktok\.com/(t/[\w\d]+|@[\w\d_.]+/video/\d+)"
REDDIT_REGEX = r"(https?://)?(www\.)?reddit\.com/r/\w+/comments/\w+"
FACEBOOK_REGEX = r"(https?://)?(www\.)?facebook\.com/reel/[\w\d./?=&-]+"
YOUTUBE_REGEX = r"(?:https?://)?(?:www\.)?(?:youtube\.com/(?:watch\?v=|embed/|shorts/)|youtu\.be/)([A-Za-z0-9_-]{11})"
links = []
def is_link(message):
    if
    pass
def convert_link(message):
    modified_url = None

    if re.search(INSTAGRAM_REGEX, message.content):
        modified_url = re.sub(r"instagram", "instagramez", message.content)
        return [modified_url,'instagram']

    elif re.search(TWITTER_REGEX, message.content):
        modified_url = re.sub(r"(twitter|x)", "twitterez", message.content)
        return [modified_url, 'twitter']

    elif re.search(TIKTOK_REGEX, message.content):
        modified_url = re.sub(r"tiktok", "tiktokez", message.content)
        return [modified_url, 'tiktok']

    elif re.search(REDDIT_REGEX, message.content):
        modified_url = re.sub(r"reddit", "redditez", message.content)
        return [modified_url, 'reddit']

    elif re.search(FACEBOOK_REGEX, message.content):
        modified_url = re.sub(r"facebook", "facebookez", message.content)
        return [modified_url, 'facebook']

    return [modified_url,modified_url]
