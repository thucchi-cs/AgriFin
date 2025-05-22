from calendar import monthrange
from datetime import date, timedelta
from flask import Flask, render_template, redirect, request, flash, session, jsonify
from flask_session import Session
from supabase import create_client, Client
from helpers import *
from werkzeug.security import generate_password_hash


app = Flask(__name__)
# flask run --debug

# Set up jinja filters
app.jinja_env.filters["usd"] = format_usd
app.jinja_env.filters["abs"] = absolute
app.jinja_env.filters["date"] = format_date
app.jinja_env.globals["today"] = get_today

# Set up web app
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Set up database
db_url = "https://mmthtxmumsrjsqfwwwuz.supabase.co"
db_key = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im1tdGh0eG11bXNyanNxZnd3d3V6Iiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc0Nzc5NjQ0MSwiZXhwIjoyMDYzMzcyNDQxfQ.3n7769s9J8c0QBmLoIYeYftyGFksYXmUapMQvFjuxZU"
db: Client = create_client(db_url, db_key)

# Website homepage
@app.route("/", methods=["POST", "GET"])
def index():
    if session.get("user_id"):
        # Redirect to dashboard if logged in
        return redirect("/dashboard")
    
    # Redirect to login if not logged in
    return redirect("/login")

# User's dashboard
@app.route("/dashboard")
@login_required
def dashboard():   
    # Get user data
    user = list(db.table("users").select("*").eq("id", session.get("user_id")).execute())[0][1][0]
    balance = get_user_balance(db, session.get("user_id"))
    
    # Get user's income and expenses over this month to display
    today = date.today()
    start = date(today.year, today.month, 1)
    end = date(today.year, today.month, monthrange(today.year, today.month)[1])
    income = db.table("transactions").select("abs_amount").eq("user_id", session.get("user_id")).eq("deleted", False).gt("amount", 0).gte("date_transacted", start).lte("date_transacted", end).execute().data
    income = [i["abs_amount"] for i in income]
    expenses = db.table("transactions").select("abs_amount").eq("user_id", session.get("user_id")).eq("deleted", False).lt("amount", 0).gte("date_transacted", start).lte("date_transacted", end).execute().data
    expenses = [i["abs_amount"] for i in expenses]
    income = sum(income)
    expenses = sum(expenses)
    
    # Get current month and year to be displayed
    month_year = today.strftime("%B %Y")
    
    # Go to user's dashboard
    return render_template("dashboard.html", username=user["username"], date_joined=user["date_joined"], balance=balance, income=income, expenses=expenses, page="dashboard", month_year=month_year)

# Login page
@app.route("/login", methods=["POST", "GET"])
def login():    
    # Login request
    if request.method == "POST":
        # Get input from page
        username = request.form.get("username")
        password = request.form.get("password")
        
        # Check if inputs are valid
        if check_valid_login(db, username, password):
            # Log in the user for the current session
            set_session_user(db, username)
            
            # Go to user's dashboard
            return redirect("/dashboard")
        
    
    # Go to login page
    return render_template("login.html")

# Register page
@app.route("/register", methods=["POST", "GET"])
def register():
    # Register request
    if request.method == "POST":
        # Get fields filled out from page
        username = request.form.get("username")
        password = request.form.get("password")
        password2 = request.form.get("password2")
        balance = request.form.get("balance")
        
        # Check for input validity
        if check_valid_registration(db, username, password, password2, balance):
            # Hash password for security
            hashed_password = generate_password_hash(password)
        
            # Add user to database
            db.table("users").insert({"username": username, "password_hash": hashed_password}).execute()
            
            # Login user to the current session
            set_session_user(db, username)
            
            # Initialize user with $0
            db.table("balances").insert({"user_id": session["user_id"], "current_balance": balance}).execute()
            
            # Direct user to dashboard
            return redirect("/dashboard")
        
    
    # Go to register page
    return render_template("register.html")

# User logs out
@app.route("/logout")
def logout():
    # Clear current session
    session.clear()
    
    # Return to website homepage
    return redirect("/")

