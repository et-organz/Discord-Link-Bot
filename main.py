import discord
import os
from dotenv import load_dotenv
import re
from link_util import convert_link
import user_reaction_util
import db
from discord.ext import commands
import gif_util 
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

    # Custom help command
    if message.content.startswith('$help'):
        help_text = """
Available commands:
1. !makegif <start_time> <video_url> - Create a GIF from a video
2. !top_links - View the top links in the server
3. !top_image - View the top image in the server
4. !top_video - View the top video in the server
5. !top_gif - View the top GIF in the server
6. !top_domain - View the top domain in the server
        """
        await message.channel.send(help_text)

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
            message_id, domain, total_reacts = link
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
    
    elif message.content.startswith('$makegif'):
        try:
            parts = message.content.split()
            if len(parts) < 3:
                await message.channel.send("Usage: `!makegif <start_time> <video_url>`")
                return
            
            start_time = float(parts[1])
            video_url = parts[2]

            await message.channel.send("Downloading and processing your video... 🎬")

            input_video_path = "temp_video.mp4"
            output_gif_path = "output.gif"

            gif_util.download_video(video_url, input_video_path)
            gif_util.video_to_gif(input_video_path, output_gif_path, start_time=start_time)
            await message.channel.send(file=discord.File(output_gif_path))

        except Exception as e:
            await message.channel.send(f"An error occurred: {e}")
            import traceback
            traceback.print_exc()
        finally:
            if os.path.exists("temp_video.mp4"):
                os.remove("temp_video.mp4")
            if os.path.exists("output.gif"):
                os.remove("output.gif")
    

@client.event
async def on_raw_reaction_add(payload: discord.RawReactionActionEvent):
    emoji = str(payload.emoji)
    user_id = payload.user_id
    message_id = payload.message_id
    print(f'{user_id} raw reacted with {emoji} with messageid{message_id}')
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
