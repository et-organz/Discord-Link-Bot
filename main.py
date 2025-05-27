import discord
import os
from dotenv import load_dotenv
from link_util import convert_link, count_links_in_channel
import db
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
    channel = client.get_channel(TARGET_CHANNEL_ID)
    if channel:
        print("Backfilling link and media history...")
        messages = []
        async for message in channel.history(limit=None, oldest_first=True):
            if message.author.bot:
                continue
            messages.append(message)

        media_inserted = db.backfill_messages_from_history(messages)

        print(f"Inserted {media_inserted} message(s) into the database.")
        await count_links_in_channel(channel)


@client.event
async def on_message(message):
    if message.author == client.user:
        return

    # Custom help command
    if message.content.startswith('$help'):
        help_text = """Available commands:
        1. $top_posts <post_type> [limit] [time_range]: Returns the top posts based on reaction count.
           - post_type options: link, image, gif, movie, all (default: all)
           - limit (optional): Number of results to return (default: 5)
           - time_range (optional): week, month, or all (default: all)
           Example: $top_posts gif 3 week
        
        2. $top_users <post_type> [limit] [time_range]: Returns the top users by unique reactors.
           - post_type options: link, image, gif, movie, all (default: all)
           - limit (optional): Number of users to list (default: 5)
           - time_range (optional): week, month, or all (default: all)
           Example: $top_users link 3 month
        
        3. $top_domain: Returns the most frequently linked domain in the server.
        
        4. $makegif <start_time> <youtube_url>: Creates a 5-second GIF starting from the specified time in a YouTube video.
           Example: $makegif 30 https://youtube.com/watch?v=example
        
        5. $contest [week|month]: Shows contest results for top posters by links and media based on unique reactors.
           Example: $contest month
        """


        await message.channel.send(help_text)

    guild_id = message.guild.id
    converted_url = convert_link(message)
    if converted_url:
        await message.channel.send(converted_url)
    if message.content.startswith('$top_posts'):
        parts = message.content.split()

        # Default values
        post_type = "all"
        time_range = "all"
        limit = 5

        # Parse user-provided parameters
        if len(parts) >= 2:
            post_type = parts[1].lower()

        if len(parts) >= 3:
            if parts[2].isdigit():
                limit = int(parts[2])
            else:
                time_range = parts[2].lower()

        if len(parts) >= 4:
            if parts[3].isdigit():
                limit = int(parts[3])
            else:
                await message.channel.send("❗ Limit must be a number.")
                return

        try:
            top_posts = db.get_top_posts(guild_id, post_type=post_type, time_range=time_range, limit=limit)

            if not top_posts:
                await message.channel.send("No posts found for that query.")
                return

            title_map = {
                "link": "Links",
                "image": "Images",
                "movie": "Videos",
                "gif": "GIFs",
                "all": "Posts"
            }

            title = title_map.get(post_type, "Posts")
            response = f"**Top {limit} {title} ({time_range})**\n"

            for item in top_posts:
                user_name = await client.fetch_user(item["user_id"])
                domain = f"Domain: `{item['domain_name']}`, " if "domain_name" in item else ""
                response += (
                    f"- {domain}Reactions: {item['reaction_count']}, "
                    f"Posted by user: {user_name}, Content: {item['content']}\n"
                )

            await message.channel.send(response)

        except Exception as e:
            print(e)
            await message.channel.send("❗ An error occurred while fetching top posts.")

    elif message.content.startswith('$top_users'):

        parts = message.content.split()

        # Set default values

        post_type = "all"

        limit = 5

        time_range = "all"  # Optional: extend support for week/month

        # Parse arguments with safe defaults

        if len(parts) >= 2:
            post_type = parts[1].lower()

        if len(parts) >= 3:

            if parts[2].isdigit():

                limit = int(parts[2])

            else:

                print("Invalid limit provided, defaulting to 5")

        if len(parts) >= 4:
            time_range = parts[3].lower()

        try:

            top_posters = db.get_top_posters(post_type, limit, time_range)

            if not top_posters:
                await message.channel.send("No results found for that category.")

                return

            response = f"🏆 Top {limit} {post_type} posters ({time_range}):\n"

            for i, poster in enumerate(top_posters, 1):
                response += f"{i}. <@{poster['user_id']}> with {poster['unique_reactors']} unique reactors\n"

            await message.channel.send(response)

        except Exception as e:

            print(e)

            await message.channel.send("❗ An error occurred while fetching top posters.")

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

    elif message.content.startswith('$contest'):

        args = message.content.split()

        period = 'week'

        if len(args) > 1 and args[1].lower() in ['week', 'month']:
            period = args[1].lower()

        # Fetch top posters

        top_links = db.get_top_posters(post_type='link', limit=5, time_range=period)

        top_media = db.get_top_posters(post_type='all', limit=5, time_range=period)  # Combine all media types

        embed = discord.Embed(

            title=f"🏆 {period.capitalize()}ly Contest Winners!",

            description=f"Here are the top posters for the past {period}.",

            color=discord.Color.gold()

        )

        link_str = ""

        for i, entry in enumerate(top_links):
            user = await client.fetch_user(entry["user_id"])

            link_str += f"{i + 1}. {user.name} — {entry['unique_reactors']} reactions\n"

        if not link_str:
            link_str = "No link posters found."

        media_str = ""

        for i, entry in enumerate(top_media):
            user = await client.fetch_user(entry["user_id"])

            media_str += f"{i + 1}. {user.name} — {entry['unique_reactors']} reactions\n"

        if not media_str:
            media_str = "No media posters found."

        embed.add_field(name="🔗 Top Link Posters", value=link_str, inline=False)

        embed.add_field(name="🖼️ Top Media Posters", value=media_str, inline=False)

        await message.channel.send(embed=embed)

    else:
        db.insert_media(message)



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
