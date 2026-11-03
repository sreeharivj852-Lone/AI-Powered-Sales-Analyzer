import os
from dotenv import load_dotenv

load_dotenv()
import tkinter as tk
from tkinter import ttk
from PIL import Image, ImageTk
import mysql.connector
from datetime import date
import matplotlib.pyplot as plt
from sales_chatbot import open_chatbot

# ---------------- MAIN WINDOW ----------------
main_scrn = tk.Tk()
main_scrn.title('Sale Analyzer')
main_scrn.geometry("850x500")
main_scrn.resizable(False, False)

# Background Image
img = Image.open("salesanalyzer_bg.png").resize((850, 450))
bg_img = ImageTk.PhotoImage(img)
tk.Label(main_scrn, image=bg_img).place(x=0, y=0, relwidth=1, relheight=1)

# ---------------- COMMON DB FUNCTION ----------------
def get_connection():
    return mysql.connector.connect(
        host=os.getenv("DB_HOST", "localhost"),
        user=os.getenv("DB_USER", "root"),
        password=os.getenv("DB_PASSWORD", "root"),
        database=os.getenv("DB_NAME", "sales")
    )

# ---------------- EXIT ----------------
def exit_app():
    main_scrn.destroy()

# ---------------- PRODUCT INPUT ----------------
def open_product_input_window():
    win = tk.Toplevel()
    win.title("Add Product")
    win.geometry("400x220")

    alert = tk.Label(win)
    alert.place(x=120, y=130)

    tk.Label(win, text="Product ID").place(x=40, y=20)
    p1 = tk.Entry(win)
    p1.place(x=180, y=20)

    tk.Label(win, text="Name").place(x=40, y=60)
    n1 = tk.Entry(win)
    n1.place(x=180, y=60)

    tk.Label(win, text="Price").place(x=40, y=100)
    c1 = tk.Entry(win)
    c1.place(x=180, y=100)

    def save_product():
        p_id = p1.get()
        name = n1.get()
        price = c1.get()

        if not p_id or not name or not price:
            alert.config(text="⚠ Fill all fields", fg="orange")
            return

        try:
            price = float(price)
        except:
            alert.config(text="❌ Invalid price", fg="red")
            return

        try:
            conn = get_connection()
            cursor = conn.cursor()

            cursor.execute(
                "INSERT INTO products (product_ID, p_Name, price) VALUES (%s,%s,%s)",
                (p_id, name, price)
            )
            conn.commit()

            alert.config(text="✅ Saved", fg="green")
            p1.delete(0, tk.END)
            n1.delete(0, tk.END)
            c1.delete(0, tk.END)

            cursor.close()
            conn.close()

        except:
            alert.config(text="❌ Error / Duplicate ID", fg="red")

    tk.Button(win, text="SAVE", command=save_product).place(x=80, y=170)
    tk.Button(win, text="CLOSE", command=win.destroy).place(x=200, y=170)

# ---------------- VIEW PRODUCTS ----------------
def view_products():
    win = tk.Toplevel()
    win.title("Products")
    win.geometry("600x350")

    table = ttk.Treeview(win, columns=("ID","Name","Price"), show="headings")

    for col in ("ID","Name","Price"):
        table.heading(col, text=col)
        table.column(col, anchor="center")

    table.pack(fill="both", expand=True)

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM products")

    for row in cursor.fetchall():
        table.insert("", tk.END, values=row)

    cursor.close()
    conn.close()

# ---------------- SALES INPUT ----------------
def open_sales_in():
    items = []

    win = tk.Toplevel()
    win.title("Add Sale")
    win.geometry("400x300")

    alert = tk.Label(win)
    alert.place(x=120, y=200)

    tk.Label(win, text="Date (YYYY-MM-DD)").place(x=20, y=20)
    d1 = tk.Entry(win)
    d1.place(x=200, y=20)

    tk.Label(win, text="Product ID").place(x=20, y=60)
    p1 = tk.Entry(win)
    p1.place(x=200, y=60)

    tk.Label(win, text="Quantity").place(x=20, y=100)
    q1 = tk.Entry(win)
    q1.place(x=200, y=100)

    # Add Item
    def add_item():
        pid = p1.get()
        qty = q1.get()

        if not pid or not qty:
            alert.config(text="⚠ Fill fields", fg="orange")
            return

        try:
            qty = float(qty)
        except:
            alert.config(text="❌ Invalid quantity", fg="red")
            return

        items.append((pid, qty))
        alert.config(text=f"Added {pid} x {qty}", fg="green")

        p1.delete(0, tk.END)
        q1.delete(0, tk.END)

    # Save Sale
    def save_sale():
        d = d1.get()

        if not d or not items:
            alert.config(text="⚠ Add date & items", fg="orange")
            return

        try:
            d = date.fromisoformat(d)
        except:
            alert.config(text="❌ Invalid date", fg="red")
            return

        try:
            conn = get_connection()
            cursor = conn.cursor()

            cursor.execute("INSERT INTO sales (sale_date) VALUES (%s)", (d,))
            conn.commit()
            sale_id = cursor.lastrowid

            for pid, qty in items:
                cursor.execute("SELECT price FROM products WHERE product_ID=%s",(pid,))
                res = cursor.fetchone()

                if not res:
                    alert.config(text=f"❌ Invalid ID {pid}", fg="red")
                    return

                price = float(res[0])
                total = price * qty

                cursor.execute("""
                    INSERT INTO sale_items 
                    (sale_id, product_id, quantity, total_price)
                    VALUES (%s,%s,%s,%s)
                """,(sale_id, pid, qty, total))

            conn.commit()
            alert.config(text="✅ Sale Saved", fg="green")

            items.clear()
            d1.delete(0, tk.END)

            cursor.close()
            conn.close()

        except Exception as e:
            print(e)
            alert.config(text="❌ Error", fg="red")

    tk.Button(win, text="ADD", command=add_item).place(x=80, y=150)
    tk.Button(win, text="SAVE", command=save_sale).place(x=200, y=150)
    tk.Button(win, text="CLOSE", command=win.destroy).place(x=150, y=250)

