import discord
from discord.ext import commands
from discord import app_commands
import os
from dotenv import load_dotenv
import db
import gif_util
from link_util import convert_link, count_links_in_channel
import asyncio
from datetime import datetime

STATUS_FILE = "last_alive.txt"

async def periodic_status_writer():
    while True:
        with open(STATUS_FILE, "w") as f:
            f.write(datetime.utcnow().isoformat())
        await asyncio.sleep(60)  # write every 60 seconds
load_dotenv()
API_KEY = os.getenv("API_KEY")

intents = discord.Intents.default()
intents.message_content = True
intents.messages = True
intents.reactions = True

class MyClient(discord.Client):
    def __init__(self):
        super().__init__(intents=intents)
        self.tree = app_commands.CommandTree(self)

    async def setup_hook(self):
        for guild in self.guilds:
            self.tree.copy_global_to(guild=guild)
        await self.tree.sync()

client = MyClient()

@client.event
async def on_ready():
    print(f'✅ Logged in as {client.user}')
    client.loop.create_task(periodic_status_writer())

    # Check for unclean shutdown:
    try:
        with open(STATUS_FILE, "r") as f:
            last_alive_str = f.read().strip()
            last_alive = datetime.fromisoformat(last_alive_str)
            time_since = datetime.utcnow() - last_alive
            if time_since.total_seconds() > 90:
                print("🛠️ Bot was offline for too long. Backlogging messages...")
                # await run_backlog_process(last_alive) # Note to elijiah add backlogging here
            else:
                print("✅ Clean or recent restart detected.")
    except FileNotFoundError:
        print("No previous status file found. Assuming first launch.")

# Moderator check
def is_moderator(interaction: discord.Interaction) -> bool:
    return interaction.user.guild_permissions.manage_messages or interaction.user.guild_permissions.administrator

@client.tree.command(name="backfill", description="Backfill all messages in text channels.")
async def backfill_command(interaction: discord.Interaction):
    if not is_moderator(interaction):
        await interaction.response.send_message("❌ You need moderator permissions to run this command.", ephemeral=True)
        return

    await interaction.response.send_message("Starting backfill... This may take a while.")
    for channel in interaction.guild.text_channels:
        try:
            messages = [m async for m in channel.history(limit=None, oldest_first=True) if not m.author.bot]
            count = db.backfill_messages_from_history(messages)
            await count_links_in_channel(channel)
            print(f"✅ Inserted {count} messages from #{channel.name}")
        except discord.Forbidden:
            print(f"🚫 No access to #{channel.name}")
        except Exception as e:
            print(f"❗ Error in {channel.name}: {e}")
    await interaction.followup.send("✅ Backfill complete!")

@client.tree.command(name="top_posts", description="Get top posts based on reaction count.")
@app_commands.describe(post_type="Type of post", limit="Number of posts", time_range="Time filter (week/month/all)")
async def top_posts(interaction: discord.Interaction, post_type: str = "all", limit: int = 5, time_range: str = "all"):
    try:
        posts = db.get_top_posts(interaction.guild_id, post_type, limit, time_range)
        if not posts:
            await interaction.response.send_message("No posts found.")
            return

        title_map = {
            "link": "Links", "image": "Images", "movie": "Videos", "gif": "GIFs", "all": "Posts"
        }
        header = f"**Top {limit} {title_map.get(post_type, 'Posts')} ({time_range})**"
        
        lines = [header]
        for item in posts:
            user = await client.fetch_user(item["user_id"])
            domain = f"Domain: `{item['domain_name']}`, " if item.get("domain_name") else ""
            line = f"- {domain}Reactions: {item['reaction_count']}, by {user.mention}, Content: {item['content']}"
            lines.append(line)
        
        # Split lines into chunks <= 1900 chars (give some margin)
        chunks = []
        current_chunk = ""
        for line in lines:
            if len(current_chunk) + len(line) + 1 > 1900:
                chunks.append(current_chunk)
                current_chunk = ""
            current_chunk += line + "\n"
        if current_chunk:
            chunks.append(current_chunk)

        await interaction.response.send_message(chunks[0])
        for chunk in chunks[1:]:
            await interaction.followup.send(chunk)

    except Exception as e:
        print(e)
        # If interaction is not responded to yet:
        try:
            await interaction.response.send_message("❗ Error fetching top posts.")
        except discord.errors.InteractionResponded:
            await interaction.followup.send("❗ Error fetching top posts.")

@client.tree.command(name="top_users", description="Get top users based on unique reactors.")
@app_commands.describe(post_type="Type of post", limit="Number of users", time_range="Time filter (week/month/all)")
async def top_users(interaction: discord.Interaction, post_type: str = "all", limit: int = 5, time_range: str = "all"):
    try:
        posters = db.get_top_posters(post_type, limit, time_range)
        if not posters:
            await interaction.response.send_message("No results found.")
            return

        lines = [f"🏆 Top {limit} {post_type} posters ({time_range}):"]
        for i, entry in enumerate(posters, 1):
            lines.append(f"{i}. <@{entry['user_id']}> with {entry['unique_reactors']} unique reactors")

        await interaction.response.send_message("\n".join(lines))
    except Exception as e:
        print(e)
        await interaction.response.send_message("❗ Error fetching top users.")