# Analysis page
@app.route("/analysis")
@login_required
def analysis():
    return render_template("analysis.html", page="analysis")

# Transactions page
@app.route("/transactions", methods=["POST", "GET"])
@login_required
def transactions():
    # Default sorting values
    orders = {"date_transacted": "Date", "abs_amount": "Amount"}
    sort_by = "date_transacted"
    desc = False
    filter_category = "All"
    
    # Get sorting values if needed
    if request.method == "POST":
        sort_by = request.form.get("sort")
        desc = request.form.get("reverse")
        desc = False if desc == "False" else True
        filter_category = request.form.get("categories")
        filter_category = 0 if filter_category == "All" else int(filter_category)
    
    # Query database for transactions
    desc = not desc
    if filter_category == "All":
        user_transactions = db.table("transactions").select("*, categories(category)").eq("user_id", session['user_id']).order(sort_by, desc=desc).execute().data
    else:
        user_transactions = db.table("transactions").select("*, categories(category)").eq("user_id", session['user_id']).eq("category_id", filter_category).order(sort_by, desc=desc).execute().data
    
    has_transactions = len(user_transactions) > 0

    # Go to transactions page
    return render_template("transactions.html", transactions=user_transactions, has_transactions=has_transactions, sort=sort_by, order_keys=orders.keys(), orders=orders, desc=not desc, page="transactions", categories_income=session["categories_income"], categories_expense=session["categories_expense"], filter_category=filter_category)

# Add a transaction
@app.route("/add_transaction", methods=["POST", "GET"])
@login_required
def add_transaction():
    if request.method == "POST":        
        # Get inputs
        amount = float(request.form.get("amount"))
        date_transacted = request.form.get("date")
        type = request.form.get("type")
        category = request.form.get(f"category_{type}")
        amount *= -1 if type == "expense" else 1
        water = request.form.get("water")
        farming_type = request.form.get("farming_type")
        sustainable = request.form.get("sustainable")
        today = date.today()

        # Arrange inputs into json dictionary to be passed in to database
        data = {
            "user_id": session.get("user_id"), 
            "amount": amount, 
            "abs_amount": abs(amount),
            "date_transacted": date_transacted, 
            "date_added": str(today), 
            "category_id": category,
            "water_usage": water,
            "farming_id": farming_type,
            "sustainable": sustainable
        }
        
        # Insert transaction into database
        db.table("transactions").insert(data).execute()
        
        # Update user's current balance
        current_balance = get_user_balance(db, session.get("user_id"))
        db.table("balances").update({"current_balance": current_balance+amount}).eq("user_id", session.get("user_id")).execute()
        
        # Go back to transactions page
        return redirect("/transactions")
    
    farming_types = db.table("farming_types").select("*").execute().data
    # Open add transactions page
    return render_template("add_transaction.html", add=True, edit=False, categories_income=session["categories_income"], categories_expense=session["categories_expense"], farming_types=farming_types)

# Edit a transaction page
@app.route("/edit_transaction", methods=["POST"])
@login_required
def edit_transaction():
    # Get info of transaction to be edited
    transaction_info = db.table("transactions").select("*").eq("transaction_id", request.form.get("id")).execute().data[0]
    farming_types = db.table("farming_types").select("*").execute().data
    
    # Go to add transaction page
    return render_template("add_transaction.html", add=False, edit=True, info=transaction_info, categories_income=session["categories_income"], categories_expense=session["categories_expense"], farming_types=farming_types)

