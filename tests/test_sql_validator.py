"""
tests/test_sql_validator.py - Comprehensive Unit Tests for SQL Validator
Tests SELECT acceptance, modifying statement rejection (INSERT, UPDATE, DELETE,
DROP, etc.), multi-statement rejection, table whitelist enforcement, comments,
and dangerous SQL constructs.
"""

import unittest
from sql_validator import validate_and_sanitize_sql, SQLValidationResult


class TestSQLValidator(unittest.TestCase):
    """Test suite for the AI SQL validation engine."""

    # ------------------ 1. SELECT Query Acceptance ------------------
    def test_simple_select_accepted(self):
        query = "SELECT * FROM products"
        res = validate_and_sanitize_sql(query)
        self.assertTrue(res.is_valid)
        self.assertIn("SELECT * FROM products", res.query)
        self.assertIn("LIMIT", res.query)

    def test_aggregate_select_accepted(self):
        query = "SELECT SUM(total_price) FROM sale_items"
        res = validate_and_sanitize_sql(query)
        self.assertTrue(res.is_valid)
        self.assertIn("SUM(total_price)", res.query)

    def test_multi_table_join_accepted(self):
        query = """
        SELECT s.sale_date, p.p_Name, si.quantity, si.total_price
        FROM sales s
        JOIN sale_items si ON s.sale_id = si.sale_id
        JOIN products p ON si.product_id = p.product_ID
        WHERE s.sale_date >= '2026-01-01'
        ORDER BY s.sale_date DESC
        LIMIT 20
        """
        res = validate_and_sanitize_sql(query)
        self.assertTrue(res.is_valid)
        self.assertIn("LIMIT 20", res.query)

    def test_markdown_code_fences_stripped_and_accepted(self):
        query = "```sql\nSELECT p_Name, price FROM products WHERE price > 50\n```"
        res = validate_and_sanitize_sql(query)
        self.assertTrue(res.is_valid)
        self.assertIn("SELECT p_Name, price FROM products", res.query)

    def test_subquery_on_allowed_tables_accepted(self):
        query = "SELECT p.p_Name FROM (SELECT * FROM products WHERE price < 100) p"
        res = validate_and_sanitize_sql(query)
        self.assertTrue(res.is_valid)

    def test_explicit_schema_qualification_accepted(self):
        query = "SELECT * FROM sales.products"
        res = validate_and_sanitize_sql(query)
        self.assertTrue(res.is_valid)

    # ------------------ 2. Modifying Statement Rejections ------------------
    def test_insert_query_rejected(self):
        query = "INSERT INTO products (product_ID, p_Name, price) VALUES ('99', 'Fake', 10.0)"
        res = validate_and_sanitize_sql(query)
        self.assertFalse(res.is_valid)
        self.assertIn("Only read-only SELECT", res.error)

    def test_update_query_rejected(self):
        query = "UPDATE products SET price = 0 WHERE product_ID = '1'"
        res = validate_and_sanitize_sql(query)
        self.assertFalse(res.is_valid)
        self.assertIn("Only read-only SELECT", res.error)

    def test_delete_query_rejected(self):
        query = "DELETE FROM sales WHERE sale_id = 1"
        res = validate_and_sanitize_sql(query)
        self.assertFalse(res.is_valid)
        self.assertIn("Only read-only SELECT", res.error)

    def test_drop_query_rejected(self):
        query = "DROP TABLE products"
        res = validate_and_sanitize_sql(query)
        self.assertFalse(res.is_valid)
        self.assertIn("Only read-only SELECT", res.error)

    def test_alter_query_rejected(self):
        query = "ALTER TABLE products ADD COLUMN secret_key VARCHAR(255)"
        res = validate_and_sanitize_sql(query)
        self.assertFalse(res.is_valid)
        self.assertIn("Only read-only SELECT", res.error)

    def test_truncate_query_rejected(self):
        query = "TRUNCATE TABLE sale_items"
        res = validate_and_sanitize_sql(query)
        self.assertFalse(res.is_valid)
        self.assertIn("Only read-only SELECT", res.error)

    def test_create_query_rejected(self):
        query = "CREATE TABLE backdoor (id INT)"
        res = validate_and_sanitize_sql(query)
        self.assertFalse(res.is_valid)
        self.assertIn("Only read-only SELECT", res.error)

    def test_replace_query_rejected(self):
        query = "REPLACE INTO products VALUES ('1', 'shoe', 15.0)"
        res = validate_and_sanitize_sql(query)
        self.assertFalse(res.is_valid)
        self.assertIn("Only read-only SELECT", res.error)

    def test_grant_query_rejected(self):
        query = "GRANT ALL PRIVILEGES ON *.* TO 'attacker'@'%'"
        res = validate_and_sanitize_sql(query)
        self.assertFalse(res.is_valid)

    # ------------------ 3. Multiple Statement Rejection ------------------
    def test_multiple_statements_rejected(self):
        query = "SELECT * FROM products; DROP TABLE products;"
        res = validate_and_sanitize_sql(query)
        self.assertFalse(res.is_valid)
        self.assertIn("Multiple SQL statements", res.error)

    def test_chained_select_statements_rejected(self):
        query = "SELECT * FROM products; SELECT * FROM sales;"
        res = validate_and_sanitize_sql(query)
        self.assertFalse(res.is_valid)
        self.assertIn("Multiple SQL statements", res.error)

    # ------------------ 4. Dangerous Construct Rejections ------------------
    def test_into_outfile_rejected(self):
        query = "SELECT * FROM products INTO OUTFILE '/var/lib/mysql-files/dump.txt'"
        res = validate_and_sanitize_sql(query)
        self.assertFalse(res.is_valid)
        self.assertIn("OUTFILE", res.error)

    def test_sleep_and_benchmark_rejected(self):
        res1 = validate_and_sanitize_sql("SELECT SLEEP(10)")
        self.assertFalse(res1.is_valid)
        self.assertIn("SLEEP", res1.error)

        res2 = validate_and_sanitize_sql("SELECT BENCHMARK(10000000, MD5(1))")
        self.assertFalse(res2.is_valid)
        self.assertIn("BENCHMARK", res2.error)

    def test_system_variable_rejected(self):
        query = "SELECT @@version"
        res = validate_and_sanitize_sql(query)
        self.assertFalse(res.is_valid)
        self.assertIn("system variables", res.error)

    def test_system_schema_access_rejected(self):
        query = "SELECT * FROM mysql.user"
        res = validate_and_sanitize_sql(query)
        self.assertFalse(res.is_valid)
        self.assertTrue("MYSQL" in res.error or "Unauthorized" in res.error)

    def test_information_schema_rejected(self):
        query = "SELECT table_name FROM information_schema.tables"
        res = validate_and_sanitize_sql(query)
        self.assertFalse(res.is_valid)

    def test_sql_comments_rejected(self):
        res1 = validate_and_sanitize_sql("SELECT * FROM products -- comment here")
        self.assertFalse(res1.is_valid)
        self.assertIn("comment", res1.error.lower())

        res2 = validate_and_sanitize_sql("/* evil comment */ SELECT * FROM products")
        self.assertFalse(res2.is_valid)
        self.assertIn("comment", res2.error.lower())

    # ------------------ 5. Table Whitelist Rejections ------------------
    def test_unauthorized_table_rejected(self):
        query = "SELECT * FROM users"
        res = validate_and_sanitize_sql(query)
        self.assertFalse(res.is_valid)
        self.assertIn("Unauthorized table reference: 'users'", res.error)

    def test_subquery_unauthorized_table_rejected(self):
        query = "SELECT * FROM (SELECT * FROM credentials) c"
        res = validate_and_sanitize_sql(query)
        self.assertFalse(res.is_valid)
        self.assertIn("Unauthorized table reference", res.error)

    # ------------------ 6. Invalid and Empty SQL ------------------
    def test_empty_sql_rejected(self):
        res = validate_and_sanitize_sql("")
        self.assertFalse(res.is_valid)
        self.assertIn("Empty SQL query", res.error)

    def test_non_sql_text_rejected(self):
        res = validate_and_sanitize_sql("I cannot answer this question.")
        self.assertFalse(res.is_valid)


if __name__ == "__main__":
    unittest.main()
