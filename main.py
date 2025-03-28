import discord
import re
from link_util import convert_link
import user_reaction_util

intents = discord.Intents.default()
intents.message_content = True

client = discord.Client(intents=intents)


# Regular expression to check for URLs in a message
url_pattern = re.compile(r'https?://[^\s]+')

@client.event
async def on_ready():
    print(f'We have logged in as {client.user}')

@client.event
async def on_message(message):
    if message.author == client.user:
        return

    if message.content.startswith('$hello'):
        await message.channel.send('Hello!')
    converted_url = convert_link(message)
    if converted_url:
        await message.channel.send(converted_url)
    if url_pattern.search(message.content):
        await user_reaction_util.url_posted(message)
    if message.content.startswith(f'$links'):
        await message.channel.send(await user_reaction_util.get_user_link_count(message.author.id))





client.run('MTM0NzgxMjY3MTQ0NTAxMjUyMg.G10ccd.YDZhOHkvmpQu1d1czMoSR7uLPm03CKEP2peyCE')
