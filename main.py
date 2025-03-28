import discord
import re
from link_util import convert_link
import user_reaction_util

intents = discord.Intents.default()
intents.message_content = True

client = discord.Client(intents=intents)

# Define the channel ID where you want to count the links
TARGET_CHANNEL_ID = 1347815817080999969

@client.event
async def on_ready():
    print(f'We have logged in as {client.user}')
    # Get the channel by ID
    channel = client.get_channel(TARGET_CHANNEL_ID)
    if channel:
        await user_reaction_util.count_links_in_channel(channel)

@client.event
async def on_message(message):
    if message.author == client.user:
        return

    if message.content.startswith('$hello'):
        await message.channel.send('Hello!')
    converted_url = convert_link(message)
    if converted_url:
        await message.channel.send(converted_url)
    if user_reaction_util.url_pattern.search(message.content):
        await user_reaction_util.url_posted(message)
    if message.content.startswith(f'$links'):
        await message.channel.send(await user_reaction_util.get_user_link_count(message.author.id))
    if message.content.startswith(f'$link'):
        command_text = message.content[len('$link'):].strip()
        await message.channel.send( await user_reaction_util.get_other_user_link_count(int(command_text)))





client.run('MTM0NzgxMjY3MTQ0NTAxMjUyMg.G10ccd.YDZhOHkvmpQu1d1czMoSR7uLPm03CKEP2peyCE')
