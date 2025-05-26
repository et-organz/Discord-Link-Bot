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

def get_top_posters(post_type: str = "all", limit: int = 5, time_range: str = "all"):
    with conn:
        with conn.cursor() as cur:
            queries = []
            params = []

            # Date filtering based on time_range
            date_filter = ""
            if time_range == "week":
                start_date = datetime.utcnow() - timedelta(days=7)
                date_filter = "AND created_at >= %s"
                date_params = [start_date]
            elif time_range == "month":
                start_date = datetime.utcnow() - timedelta(days=30)
                date_filter = "AND created_at >= %s"
                date_params = [start_date]
            else:
                date_params = []

            # Media messages
            if post_type.lower() in ["image", "gif", "movie"]:
                queries.append(f"""
                    SELECT user_id, SUM(array_length(reactors, 1)) AS total_unique_reactors
                    FROM media_messages
                    WHERE media_type = %s {date_filter}
                    GROUP BY user_id
                """)
                params.extend([post_type] + date_params)

            # Link messages
            elif post_type.lower() == "link":
                queries.append(f"""
                    SELECT user_id, SUM(array_length(reactors, 1)) AS total_unique_reactors
                    FROM link_messages
                    WHERE 1=1 {date_filter}
                    GROUP BY user_id
                """)
                params.extend(date_params)

            # All posts
            elif post_type.lower() == "all":
                queries.append(f"""
                    SELECT user_id, SUM(array_length(reactors, 1)) AS total_unique_reactors
                    FROM media_messages
                    WHERE 1=1 {date_filter}
                    GROUP BY user_id
                """)
                queries.append(f"""
                    SELECT user_id, SUM(array_length(reactors, 1)) AS total_unique_reactors
                    FROM link_messages
                    WHERE 1=1 {date_filter}
                    GROUP BY user_id
                """)
                params.extend(date_params * 2)  # For both media + link

            # Combine and finalize query
            union_query = " UNION ALL ".join(queries)
            final_query = f"""
                SELECT user_id, SUM(total_unique_reactors) AS overall_reactors
                FROM ({union_query}) AS combined
                GROUP BY user_id
                ORDER BY overall_reactors DESC NULLS LAST
                LIMIT %s;
            """

            cur.execute(final_query, (*params, limit))
            results = cur.fetchall()

            return [{"user_id": row[0], "unique_reactors": row[1] or 0} for row in results]


def get_top_links(guild_id, size):
    with conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT link, domain_name, user_id, 
                       COALESCE(cardinality(reactors), 0) AS reaction_count
                FROM link_messages
                WHERE guild_id = %s
                ORDER BY reaction_count DESC
                LIMIT %s;
            """, (guild_id, size))

            messages = cur.fetchall()

            return [
                (link, domain_name, reaction_count, user_id)
                for link, domain_name, user_id, reaction_count in messages
            ]


def get_top_media(guild_id, media_type, size):
    with conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT media_url, user_id, 
                       COALESCE(cardinality(reactors), 0) AS reaction_count
                FROM media_messages
                WHERE guild_id = %s AND media_type = %s
                ORDER BY reaction_count DESC
                LIMIT %s;
            """, (guild_id, media_type, size))

            messages = cur.fetchall()

            return [
                (media_url, reaction_count, user_id)
                for media_url, user_id, reaction_count in messages
            ]

def get_top_domain(guild_id):
    with conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT domain_name, COUNT(*) AS count
                FROM link_messages
                WHERE guild_id = %s
                GROUP BY domain_name
                ORDER BY count DESC
                LIMIT 1;
            """, (guild_id,))
            result = cur.fetchone()
            return  result


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

def backfill_messages_from_history(messages):
    message_count = 0

    for message in messages:
        if message.author.bot:
            continue
        insert_media(message)
        message_count += 1

    return message_count