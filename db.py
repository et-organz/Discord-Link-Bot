import psycopg2

# Define connection parameters
db_params = {
    "dbname": "your_database_name",
    "user": "your_username",
    "password": "your_password",
    "host": "your_host",  # e.g., "localhost" or an IP address
    "port": "5432"  # Default PostgreSQL port
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
