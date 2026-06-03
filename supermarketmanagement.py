import tkinter as tk
from tkinter import ttk, messagebox, filedialog, simpledialog
import datetime
import os
import tempfile
import platform
import subprocess
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from PIL import Image, ImageTk
import mysql.connector

try:
    db = mysql.connector.connect(
        host="localhost",
        user="root",
        password="DB_PASSWORD",
        database="supermarket"
    )
    cursor = db.cursor()
except mysql.connector.Error as err:
    print("MySQL connection failed:", err)
    db = None
    cursor = None

#Config & Globals
STOCK_FILE = "stock_data.txt"
BILL_FILE = "bill_history.txt"
INVOICE_FILE = "invoice_number.txt"

#low stock warning
LOW_STOCK_LIMIT = 5 

USER_FILE = "users.txt"
current_user_role = None
current_user_name = None

# Data containers
stock = {}  # name -> [price(float), qty(int), category(str)]
billing_items = []  # list of (name, category, qty, price, total)
grand_total = 0.0
invoice_no = 1

# Coupon System
COUPONS = {
    "SAVE10": 10,
    "FEST20": 20,
    "WELCOME5": 5,
    "NEW15": 15,
    "SUPER25": 25}
discount_amount = 0

# Supermarket Categories
CATEGORIES = [
    "Grocery",
    "Snacks",
    "Beverages",
    "Dairy",
    "Personal Care",
    "Household",
    "Fruit-Vegetable",
    "Meat-Frozen",
    "Electronics",
    "Clothing",
    "Stationery"
]

# GST Rates (%)
GST_RATES = {
    "Grocery": 5,
    "Snacks": 12,
    "Beverages": 12,
    "Dairy": 5,
    "Personal Care": 18,
    "Household": 18,
    "Fruit-Vegetable": 0,
    "Meat-Frozen": 5,
    "Electronics": 18,
    "Clothing": 12,
    "Stationery": 5
}

# Loyalty System
LOYALTY_FILE = "loyalty_points.txt"
loyalty_points = {}
loyalty_discount = 0
earned_points = 0
remaining_points = 0

#Helpers: Invoice & Persistence
def load_invoice_no():
    global invoice_no
    if os.path.exists(INVOICE_FILE):
        try:
            with open(INVOICE_FILE, "r") as f:
                invoice_no = int(f.read().strip()) + 1
        except Exception:
            invoice_no = 1
    else:
        invoice_no = 1

def save_invoice_no():
    try:
        with open(INVOICE_FILE, "w") as f:
            f.write(str(invoice_no))
    except Exception:
        pass

def save_stock():
    try:
        with open(STOCK_FILE, "w", encoding="utf-8") as f:
            for name, (price, qty, category) in stock.items():
                f.write(f"{name},{price},{qty},{category}\n")
                if db and cursor:
                    try:
                        cursor.execute("""
                        REPLACE INTO stock (name,price,quantity,category)
                        VALUES (%s,%s,%s,%s)
                        """, (name, price, qty, category))
                    except Exception as e:
                        print("MySQL save error:", e)
        if db and cursor:
            db.commit()
    except Exception as e:
        messagebox.showerror("Error", f"Failed to save stock: {e}")

def load_stock():
    """Load stock from MySQL and text file"""
    global stock
    stock.clear()
    try:
        if cursor:
            cursor.execute("SELECT name, price, quantity, category FROM stock")
            rows = cursor.fetchall()
            for name, price, qty, category in rows:
                stock[name] = [float(price), int(qty), category]
    except Exception as e:
        print("MySQL load error:", e)
    if os.path.exists(STOCK_FILE):
        try:
            with open(STOCK_FILE, "r", encoding="utf-8") as f:
                for line in f:
                    parts = line.strip().split(",")
                    if len(parts) == 4:
                        name, price_s, qty_s, category = parts
                        if name not in stock:
                            stock[name] = [float(price_s),int(qty_s),category]
        except Exception as e:
            print("TXT load error:", e)
    update_stock_table()

#Loyalty Points        
def load_loyalty_points():
    global loyalty_points
    if not os.path.exists(LOYALTY_FILE):
        return
    try:
        with open(LOYALTY_FILE, "r") as f:
            for line in f:
                phone, pts = line.strip().split(",")
                loyalty_points[phone] = int(pts)
    except:
        pass

def save_loyalty_points():
    try:
        with open(LOYALTY_FILE, "w") as f:
            for phone, pts in loyalty_points.items():
                f.write(f"{phone},{pts}\n")
    except:
        pass

#GUI Update Utilities
def update_counts():
    """Refresh the labels that show counts"""
    try:
        stock_count_label.config(text=f"Stock Items: {len(stock)}")
        bill_count_label.config(text=f"Bill Items: {len(billing_items)}")
    except Exception:
        pass

def refresh_bill_item_combo():
    try:
        names = sorted(stock.keys())
        bill_item_combo['values'] = names
    except Exception:
        pass

def refresh_category_filter():
    """Refresh category dropdown with unique categories"""
    categories = sorted({data[2] for data in stock.values()})
    category_combo['values'] = ["All"] + categories
    if category_filter.get() not in category_combo['values']:
        category_filter.set("All")

def shop_header_text():
    return (
        "=====      Abinish Digital Mart         =====\n"
        "===== 449, Madurai Road, Sivagami Puram =====\n"
        "=====        Virudhunagar               =====\n"
        "=====      Contact no: 97509 03377      =====\n")

# Login System
def check_login(username, password):
    global current_user_role, current_user_name
    try:
        cursor.execute(
            "SELECT role FROM users WHERE username=%s AND password=%s",
            (username, password)
        )
        result = cursor.fetchone()
        if result:
            current_user_role = result[0]
            current_user_name = username
            return True
    except mysql.connector.Error as err:
        messagebox.showerror("Database Error", str(err))
    return False

