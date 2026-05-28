from config.database import get_connection, close_connection


class BaseModel:
    """
    Shared base for all model classes.
    Provides a context-managed DB connection so every model method
    can open a connection, do its work, and close cleanly — even on error.

    Usage in a subclass:
        with self.get_db() as (conn, cursor):
            cursor.execute("SELECT ...")
            return cursor.fetchall()
    """

    class _DBContext:
        def __init__(self):
            self.connection = None
            self.cursor = None

        def __enter__(self):
            self.connection = get_connection()
            self.cursor = self.connection.cursor(dictionary=True)
            return self.connection, self.cursor

        def __exit__(self, exc_type, exc_val, exc_tb):
            if exc_type is None:
                self.connection.commit()
            else:
                self.connection.rollback()
            close_connection(self.connection, self.cursor)
            return False  # re-raise any exception

    def get_db(self):
        return self._DBContext()
