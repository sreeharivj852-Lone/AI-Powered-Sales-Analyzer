"""
tests/test_chatbot_flow.py - Integration and Mock Tests for Chatbot Pipeline
Tests the complete end-to-end question -> Gemini -> SQL validator -> DB -> Result pipeline.
"""

import unittest
from unittest.mock import patch, MagicMock
from sales_chatbot import get_chatbot_response


class TestChatbotFlow(unittest.TestCase):
    """Test suite for the chatbot query execution pipeline."""

    @patch("sales_chatbot.generate_sql_from_question")
    @patch("sales_chatbot.get_db_cursor")
    def test_successful_chatbot_flow(self, mock_get_db_cursor, mock_generate_sql):
        mock_generate_sql.return_value = "SELECT p_Name, price FROM products WHERE price > 50"

        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = [("Gaming Mouse", 65.0), ("Mechanical Keyboard", 120.0)]
        mock_cursor.description = [("p_Name",), ("price",)]
        mock_get_db_cursor.return_value.__enter__.return_value = mock_cursor

        response = get_chatbot_response("Show expensive products")

        self.assertIn("Gaming Mouse", response)
        self.assertIn("Mechanical Keyboard", response)
        self.assertIn("[Executed: SELECT p_Name, price FROM products WHERE price > 50", response)

    @patch("sales_chatbot.generate_sql_from_question")
    @patch("sales_chatbot.get_db_cursor")
    def test_unsafe_ai_generated_sql_rejected_before_db_execution(self, mock_get_db_cursor, mock_generate_sql):
        # Suppose Gemini hallucinated or was tricked into generating an injection
        mock_generate_sql.return_value = "DROP TABLE products; --"

        response = get_chatbot_response("Delete everything")

        self.assertIn("Security Notice: Query execution rejected", response)
        # Database cursor should NEVER be opened or executed
        mock_get_db_cursor.assert_not_called()

    @patch("sales_chatbot.generate_sql_from_question")
    @patch("sales_chatbot.get_db_cursor")
    def test_unauthorized_table_rejected_before_db_execution(self, mock_get_db_cursor, mock_generate_sql):
        mock_generate_sql.return_value = "SELECT * FROM user_passwords"

        response = get_chatbot_response("Show passwords")

        self.assertIn("Security Notice: Query execution rejected", response)
        self.assertIn("Unauthorized table reference", response)
        mock_get_db_cursor.assert_not_called()


if __name__ == "__main__":
    unittest.main()