def apply_role_permissions():

    home_stock_btn.grid_remove()
    home_billing_btn.grid_remove()
    recall_btn.grid_remove()
    dashboard_btn.grid_remove()
    history_btn.grid_remove()

    edit_btn.config(state="normal")
    remove_btn.config(state="normal")
    add_stock_btn.config(state="normal")

    if current_user_role == "Admin":
        home_stock_btn.grid(row=0, column=0, padx=10)
        home_billing_btn.grid(row=0, column=1, padx=10)
        recall_btn.grid(row=0, column=2, padx=10)
        dashboard_btn.grid(row=0, column=3, padx=10)
        history_btn.grid(row=0, column=4, padx=10)

    elif current_user_role == "Manager":
        home_stock_btn.grid(row=0, column=0, padx=10)
        recall_btn.grid(row=0, column=1, padx=10)
        dashboard_btn.grid(row=0, column=2, padx=10)
        remove_btn.config(state="disabled")

    elif current_user_role == "Staff":
        home_billing_btn.grid(row=0, column=0, padx=10)
        edit_btn.config(state="disabled")
        remove_btn.config(state="disabled")
        add_stock_btn.config(state="disabled")

    elif current_user_role == "Accountant":
        recall_btn.grid(row=0, column=1, padx=10)
        dashboard_btn.grid(row=0, column=2, padx=10)
        edit_btn.config(state="disabled")
        remove_btn.config(state="disabled")
        add_stock_btn.config(state="disabled")
        
def logout():
    global current_user_role, current_user_name
    if messagebox.askyesno("Logout", "Are you sure you want to logout?"):
        current_user_role = None
        current_user_name = None
        root.withdraw()
        show_login()
        
# CHANGE PASSWORD FUNCTION
def change_password():
    if current_user_role != "Admin":
        messagebox.showerror("Access Denied","Only Admin can change passwords.")
        return
    win = tk.Toplevel(root)
    win.title("Change Password")
    win.geometry("350x260")
    win.resizable(False, False)
    win.configure(bg="#f8f9fa")
    user_var = tk.StringVar(value=current_user_name)
    old_var = tk.StringVar()
    new_var = tk.StringVar()
    confirm_var = tk.StringVar()
    tk.Label(win,text="Change Password",font=("Segoe UI", 14, "bold"),bg="#f8f9fa",fg="#007bff").pack(pady=10)
    tk.Label(win,text="Username",bg="#f8f9fa").pack()
    tk.Entry(win,textvariable=user_var,state="readonly",width=30).pack(pady=5)
    tk.Label(win,text="Old Password",bg="#f8f9fa").pack()
    tk.Entry(win,textvariable=old_var,show="*",width=30).pack(pady=5)
    tk.Label(win,text="New Password",bg="#f8f9fa").pack()
    tk.Entry(win,textvariable=new_var,show="*",width=30).pack(pady=5)
    tk.Label(win,text="Confirm Password",bg="#f8f9fa").pack()
    tk.Entry(win,textvariable=confirm_var,show="*",width=30).pack(pady=5)

    # UPDATE PASSWORD
    def update_password():
        username = user_var.get().strip()
        old_pw = old_var.get().strip()
        new_pw = new_var.get().strip()
        confirm_pw = confirm_var.get().strip()
        if not old_pw or not new_pw or not confirm_pw:
            messagebox.showerror("Error","All fields are required")
            return
        if len(new_pw) < 4:
            messagebox.showerror("Error","Password must be at least 4 characters")
            return
        if new_pw != confirm_pw:
            messagebox.showerror("Error","New passwords do not match")
            return
        try:
            cursor.execute("""
                SELECT * FROM users
                WHERE username=%s AND password=%s
                """,
                (username, old_pw)
            )
            result = cursor.fetchone()
            if not result:
                messagebox.showerror("Error","Old password incorrect")
                return
            cursor.execute(
                """
                UPDATE users
                SET password=%s
                WHERE username=%s
                """,
                (new_pw, username)
            )
            db.commit()
            messagebox.showinfo("Success","Password changed successfully")
            win.destroy()
        except mysql.connector.Error as err:
            messagebox.showerror("Database Error",str(err))
    tk.Button(win,text="Update Password",command=update_password,bg="#28a745",fg="white",font=("Segoe UI", 10, "bold"),width=20).pack(pady=15)

#Stock Functions
def add_stock():
    name = stock_name.get().strip()
    category = stock_category.get().strip() or "General"
    if not name:
        messagebox.showerror("Error", "Enter item name")
        return
    try:
        price = float(stock_price.get())
        qty = int(stock_qty.get())
    except ValueError:
        messagebox.showerror("Error", "Enter valid price and quantity")
        return
    if name in stock:
        stock[name][1] += qty
        stock[name][0] = price
        stock[name][2] = category
    else:
        stock[name] = [price, qty, category]
    stock_name.set("")
    stock_price.set("")
    stock_qty.set("")
    stock_category.set("")
    update_stock_table(search_var.get())
    save_stock()

def update_stock_table(filter_text=""):
    for row in stock_table.get_children():
        stock_table.delete(row)
    ft = filter_text.strip().lower()
    selected_cat = category_filter.get()
    for item, (price, qty, category) in sorted(stock.items()):
        if ft and ft not in item.lower() and ft not in category.lower():
            continue
        if selected_cat and selected_cat != "All" and category != selected_cat:
            continue
        tag = "low" if qty < LOW_STOCK_LIMIT else ""
        stock_table.insert("", "end", values=(item, f"{price:.2f}", qty, category), tags=(tag,))
    stock_table.tag_configure("low", background="#ffefef")
    refresh_bill_item_combo()
    update_counts()
    refresh_category_filter()

def remove_stock():
    sel = stock_table.selection()
    if not sel:
        messagebox.showwarning("Warning", "Select an item to remove")
        return
    item_values = stock_table.item(sel[0])["values"]
    name = item_values[0]
    if messagebox.askyesno("Confirm", f"Remove '{name}' from stock?"):
        if name in stock:
            del stock[name]
            update_stock_table(search_var.get())
            save_stock()
            messagebox.showinfo("Removed", f"{name} removed from stock")

