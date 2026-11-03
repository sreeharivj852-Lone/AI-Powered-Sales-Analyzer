# -------------------- Libraries --------------------
import mysql.connector
from tkinter import *
from google import genai

# -------------------- API Setup --------------------
import os
from dotenv import load_dotenv

load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")
client = genai.Client(api_key=api_key) if api_key else genai.Client()

# -------------------- DB Connection --------------------
connection = mysql.connector.connect(
    host=os.getenv("DB_HOST", "localhost"),
    user=os.getenv("DB_USER", "root"),
    password=os.getenv("DB_PASSWORD", "root"),
    database=os.getenv("DB_NAME", "sales")
)
cursor = connection.cursor()

# -------------------- Chatbot Logic --------------------
def get_chatbot_response(user_input):
    prompt = f"""
    You are an expert MySQL query generator.

    Database name: sales

    Tables:
    products(product_ID, p_Name, price)
    sale_items(sale_id, product_id, quantity, total_price)
    sales(sale_id, sale_date)

    Rules:
    - Only SELECT queries
    - Use JOINs when needed
    - Prefer SUM(total_price) for revenue
    - Return ONLY SQL query (no explanation)

    User Question:
    {user_input}
    """

    try:
        response = client.models.generate_content(
            model="models/gemini-2.5-flash-lite",
            contents=prompt
        )

        query = response.text.strip()
        query = query.replace("```sql", "").replace("```", "").strip()

        cursor.execute(query)
        data = cursor.fetchall()

        if not data:
            return "No data found."

        # Clean output
        result = data[0][0]

        if isinstance(result, float):
            result = int(result) if result.is_integer() else round(result, 2)

        return f"Result: {result}"

    except Exception as e:
        return f"Error: {e}"

# -------------------- Chatbot UI --------------------
def open_chatbot():
    win = Toplevel()
    win.title("AI Sales Assistant")
    win.geometry("500x600")

    # Chat display
    chat_area = Text(win, wrap=WORD, state='disabled')
    chat_area.pack(padx=10, pady=10, fill=BOTH, expand=True)

    # Scrollbar
    scrollbar = Scrollbar(chat_area)
    scrollbar.pack(side=RIGHT, fill=Y)
    chat_area.config(yscrollcommand=scrollbar.set)
    scrollbar.config(command=chat_area.yview)

    # Input field
    entry = Entry(win)
    entry.pack(padx=10, pady=5, fill=X)

    def send():
        user_msg = entry.get()
        entry.delete(0, END)

        if not user_msg.strip():
            return

        chat_area.config(state='normal')
        chat_area.insert(END, f"You: {user_msg}\n")

        bot_reply = get_chatbot_response(user_msg)

        chat_area.insert(END, f"Bot: {bot_reply}\n\n")
        chat_area.config(state='disabled')
        chat_area.see(END)

    # Send button
    Button(win, text="Send", command=send).pack(pady=5)

    # Enter key support
    entry.bind("<Return>", lambda event: send())