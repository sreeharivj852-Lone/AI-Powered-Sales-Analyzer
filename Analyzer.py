"""
Analyzer.py - Sales Analyzer Main Application Dashboard
Manages products, sales records, graphical analytics, and launches
the AI Sales Assistant. Uses secure, leak-proof database connection management.
"""

import os
from datetime import date
import tkinter as tk
from tkinter import ttk, messagebox
from PIL import Image, ImageTk
import matplotlib.pyplot as plt
from dotenv import load_dotenv

from db import get_db_cursor, DatabaseConfigError
from sales_chatbot import open_chatbot

# Load environment configuration
load_dotenv()

# ---------------- MAIN WINDOW ----------------
main_scrn = tk.Tk()
main_scrn.title('Sale Analyzer')
main_scrn.geometry("850x500")
main_scrn.resizable(False, False)

# Background Image setup with fallback
try:
    if os.path.exists("salesanalyzer_bg.png"):
        img = Image.open("salesanalyzer_bg.png").resize((850, 450))
        bg_img = ImageTk.PhotoImage(img)
        tk.Label(main_scrn, image=bg_img).place(x=0, y=0, relwidth=1, relheight=1)
    else:
        main_scrn.configure(bg="#f4f6f9")
except Exception as img_err:
    print(f"Warning: Could not load background image: {img_err}")
    main_scrn.configure(bg="#f4f6f9")


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
        p_id = p1.get().strip()
        name = n1.get().strip()
        price_str = c1.get().strip()

        if not p_id or not name or not price_str:
            alert.config(text="⚠ Fill all fields", fg="orange")
            return

        try:
            price = float(price_str)
            if price < 0:
                alert.config(text="❌ Price must be positive", fg="red")
                return
        except ValueError:
            alert.config(text="❌ Invalid price", fg="red")
            return

        try:
            with get_db_cursor(commit=True) as cursor:
                cursor.execute(
                    "INSERT INTO products (product_ID, p_Name, price) VALUES (%s, %s, %s)",
                    (p_id, name, price)
                )

            alert.config(text="✅ Saved", fg="green")
            p1.delete(0, tk.END)
            n1.delete(0, tk.END)
            c1.delete(0, tk.END)

        except DatabaseConfigError as dce:
            alert.config(text="❌ DB Config Error", fg="red")
            messagebox.showerror("Configuration Error", str(dce))
        except Exception as e:
            err_msg = str(e)
            if "Duplicate entry" in err_msg or "PRIMARY" in err_msg:
                alert.config(text="❌ Duplicate Product ID", fg="red")
            else:
                alert.config(text="❌ Database Error", fg="red")
                messagebox.showerror("Database Error", f"Unable to save product: {err_msg}")

    tk.Button(win, text="SAVE", command=save_product).place(x=80, y=170)
    tk.Button(win, text="CLOSE", command=win.destroy).place(x=200, y=170)


