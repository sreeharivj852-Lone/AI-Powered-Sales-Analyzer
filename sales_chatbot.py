"""
sales_chatbot.py - AI Sales Assistant Chatbot
Integrates Google Gemini 2.5 Flash-Lite with MySQL using strict SQL validation,
background threading for non-blocking UI, and robust error handling.
"""

import os
import threading
from tkinter import (
    Toplevel, Text, Scrollbar, Entry, Button, Label, Frame,
    WORD, BOTH, RIGHT, Y, X, END, DISABLED, NORMAL
)
from dotenv import load_dotenv

from db import get_db_cursor, DatabaseConfigError
from sql_validator import validate_and_sanitize_sql
from result_formatter import format_sql_results

load_dotenv()


def _get_gemini_client():
    """
    Initializes and returns a Google GenAI client using GEMINI_API_KEY.
    Raises ValueError if API key is not configured.
    """
    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    if not api_key:
        raise ValueError(
            "Gemini API key is not configured. Please set GEMINI_API_KEY in your .env file."
        )

    try:
        from google import genai
        return genai.Client(api_key=api_key)
    except ImportError:
        raise ImportError(
            "The 'google-genai' package is not installed. Please install it via: pip install google-genai"
        )


def generate_sql_from_question(user_input: str) -> str:
    """
    Calls the Gemini API to translate a user's natural language question
    into a MySQL SELECT query.
    """
    client = _get_gemini_client()

    prompt = f"""
    You are an expert MySQL query generator.

    Database name: sales

    Tables:
    products(product_ID, p_Name, price)
    sale_items(id, sale_id, product_id, quantity, total_price)
    sales(sale_id, sale_date)

    Strict Rules:
    - Only generate read-only SELECT queries.
    - NEVER generate INSERT, UPDATE, DELETE, DROP, ALTER, TRUNCATE, or CREATE statements.
    - Use INNER JOIN or LEFT JOIN when connecting tables.
    - Prefer SUM(si.total_price) for calculating total revenue.
    - Return ONLY the raw SQL query with no explanation, no markdown quotes, and no commentary.

    User Question:
    {user_input}
    """

    response = client.models.generate_content(
        model="models/gemini-2.5-flash-lite",
        contents=prompt
    )

    if not response or not response.text:
        raise ValueError("Gemini returned an empty response.")

    return response.text.strip()


def get_chatbot_response(user_input: str) -> str:
    """
    Coordinates the natural language to SQL pipeline:
    1. Translates natural language question to SQL using Gemini.
    2. Validates SQL through strict AST parser and whitelist checks.
    3. Executes the sanitized query on MySQL using a read-only cursor.
    4. Formats results into clean, readable text.
    5. Catches and sanitizes all errors.
    """
    try:
        # Step 1: Generate SQL via Gemini
        raw_sql = generate_sql_from_question(user_input)

        # Step 2: Validate and sanitize SQL
        validation = validate_and_sanitize_sql(raw_sql)
        if not validation.is_valid:
            return (
                f"⚠️ Security Notice: Query execution rejected.\n"
                f"Reason: {validation.error}"
            )

        sanitized_sql = validation.query

        # Step 3: Execute validated SQL using read-only database cursor
        with get_db_cursor(readonly=True) as cursor:
            cursor.execute(sanitized_sql)
            rows = cursor.fetchall()
            desc = cursor.description

        # Step 4: Format results
        formatted_result = format_sql_results(desc, rows)
        return f"{formatted_result}\n\n[Executed: {sanitized_sql}]"

    except ValueError as ve:
        return f"Configuration/API Notice: {ve}"
    except DatabaseConfigError as dce:
        return f"Database Configuration Error: {dce}"
    except ConnectionError as ce:
        return f"Database Connection Error: {ce}"
    except Exception as e:
        err_str = str(e)
        # Avoid leaking internal system details or credentials
        if "API_KEY_INVALID" in err_str or "API key not valid" in err_str:
            return "Error: Invalid Gemini API key. Please check your GEMINI_API_KEY in .env."
        if "quota" in err_str.lower():
            return "Error: Gemini API quota exceeded. Please try again later."
        if "connect" in err_str.lower() or "timeout" in err_str.lower():
            return "Network/Connection Error: Request timed out or unable to reach service."

        # Generic safe error message
        return f"Error processing request: {err_str}"


def open_chatbot():
    """
    Launches the AI Sales Assistant Tkinter window.
    Implements background threading to prevent UI freezing during API calls.
    """
    win = Toplevel()
    win.title("AI Sales Assistant")
    win.geometry("520x620")
    win.minsize(450, 500)

    # Chat display text area
    chat_area = Text(win, wrap=WORD, state=DISABLED, font=("Arial", 10))
    chat_area.pack(padx=10, pady=(10, 5), fill=BOTH, expand=True)

    # Scrollbar
    scrollbar = Scrollbar(chat_area)
    scrollbar.pack(side=RIGHT, fill=Y)
    chat_area.config(yscrollcommand=scrollbar.set)
    scrollbar.config(command=chat_area.yview)

    # Status indicator
    status_label = Label(win, text="Ready", fg="#666666", anchor="w", font=("Arial", 9, "italic"))
    status_label.pack(padx=12, pady=(0, 5), fill=X)

    # Input controls frame
    input_frame = Frame(win)
    input_frame.pack(padx=10, pady=(0, 10), fill=X)

    entry = Entry(input_frame, font=("Arial", 11))
    entry.pack(side="left", fill=X, expand=True, padx=(0, 5), ipady=3)

    send_btn = Button(input_frame, text="Send", width=10, font=("Arial", 10, "bold"))
    send_btn.pack(side="right")

    # Welcome message
    chat_area.config(state=NORMAL)
    chat_area.insert(
        END,
        "Bot: Hello! I am your AI Sales Assistant. Ask me questions about products, "
        "sales transactions, or revenue!\n\n"
    )
    chat_area.config(state=DISABLED)

    def on_response_ready(reply_text: str):
        """Callback invoked on the main Tkinter thread when processing completes."""
        chat_area.config(state=NORMAL)
        chat_area.insert(END, f"Bot:\n{reply_text}\n\n")
        chat_area.config(state=DISABLED)
        chat_area.see(END)

        # Restore UI controls
        status_label.config(text="Ready", fg="#666666")
        entry.config(state=NORMAL)
        send_btn.config(state=NORMAL)
        entry.focus_set()

    def send():
        """Handles user message submission on a background thread."""
        user_msg = entry.get().strip()
        if not user_msg:
            return

        # Clear input field
        entry.delete(0, END)

        # Update chat display with user query
        chat_area.config(state=NORMAL)
        chat_area.insert(END, f"You: {user_msg}\n\n")
        chat_area.config(state=DISABLED)
        chat_area.see(END)

        # Disable controls to prevent duplicate submissions
        entry.config(state=DISABLED)
        send_btn.config(state=DISABLED)
        status_label.config(text="⏳ AI Assistant is thinking and querying database...", fg="#0055aa")

        # Execute query processing in background thread
        def worker():
            reply = get_chatbot_response(user_msg)
            # Safely schedule GUI update on main thread
            win.after(0, on_response_ready, reply)

        threading.Thread(target=worker, daemon=True).start()

    send_btn.config(command=send)
    entry.bind("<Return>", lambda event: send())
    entry.focus_set()
