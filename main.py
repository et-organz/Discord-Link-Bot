import discord
from link_util import convert_link

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
    converted_url = convert_link(message)
    if converted_url:
        await message.channel.send(converted_url)





client.run('MTM0NzgxMjY3MTQ0NTAxMjUyMg.G10ccd.YDZhOHkvmpQu1d1czMoSR7uLPm03CKEP2peyCE')
