import re
INSTAGRAM_REGEX = r"(https?://)?(www\.)?instagram\.com/[A-Za-z0-9_.]+/?"
TWITTER_REGEX = r"(https?://)?(www\.)?(twitter|x)\.com/[A-Za-z0-9_]+/status/\d+"
TIKTOK_REGEX = r"(https?://)?(www\.)?tiktok\.com/(t/[\w\d]+|@[\w\d_.]+/video/\d+)"
REDDIT_REGEX = r"(https?://)?(www\.)?reddit\.com/r/\w+/comments/\w+"
FACEBOOK_REGEX = r"(https?://)?(www\.)?facebook\.com/reel/[\w\d./?=&-]+"

def convert_link(message):
    modified_url = None

    if re.search(INSTAGRAM_REGEX, message.content):
        modified_url = re.sub(r"instagram", "instagramez", message.content)

    elif re.search(TWITTER_REGEX, message.content):
        modified_url = re.sub(r"(twitter|x)", "twitterez", message.content)

    elif re.search(TIKTOK_REGEX, message.content):
        modified_url = re.sub(r"tiktok", "tiktokez", message.content)

    elif re.search(REDDIT_REGEX, message.content):
        modified_url = re.sub(r"reddit", "redditez", message.content)

    elif re.search(FACEBOOK_REGEX, message.content):
        modified_url = re.sub(r"facebook", "facebookez", message.content)

    return modified_url