# ---------------- VIEW SALES ----------------
def view_sales():
    win = tk.Toplevel()
    win.title("Sales")
    win.geometry("750x400")

    table = ttk.Treeview(win, columns=("Date","Product","Qty","Total"), show="headings")

    for col in ("Date","Product","Qty","Total"):
        table.heading(col, text=col)
        table.column(col, anchor="center")

    table.pack(fill="both", expand=True)

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT s.sale_date, p.p_Name, si.quantity, si.total_price
        FROM sales s
        JOIN sale_items si ON s.sale_id = si.sale_id
        JOIN products p ON si.product_id = p.product_ID
    """)

    for row in cursor.fetchall():
        table.insert("", tk.END, values=row)

    cursor.close()
    conn.close()
#-------------------view graph---------------------


def graph_sales_by_date():
    try:
        conn = get_connection()
        cursor = conn.cursor()

        query = """
        SELECT s.sale_date, SUM(si.total_price)
        FROM sales s
        JOIN sale_items si ON s.sale_id = si.sale_id
        GROUP BY s.sale_date
        ORDER BY s.sale_date;
        """

        cursor.execute(query)
        data = cursor.fetchall()

        if not data:
            print("No data available")
            return

        dates = []
        totals = []

        for row in data:
            dates.append(str(row[0]))
            totals.append(float(row[1]))

        plt.figure()
        plt.plot(dates, totals, marker='o')
        plt.xlabel("Date")
        plt.ylabel("Total Sales")
        plt.title("Sales by Date")
        plt.xticks(rotation=45)
        plt.tight_layout()

        plt.show()

        cursor.close()
        conn.close()

    except Exception as e:
        print("Error:", e)
#--------------------view product graph--------

def graph_product():
    graph_win = tk.Toplevel()
    graph_win.title("Product Graph")
    graph_win.geometry("300x150")

    tk.Label(graph_win, text="Enter Product ID:").pack(pady=10)
    entry = tk.Entry(graph_win)
    entry.pack()

    def show_graph():
        p_id = entry.get()

        if not p_id:
            print("Enter Product ID")
            return

        try:
            conn = get_connection()
            cursor = conn.cursor()

            query = """
            SELECT s.sale_date, si.quantity
            FROM sales s
            JOIN sale_items si ON s.sale_id = si.sale_id
            WHERE si.product_id = %s
            ORDER BY s.sale_date;
            """

            cursor.execute(query, (p_id,))
            data = cursor.fetchall()

            if not data:
                print("No data found")
                return

            dates = []
            quantities = []

            for row in data:
                dates.append(str(row[0]))
                quantities.append(float(row[1]))

            plt.figure()
            plt.plot(dates, quantities, marker='o')
            plt.xlabel("Date")
            plt.ylabel("Quantity Sold")
            plt.title(f"Sales of Product {p_id}")
            plt.xticks(rotation=45)
            plt.tight_layout()

            plt.show()

            cursor.close()
            conn.close()

        except Exception as e:
            print("Error:", e)

    tk.Button(graph_win, text="SHOW GRAPH", command=show_graph).pack(pady=10)
#--------------------------- view date graph---------------
import matplotlib.pyplot as plt
import tkinter as tk

def graph_by_date():
    win = tk.Toplevel()
    win.title("Graph by Date")
    win.geometry("300x150")

    tk.Label(win, text="Enter Date (YYYY-MM-DD):").pack(pady=10)
    entry = tk.Entry(win)
    entry.pack()

    def show_graph():
        d = entry.get()

        if not d:
            print("Enter date")
            return

        try:
            conn = get_connection()
            cursor = conn.cursor()

            query = """
            SELECT p.p_Name, SUM(si.quantity)
            FROM sales s
            JOIN sale_items si ON s.sale_id = si.sale_id
            JOIN products p ON si.product_id = p.product_ID
            WHERE s.sale_date = %s
            GROUP BY p.p_Name;
            """

            cursor.execute(query, (d,))
            data = cursor.fetchall()

            if not data:
                print("No data found")
                return

            products = []
            quantities = []

            for row in data:
                products.append(row[0])
                quantities.append(float(row[1]))

            plt.figure()
            plt.bar(products, quantities)
            plt.xlabel("Products")
            plt.ylabel("Quantity Sold")
            plt.title(f"Sales on {d}")
            plt.xticks(rotation=30)
            plt.tight_layout()

            plt.show()

            cursor.close()
            conn.close()

        except Exception as e:
            print("Error:", e)

    tk.Button(win, text="SHOW GRAPH", command=show_graph).pack(pady=10)
#-----------------------show total revenue--------
import matplotlib.pyplot as plt
import tkinter as tk

def graph_product_revenue():
    win = tk.Toplevel()
    win.title("Product Revenue")
    win.geometry("300x150")

    tk.Label(win, text="Enter Product ID:").pack(pady=10)
    entry = tk.Entry(win)
    entry.pack()

    def show_graph():
        p_id = entry.get()

        if not p_id:
            print("Enter Product ID")
            return

        try:
            conn = get_connection()
            cursor = conn.cursor()

            query = """
            SELECT p.p_Name, SUM(si.total_price)
            FROM sale_items si
            JOIN products p ON si.product_id = p.product_ID
            WHERE si.product_id = %s
            GROUP BY p.p_Name;
            """

            cursor.execute(query, (p_id,))
            data = cursor.fetchone()

            if not data:
                print("No data found")
                return

            product_name = data[0]
            total_revenue = float(data[1])

            # 🌟 Bar Graph (Single)
            plt.figure()
            plt.bar([product_name], [total_revenue])
            plt.xlabel("Product")
            plt.ylabel("Total Revenue")
            plt.title(f"Revenue of {product_name}")
            plt.tight_layout()

            plt.show()

            cursor.close()
            conn.close()

        except Exception as e:
            print("Error:", e)

    tk.Button(win, text="SHOW REVENUE", command=show_graph).pack(pady=10)
# ---------------- BUTTONS ----------------
# 🌟 Button positions (3x3 grid)
btn_width = 18
btn_height = 2

start_x = 200
start_y = 200
gap_x = 180
gap_y = 70


# ---------------- BUTTON GRID ----------------

# Row 1
tk.Button(main_scrn, text="ADD PRODUCT", width=btn_width, height=btn_height,
          command=open_product_input_window).place(x=start_x, y=start_y)

tk.Button(main_scrn, text="VIEW PRODUCTS", width=btn_width, height=btn_height,
          command=view_products).place(x=start_x + gap_x, y=start_y)

tk.Button(main_scrn, text="ENTER SALE", width=btn_width, height=btn_height,
          command=open_sales_in).place(x=start_x + 2*gap_x, y=start_y)


# Row 2
tk.Button(main_scrn, text="VIEW SALES", width=btn_width, height=btn_height,
          command=view_sales).place(x=start_x, y=start_y + gap_y)

tk.Button(main_scrn, text="SALES GRAPH", width=btn_width, height=btn_height,
          command=graph_sales_by_date).place(x=start_x + gap_x, y=start_y + gap_y)

tk.Button(main_scrn, text="PRODUCT GRAPH", width=btn_width, height=btn_height,
          command=graph_product).place(x=start_x + 2*gap_x, y=start_y + gap_y)


# Row 3
tk.Button(main_scrn, text="DATE GRAPH", width=btn_width, height=btn_height,
          command=graph_by_date).place(x=start_x, y=start_y + 2*gap_y)

tk.Button(main_scrn, text="PRODUCT REVENUE", width=btn_width, height=btn_height,
          command=graph_product_revenue).place(x=start_x + gap_x, y=start_y + 2*gap_y)

tk.Button(main_scrn, text="AI ASSISTANT", width=btn_width, height=btn_height,
          command=open_chatbot).place(x=start_x + 2*gap_x, y=start_y + 2*gap_y)


# Exit Button (centered below)
tk.Button(main_scrn, text="EXIT", width=btn_width, height=btn_height,
          command=exit_app).place(x=start_x + gap_x, y=start_y + 3*gap_y)


# ---------------- LABEL ----------------
tk.Label(main_scrn, text="WELCOME TO SALES ANALYZER",
         font=("arial", 25)).place(x=180, y=30)

main_scrn.mainloop()