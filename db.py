"""
db.py - Centralized Database Connection and Lifecycle Management
Provides secure database configuration from environment variables,
validation, and robust context managers to prevent connection leaks.
"""

import os
from contextlib import contextmanager
from typing import Dict, Any
from dotenv import load_dotenv

# Ensure environment variables are loaded
load_dotenv()


class DatabaseConfigError(Exception):
    """Raised when required database environment variables are missing or invalid."""
    pass


def get_db_config(readonly: bool = False) -> Dict[str, Any]:
    """
    Retrieves and validates MySQL database configuration from environment variables.

    If readonly=True, attempts to use CHATBOT_DB_USER / CHATBOT_DB_PASSWORD if configured,
    providing defense-in-depth for AI-generated query execution.

    Raises:
        DatabaseConfigError: If required configuration keys are missing or invalid.
    """
    host = os.getenv("DB_HOST", "").strip()
    name = os.getenv("DB_NAME", "").strip()
    port_str = os.getenv("DB_PORT", "3306").strip()

    missing = []
    if not host:
        missing.append("DB_HOST")
    if not name:
        missing.append("DB_NAME")

    # Use dedicated read-only credentials if requested and configured
    if readonly and os.getenv("CHATBOT_DB_USER"):
        user = os.getenv("CHATBOT_DB_USER", "").strip()
        password = os.getenv("CHATBOT_DB_PASSWORD", "").strip()
    else:
        user = os.getenv("DB_USER", "").strip()
        password = os.getenv("DB_PASSWORD", "").strip()

    if not user:
        missing.append("DB_USER (or CHATBOT_DB_USER)")
    if password is None or password == "":
        missing.append("DB_PASSWORD (or CHATBOT_DB_PASSWORD)")

    if missing:
        raise DatabaseConfigError(
            f"Missing required database configuration in .env: {', '.join(missing)}. "
            "Please check your .env file or copy from .env.example."
        )

    try:
        port = int(port_str)
    except ValueError:
        raise DatabaseConfigError(f"Invalid DB_PORT '{port_str}'. Must be an integer (default 3306).")

    return {
        "host": host,
        "user": user,
        "password": password,
        "database": name,
        "port": port,
        "connection_timeout": 5
    }


def get_db_connection(readonly: bool = False):
    """
    Establishes and returns a raw MySQL database connection.
    Callers should prefer the `get_db_cursor` context manager.
    """
    import mysql.connector

    config = get_db_config(readonly=readonly)
    try:
        return mysql.connector.connect(**config)
    except mysql.connector.Error as err:
        raise ConnectionError(
            f"Failed to connect to MySQL database at {config['host']}:{config['port']}. "
            f"Ensure MySQL is running and your credentials are correct. (Details: {err.msg})"
        ) from err


@contextmanager
def get_db_cursor(commit: bool = False, readonly: bool = False, dictionary: bool = False):
    """
    Context manager that yields an active MySQL cursor.

    Features:
    - Guaranteed cursor and connection closure via try/finally.
    - Automatic commit on successful completion (if commit=True).
    - Automatic rollback if an exception is raised during a modifying transaction.
    - Prevents dangling transactions and resource leaks.

    Usage:
        with get_db_cursor() as cursor:
            cursor.execute("SELECT * FROM products")
            rows = cursor.fetchall()

        with get_db_cursor(commit=True) as cursor:
            cursor.execute("INSERT INTO products ...", (...))
    """
    conn = get_db_connection(readonly=readonly)
    cursor = conn.cursor(dictionary=dictionary)
    try:
        yield cursor
        if commit:
            conn.commit()
    except Exception:
        if commit:
            try:
                conn.rollback()
            except Exception:
                pass
        raise
    finally:
        try:
            cursor.close()
        except Exception:
            pass
        try:
            conn.close()
        except Exception:
            pass
