import discord

intents = discord.Intents.default()
intents.message_content = True

client = discord.Client(intents=intents)

@client.event
async def on_message(message):
    if message.author == client.user:
        return
    
    if message.content.startswith('$hello'):
        await message.channel.send('Hello')

client.run('MTM0NzgxMjY3MTQ0NTAxMjUyMg.G10ccd.YDZhOHkvmpQu1d1czMoSR7uLPm03CKEP2peyCE')