def edit_stock():
    sel = stock_table.selection()
    if not sel:
        messagebox.showwarning("Warning", "Select an item to edit")
        return
    item_values = stock_table.item(sel[0])["values"]
    name = item_values[0]
    if name not in stock:
        messagebox.showerror("Error", "Selected item not found in internal stock")
        return
    edit_win = tk.Toplevel(root)
    edit_win.title(f"Edit Stock - {name}")
    edit_win.geometry("320x200")
    edit_win.resizable(False, False)
    tk.Label(edit_win, text="Item:").grid(row=0, column=0, padx=8, pady=8, sticky="e")
    tk.Label(edit_win, text=name).grid(row=0, column=1, padx=8, pady=8, sticky="w")
    
    tk.Label(edit_win, text="Price:").grid(row=1, column=0, padx=8, pady=8, sticky="e")
    pvar = tk.StringVar(value=str(stock[name][0]))
    tk.Entry(edit_win, textvariable=pvar).grid(row=1, column=1, padx=8, pady=8, sticky="w")
    
    tk.Label(edit_win, text="Quantity:").grid(row=2, column=0, padx=8, pady=8, sticky="e")
    qvar = tk.StringVar(value=str(stock[name][1]))
    tk.Entry(edit_win, textvariable=qvar).grid(row=2, column=1, padx=8, pady=8, sticky="w")
    
    tk.Label(edit_win, text="Category:").grid(row=3, column=0, padx=8, pady=8, sticky="e")
    cvar = tk.StringVar(value=str(stock[name][2]))
    tk.Entry(edit_win, textvariable=cvar).grid(row=3, column=1, padx=8, pady=8, sticky="w")

    def save_changes():
        try:
            new_price = float(pvar.get())
            new_qty = int(qvar.get())
            stock[name][0] = new_price
            stock[name][1] = new_qty
            stock[name][2] = cvar.get().strip() or "General"
            update_stock_table(search_var.get())
            save_stock()
            edit_win.destroy()
            messagebox.showinfo("Success", f"{name} updated")
        except ValueError:
            messagebox.showerror("Error", "Enter valid numeric values")
    tk.Button(edit_win, text="Save", command=save_changes, bg="#007bff", fg="white").grid(row=4, column=0, columnspan=2, pady=10)

#Billing Functions
def add_to_bill():
    global grand_total
    name = bill_item.get().strip()
    if not name:
        messagebox.showerror("Error", "Select an item to add")
        return
    try:
        qty = int(bill_qty.get())
    except ValueError:
        messagebox.showerror("Error", "Enter a valid quantity")
        return
    if qty <= 0:
        messagebox.showerror("Error", "Quantity must be positive")
        return
    if name not in stock:
        messagebox.showerror("Error", "Item not found in stock")
        return
    if stock[name][1] < qty:
        messagebox.showerror("Error", f"Not enough stock available. Current qty: {stock[name][1]}")
        return
    price = float(stock[name][0])
    category = stock[name][2] if len(stock[name]) > 2 else "General"
    gst_percent = GST_RATES.get(category, 0)
    item_total = price * qty
    gst_amount = (item_total * gst_percent) / 100
    total = item_total + gst_amount
    grand_total += total
    stock[name][1] -= qty
    if stock[name][1] < LOW_STOCK_LIMIT:
        messagebox.showwarning("Low Stock", f"{name} is running low (Qty left: {stock[name][1]})")
    billing_items.append((name, category, qty, price, total))
    bill_table.insert("", "end", values=(name,category,qty,f"{price:.2f}",f"{gst_percent}%",f"{gst_amount:.2f}",f"{total:.2f}"))
    grand_total_label.config(text=f"Grand Total: ₹{grand_total:.2f}")
    bill_item.set("")
    bill_qty.set("")
    update_stock_table(search_var.get())
    update_counts()
    save_stock()
    
def remove_item():
    global grand_total, billing_items
    selected_item = bill_table.selection()
    if not selected_item:
        messagebox.showwarning("Warning", "Select item to remove")
        return
    item_id = selected_item[0]
    values = bill_table.item(item_id, "values")
    product = values[0]
    category = values[1]
    qty = int(values[2])
    price = float(values[3])
    total = float(values[6])
    if product in stock:
        stock[product][1] += qty
    for item in billing_items:
        if (
            item[0] == product and
            item[1] == category and
            item[2] == qty and
            item[3] == price
        ):
            billing_items.remove(item)
            break
    bill_table.delete(item_id)
    grand_total -= total
    if grand_total < 0:
        grand_total = 0
    grand_total_label.config(
        text=f"Grand Total: ₹{grand_total:.2f}"
    )
    update_stock_table(search_var.get())
    save_stock()
    update_counts()
    messagebox.showinfo("Removed", f"{product} removed from bill")

def edit_quantity():
    global grand_total
    selected_item = bill_table.selection()
    if not selected_item:
        messagebox.showwarning("Warning","Select item to edit")
        return
    item_id = selected_item[0]
    values = bill_table.item(item_id, "values")
    product = values[0]
    category = values[1]
    old_qty = int(values[2])
    price = float(values[3])
    gst_percent = float(values[4].replace("%", ""))
    new_qty = simpledialog.askinteger("Edit Quantity",f"Enter new quantity for {product}:",initialvalue=old_qty,minvalue=1)
    if new_qty is None:
        return
    qty_difference = new_qty - old_qty
    if qty_difference > 0:
        if stock[product][1] < qty_difference:
            messagebox.showerror("Error","Not enough stock available")
            return
        stock[product][1] -= qty_difference
    elif qty_difference < 0:
        stock[product][1] += abs(qty_difference)
    item_total = price * new_qty
    gst_amount = (item_total * gst_percent) / 100
    total = item_total + gst_amount
    bill_table.item(item_id,values=(product,category,new_qty,f"{price:.2f}",f"{gst_percent}%",f"{gst_amount:.2f}",f"{total:.2f}"))
    for i, item in enumerate(billing_items):
        if (item[0] == product and item[1] == category and item[3] == price):
            billing_items[i] = (product,category,new_qty,price,total)
            break
    update_total()
    update_stock_table(search_var.get())
    save_stock()

