import json

import psycopg2
import asyncpg
import os
import re
from link_util import get_link_from_message, get_url_type
from dotenv import load_dotenv
from datetime import datetime, timedelta
from urllib.parse import urlparse

load_dotenv()  # Load environment variables
database=os.getenv("DB_NAME")
user=os.getenv("DB_USER")
password=os.getenv("DB_PASSWORD") 
host=os.getenv("DB_HOST")
port=os.getenv("DB_PORT")

url_pattern = re.compile(r'https?://\S+')

# Define connection parameters
db_params = {
    "dbname": database,
    "user": user,
    "password": password,
    "host": host,      
    "port":port   
}

try:
    # Establish connection
    conn = psycopg2.connect(**db_params)
    print("Connected to the database successfully!")

    # Create a cursor object
    cur = conn.cursor()

    # Execute a simple query
    cur.execute("SELECT version();")

    # Fetch and print the result
    db_version = cur.fetchone()
    print("PostgreSQL Database Version:", db_version)

    # Close cursor and connection
    cur.close()
    conn.close()
except Exception as e:
    print("Error connecting to the database:", e)
conn = psycopg2.connect(**db_params)

def get_top_links(guild_id,size):
    with conn:
        with conn.cursor() as cur:
            cur.execute("""
            SELECT link, domain_name, reactions, user_id
            FROM link_messages
            WHERE guild_id = %s;
            """, (guild_id,))
            messages = cur.fetchall()

            # Step 2: Calculate total reactions for each message and sort by that value
            message_reactions = []

            for message in messages:
                link = message[0]
                domain_name = message[1]
                reactions = message[2]  # Assuming reactions is stored as a JSON string
                user_id = message[3]
                if not reactions:
                    total_reactions = 0
                else:
                    # Calculate total reactions (excluding the 'reactors' key)
                    total_reactions = len(reactions['reactors'])

                message_reactions.append((link, domain_name, total_reactions, user_id))

            # Step 3: Sort the messages by total reactions in descending order and return top 5
            sorted_messages = sorted(message_reactions, key=lambda x: x[2], reverse=True)

            return sorted_messages[:size]

def get_top_media(guild_id, media_type, size):

    with conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT media_url, reactions, user_id
                FROM media_messages
                WHERE guild_id = %s AND media_type = %s
            """, (guild_id, media_type))
            messages = cur.fetchall()
            # Step 2: Calculate total reactions for each message and sort by that value
            message_reactions = []

            for message in messages:
                media_url = message[0]
                reactions = message[1]
                user_id = message[2]
                if not reactions:
                    total_reactions = 0
                else:
                    # Calculate total reactions (excluding the 'reactors' key)
                    total_reactions = len(reactions['reactors'])

                message_reactions.append((media_url, total_reactions, user_id))

            # Step 3: Sort the messages by total reactions in descending order and return top 5
            sorted_messages = sorted(message_reactions, key=lambda x: x[1], reverse=True)

            return sorted_messages[:size]

def get_top_domain(guild_id):
    with conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT domain_name, COUNT(*) as count
                FROM link_messages
                WHERE guild_id = %s
                GROUP BY domain_name
                ORDER BY count DESC
                LIMIT 1;
            """, (guild_id,))
        return cur.fetchone()
def add_reaction(emoji, user_id, message_id):
    with conn:
        with conn.cursor() as cur:
            def update_db(table_name):
                cur.execute(f"""
                    UPDATE {table_name}
                    SET reactions = (
                        SELECT ARRAY(
                            SELECT DISTINCT r FROM unnest(reactions || ARRAY[ROW(%s, %s)::reaction_tuple]) AS r
                        )
                    ),
                    reactors = (
                        SELECT ARRAY(
                            SELECT DISTINCT r.user_id FROM unnest(reactions || ARRAY[ROW(%s, %s)::reaction_tuple]) AS r
                        )
                    )
                    WHERE message_id = %s;
                """, (emoji, user_id, emoji, user_id, message_id))

            update_db('link_messages')
            update_db('media_messages')


def remove_reaction(emoji, user_id, message_id):
    with conn:
        with conn.cursor() as cur:
            def update_db(table_name):
                cur.execute("""
                    UPDATE {table_name}
                    SET reactions = ARRAY(
                        SELECT r FROM unnest(reactions) AS r
                        WHERE NOT (r.emoji = %s AND r.user_id = %s)
                    ),
                    reactors = ARRAY(
                        SELECT DISTINCT r.user_id FROM unnest(reactions) AS r
                        WHERE NOT (r.emoji = %s AND r.user_id = %s)
                    )
                    WHERE message_id = %s;
                """.format(table_name=table_name), (emoji, user_id, emoji, user_id, message_id))

            update_db('link_messages')
            update_db('media_messages')





