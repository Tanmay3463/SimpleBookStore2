# Refactored single-page Gradio Bookstore App with:
# - Add-to-cart system
# - Fixed PDF receipt generation
# - Admin author dropdown + new author input
# - Improved sales history with visible book titles

import gradio as gr
import pandas as pd
import os
from fpdf import FPDF
from datetime import datetime

BOOKS_CSV = "books_inventory.csv"
SALES_CSV = "sales_history.csv"
RECEIPT_PDF = "receipt.pdf"

# Initialization
def initialize_files():
    if not os.path.exists(BOOKS_CSV):
        data = {
            "Title": [],
            "Author": [],
            "Publisher": [],
            "Stock": [],
            "Price": [],
        }
        pd.DataFrame(data).to_csv(BOOKS_CSV, index=False)

    if not os.path.exists(SALES_CSV):
        data = {
            "Date": [],
            "Title": [],
            "Quantity": [],
            "PricePerUnit": [],
            "Total": [],
        }
        pd.DataFrame(data).to_csv(SALES_CSV, index=False)

# Helpers
def load_inventory():
    return pd.read_csv(BOOKS_CSV)

def save_inventory(df):
    df.to_csv(BOOKS_CSV, index=False)

def load_sales():
    return pd.read_csv(SALES_CSV)

def save_sale(title, quantity, price):
    df = load_sales()
    new_row = {
        "Date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "Title": title,
        "Quantity": quantity,
        "PricePerUnit": price,
        "Total": quantity * price,
    }
    df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
    df.to_csv(SALES_CSV, index=False)

def generate_pdf_receipt(cart_items, total_amount):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    pdf.cell(200, 10, txt="Bookstore Receipt", ln=True, align='C')
    pdf.cell(200, 10, txt=f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", ln=True)
    pdf.ln(5)

    for item in cart_items:
        pdf.cell(200, 10, txt=f"{item['Quantity']} x {item['Title']} @ ₹{item['Price']}", ln=True)

    pdf.ln(5)
    pdf.cell(200, 10, txt=f"Total Amount: ₹{total_amount:.2f}", ln=True)
    pdf.output(RECEIPT_PDF)
    return RECEIPT_PDF

# Add to cart
cart_items = []

def add_to_cart(title, quantity):
    df = load_inventory()
    if title not in df["Title"].values:
        return "❌ Book not found.", cart_items

    if quantity <= 0:
        return "⚠️ Enter a valid quantity.", cart_items

    row = df[df["Title"] == title].iloc[0]
    cart_items.append({
        "Title": title,
        "Quantity": quantity,
        "Price": row["Price"]
    })
    return f"🛒 Added {quantity} x '{title}' to cart.", cart_items

def display_cart():
    global cart_items
    if not cart_items:
        return "🛒 Cart is empty."
    summary = ""
    total = 0
    for item in cart_items:
        summary += f"{item['Quantity']} x {item['Title']} @ ₹{item['Price']} = ₹{item['Quantity'] * item['Price']:.2f}\n"
        total += item['Quantity'] * item['Price']
    summary += f"\n**Total = ₹{total:.2f}**"
    return summary

def checkout():
    global cart_items
    if not cart_items:
        return "🛒 Cart is empty.", None
    df = load_inventory()
    total = 0
    for item in cart_items:
        idx = df[df["Title"] == item["Title"]].index
        if len(idx) == 0:
            return f"❌ Book '{item['Title']}' not found in stock.", None
        stock = df.at[idx[0], "Stock"]
        if item["Quantity"] > stock:
            return f"❌ Not enough stock for '{item['Title']}'. Available: {stock}", None

    # Process purchase
    for item in cart_items:
        idx = df[df["Title"] == item["Title"]].index[0]
        df.at[idx, "Stock"] -= item["Quantity"]
        save_sale(item["Title"], item["Quantity"], item["Price"])
        total += item["Quantity"] * item["Price"]

    save_inventory(df)
    receipt_path = generate_pdf_receipt(cart_items, total)
    cart.clear()
    return f"✅ Purchase successful! Total: ₹{total:.2f}", receipt_path

# Admin operations
def get_unique_authors():
    df = load_inventory()
    return sorted(df["Author"].dropna().unique().tolist())

def add_book(title, author_select, author_input, publisher, stock, price):
    author = author_input if author_select == "Other" else author_select
    df = load_inventory()
    if title in df["Title"].values:
        return "❌ Book already exists."
    new_row = {
        "Title": title,
        "Author": author,
        "Publisher": publisher,
        "Stock": stock,
        "Price": price,
    }
    df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
    save_inventory(df)
    return "✅ Book added successfully."

def edit_book(title, new_stock, new_price):
    df = load_inventory()
    idx = df[df["Title"] == title].index
    if len(idx) == 0:
        return "❌ Book not found."
    if new_stock >= 0:
        df.at[idx[0], "Stock"] = new_stock
    if new_price >= 0:
        df.at[idx[0], "Price"] = new_price
    save_inventory(df)
    return "✅ Book updated."

def remove_book(title):
    df = load_inventory()
    if title not in df["Title"].values:
        return "❌ Book not found."
    df = df[df["Title"] != title]
    save_inventory(df)
    return "✅ Book removed."

# App UI
def build_ui():
    initialize_files()
    with gr.Blocks() as app:
        with gr.Tab("🛒 Bookstore"):
            book_list = load_inventory()["Title"].tolist()
            dropdown = gr.Dropdown(choices=book_list, label="Choose a Book")
            quantity = gr.Number(label="Quantity", value=1, minimum=1)
            cart_output = gr.Markdown()
            result = gr.Markdown()
            receipt = gr.File()

            with gr.Row():
                add_btn = gr.Button("Add to Cart")
                buy_btn = gr.Button("Checkout")

            add_btn.click(add_to_cart, inputs=[dropdown, quantity], outputs=[result, cart_output]).then(
                display_cart, inputs=None, outputs=cart_output
            )
            buy_btn.click(checkout, inputs=None, outputs=[result, receipt])

        with gr.Tab("🧑‍💼 Admin Panel"):
            title = gr.Text(label="Title")
            authors = get_unique_authors()
            author_select = gr.Dropdown(choices=authors + ["Other"], label="Author")
            author_input = gr.Text(label="New Author (if Other)", visible=False)
            publisher = gr.Text(label="Publisher")
            stock = gr.Number(label="Stock", value=10)
            price = gr.Number(label="Price", value=100)
            add_result = gr.Markdown()
            author_select.change(lambda x: gr.update(visible=(x == "Other")), inputs=author_select, outputs=author_input)
            gr.Button("Add Book").click(add_book, inputs=[title, author_select, author_input, publisher, stock, price], outputs=add_result)

            gr.Markdown("### ✏️ Edit Book")
            edit_title = gr.Text(label="Book Title")
            new_stock = gr.Number(label="New Stock", value=-1)
            new_price = gr.Number(label="New Price", value=-1)
            gr.Button("Update Book").click(edit_book, inputs=[edit_title, new_stock, new_price], outputs=add_result)

            gr.Markdown("### ❌ Remove Book")
            delete_title = gr.Text(label="Book Title to Delete")
            gr.Button("Remove Book").click(remove_book, inputs=delete_title, outputs=add_result)

        with gr.Tab("📈 Sales History"):
            gr.Markdown("### All Sales")
            gr.Dataframe(load_sales)

    return app

ui = build_ui()
ui.launch()
