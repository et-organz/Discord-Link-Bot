import discord
import os
from dotenv import load_dotenv
import re
from link_util import convert_link
import user_reaction_util
import db
load_dotenv()

api_key = os.getenv("API_KEY")

intents = discord.Intents.default()
intents.message_content = True
intents.messages = True     # To recieve message events
intents.reactions = True    # To recieve reaction events

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

    db.insert_media(message)

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
    guild_id = message.guild.id

    if message.content.startswith('$top_links'):
        top_links = db.get_top_links(guild_id)
        response = "**Top 5 Links:**\n"
        for link in top_links:
            message_id, domain, reactions = link
            total_reacts = sum(int(v) for k, v in reactions.items() if k != "reactors")
            response += f"- Message ID: {message_id}, Domain: `{domain}`, Reactions: {total_reacts}\n"
        await message.channel.send(response)

    elif message.content.startswith('$top_image'):
        top_image = db.get_top_media(guild_id, 'image')
        if top_image:
            response = f"**Top Image Post:** Message ID: {top_image[0]}, Reactions: {top_image[1]}"
        else:
            response = "No top image found."
        await message.channel.send(response)

    elif message.content.startswith('$top_video'):
        top_video = db.get_top_media(guild_id, 'video')
        if top_video:
            response = f"**Top Video Post:** Message ID: {top_video[0]}, Reactions: {top_video[1]}"
        else:
            response = "No top video found."
        await message.channel.send(response)

    elif message.content.startswith('$top_gif'):
        top_gif = db.get_top_media(guild_id, 'gif')
        if top_gif:
            response = f"**Top GIF Post:** Message ID: {top_gif[0]}, Reactions: {top_gif[1]}"
        else:
            response = "No top GIF found."
        await message.channel.send(response)

    elif message.content.startswith('$top_domain'):
        top_domain = db.get_top_domain(guild_id)
        if top_domain:
            domain, count = top_domain
            response = f"**Most Linked Domain:** `{domain}` with {count} links."
        else:
            response = "No domains found."
        await message.channel.send(response)



@client.event
async def on_reaction_add(reaction, user):
    # Potential problem: on_reaction_add() only seems to capture the reaction 
    # of links that have been posted after the bot started running. 

    print(f'{user} reacted with {reaction.emoji}')

    if reaction.message.author == client.user:
        return  # Skips reactions to the bot's messages, unsure if this is desired 

    # reaction.emoji grants access to the emoji
    

@client.event
async def on_raw_reaction_add(payload: discord.RawReactionActionEvent):
    emoji = str(payload.emoji)
    user_id = payload.user_id
    message_id = payload.message_id

    # Ignore the bot itself
    if user_id == client.user.id:
        return

    db.add_reaction(emoji, user_id, message_id)

@client.event
async def on_raw_reaction_remove(payload: discord.RawReactionActionEvent):
    emoji = str(payload.emoji)
    user_id = payload.user_id
    message_id = payload.message_id

    if user_id == client.user.id:
        return
    print(f"Reaction removed: {emoji} by user {user_id} on message {message_id}")
    db.remove_reaction(emoji, user_id, message_id)



client.run(api_key)
