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


from datetime import datetime, timedelta

def get_top_posts(guild_id: int, post_type: str = "all", limit: int | str = 5, time_range: str = "all"):
    """
    Retrieves top posts based on reaction count within a guild, filtered by type and time.
    Returns list of dicts with user_id, reaction_count, domain_name (or None), and content (media_url or link).
    """

    # Normalize limit
    if isinstance(limit, str):
        if limit.lower() == "all":
            limit = 10  # or another large number
        else:
            raise ValueError("`limit` must be an integer or the string 'all'")
    elif not isinstance(limit, int):
        raise ValueError("`limit` must be an integer or the string 'all'")

    # Date filtering
    date_filter = ""
    date_params = []
    if time_range == "week":
        start_date = datetime.utcnow() - timedelta(days=7)
        date_filter = "AND created_at >= %s"
        date_params = [start_date]
    elif time_range == "month":
        start_date = datetime.utcnow() - timedelta(days=30)
        date_filter = "AND created_at >= %s"
        date_params = [start_date]

    queries = []
    param_sets = []

    if post_type.lower() in ["image", "gif", "movie"]:
        queries.append(f"""
            SELECT user_id, array_length(reactors, 1) AS reaction_count, NULL AS domain_name, media_url AS content
            FROM media_messages
            WHERE guild_id = %s AND media_type = %s {date_filter}
            ORDER BY reaction_count DESC NULLS LAST
            LIMIT %s
        """)
        param_sets.append([guild_id, post_type] + date_params + [limit])

    elif post_type.lower() == "link":
        queries.append(f"""
            SELECT user_id, array_length(reactors, 1) AS reaction_count, domain_name, link AS content
            FROM link_messages
            WHERE guild_id = %s {date_filter}
            ORDER BY reaction_count DESC NULLS LAST
            LIMIT %s
        """)
        param_sets.append([guild_id] + date_params + [limit])

    elif post_type.lower() == "all":
        queries.append(f"""
            SELECT user_id, array_length(reactors, 1) AS reaction_count, NULL AS domain_name, media_url AS content
            FROM media_messages
            WHERE guild_id = %s {date_filter}
        """)
        param_sets.append([guild_id] + date_params)

        queries.append(f"""
            SELECT user_id, array_length(reactors, 1) AS reaction_count, domain_name, link AS content
            FROM link_messages
            WHERE guild_id = %s {date_filter}
        """)
        param_sets.append([guild_id] + date_params)

        union_query = " UNION ALL ".join(queries)
        final_query = f"""
            SELECT * FROM ({union_query}) AS combined
            ORDER BY reaction_count DESC NULLS LAST
            LIMIT %s
        """
        all_params = [param for param_set in param_sets for param in param_set] + [limit]

        with conn:
            with conn.cursor() as cur:
                cur.execute(final_query, all_params)
                results = cur.fetchall()
                return [
                    {
                        "user_id": row[0],
                        "reaction_count": row[1] or 0,
                        "domain_name": row[2],
                        "content": row[3]
                    } for row in results
                ]

    else:
        raise ValueError(f"Invalid post_type: {post_type}")

    # Single query case (image/gif/movie or link)
    final_query = queries[0]
    params = param_sets[0]

    with conn:
        with conn.cursor() as cur:
            cur.execute(final_query, params)
            results = cur.fetchall()
            return [
                {
                    "user_id": row[0],
                    "reaction_count": row[1] or 0,
                    "domain_name": row[2],
                    "content": row[3]
                } for row in results
            ]


def get_top_posters(post_type: str = "all", limit: int = 5, time_range: str = "all"):
    """
     Retrieves users with the most total reactions on their posts.

     Parameters:
     - post_type (str): Type of post to filter by ("image", "gif", "movie", "link", or "all"). Defaults to "all".
     - limit (int): Maximum number of top posters to return. Defaults to 5.
     - time_range (str): Time window for aggregation ("week", "month", or "all"). Defaults to "all".

     Returns:
     - List[dict]: List of dictionaries with user_id and their total unique reaction count.
     """
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


def get_top_domain(guild_id):
    """
    Retrieves the most frequently linked domain in a given guild.

    Parameters:
    - guild_id (int): ID of the guild to filter link messages.

    Returns:
    - Tuple[str, int]: The domain name and its count.
    """
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
            return result


def add_reaction(emoji, user_id, message_id):
    """
    Adds a reaction to a message and updates the reactors list.

    Parameters:
    - emoji (str): Emoji used for the reaction.
    - user_id (int): ID of the user who reacted.
    - message_id (int): ID of the message being reacted to.
    """
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
    """
    Removes a specific reaction from a message.

    Parameters:
    - emoji (str): Emoji of the reaction to be removed.
    - user_id (int): ID of the user whose reaction is to be removed.
    - message_id (int): ID of the message from which to remove the reaction.
    """
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
    """
    Inserts a message into either the link_messages or media_messages table based on its content.

    Parameters:
    - message (discord.Message): The message object to be inserted into the database.
    """
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
    """
    Inserts a list of messages into the database while skipping messages from bots.

    Parameters:
    - messages (List[discord.Message]): List of message objects to insert into the database.

    Returns:
    - int: Number of messages successfully inserted.
    """
    message_count = 0

    for message in messages:
        if message.author.bot:
            continue
        insert_media(message)
        message_count += 1

    return message_count