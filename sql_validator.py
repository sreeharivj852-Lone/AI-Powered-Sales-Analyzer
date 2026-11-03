"""
sql_validator.py - Strict Security Validator for AI-Generated SQL Queries
Ensures AI-generated queries are strictly SELECT statements, adhere to an approved
schema and table whitelist, contain no multiple statements or forbidden constructs,
and prevents SQL injection or denial-of-service vulnerabilities.
"""

import re
from typing import Set, Optional
import sqlparse
from sqlparse.sql import IdentifierList, Identifier, Parenthesis
from sqlparse.tokens import Keyword, Comment

# Approved tables for query execution
ALLOWED_TABLES = {"products", "sales", "sale_items"}

# Approved database schema (only allow explicit qualification with 'sales')
ALLOWED_SCHEMAS = {"sales"}

# Forbidden keywords and operations (any occurrence is an immediate rejection)
FORBIDDEN_KEYWORDS = {
    "INSERT", "UPDATE", "DELETE", "DROP", "ALTER", "TRUNCATE", "CREATE",
    "REPLACE", "GRANT", "REVOKE", "LOCK", "UNLOCK", "RENAME", "CALL",
    "EXEC", "EXECUTE", "HANDLER", "DO", "SHUTDOWN", "KILL", "OUTFILE",
    "DUMPFILE", "LOAD_FILE", "LOAD DATA", "BENCHMARK", "SLEEP"
}

# Forbidden system schemas
FORBIDDEN_SCHEMAS = {
    "INFORMATION_SCHEMA", "PERFORMANCE_SCHEMA", "MYSQL", "SYS"
}

DEFAULT_ROW_LIMIT = 50


class SQLValidationResult:
    """Represents the outcome of SQL validation and sanitization."""
    def __init__(self, is_valid: bool, query: str = "", error: str = ""):
        self.is_valid = is_valid
        self.query = query
        self.error = error

    def __repr__(self):
        return f"SQLValidationResult(is_valid={self.is_valid}, query={self.query!r}, error={self.error!r})"


def _clean_query_text(raw_sql: str) -> str:
    """Strips markdown code fences and extraneous whitespace."""
    if not raw_sql:
        return ""
    text = raw_sql.strip()

    # Strip markdown code fences if present
    if text.startswith("```"):
        lines = text.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].startswith("```"):
            lines = lines[:-1]
        text = "\n".join(lines).strip()

    return text.strip().rstrip(";")


def _check_forbidden_tokens(tokens) -> Optional[str]:
    """Recursively inspects SQL tokens for forbidden keywords, schemas, or comments."""
    for token in tokens:
        # Check for comments
        if token.ttype in (Comment.Single, Comment.Multiline) or token.value.startswith(("--", "/*", "#")):
            return "SQL comments are not allowed."

        val_upper = token.value.strip().upper()

        # Check for access to system variables (e.g. @@version)
        if "@@" in val_upper:
            return "Accessing system variables (@@) is strictly forbidden."

        # Check for forbidden keywords using regex word boundary
        for forbidden in FORBIDDEN_KEYWORDS:
            if re.search(r'\b' + re.escape(forbidden) + r'\b', val_upper):
                return f"Disallowed SQL keyword or construct detected: '{forbidden}'"

        # Check for forbidden system schemas
        for forbidden_schema in FORBIDDEN_SCHEMAS:
            if re.search(r'\b' + re.escape(forbidden_schema) + r'\b', val_upper):
                return f"Access to system schema '{forbidden_schema}' is strictly forbidden."

        # Recurse into compound tokens
        if hasattr(token, "tokens") and token.tokens:
            nested_err = _check_forbidden_tokens(token.tokens)
            if nested_err:
                return nested_err

    return None


