"""
result_formatter.py - Human-Readable SQL Result Formatting
Formats MySQL execution results into readable text displays for the chatbot UI,
preserving column names, handling NULL values, formatting numbers, and managing
large result sets gracefully.
"""

from decimal import Decimal
from typing import List, Tuple, Any, Optional

MAX_DISPLAY_ROWS = 25


def format_sql_results(
    cursor_description: Optional[List[Tuple[Any, ...]]],
    rows: List[Tuple[Any, ...]],
    max_display: int = MAX_DISPLAY_ROWS
) -> str:
    """
    Formats SQL execution results into a clear, readable text format.

    - Preserves column headers from cursor_description.
    - Handles NULL values (displayed as 'N/A').
    - Formats numbers, currencies, dates, and floats cleanly.
    - Automatically formats single scalar answers, single records, or aligned tabular data.
    - Truncates oversized result sets with an informative notice.
    """
    if not rows:
        return "No records found matching your query."

    if not cursor_description:
        return f"Query executed successfully ({len(rows)} rows returned)."

    headers = [col[0] for col in cursor_description]
    total_rows = len(rows)
    displayed_rows = rows[:max_display]

    def format_cell(val: Any) -> str:
        if val is None:
            return "N/A"
        if isinstance(val, (float, Decimal)):
            f_val = float(val)
            if f_val.is_integer():
                return f"{int(f_val):,}"
            return f"{f_val:,.2f}"
        if isinstance(val, int):
            return f"{val:,}"
        return str(val).strip()

    # Case 1: Single scalar value (1 row, 1 column)
    if len(headers) == 1 and total_rows == 1:
        val_str = format_cell(rows[0][0])
        col_name = headers[0]
        # Clean up column expression names like SUM(si.total_price)
        if any(fn in col_name.upper() for fn in ("SUM", "COUNT", "AVG", "MIN", "MAX")):
            return f"{col_name}: {val_str}"
        return f"Result ({col_name}): {val_str}"

    # Case 2: Single record with multiple columns (formatted as key-value pairs)
    if len(headers) > 1 and total_rows == 1:
        lines = []
        for header, val in zip(headers, rows[0]):
            lines.append(f"- {header}: {format_cell(val)}")
        return "\n".join(lines)

    # Case 3: Multiple records (formatted as an aligned text table)
    table_data = [[format_cell(cell) for cell in row] for row in displayed_rows]

    # Calculate column widths
    col_widths = [len(h) for h in headers]
    for row in table_data:
        for idx, cell in enumerate(row):
            col_widths[idx] = max(col_widths[idx], len(cell))

    # Construct the formatted table
    header_line = " | ".join(h.ljust(col_widths[i]) for i, h in enumerate(headers))
    sep_line = "-+-".join("-" * col_widths[i] for i in range(len(headers)))

    row_lines = [
        " | ".join(cell.ljust(col_widths[i]) for i, cell in enumerate(row))
        for row in table_data
    ]

    output = f"{header_line}\n{sep_line}\n" + "\n".join(row_lines)

    if total_rows > max_display:
        output += f"\n\n[Showing first {max_display} of {total_rows} total records]"
    else:
        output += f"\n\n({total_rows} {'record' if total_rows == 1 else 'records'} found)"

    return output
