import mysql.connector
from mysql.connector import Error
from config.settings import DB_CONFIG


def get_connection():
    """
    Opens and returns a connection to the pythfinder_tracker database.
    Raises an exception if the connection fails.
    """
    try:
        connection = mysql.connector.connect(**DB_CONFIG)
        return connection
    except Error as e:
        raise ConnectionError(f"Failed to connect to database: {e}")


def close_connection(connection, cursor=None):
    """
    Safely closes a cursor and/or connection.
    """
    if cursor:
        cursor.close()
    if connection and connection.is_connected():
        connection.close()