def _extract_table_names(tokens) -> Set[str]:
    """
    Extracts table names from FROM and JOIN clauses, correctly handling
    aliases, subqueries inside parentheses, and table joins.
    """
    tables = set()
    from_seen = False

    for token in tokens:
        if token.is_whitespace:
            continue

        # Handle subqueries wrapped in Parenthesis
        if isinstance(token, Parenthesis):
            tables.update(_extract_table_names(token.tokens))
            continue

        val_upper = token.value.upper()

        if token.ttype is Keyword and val_upper in (
            "FROM", "JOIN", "INNER JOIN", "LEFT JOIN", "RIGHT JOIN",
            "CROSS JOIN", "STRAIGHT_JOIN", "NATURAL JOIN"
        ):
            from_seen = True
            continue

        if from_seen:
            if isinstance(token, IdentifierList):
                for ident in token.get_identifiers():
                    # Check if identifier wraps a subquery parenthesis
                    if any(isinstance(s, Parenthesis) for s in getattr(ident, "tokens", [])):
                        tables.update(_extract_table_names(ident.tokens))
                    else:
                        real = ident.get_real_name()
                        if real:
                            parent = ident.get_parent_name()
                            tables.add(f"{parent}.{real}" if parent else real)
                from_seen = False
            elif isinstance(token, Identifier):
                if any(isinstance(s, Parenthesis) for s in getattr(token, "tokens", [])):
                    tables.update(_extract_table_names(token.tokens))
                else:
                    real = token.get_real_name()
                    if real:
                        parent = token.get_parent_name()
                        tables.add(f"{parent}.{real}" if parent else real)
                from_seen = False
            elif token.ttype is Keyword:
                # Encountered WHERE, GROUP BY, ORDER BY, LIMIT, etc.
                from_seen = False

        if hasattr(token, "tokens") and token.tokens and not isinstance(token, Identifier):
            tables.update(_extract_table_names(token.tokens))

    return tables


def validate_and_sanitize_sql(raw_sql: str, max_limit: int = DEFAULT_ROW_LIMIT) -> SQLValidationResult:
    """
    Validates that a generated SQL string:
    1. Is non-empty and syntactically valid.
    2. Contains exactly ONE statement (rejects multiple statements).
    3. Is strictly a SELECT statement (rejects INSERT, UPDATE, DELETE, DROP, etc.).
    4. References only allowed tables ('products', 'sales', 'sale_items').
    5. Contains no comments, dangerous system variables, or modifying commands.
    6. Ensures a sensible LIMIT is in place to prevent memory exhaustion.

    Returns:
        SQLValidationResult with is_valid=True and sanitized query, or is_valid=False and error.
    """
    cleaned = _clean_query_text(raw_sql)
    if not cleaned:
        return SQLValidationResult(False, error="Empty SQL query received.")

    # Reject inline comments before parsing
    if any(cleaned.startswith(prefix) for prefix in ("--", "#", "/*")):
        return SQLValidationResult(False, error="SQL comments are not allowed.")

    try:
        statements = sqlparse.parse(cleaned)
    except Exception as e:
        return SQLValidationResult(False, error=f"Malformed SQL query syntax: {e}")

    if not statements:
        return SQLValidationResult(False, error="No valid SQL statement found.")

    # Reject multiple statements (prevents chained SQL injection like 'SELECT 1; DROP TABLE products;')
    if len(statements) > 1:
        return SQLValidationResult(False, error="Multiple SQL statements are strictly forbidden.")

    stmt = statements[0]

    # Statement type check (must be SELECT)
    stmt_type = stmt.get_type().upper()
    if stmt_type != "SELECT":
        return SQLValidationResult(
            False,
            error=f"Only read-only SELECT queries are permitted. Attempted operation: '{stmt_type}'."
        )

    # Deep token verification for forbidden keywords/constructs
    forbidden_err = _check_forbidden_tokens(stmt.tokens)
    if forbidden_err:
        return SQLValidationResult(False, error=forbidden_err)

    # Extract and validate all referenced tables
    referenced_tables = _extract_table_names(stmt.tokens)

    for tbl in referenced_tables:
        clean_tbl = tbl.lower().strip("`")
        if "." in clean_tbl:
            parts = clean_tbl.split(".")
            if len(parts) == 2:
                schema_name, tbl_name = parts
                if schema_name not in ALLOWED_SCHEMAS or tbl_name not in ALLOWED_TABLES:
                    return SQLValidationResult(
                        False,
                        error=f"Unauthorized table/schema reference: '{tbl}'. Allowed tables: {', '.join(sorted(ALLOWED_TABLES))}."
                    )
            else:
                return SQLValidationResult(False, error=f"Invalid table qualification format: '{tbl}'.")
        elif clean_tbl not in ALLOWED_TABLES:
            return SQLValidationResult(
                False,
                error=f"Unauthorized table reference: '{tbl}'. Allowed tables: {', '.join(sorted(ALLOWED_TABLES))}."
            )

    # Enforce safe row limit if not already specified in query
    sanitized = cleaned
    if not re.search(r'\bLIMIT\s+\d+', sanitized, re.IGNORECASE):
        sanitized = f"{sanitized} LIMIT {max_limit}"

    return SQLValidationResult(True, query=sanitized)
