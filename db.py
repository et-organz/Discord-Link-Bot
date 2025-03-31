import psycopg2
import asyncpg
import os
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
