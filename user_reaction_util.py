import discord
import re
from collections import defaultdict

# Dictionary to store how many times a user has posted a link
user_link_count = defaultdict(int)

# Regular expression to check for URLs in a message
url_pattern = re.compile(r'https?://[^\s]+')

# Increments user link count
async def url_posted(message):
    user_link_count[message.author.id] += 1

# Check how many links a user has posted
async def get_user_link_count(user_id):
    return user_link_count.get(user_id, 0)

async def get_other_user_link_count(user_id):
    return user_link_count.get(user_id, 0)

# Fetch all messages and counting links for every user in a specific channel
async def count_links_in_channel(channel):
    async for message in channel.history(limit=100):  # Adjust limit as needed
        if url_pattern.search(message.content):
            user_link_count[message.author.id] += 1
