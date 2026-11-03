"""
tests/test_db_config.py - Unit Tests for Database Configuration & Environment Management
Tests configuration loading, validation of required environment variables,
read-only credential selection, and error reporting.
"""

import os
import unittest
from unittest.mock import patch, MagicMock
from db import get_db_config, DatabaseConfigError, get_db_cursor


class TestDatabaseConfig(unittest.TestCase):
    """Test suite for database environment configuration and validation."""

    def test_missing_all_env_vars_raises_error(self):
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(DatabaseConfigError) as ctx:
                get_db_config()
            self.assertIn("Missing required database configuration", str(ctx.exception))
            self.assertIn("DB_HOST", str(ctx.exception))
            self.assertIn("DB_NAME", str(ctx.exception))

    def test_missing_db_password_raises_error(self):
        mock_env = {
            "DB_HOST": "localhost",
            "DB_NAME": "sales",
            "DB_USER": "root",
            "DB_PASSWORD": ""  # Missing/empty password
        }
        with patch.dict(os.environ, mock_env, clear=True):
            with self.assertRaises(DatabaseConfigError) as ctx:
                get_db_config()
            self.assertIn("DB_PASSWORD", str(ctx.exception))

    def test_valid_env_config(self):
        mock_env = {
            "DB_HOST": "127.0.0.1",
            "DB_PORT": "3306",
            "DB_NAME": "sales",
            "DB_USER": "sales_admin",
            "DB_PASSWORD": "SecretPassword123"
        }
        with patch.dict(os.environ, mock_env, clear=True):
            config = get_db_config()
            self.assertEqual(config["host"], "127.0.0.1")
            self.assertEqual(config["port"], 3306)
            self.assertEqual(config["database"], "sales")
            self.assertEqual(config["user"], "sales_admin")
            self.assertEqual(config["password"], "SecretPassword123")

    def test_invalid_port_raises_error(self):
        mock_env = {
            "DB_HOST": "localhost",
            "DB_NAME": "sales",
            "DB_USER": "root",
            "DB_PASSWORD": "secret_password",
            "DB_PORT": "not_a_number"
        }
        with patch.dict(os.environ, mock_env, clear=True):
            with self.assertRaises(DatabaseConfigError) as ctx:
                get_db_config()
            self.assertIn("Invalid DB_PORT", str(ctx.exception))

    def test_readonly_user_fallback_and_selection(self):
        # When CHATBOT_DB_USER is set, readonly=True should use it
        mock_env_with_ro = {
            "DB_HOST": "localhost",
            "DB_NAME": "sales",
            "DB_USER": "root",
            "DB_PASSWORD": "root_password",
            "CHATBOT_DB_USER": "sales_readonly",
            "CHATBOT_DB_PASSWORD": "ro_password"
        }
        with patch.dict(os.environ, mock_env_with_ro, clear=True):
            ro_config = get_db_config(readonly=True)
            self.assertEqual(ro_config["user"], "sales_readonly")
            self.assertEqual(ro_config["password"], "ro_password")

            rw_config = get_db_config(readonly=False)
            self.assertEqual(rw_config["user"], "root")

    @patch("db.get_db_connection")
    def test_get_db_cursor_context_manager_cleanup(self, mock_get_conn):
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_get_conn.return_value = mock_conn

        # Test normal flow
        with get_db_cursor(commit=True) as cur:
            cur.execute("SELECT 1")

        mock_conn.commit.assert_called_once()
        mock_cursor.close.assert_called_once()
        mock_conn.close.assert_called_once()

    @patch("db.get_db_connection")
    def test_get_db_cursor_context_manager_rollback_on_error(self, mock_get_conn):
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_get_conn.return_value = mock_conn

        with self.assertRaises(ValueError):
            with get_db_cursor(commit=True) as cur:
                cur.execute("INSERT INTO products ...")
                raise ValueError("Simulated database query failure")

        mock_conn.rollback.assert_called_once()
        mock_cursor.close.assert_called_once()
        mock_conn.close.assert_called_once()


if __name__ == "__main__":
    unittest.main()