# ---------------- VIEW PRODUCTS ----------------
def view_products():
    win = tk.Toplevel()
    win.title("Products")
    win.geometry("600x350")

    table = ttk.Treeview(win, columns=("ID", "Name", "Price"), show="headings")

    for col in ("ID", "Name", "Price"):
        table.heading(col, text=col)
        table.column(col, anchor="center")

    table.pack(fill="both", expand=True)

    try:
        with get_db_cursor() as cursor:
            cursor.execute("SELECT product_ID, p_Name, price FROM products")
            rows = cursor.fetchall()
            for row in rows:
                table.insert("", tk.END, values=row)
    except DatabaseConfigError as dce:
        messagebox.showerror("Configuration Error", str(dce))
    except Exception as e:
        messagebox.showerror("Database Error", f"Failed to retrieve products: {e}")


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
    d1.insert(0, str(date.today()))

    tk.Label(win, text="Product ID").place(x=20, y=60)
    p1 = tk.Entry(win)
    p1.place(x=200, y=60)

    tk.Label(win, text="Quantity").place(x=20, y=100)
    q1 = tk.Entry(win)
    q1.place(x=200, y=100)

    def add_item():
        pid = p1.get().strip()
        qty_str = q1.get().strip()

        if not pid or not qty_str:
            alert.config(text="⚠ Fill fields", fg="orange")
            return

        try:
            qty = int(qty_str)
            if qty <= 0:
                alert.config(text="❌ Quantity must be > 0", fg="red")
                return
        except ValueError:
            alert.config(text="❌ Invalid quantity (integer required)", fg="red")
            return

        items.append((pid, qty))
        alert.config(text=f"Added {pid} x {qty} ({len(items)} in cart)", fg="green")

        p1.delete(0, tk.END)
        q1.delete(0, tk.END)

    def save_sale():
        d_str = d1.get().strip()

        if not d_str or not items:
            alert.config(text="⚠ Add date & items", fg="orange")
            return

        try:
            d = date.fromisoformat(d_str)
        except ValueError:
            alert.config(text="❌ Invalid date format (YYYY-MM-DD)", fg="red")
            return

        try:
            # Atomic transaction: inserts sale and all line items, rolling back if any product ID is invalid
            with get_db_cursor(commit=True) as cursor:
                cursor.execute("INSERT INTO sales (sale_date) VALUES (%s)", (d,))
                sale_id = cursor.lastrowid

                for pid, qty in items:
                    cursor.execute("SELECT price FROM products WHERE product_ID=%s", (pid,))
                    res = cursor.fetchone()

                    if not res:
                        raise ValueError(f"Product ID '{pid}' does not exist in inventory.")

                    price = float(res[0])
                    total = price * qty

                    cursor.execute("""
                        INSERT INTO sale_items 
                        (sale_id, product_id, quantity, total_price)
                        VALUES (%s, %s, %s, %s)
                    """, (sale_id, pid, qty, total))

            alert.config(text="✅ Sale Saved Successfully", fg="green")
            items.clear()
            p1.delete(0, tk.END)
            q1.delete(0, tk.END)

        except ValueError as ve:
            alert.config(text=f"❌ {ve}", fg="red")
        except DatabaseConfigError as dce:
            alert.config(text="❌ DB Config Error", fg="red")
            messagebox.showerror("Configuration Error", str(dce))
        except Exception as e:
            alert.config(text="❌ Error saving sale", fg="red")
            messagebox.showerror("Error", f"Failed to record sale: {e}")

    tk.Button(win, text="ADD", command=add_item).place(x=80, y=150)
    tk.Button(win, text="SAVE", command=save_sale).place(x=200, y=150)
    tk.Button(win, text="CLOSE", command=win.destroy).place(x=150, y=250)


# ---------------- VIEW SALES ----------------
def view_sales():
    win = tk.Toplevel()
    win.title("Sales Records")
    win.geometry("750x400")

    table = ttk.Treeview(win, columns=("Date", "Product", "Qty", "Total"), show="headings")

    for col in ("Date", "Product", "Qty", "Total"):
        table.heading(col, text=col)
        table.column(col, anchor="center")

    table.pack(fill="both", expand=True)

    try:
        with get_db_cursor() as cursor:
            cursor.execute("""
                SELECT s.sale_date, p.p_Name, si.quantity, si.total_price
                FROM sales s
                JOIN sale_items si ON s.sale_id = si.sale_id
                JOIN products p ON si.product_id = p.product_ID
                ORDER BY s.sale_date DESC
            """)
            for row in cursor.fetchall():
                table.insert("", tk.END, values=row)
    except DatabaseConfigError as dce:
        messagebox.showerror("Configuration Error", str(dce))
    except Exception as e:
        messagebox.showerror("Database Error", f"Failed to retrieve sales records: {e}")


# ---------------- ANALYTICS GRAPHS ----------------
def graph_sales_by_date():
    """Generates a line plot of total sales revenue over time."""
    try:
        with get_db_cursor() as cursor:
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
            messagebox.showinfo("No Data", "No sales records available to graph.")
            return

        dates = [str(row[0]) for row in data]
        totals = [float(row[1]) for row in data]

        plt.figure()
        plt.plot(dates, totals, marker='o')
        plt.xlabel("Date")
        plt.ylabel("Total Sales")
        plt.title("Sales by Date")
        plt.xticks(rotation=45)
        plt.tight_layout()
        plt.show()

    except DatabaseConfigError as dce:
        messagebox.showerror("Configuration Error", str(dce))
    except Exception as e:
        messagebox.showerror("Graph Error", f"Unable to display sales graph: {e}")


