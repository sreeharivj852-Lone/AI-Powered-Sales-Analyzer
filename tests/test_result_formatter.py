"""
tests/test_result_formatter.py - Unit Tests for SQL Result Formatting
Tests empty results, NULL handling, scalar values, single rows, multi-row tables,
and truncation handling.
"""

import unittest
from decimal import Decimal
from result_formatter import format_sql_results


class TestResultFormatter(unittest.TestCase):
    """Test suite for result formatting logic."""

    def test_empty_results(self):
        desc = [("product_ID",), ("p_Name",), ("price",)]
        rows = []
        result = format_sql_results(desc, rows)
        self.assertEqual(result, "No records found matching your query.")

    def test_single_scalar_result(self):
        desc = [("SUM(total_price)",)]
        rows = [(Decimal("14250.75"),)]
        result = format_sql_results(desc, rows)
        self.assertIn("SUM(total_price): 14,250.75", result)

    def test_single_row_multiple_columns(self):
        desc = [("p_Name",), ("price",)]
        rows = [("Wireless Mouse", Decimal("29.99"))]
        result = format_sql_results(desc, rows)
        self.assertIn("- p_Name: Wireless Mouse", result)
        self.assertIn("- price: 29.99", result)

    def test_multi_row_multi_column_table(self):
        desc = [("ID",), ("Name",), ("Price",)]
        rows = [
            ("P01", "Keyboard", Decimal("49.99")),
            ("P02", "Monitor", Decimal("299.00")),
            ("P03", "Mousepad", Decimal("15.50")),
        ]
        result = format_sql_results(desc, rows)
        # Should include table headers
        self.assertIn("ID", result)
        self.assertIn("Name", result)
        self.assertIn("Price", result)
        # Should include rows
        self.assertIn("Keyboard", result)
        self.assertIn("Monitor", result)
        self.assertIn("Mousepad", result)
        self.assertIn("(3 records found)", result)

    def test_null_value_formatting(self):
        desc = [("product_ID",), ("p_Name",), ("price",)]
        rows = [("P99", "Unpriced Item", None)]
        result = format_sql_results(desc, rows)
        self.assertIn("N/A", result)

    def test_truncation_with_large_result_sets(self):
        desc = [("id",), ("val",)]
        rows = [(i, f"Item {i}") for i in range(1, 40)]  # 39 rows
        result = format_sql_results(desc, rows, max_display=10)
        self.assertIn("[Showing first 10 of 39 total records]", result)


if __name__ == "__main__":
    unittest.main()