@client.tree.command(name="top_domain", description="Show the most linked domain in the server.")
async def top_domain(interaction: discord.Interaction):
    try:
        domain_data = db.get_top_domain(interaction.guild_id)
        if domain_data:
            domain, count = domain_data
            await interaction.response.send_message(f"**Most Linked Domain:** `{domain}` with {count} links.")
        else:
            await interaction.response.send_message("No domains found.")
    except Exception as e:
        print(e)
        await interaction.response.send_message("❗ Error fetching domain.")

@client.tree.command(name="makegif", description="Create a GIF from a YouTube video.")
@app_commands.describe(start_time="Start time in seconds", video_url="YouTube video URL")
async def makegif(interaction: discord.Interaction, start_time: float, video_url: str):
    await interaction.response.send_message("Downloading and processing your video... 🎬")
    try:
        gif_util.download_video(video_url, "temp_video.mp4")
        gif_util.video_to_gif("temp_video.mp4", "output.gif", start_time=start_time)
        await interaction.followup.send(file=discord.File("output.gif"))
    except Exception as e:
        await interaction.followup.send(f"An error occurred: {e}")
        import traceback; traceback.print_exc()
    finally:
        if os.path.exists("temp_video.mp4"): os.remove("temp_video.mp4")
        if os.path.exists("output.gif"): os.remove("output.gif")

@client.tree.command(name="contest", description="Show contest results for top link/media posters.")
@app_commands.describe(period="Choose week or month")
async def contest(interaction: discord.Interaction, period: str = "week"):
    if period not in ["week", "month"]:
        await interaction.response.send_message("Invalid period. Use 'week' or 'month'.")
        return
    try:
        top_links = db.get_top_posters("link", 5, period)
        top_media = db.get_top_posters("all", 5, period)

        embed = discord.Embed(
            title=f"🏆 {period.capitalize()}ly Contest Winners!",
            description=f"Top posters for the past {period}:",
            color=discord.Color.gold()
        )

        def format_entries(entries):
            return "\n".join(f"{i+1}. <@{e['user_id']}> — {e['unique_reactors']} reactions" for i, e in enumerate(entries)) or "No results."

        embed.add_field(name="🔗 Top Link Posters", value=format_entries(top_links), inline=False)
        embed.add_field(name="🖼️ Top Media Posters", value=format_entries(top_media), inline=False)

        await interaction.response.send_message(embed=embed)
    except Exception as e:
        print(e)
        await interaction.response.send_message("❗ Error fetching contest data.")

@client.tree.command(name="help", description="Shows all available bot commands.")
async def help_command(interaction: discord.Interaction):
    embed = discord.Embed(
        title="📖 Bot Help Menu",
        description="Here’s a list of all available commands:",
        color=discord.Color.blurple()
    )

    # Public command
    embed.add_field(
        name="/makegif <start_time> <youtube_url>",
        value="🎬 Creates a 5-second GIF starting from the specified time in a YouTube video.",
        inline=False
    )

    # Mod-only commands
    embed.add_field(
        name="/top_posts <post_type> [limit] [time_range]",
        value="🔝 Shows top posts by reaction count.\n"
              "• post_type: link, image, gif, movie, all\n"
              "• time_range: week, month, all (default: all)\n"
              "🔒 **Mod-only**",
        inline=False
    )

    embed.add_field(
        name="/top_users <post_type> [limit] [time_range]",
        value="👥 Shows top users by unique reactors.\n"
              "• post_type: link, image, gif, movie, all\n"
              "• time_range: week, month, all (default: all)\n"
              "🔒 **Mod-only**",
        inline=False
    )

    embed.add_field(
        name="/top_domain",
        value="🌐 Shows the most frequently linked domain.\n🔒 **Mod-only**",
        inline=False
    )

    embed.add_field(
        name="/contest [week|month]",
        value="🏆 Shows contest results for top link and media posters based on unique reactions.\n🔒 **Mod-only**",
        inline=False
    )

    embed.add_field(
        name="/backfill",
        value="📥 Manually trigger backfilling of messages in all text channels.\n🔒 **Mod-only**",
        inline=False
    )

    await interaction.response.send_message(embed=embed, ephemeral=True)

@client.event
async def on_raw_reaction_add(payload: discord.RawReactionActionEvent):
    if payload.user_id != client.user.id:
        db.add_reaction(str(payload.emoji), payload.user_id, payload.message_id)

@client.event
async def on_raw_reaction_remove(payload: discord.RawReactionActionEvent):
    if payload.user_id != client.user.id:
        db.remove_reaction(str(payload.emoji), payload.user_id, payload.message_id)

@client.event
async def on_message(message):
    if message.author == client.user:
        return
    converted = convert_link(message)
    if converted:
        await message.channel.send(converted)
    db.insert_media(message)

client.run(API_KEY)