def graph_product():
    """Generates a trend plot of quantity sold over time for a specific product."""
    graph_win = tk.Toplevel()
    graph_win.title("Product Graph")
    graph_win.geometry("300x150")

    tk.Label(graph_win, text="Enter Product ID:").pack(pady=10)
    entry = tk.Entry(graph_win)
    entry.pack()

    def show_graph():
        p_id = entry.get().strip()

        if not p_id:
            messagebox.showwarning("Input Required", "Please enter a Product ID.")
            return

        try:
            with get_db_cursor() as cursor:
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
                messagebox.showinfo("No Data", f"No sales records found for Product ID '{p_id}'.")
                return

            dates = [str(row[0]) for row in data]
            quantities = [float(row[1]) for row in data]

            plt.figure()
            plt.plot(dates, quantities, marker='o')
            plt.xlabel("Date")
            plt.ylabel("Quantity Sold")
            plt.title(f"Sales of Product {p_id}")
            plt.xticks(rotation=45)
            plt.tight_layout()
            plt.show()

        except DatabaseConfigError as dce:
            messagebox.showerror("Configuration Error", str(dce))
        except Exception as e:
            messagebox.showerror("Graph Error", f"Unable to display product graph: {e}")

    tk.Button(graph_win, text="SHOW GRAPH", command=show_graph).pack(pady=10)


def graph_by_date():
    """Generates a bar chart of product quantities sold on a specific date."""
    win = tk.Toplevel()
    win.title("Graph by Date")
    win.geometry("300x150")

    tk.Label(win, text="Enter Date (YYYY-MM-DD):").pack(pady=10)
    entry = tk.Entry(win)
    entry.pack()

    def show_graph():
        d_str = entry.get().strip()

        if not d_str:
            messagebox.showwarning("Input Required", "Please enter a Date (YYYY-MM-DD).")
            return

        try:
            d = date.fromisoformat(d_str)
        except ValueError:
            messagebox.showerror("Invalid Date", "Date must be in format YYYY-MM-DD.")
            return

        try:
            with get_db_cursor() as cursor:
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
                messagebox.showinfo("No Data", f"No sales recorded on date '{d}'.")
                return

            products = [row[0] for row in data]
            quantities = [float(row[1]) for row in data]

            plt.figure()
            plt.bar(products, quantities)
            plt.xlabel("Products")
            plt.ylabel("Quantity Sold")
            plt.title(f"Sales on {d}")
            plt.xticks(rotation=30)
            plt.tight_layout()
            plt.show()

        except DatabaseConfigError as dce:
            messagebox.showerror("Configuration Error", str(dce))
        except Exception as e:
            messagebox.showerror("Graph Error", f"Unable to display date graph: {e}")

    tk.Button(win, text="SHOW GRAPH", command=show_graph).pack(pady=10)


def graph_product_revenue():
    """Generates a bar chart showing total revenue earned by a specific product."""
    win = tk.Toplevel()
    win.title("Product Revenue")
    win.geometry("300x150")

    tk.Label(win, text="Enter Product ID:").pack(pady=10)
    entry = tk.Entry(win)
    entry.pack()

    def show_graph():
        p_id = entry.get().strip()

        if not p_id:
            messagebox.showwarning("Input Required", "Please enter a Product ID.")
            return

        try:
            with get_db_cursor() as cursor:
                query = """
                SELECT p.p_Name, SUM(si.total_price)
                FROM sale_items si
                JOIN products p ON si.product_id = p.product_ID
                WHERE si.product_id = %s
                GROUP BY p.p_Name;
                """
                cursor.execute(query, (p_id,))
                data = cursor.fetchone()

            if not data or data[1] is None:
                messagebox.showinfo("No Data", f"No revenue data found for Product ID '{p_id}'.")
                return

            product_name = data[0]
            total_revenue = float(data[1])

            plt.figure()
            plt.bar([product_name], [total_revenue])
            plt.xlabel("Product")
            plt.ylabel("Total Revenue")
            plt.title(f"Revenue of {product_name}")
            plt.tight_layout()
            plt.show()

        except DatabaseConfigError as dce:
            messagebox.showerror("Configuration Error", str(dce))
        except Exception as e:
            messagebox.showerror("Graph Error", f"Unable to display revenue graph: {e}")

    tk.Button(win, text="SHOW REVENUE", command=show_graph).pack(pady=10)


# ---------------- BUTTON GRID (3x3) ----------------
btn_width = 18
btn_height = 2

start_x = 200
start_y = 200
gap_x = 180
gap_y = 70

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

# Exit Button
tk.Button(main_scrn, text="EXIT", width=btn_width, height=btn_height,
          command=exit_app).place(x=start_x + gap_x, y=start_y + 3*gap_y)

# ---------------- HEADER TITLE ----------------
tk.Label(main_scrn, text="WELCOME TO SALES ANALYZER",
         font=("arial", 25)).place(x=180, y=30)

if __name__ == "__main__":
    main_scrn.mainloop()
