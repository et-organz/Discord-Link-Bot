import discord
from collections import defaultdict

# Dictionary to store how many times a user has posted a link
user_link_count = defaultdict(int)

# Increments user link count
async def url_posted(message):
    user_link_count[message.author.id] += 1

# Check how many links a user has posted
async def get_user_link_count(user_id):
    return user_link_count.get(user_id, 0)