# Edit transaction
@app.route("/edited_transaction", methods=["POST"])
def edited_transaction():    
    # Get inputs
    amount = float(request.form.get("amount"))
    date_transacted = request.form.get("date")
    type = request.form.get("type")
    category = request.form.get(f"category_{type}")
    amount *= -1 if type == "expense" else 1
    id = request.form.get("id")
    water = request.form.get("water")
    farming_type = request.form.get("farming_type")
    sustainable = request.form.get("sustainable")

    # Find updated difference 
    difference = amount - db.table("transactions").select("*").eq("transaction_id", request.form.get("id")).execute().data[0]["amount"]
    
    # Add transaction to database table 'transactions'
    data = {
        "amount": amount,
        "abs_amount": abs(amount),
        "date_transacted": date_transacted,
        "category_id": category,
        "water_usage": water,
        "farming_id": farming_type,
        "sustainable": sustainable
    }
    db.table("transactions").update(data).eq("transaction_id", id).execute()
    
    # Update user's current balance
    current_balance = get_user_balance(db, session.get("user_id"))
    db.table("balances").update({"current_balance": current_balance+difference}).eq("user_id", session.get("user_id")).execute()
    
    # Return to transactions page
    return redirect("/transactions")

# Delete a transaction
@app.route("/delete_transaction", methods=["POST"])
def delete_transaction():
    # Get id and amount of transaction to be deleted
    id = request.form.get("id")
    amount = db.table("transactions").select("*").eq("transaction_id", request.form.get("id")).execute().data[0]["amount"]
    
    # Delete transaction from database
    db.table("transactions").update({"deleted": True}).eq("transaction_id", id).execute()
    
    # Update user's balance
    current_balance = get_user_balance(db, session.get("user_id"))
    db.table("balances").update({"current_balance": current_balance-amount}).eq("user_id", session.get("user_id")).execute()
    
    # Return to transactions page
    return redirect("/transactions")

# Restore a deleted transaction
@app.route("/restore_transaction", methods=["POST"])
def restore_transaction():
    # Get id and amount of transaction to be deleted
    id = request.form.get("id")
    amount = db.table("transactions").select("*").eq("transaction_id", request.form.get("id")).execute().data[0]["amount"]
    
    # Restore transaction from database
    db.table("transactions").update({"deleted": False}).eq("transaction_id", id).execute()
    
    # Update user's balance
    current_balance = get_user_balance(db, session.get("user_id"))
    db.table("balances").update({"current_balance": current_balance+amount}).eq("user_id", session.get("user_id")).execute()
    
    # Return to transactions page
    return redirect("/transactions")
        
# Update session from script.js
@app.route('/update_session', methods=['POST'])
def update_session():
    data = request.get_json()
    session[data.get("key")] = data.get("value")
    return 'Session updated'

# Get user's data for chart analysis
@app.route("/get_chart_data")
def get_transac_analysis_data(): 
    week = True if request.args.get("periods", "weeks") == "weeks" else False
    labels, date_ranges = get_date_ranges(week)

    # Query data base for each time range
    total = [] 
    sustainable = []     
    for r in date_ranges:
        # Get inputs
        transac_type = request.args.get("type", "income")
        
        # Query either income or expenses
        if transac_type == "income":
            response = db.table("transactions").select("abs_amount", "sustainable").eq("user_id", session.get("user_id")).eq("deleted", False).gt("amount", 0).gte("date_transacted", r.get("begin")).lte("date_transacted", r.get("end")).execute()
        else:
            response = db.table("transactions").select("abs_amount", "sustainable").eq("user_id", session.get("user_id")).eq("deleted", False).lt("amount", 0).gte("date_transacted", r.get("begin")).lte("date_transacted", r.get("end")).execute()
        
        # Update info to be displayed
        data = response.data
        total_amount = 0
        total_sustainable = 0
        for d in data:
            total_amount += d["abs_amount"]
            total_sustainable += d["abs_amount"] if d["sustainable"] else 0
            print(d["sustainable"])

        total.append(total_amount)
        sustainable.append(total_sustainable)

        
    # Return the labels and values for graphs
    return jsonify({"labels":labels, "values": total, "sustainable": sustainable})