def update_total():
    global grand_total
    grand_total = 0
    for item in bill_table.get_children():
        values = bill_table.item(item, "values")
        total = float(values[6])
        grand_total += total
    grand_total_label.config(text=f"Grand Total: ₹{grand_total:.2f}")

def _write_bill_file(f, inv_no, customer_name_s, customer_phone_s, items, total_amount):
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    f.write(shop_header_text())
    f.write(f"Invoice No: {inv_no}\n")
    f.write(f"Customer: {customer_name_s} | Phone: {customer_phone_s}\n")
    f.write(f"Payment Mode: {payment_mode_var.get()}\n")
    if payment_mode_var.get() == "Cash":
        f.write(f"Cash Received: ₹{cash_received_var.get()}\n")
        f.write(f"Balance Returned: ₹{balance_var.get()}\n")
    f.write(f"Date & Time: {now}\n\n")
    f.write(f"{'Item':15}{'Category':15}{'Qty':>5}{'Price':>10}{'GST%':>8}{'GST':>10}{'Total':>10}\n")
    f.write("-" * 65 + "\n")
    for item, category, qty, price, total in items:
        gst_percent = GST_RATES.get(category, 0)
        item_total = price * qty
        gst_amount = (item_total * gst_percent) / 100
        f.write(f"{item:15}{category:15}{qty:>5}{price:>10.2f}{gst_percent:>8}%{gst_amount:>10.2f}{total:>10.2f}\n")
    f.write("-" * 65 + "\n")
    f.write(f"Grand Total: ₹{total_amount:.2f}\n")
    if discount_amount > 0:
        f.write(f"Coupon Discount: -₹{discount_amount:.2f}\n")
    if loyalty_discount > 0:
        f.write(f"Loyalty Points Used: -₹{loyalty_discount:.2f}\n")
    final_amount = total_amount - loyalty_discount - discount_amount
    if final_amount < 0:
        final_amount = 0
    f.write(f"Final Payable Amount: ₹{final_amount:.2f}\n")
    f.write(f"Points Earned This Bill: {earned_points}\n")
    f.write(f"Points Balance: {remaining_points}\n")
    f.write("=" * 65 + "\n\n")

def save_bill_history():
    global invoice_no
    if not billing_items:
        return
    try:
        with open(BILL_FILE, "a", encoding="utf-8") as f:
            _write_bill_file(f,invoice_no,customer_name.get(),customer_phone.get(),billing_items,grand_total)
    except Exception as e:
        messagebox.showerror("Error",f"Failed to save bill history: {e}")
    try:
        if db and cursor:
            cursor.execute("""
            INSERT INTO bills
            (invoice_no, customer_name, phone, total)
            VALUES (%s,%s,%s,%s)
            """, (invoice_no,customer_name.get(),customer_phone.get(),grand_total))
            db.commit()
    except Exception as e:
        print("Bill save error:", e)