def insert_media(message):


    message_id = message.id
    user_id = message.author.id
    channel_id = message.channel.id
    guild_id = message.guild.id if message.guild else None  # DM check
    link = get_link_from_message(message)
    domain_name = get_url_type(message)
    # Start with empty reactions array and reactors array
    reactions = []   # This should be a list of tuples (emoji, user_id)
    reactors = []    # This should be a list of unique user_ids who reacted

    with conn:
        with conn.cursor() as cur:

            if link:
                cur.execute("""
                    INSERT INTO link_messages (
                        message_id, user_id, channel_id, guild_id, link, domain_name, reactions, reactors
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (message_id) DO NOTHING;
                """, (
                    message_id,
                    user_id,
                    channel_id,
                    guild_id,
                    link,
                    domain_name,
                    reactions,    # pass empty list; psycopg2 converts to array
                    reactors      # pass empty list for reactors
                ))
            if message.attachments:

                media_type = None
                media_url = None
                for attachment in message.attachments:
                    content_type = attachment.content_type or attachment.filename
                    if "gif" in content_type or attachment.filename.lower().endswith(".gif"):
                        media_type = "gif"
                        media_url = attachment.url
                        break
                    elif "video" in content_type:
                        media_type = "video"
                        media_url = attachment.url
                        break
                    elif "image" in content_type:
                        media_type = "image"
                        media_url = attachment.url
                        break

                if media_type:
                    cur.execute("""
                            INSERT INTO media_messages (
                                message_id, user_id, channel_id, guild_id, media_url, media_type, reactions, reactors
                            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                            ON CONFLICT (message_id) DO NOTHING;
                        """, (
                        message_id,
                        user_id,
                        channel_id,
                        guild_id,
                        media_url,
                        media_type,
                        reactions,
                        reactors
                    ))

def get_top_posters(guild_id, period="week"):
    if period == "week":
        since = datetime.utcnow() - timedelta(days=7)
    elif period == "month":
        since = datetime.utcnow() - timedelta(days=30)
    else:
        raise ValueError("Period must be 'week' or 'month'.")

    with conn:
        with conn.cursor() as cur:
            # Get top link posters
            cur.execute("""
                SELECT user_id, COUNT(*) as link_count
                FROM link_messages
                WHERE guild_id = %s AND created_at >= %s
                GROUP BY user_id
                ORDER BY link_count DESC
                LIMIT 3;
            """, (guild_id, since))
            top_links = cur.fetchall()

            # Get top media posters
            cur.execute("""
                SELECT user_id, COUNT(*) as media_count
                FROM media_messages
                WHERE guild_id = %s AND created_at >= %s
                GROUP BY user_id
                ORDER BY media_count DESC
                LIMIT 3;
            """, (guild_id, since))
            top_media = cur.fetchall()

    return top_links, top_media

def extract_domain(link):
    try:
        parsed = urlparse(link)
        return parsed.netloc
    except Exception:
        return None

def backfill_links_from_history(messages, guild_id):
    insert_count = 0
    with conn:
        with conn.cursor() as cur:
            for message in messages:
                if message.author.bot:
                    continue

                urls = url_pattern.findall(message.content)
                for url in urls:
                    parsed = urlparse(url)
                    domain_name = parsed.netloc

                    cur.execute("""
                        INSERT INTO link_messages (message_id, user_id, guild_id, channel_id, domain_name, link, reactions, created_at)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                        ON CONFLICT (message_id) DO NOTHING;
                    """, (
                        message.id,
                        message.author.id,
                        guild_id,
                        message.channel.id,
                        domain_name,
                        url,
                        json.dumps({}),  
                        message.created_at
                    ))
                    insert_count += 1

    return insert_count

def detect_media_type(url):
    url = str(url)  # Ensure it's a string
    if url.endswith(('.jpg', '.jpeg', '.png', '.webp')):
        return 'image'
    elif url.endswith(('.mp4', '.mov', '.webm', '.mkv')):
        return 'video'
    elif url.endswith('.gif'):
        return 'gif'
    return None


def backfill_media_from_history(messages, guild_id):
    insert_count = 0
    with conn:
        with conn.cursor() as cur:
            for message in messages:
                media_items = []

                # Check for attachments
                for attachment in message.attachments:
                    media_type = detect_media_type(attachment.filename)
                    if media_type:
                        media_items.append((attachment.url, media_type))

                # Check embeds
                for embed in message.embeds:
                    if hasattr(embed, "url") and embed.url:
                        media_type = detect_media_type(embed.url)
                        if media_type:
                            media_items.append((str(embed.url), media_type))

                # Insert found media items
                for media_url, media_type in media_items:
                    cur.execute("""
                        INSERT INTO media_messages (
                            message_id, user_id, guild_id, channel_id,
                            media_type, media_url, reactions, created_at
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                        ON CONFLICT (message_id) DO NOTHING;
                    """, (
                        message.id,
                        message.author.id,
                        guild_id,
                        message.channel.id,
                        media_type,
                        media_url,
                        json.dumps({}),  # safely serialize empty reactions
                        message.created_at
                    ))
                    insert_count += 1
    return insert_count