# Get user's water usage for analysis
@app.route("/water")
def get_water():
    week = True if request.args.get("period", "weeks") == "weeks" else False
    labels, date_ranges = get_date_ranges(week)

    # Query data base for each time range
    values = []    
    for r in date_ranges:
        
        # Get water usage of this date range
        response = db.table("transactions").select("water_usage").eq("user_id", session.get("user_id")).eq("deleted", False).gte("date_transacted", r.get("begin")).lte("date_transacted", r.get("end")).execute()
        
        # Update info to be displayed
        data = response.data
        data = [i["water_usage"] for i in data]

        values.append(sum(data))

        
    # Return the labels and values for graphs
    return jsonify({"labels":labels, "values": values})

# Get user's balance over the month for charts
@app.route("/balance")
def get_balance():
    # Find today
    today = date.today()
    labels = []
    values = []
    
    # Get user's current balance
    current_balance = db.table("balances").select("current_balance").eq("user_id", session.get("user_id")).execute().data[0]["current_balance"]

    # Find user's balance everyday of this month
    for i in range(today.day, 0, -1):
        # Get date 
        current_date = date(today.year, today.month, i)
        
        # Query all transactions of current date
        today_amount = db.table("transactions").select("amount").eq("user_id", session.get("user_id")).eq("date_transacted", current_date).eq("deleted", False).execute().data
        
        # No balance changes if there are no transactions
        if len(today_amount) == 0:
            today_amount = 0
        else:
            # Add all transactions together
            today_amount = [j["amount"] for j in today_amount]
            today_amount = sum(today_amount)
        
        # Update balance for that date
        current_balance -= today_amount

        # Add info to be passed into charts
        labels.insert(0, current_date.strftime("%m/%d"))
        values.insert(0, current_balance)
    
    # Add NULL info for dates after today of this month
    for i in range(today.day+1, monthrange(today.year, today.month)[1] + 1):
        current_date = date(today.year, today.month, i)
        labels.append(current_date.strftime("%m/%d"))
        values.append(None)
    
    # Return labels and values for charts
    return jsonify({"labels":labels, "values": values})

# Get the user's categories
@app.route("/categories")
def get_categories():
    # Get current date and month
    today = date.today()
    start = date(today.year, today.month, 1)
    end = date(today.year, today.month, monthrange(today.year, today.month)[1])
    
    # Query all transactions of this month
    categories = db.table("transactions").select("categories(category)", "abs_amount").eq("user_id", session.get("user_id")).eq("deleted", False).lt("amount", 0).gte("date_transacted", start).lte("date_transacted", end).execute().data
    values = {}
    
    # Get inputs    
    sort_type = request.args.get("type", "spending")
    
    # Update counts for categories based on each transaction
    for i in categories:
        count = values.get(str(i["categories"]["category"]).capitalize(), 0)
        
        # Update frequency count
        if sort_type == "frequency":
            count += 1
            
        # Update amount count
        elif sort_type == "spending":
            count += i["abs_amount"]
            
        # Add info to data to be passed into chart
        values[str(i["categories"]["category"]).capitalize()] = count
    
    # Return labels and values for charts
    return jsonify({"labels": list(values.keys()), "values": list(values.values())})

# Get the user's farming types
@app.route("/farming")
def get_types():
    # Get current date and month
    today = date.today()
    start = date(today.year, today.month, 1)
    end = date(today.year, today.month, monthrange(today.year, today.month)[1])
    
    # Query all transactions of this month
    types = db.table("transactions").select("farming_types(type)", "abs_amount").eq("user_id", session.get("user_id")).eq("deleted", False).gte("date_transacted", start).lte("date_transacted", end).execute().data
    values = {}
    
    # Get inputs    
    sort_type = request.args.get("type", "values")
    
    # Update counts for categories based on each transaction
    for i in types:
        count = values.get(str(i["farming_types"]["type"]).capitalize(), 0)
        
        # Update frequency count
        if sort_type == "frequency":
            count += 1
            
        # Update amount count
        elif sort_type == "values":
            count += i["abs_amount"]
            print(count, i["abs_amount"], i["farming_types"]["type"])

        # Add info to data to be passed into chart
        values[str(i["farming_types"]["type"]).capitalize()] = count
    
    # Return labels and values for charts
    return jsonify({"labels": list(values.keys()), "values": list(values.values())})