def clear_bill():
    global billing_items, grand_total, invoice_no
    if not billing_items:
        return
    if payment_mode_var.get() == "Cash":
        try:
            received = float(cash_received_var.get())
            if received < grand_total:
                messagebox.showerror("Error", "Insufficient Cash")
                return
        except:
            messagebox.showerror("Error", "Enter valid cash amount")
            return
    if not messagebox.askyesno("Confirm", "Are you sure you want to clear and finalize the current bill?"):
        return
    global loyalty_discount, earned_points, remaining_points, discount_amount
    customer_phone_number = customer_phone.get()
    existing_points = loyalty_points.get(customer_phone_number, 0)
    earned_points = int(grand_total // 100)
    total_points = existing_points + earned_points
    loyalty_discount = min(total_points // 10,int(grand_total * 0.1))
    final_amount = grand_total - loyalty_discount - discount_amount
    if final_amount < 0:
        final_amount = 0
    remaining_points = total_points - loyalty_discount
    if customer_phone_number:
        loyalty_points[customer_phone_number] = remaining_points
        save_loyalty_points()
    grand_total_label.config(text=f"Final Payable: ₹{final_amount:.2f}")
    save_bill_history()
    billing_items = []
    grand_total = 0.0
    invoice_no += 1
    save_invoice_no()
    for row in bill_table.get_children():
        bill_table.delete(row)
    grand_total_label.config(text="Grand Total: ₹0.00")
    customer_name.set("")
    customer_phone.set("")
    coupon_var.set("")
    cash_received_var.set("")
    balance_var.set("0.00")
    discount_amount = 0
    loyalty_discount = 0
    earned_points = 0
    remaining_points = 0
    payment_mode_var.set("Cash")
    update_counts()
    save_stock()
    messagebox.showinfo("Done", "Bill finalized and saved to history.")
    
def apply_coupon():
    global grand_total, discount_amount
    code = coupon_var.get().strip().upper()
    if code in COUPONS:
        discount_percent = COUPONS[code]
        discount_amount = (grand_total * discount_percent) / 100
        new_total = grand_total - discount_amount
        grand_total_label.config(text=f"Grand Total: ₹ {new_total:.2f} (Discount {discount_percent}%)")
    else:
        messagebox.showerror("Invalid", "Invalid Coupon Code")
        
def calculate_balance():
    global grand_total
    if payment_mode_var.get() != "Cash":
        balance_var.set("0.00")
        return
    try:
        received = float(cash_received_var.get())
        balance = received - (grand_total - discount_amount - loyalty_discount)
        if balance < 0:
            balance_var.set("Insufficient Cash")
        else:
            balance_var.set(f"{balance:.2f}")
    except:
        balance_var.set("0.00")

def on_payment_mode_change(*args):
    mode = payment_mode_var.get()
    if mode == "Cash":
        cash_entry.config(state="normal")
    else:
        cash_received_var.set("")
        balance_var.set("0.0")
        cash_entry.config(state="disabled")
        
def export_bill_txt():
    if not billing_items:
        messagebox.showwarning("Warning", "No items in bill to export!")
        return
    file_path = filedialog.asksaveasfilename(defaultextension=".txt",filetypes=[("Text Files", "*.txt")],title="Export Bill As")
    if not file_path:
        return
    try:
        with open(file_path, "w", encoding="utf-8") as f:
            _write_bill_file(f, invoice_no, customer_name.get(), customer_phone.get(), billing_items, grand_total)
        messagebox.showinfo("Success", f"Bill exported to:\n{file_path}")
    except Exception as e:
        messagebox.showerror("Error", f"Failed to export bill: {e}")

def print_bill():
    if not os.path.exists(BILL_FILE):
        messagebox.showerror("Error", "No bill file found.")
        return
    try:
        if platform.system() == "Windows":
            os.startfile(BILL_FILE, "print")
        else:
            subprocess.run(["lp", BILL_FILE])
        messagebox.showinfo("Success","Bill sent to printer successfully!")
    except Exception as e:
        messagebox.showerror("Print Error", str(e))

def view_bill_history():
    if not os.path.exists(BILL_FILE):
        messagebox.showinfo("Info", "No bill history found yet.")
        return
    history_window = tk.Toplevel(root)
    history_window.title("Bill History")
    history_window.geometry("700x500")
    text_area = tk.Text(history_window, wrap="word", font=("Segoe UI", 10))
    text_area.pack(expand=True, fill="both")
    scrollbar = tk.Scrollbar(text_area)
    scrollbar.pack(side="right", fill="y")
    text_area.config(yscrollcommand=scrollbar.set)
    scrollbar.config(command=text_area.yview)
    try:
        with open(BILL_FILE, "r", encoding="utf-8") as f:
            text_area.insert("1.0", f.read())
    except Exception as e:
        messagebox.showerror("Error", f"Failed to read bill history: {e}")

#Calculate Sales
def calculate_sales():
    daily = 0
    weekly = 0
    monthly = 0
    bill_count = 0
    if not os.path.exists(BILL_FILE):
        return daily, weekly, monthly, bill_count
    today = datetime.date.today()
    start_week = today - datetime.timedelta(days=today.weekday())
    start_month = today.replace(day=1)
    with open(BILL_FILE, "r", encoding="utf-8") as f:
        data = f.read()
        blocks = data.split("=" * 65)
        for block in blocks:
            if "Date & Time:" in block and "Grand Total:" in block:
                bill_count += 1
                for line in block.split("\n"):
                    if "Date & Time:" in line:
                        date_str = line.split("Date & Time:")[1].strip()
                        bill_date = datetime.datetime.strptime(
                            date_str, "%Y-%m-%d %H:%M:%S"
                        ).date()
                    if "Grand Total:" in line:
                        amount = float(line.split("₹")[1])
                if bill_date == today:
                    daily += amount
                if start_week <= bill_date <= today:
                    weekly += amount
                if start_month <= bill_date <= today:
                    monthly += amount
    return daily, weekly, monthly, bill_count

# Sales Dashboard
def calculate_sales_by_date(selected_date):
    total = 0
    if not os.path.exists(BILL_FILE):
        return total
    with open(BILL_FILE, "r", encoding="utf-8") as f:
        data = f.read()
        blocks = data.split("=" * 65)
        for block in blocks:
            if "Date & Time:" in block and "Grand Total:" in block:
                for line in block.split("\n"):
                    if "Date & Time:" in line:
                        date_str = line.split("Date & Time:")[1].strip()
                        bill_date = datetime.datetime.strptime(
                            date_str, "%Y-%m-%d %H:%M:%S"
                        ).date()
                    if "Grand Total:" in line:
                        amount = float(line.split("₹")[1])
                if bill_date == selected_date:
                    total += amount
    return total

def show_dashboard():
    dash = tk.Toplevel(root)
    dash.title("Sales Summary Dashboard")
    dash.geometry("750x550")
    daily, weekly, monthly, bills = calculate_sales()
    tk.Label(dash, text="Sales Summary Dashboard",font=("Segoe UI", 16, "bold")).pack(pady=10)
    summary_frame = tk.Frame(dash)
    summary_frame.pack(pady=10)
    lbl_today = tk.Label(summary_frame, text=f"Today Sales: ₹{daily:.2f}",font=("Segoe UI", 12))
    lbl_today.grid(row=0, column=0, padx=15)
    lbl_week = tk.Label(summary_frame, text=f"Weekly Sales: ₹{weekly:.2f}",font=("Segoe UI", 12))
    lbl_week.grid(row=0, column=1, padx=15)
    lbl_month = tk.Label(summary_frame, text=f"Monthly Sales: ₹{monthly:.2f}",font=("Segoe UI", 12))
    lbl_month.grid(row=0, column=2, padx=15)
    tk.Label(summary_frame, text=f"Total Bills: {bills}",font=("Segoe UI", 12)).grid(row=1, column=1, pady=10)
    fig, ax = plt.subplots(figsize=(6, 4))
    x_labels = ["Today", "Weekly", "Monthly"]
    y_values = [daily, weekly, monthly]
    ax.plot(x_labels, y_values, marker='o', linestyle='-', linewidth=2)
    ax.set_title("Sales Overview")
    ax.set_xlabel("Period")
    ax.set_ylabel("Amount (₹)")
    ax.grid(True)
    canvas = FigureCanvasTkAgg(fig, master=dash)
    canvas.draw()
    canvas.get_tk_widget().pack(pady=10)
    search_frame = tk.LabelFrame(dash, text="Search by Date", padx=10, pady=10)
    search_frame.pack(pady=10)
    tk.Label(search_frame, text="Enter Date (YYYY-MM-DD):").grid(row=0, column=0, padx=5)
    date_var = tk.StringVar()
    tk.Entry(search_frame, textvariable=date_var, width=15).grid(row=0, column=1, padx=5)
    result_label = tk.Label(search_frame, font=("Segoe UI", 11, "bold"))
    result_label.grid(row=1, column=0, columnspan=2, pady=5)
    
    def search_date_sales():
        try:
            selected_date = datetime.datetime.strptime(date_var.get(), "%Y-%m-%d").date()
        except ValueError:
            messagebox.showerror("Error", "Enter date as YYYY-MM-DD")
            return
        amount = calculate_sales_by_date(selected_date)
        result_label.config(text=f"Sales on {selected_date}: ₹{amount:.2f}")
    tk.Button(search_frame, text="Search",command=search_date_sales,bg="#28a745", fg="white").grid(row=0, column=2, padx=10)

#Recall/Search Bills
def recall_bill_by_invoice(inv_str):
    if not os.path.exists(BILL_FILE):
        return None
    try:
        with open(BILL_FILE, "r", encoding="utf-8") as f:
            data = f.read()
            blocks = data.split("=" * 65)
            for block in blocks:
                if f"Invoice No: {inv_str}" in block:
                    return block
    except Exception:
        pass
    return None

def recall_bill_by_text(query):
    if not os.path.exists(BILL_FILE):
        return ""
    q = query.strip().lower()
    out = []
    try:
        with open(BILL_FILE, "r", encoding="utf-8") as f:
            data = f.read()
            blocks = data.split("=" * 65)
            for block in blocks:
                if q in block.lower():
                    out.append(block)
    except Exception:
        pass
    return "\n".join(out)

def recall_bill():
    if not os.path.exists(BILL_FILE):
        messagebox.showinfo("Info", "No bill history found yet.")
        return
    win = tk.Toplevel(root)
    win.title("Recall Bill (Invoice / Name / Phone)")
    win.geometry("550x400")
    tk.Label(win, text="Search by Invoice No (exact) or Name/Phone (partial):").pack(pady=6)
    var = tk.StringVar()
    tk.Entry(win, textvariable=var, width=40).pack(pady=6)
    text_area = tk.Text(win, wrap="word", font=("Segoe UI", 10))
    text_area.pack(expand=True, fill="both", padx=6, pady=6)

    def do_search():
        query = var.get().strip()
        text_area.delete("1.0", tk.END)
        if not query:
            return
        if query.isdigit():
            found = recall_bill_by_invoice(query)
            if found:
                text_area.insert("1.0", found)
                return
        matches = recall_bill_by_text(query)
        if matches:
            text_area.insert("1.0", matches)
        else:
            text_area.insert("1.0", "No matching bills found.")
    tk.Button(win, text="Search", command=do_search, bg="#007bff", fg="white").pack(pady=6)

#App Closing
def on_closing():
    save_stock()
    save_invoice_no()
    if billing_items:
        if messagebox.askyesno("Save Bill", "A bill is in progress. Save it to history before exiting?"):
            save_bill_history()
    root.destroy()

def show_home_page():
    bill_frame.pack_forget()
    stock_frame.pack_forget()
    home_frame.pack(fill="both", expand=True)

def open_stock():
    home_frame.pack_forget()
    bill_frame.pack_forget()
    stock_frame.pack(fill="both", expand=True)

def open_billing():
    home_frame.pack_forget()
    stock_frame.pack_forget()
    bill_frame.pack(fill="both", expand=True)

def go_to_home():
    stock_frame.pack_forget()
    bill_frame.pack_forget()
    show_home_page()
        
#UI Construction
root = tk.Tk()
style = ttk.Style()
style.theme_use("clam")
style.configure(
    "Treeview",
    font=("Segoe UI", 10),
    rowheight=28,
    background="white",
    fieldbackground="white"
)
style.configure(
    "Treeview.Heading",
    font=("Segoe UI", 10, "bold")
)
root.withdraw()
payment_mode_var = tk.StringVar(value="Cash")
cash_received_var = tk.StringVar()
balance_var = tk.StringVar(value="0.00")
root.title("Abinish Digital Mart")
home_frame = tk.Frame(root, bg="#0f172a")

try:
    logo_img = Image.open("logo.png")
    logo_img = logo_img.resize((250, 250))
    logo_photo = ImageTk.PhotoImage(logo_img)
    logo_label = tk.Label(home_frame, image=logo_photo, bg="#0f172a")
    logo_label.image = logo_photo
    logo_label.pack(pady=10)
except Exception as e:
    print("Logo not found:", e)
    
shop_name = tk.Label(home_frame,text="ABINISH DIGITAL MART",font=("Segoe UI", 22, "bold"),fg="gold",bg="#0f172a")
shop_name.pack(pady=5)
tagline = tk.Label(home_frame,text="One Destination for All Your Needs",font=("Segoe UI", 10),fg="white",bg="#0f172a")
tagline.pack(pady=5)
home_title = tk.Label(home_frame,text="Welcome to Supermarket System",font=("Segoe UI", 14, "bold"),bg="#f8f9fa")
home_title.pack(pady=10)
button_frame = tk.Frame(home_frame,bg="#0f172a")
button_frame.pack(pady=20)
home_stock_btn = tk.Button(button_frame,text="Stock Management",font=("Segoe UI", 13, "bold"),bg="#2563eb",fg="white",activebackground="#1e40af",width=22,height=2,bd=0,command=open_stock)
home_stock_btn.grid(row=0, column=0, padx=10)
home_billing_btn = tk.Button(button_frame,text="Billing Section",font=("Segoe UI", 13, "bold"),bg="#16a34a",fg="white",activebackground="#15803d",width=22,height=2,bd=0,command=open_billing)
home_billing_btn.grid(row=0, column=1, padx=10)
dashboard_btn = tk.Button(button_frame,text="Sales Dashboard",font=("Segoe UI", 13, "bold"),bg="#343a40",fg="white",width=22,height=2,bd=0,command=show_dashboard)
dashboard_btn.grid(row=0, column=2, padx=10)
history_btn = tk.Button(button_frame,text="View Bill History",font=("Segoe UI", 13, "bold"),bg="#17a2b8",fg="white",width=22,height=2,bd=0,command=view_bill_history)
history_btn.grid(row=0, column=3, padx=10)
recall_btn = tk.Button(button_frame,text="Recall Bill",font=("Segoe UI", 13, "bold"),bg="#fd7e14",fg="white",width=22,height=2,bd=0,command=recall_bill)
recall_btn.grid(row=0, column=4, padx=10)
root.state("zoomed")
root.configure(bg="#f8f9fa")
logout_btn = tk.Button(root, text="Logout", command=logout, bg="#dc3545", fg="white")
logout_btn.pack(anchor="ne", padx=10, pady=5)
change_pw_btn = tk.Button(root, text="Change Password", command=change_password, bg="#007bff", fg="white")
change_pw_btn.pack(anchor="ne", padx=10)
user_label = tk.Label(root, text="", bg="#f8f9fa", font=("Segoe UI", 10, "bold"))
user_label.pack(anchor="nw", padx=10)

#Billing Frame
bill_frame = tk.LabelFrame(root, text="Billing", padx=10, pady=10, bg="#f8f9fa")
home_btn_bill = tk.Button(bill_frame,text="Home", command=go_to_home, bg="#343a40", fg="white")
home_btn_bill.grid(row=4, column=9, padx=5)
bill_item = tk.StringVar()
bill_qty = tk.StringVar()
tk.Label(bill_frame, text="Select Item:").grid(row=0, column=5, padx=6, pady=6, sticky="e")
bill_item_combo = ttk.Combobox(bill_frame, textvariable=bill_item, state="readonly", width=30)
bill_item_combo.grid(row=0, column=6, padx=6, pady=6, sticky="w")
tk.Label(bill_frame, text="Quantity:").grid(row=0, column=7, padx=6, pady=6, sticky="e")
tk.Entry(bill_frame, textvariable=bill_qty, width=12).grid(row=0, column=8, padx=6, pady=6, sticky="w")
tk.Button(bill_frame,text="Add to Bill",command=add_to_bill,bg="#17a2b8",fg="white").grid(row=1, column=5, padx=6, pady=6)
tk.Button(bill_frame, text="Remove Item", command=remove_item, bg="red", fg="white").grid(row=2, column=7)
tk.Button(bill_frame, text="Edit Qty", command=edit_quantity, bg="orange", fg="white").grid(row=2, column=9)
columns = ("Item", "Category", "Qty", "Price", "GST%", "GST Amt", "Total")
bill_table = ttk.Treeview(bill_frame, columns=columns, show="headings", height=15)
for col in columns:
    bill_table.heading(col, text=col)
    bill_table.column(col, width=100 if col != "Item" else 150)
bill_table.grid(row=1, column=0, columnspan=5, padx=6, pady=6)
bill_table.grid_rowconfigure(1, weight=1)
bill_table.grid_columnconfigure(0, weight=1)
bill_table.configure(height=10)
bill_count_label = tk.Label(bill_frame, text="Bill Items: 0", bg="#f8f9fa")
bill_count_label.grid(row=2, column=0, padx=6, pady=2, sticky="w")
bill_bottom_frame = tk.Frame(bill_frame,bg="#f8f9fa")
bill_bottom_frame.grid(row=3, column=0, columnspan=12, sticky="ew", pady=10)
grand_total_label = tk.Label(bill_bottom_frame,text="Grand Total: ₹0.00",font=("Segoe UI", 14, "bold"),bg="#f8f9fa",fg="red")
grand_total_label.grid(row=0, column=2, padx=20)

# Payment Mode
tk.Label(bill_frame, text="Payment Mode:", bg="#f8f9fa", font=("Segoe UI", 10, "bold")).grid(row=8, column=0, pady=5)
tk.Radiobutton(bill_frame, text="Cash", variable=payment_mode_var, value="Cash", bg="#f8f9fa").grid(row=8, column=1)
payment_mode_var.trace_add("write",on_payment_mode_change)
tk.Radiobutton(bill_frame, text="UPI", variable=payment_mode_var, value="UPI", bg="#f8f9fa").grid(row=8, column=2)
tk.Radiobutton(bill_frame, text="Card", variable=payment_mode_var, value="Card", bg="#f8f9fa").grid(row=8, column=3)

# Cash Section
tk.Label(bill_bottom_frame, text="Cash Received:", bg="#f8f9fa",font=("Segoe UI", 10, "bold")).grid(row=4, column=0, padx=5, pady=5)
cash_entry = tk.Entry(bill_bottom_frame, textvariable=cash_received_var, width=15)
cash_entry.grid(row=4, column=1, padx=5, pady=5)
cash_entry.config(state="normal")
tk.Label(bill_bottom_frame, text="Balance:", bg="#f8f9fa",font=("Segoe UI", 10, "bold")).grid(row=4, column=2, padx=5, pady=5)
tk.Label(bill_bottom_frame, textvariable=balance_var,bg="#f8f9fa", fg="green", font=("Segoe UI", 12, "bold")).grid(row=4, column=3, padx=5, pady=5)
cash_received_var.trace_add("write", lambda *args: calculate_balance())

# Coupon Code
tk.Label(bill_bottom_frame,text="Coupon Code:",bg="#f8f9fa",font=("Segoe UI", 10, "bold")).grid(row=1, column=0, padx=5)
coupon_var = tk.StringVar()
tk.Entry(bill_bottom_frame,textvariable=coupon_var,width=20).grid(row=1, column=1, padx=5)
tk.Button(bill_bottom_frame,text="Apply",bg="#17a2b8",fg="white",command=apply_coupon).grid(row=1, column=2, padx=5)

#Customer details
customer_name = tk.StringVar()
customer_phone = tk.StringVar()
tk.Label(bill_frame, text="Customer Name:").grid(row=0, column=0, padx=6, pady=6, sticky="e")
tk.Entry(bill_frame, textvariable=customer_name, width=25).grid(row=0, column=1, padx=6, pady=6, sticky="w")
tk.Label(bill_frame, text="Phone:").grid(row=0, column=2, padx=6, pady=6, sticky="e")
tk.Entry(bill_frame, textvariable=customer_phone, width=15).grid(row=0, column=3, padx=6, pady=6, sticky="w")

#Bill buttons
tk.Button(bill_frame, text="Clear Bill (Finalize)", command=clear_bill, bg="#28a745", fg="white").grid(row=2, column=5, padx=6, pady=6)
tk.Button(bill_frame, text="Export TXT", command=export_bill_txt, bg="#007bff", fg="white").grid(row=1, column=9, padx=6, pady=6)
tk.Button(bill_frame, text="Print", command=print_bill, bg="#6f42c1", fg="white").grid(row=1, column=7, padx=6, pady=6)

#Stock Frame
stock_frame = tk.LabelFrame(root, text="Stock Management", padx=10, pady=10, bg="#f8f9fa")
home_btn_stock = tk.Button(stock_frame,text="Home", command=go_to_home, bg="#343a40", fg="white")
home_btn_stock.grid(row=2, column=7, padx=5)
stock_name = tk.StringVar()
stock_price = tk.StringVar()
stock_qty = tk.StringVar()
stock_category = tk.StringVar()
tk.Label(stock_frame, text="Item Name:").grid(row=0, column=0, padx=6, pady=6, sticky="e")
tk.Entry(stock_frame, textvariable=stock_name, width=30).grid(row=0, column=1, padx=6, pady=6, sticky="w")
tk.Label(stock_frame, text="Price:").grid(row=0, column=2, padx=6, pady=6, sticky="e")
tk.Entry(stock_frame, textvariable=stock_price, width=12).grid(row=0, column=3, padx=6, pady=6, sticky="w")
tk.Label(stock_frame, text="Quantity:").grid(row=0, column=4, padx=6, pady=6, sticky="e")
tk.Entry(stock_frame, textvariable=stock_qty, width=12).grid(row=0, column=5, padx=6, pady=6, sticky="w")
tk.Label(stock_frame, text="Category:").grid(row=0, column=6, padx=6, pady=6, sticky="e")
category_combo_stock = ttk.Combobox(stock_frame,textvariable=stock_category,values=CATEGORIES,state="readonly",width=16)
category_combo_stock.grid(row=0, column=7, padx=6, pady=6, sticky="w")
category_combo_stock.set("Grocery")
add_stock_btn = tk.Button(stock_frame, text="Add / Update Stock", command=add_stock, bg="#28a745", fg="white")
add_stock_btn.grid(row=2, column=1, padx=6, pady=6)

# Search & Filter
search_var = tk.StringVar()
tk.Label(stock_frame, text="Search:").grid(row=1, column=0, padx=6, pady=6, sticky="e")
tk.Entry(stock_frame, textvariable=search_var, width=25).grid(row=1, column=1, padx=6, pady=6, sticky="w")
category_filter = tk.StringVar()
category_combo = ttk.Combobox(stock_frame, textvariable=category_filter, state="readonly", width=20)
category_combo.grid(row=1, column=2, padx=6, pady=6, sticky="w")
category_combo['values'] = ["All"]
category_combo.current(0)

def _on_category_change(*args):
    update_stock_table(search_var.get())
category_filter.trace_add("write", _on_category_change)
search_var.trace_add("write", lambda *args: update_stock_table(search_var.get()))

# Stock Table
columns = ("Item", "Price", "Qty", "Category")
stock_table = ttk.Treeview(stock_frame, columns=columns, show="headings", height=30)
for col in columns:
    stock_table.heading(col, text=col)
    stock_table.column(col, width=200 if col != "Item" else 180)
stock_table.grid(row=5, column=0, columnspan=12, padx=10, pady=10, sticky="nsew")
stock_table.grid_rowconfigure(4, weight=1)
stock_table.grid_columnconfigure(0, weight=1)
stock_table.configure(height=13)
edit_btn = tk.Button(stock_frame, text="Edit", command=edit_stock, bg="#ffc107", fg="black")
edit_btn.grid(row=2, column=3, padx=6, pady=6)
remove_btn = tk.Button(stock_frame, text="Remove", command=remove_stock, bg="#dc3545", fg="white")
remove_btn.grid(row=2, column=5, padx=6, pady=6)
stock_count_label = tk.Label(stock_frame, text="Stock Items: 0", bg="#f8f9fa")
stock_count_label.grid(row=6, column=2, padx=6, pady=6)
    
#Initialize
load_invoice_no()
load_stock()
update_stock_table()
load_loyalty_points()

def show_login():
    login_win = tk.Toplevel()
    login_win.title("Login - Abinish Digital Mart")
    login_win.geometry("300x220")
    login_win.resizable(False, False)
    tk.Label(login_win, text="Username").pack(pady=5)
    username_var = tk.StringVar()
    tk.Entry(login_win, textvariable=username_var).pack()
    tk.Label(login_win, text="Password").pack(pady=5)
    password_var = tk.StringVar()
    tk.Entry(login_win, textvariable=password_var, show="*").pack()

    def attempt_login():
        if check_login(username_var.get(), password_var.get()):
            root.deiconify()
            user_label.config(text=f"Logged in as: {current_user_name} ({current_user_role})")
            messagebox.showinfo("Success", f"Welcome {current_user_name} ({current_user_role})")
            login_win.destroy()
            apply_role_permissions()
            show_home_page()
        else:
            messagebox.showerror("Error", "Invalid credentials")
    tk.Button(login_win, text="Login", command=attempt_login, bg="#28a745", fg="white").pack(pady=15)
    root.protocol("WM_DELETE_WINDOW", on_closing)
    login_win.grab_set()

root.after(100, show_login)
root.mainloop()
#   THE PROGRAM ENDS
#                   ABINESH DIGITAL MART
