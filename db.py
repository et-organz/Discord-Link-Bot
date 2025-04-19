import json

import psycopg2
import asyncpg
import os
from link_util import is_link, convert_link
from dotenv import load_dotenv

load_dotenv()  # Load environment variables
database=os.getenv("DB_NAME")
user=os.getenv("DB_USER")
password=os.getenv("DB_PASSWORD") 
host=os.getenv("DB_HOST")
port=os.getenv("DB_PORT")

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
def get_top_links(guild_id):
    with conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT message_id, domain_name, reactions
                FROM link_messages
                WHERE guild_id = %s
                ORDER BY (
                    SELECT SUM(value::int)
                    FROM jsonb_each_text(reactions)
                    WHERE key != 'reactors'
                ) DESC
                LIMIT 5;
            """, (guild_id,))
            return cur.fetchall()

def get_top_media(guild_id, media_type):
    with conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT message_id, reactions
                FROM media_messages
                WHERE guild_id = %s AND media_type = %s
                ORDER BY (
                    SELECT SUM(value::int)
                    FROM jsonb_each_text(reactions)
                    WHERE key != 'reactors'
                ) DESC
                LIMIT 1;
            """, (guild_id, media_type))
            return cur.fetchone()

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
def add_reaction(emoji,user_id,message_id):
    with conn:
        with conn.cursor() as cur:
            def update_db(db):
                cur.execute(f'SELECT reactions FROM {db} WHERE message_id = %s;', (message_id,))
                result = cur.fetchone()
                reactions = result[0] if result and result[0] else {}
                if reactions == {}:
                    return
                # Add user ID to the emoji list if not already present
                if emoji not in reactions:
                    reactions[emoji] = []
                if 'reactors' not in reactions:
                    reactions['reactors'] = {'user_id':[emoji]}
                else:
                    reactions['reactors']['user_id'].append(emoji)

                if user_id not in reactions[emoji]:
                    reactions[emoji].append(user_id)
                # Update the DB
                cur.execute(f'UPDATE {db} SET reactions = %s WHERE message_id = %s;',\
                            (json.dumps(reactions), message_id))

            update_db('link_messages')
            update_db('media_messages')
def remove_reaction(emoji, user_id, message_id):
    with conn:
        with conn.cursor() as cur:
            def update_db(db):
                cur.execute(f'SELECT reactions FROM {db} WHERE message_id = %s;', (message_id,))
                result = cur.fetchone()
                reactions = result[0] if result and result[0] else {}
                if reactions == {}:
                    return

                # Remove the user from the emoji's list
                if emoji in reactions and user_id in reactions[emoji]:
                    reactions[emoji].remove(user_id)
                    if not reactions[emoji]:
                        del reactions[emoji]

                # Remove from 'reactors' if present
                if 'reactors' in reactions and 'user_id' in reactions['reactors']:
                    if emoji in reactions['reactors']['user_id']:
                        reactions['reactors']['user_id'].remove(emoji)
                    # Clean up if empty
                    if not reactions['reactors']['user_id']:
                        del reactions['reactors']['user_id']
                    if not reactions['reactors']:
                        del reactions['reactors']

                # Update the DB
                result = cur.exefffcfcffcute(f'UPDATE {db} SET reactions = %s WHERE message_id = %s;',\
                            (json.dumps(reactions), message_id))
                print(result)

            update_db('link_messages')
            update_db('media_messages')





def insert_media(message):


    message_id = message.id
    user_id = message.author.id
    channel_id = message.channel.id
    guild_id = message.guild.id if message.guild else None  # DM check
    created_at = message.created_at
    link = is_link(message)
    _, domain_name = convert_link(message)


    simple_dict = {}
    with conn:
        with conn.cursor() as cur:

            if link:
                result = cur.execute("""
                    INSERT INTO link_messages  (
                        message_id, user_id, channel_id, guild_id, domain_name, reactions
                    ) VALUES (%s, %s, %s, %s, %s, %s)
                    ON CONFLICT (message_id) DO NOTHING;
                """, (
                    message_id,
                    user_id,
                    channel_id,
                    guild_id,
                    domain_name,
                    json.dumps(simple_dict, ensure_ascii=False, indent=2)
                ))
                print("result of link ", result)
            if message.attachments:
                media_type = None
                for attachment in message.attachments:
                    content_type = attachment.content_type or attachment.filename
                    if "image" in content_type:
                        media_type = "image"
                        break
                    elif "video" in content_type:
                        media_type = "video"
                        break
                    elif "gif" in content_type or attachment.filename.lower().endswith(".gif"):
                        media_type = "gif"
                        break
                if media_type:
                    cur.execute("""
                        INSERT INTO media_messages   (
                            message_id, user_id, channel_id, guild_id, media_type, reactions 
                        ) VALUES (%s, %s, %s, %s, %s, %s)
                        ON CONFLICT (message_id) DO NOTHING;
                    """, (
                        message_id,
                        user_id,
                        channel_id,
                        guild_id,
                        media_type,
                        json.dumps(simple_dict, ensure_ascii=False, indent=2)
                    ))

