# This example requires the 'message_content' intent.

import discord
import re

INSTAGRAM_REGEX = r"(https?://)?(www\.)?instagram\.com/[A-Za-z0-9_.]+/?"


intents = discord.Intents.default()
intents.message_content = True

client = discord.Client(intents=intents)

@client.event
async def on_ready():
    print(f'We have logged in as {client.user}')

@client.event
async def on_message(message):
    if message.author == client.user:
        return

    if message.content.startswith('$hello'):
        await message.channel.send('Hello!')
    match = re.search(INSTAGRAM_REGEX, message.content)


    if match:

        pattern = r"instagram"  # Match any occurrence of "instagram"
        replacement = "instagramez"

        instagram_url = re.sub(pattern, replacement, message.content)
        # Create an embed message
        await message.channel.send(instagram_url)





client.run('MTM0NzgxMjY3MTQ0NTAxMjUyMg.G10ccd.YDZhOHkvmpQu1d1czMoSR7uLPm03CKEP2peyCE')
