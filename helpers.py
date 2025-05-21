from datetime import date
from flask import redirect, session, flash
from functools import wraps
from werkzeug.security import check_password_hash
import datetime

# Format money
def format_usd(num):
    if ((type(num) != int) and (type(num) != float)):
        return num
    return f'$%0.2f' % float(num)

# Format date
def format_date(date):
    date = datetime.datetime.strptime(date, "%Y-%m-%d")
    month = date.strftime('%B')[:3]
    return f"{month} {date.day}, {date.year}"

# Get absolute value of number
def absolute(num):
    return abs(num)

def get_today():
    return date.today()

# Check if currently logged in
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get("user_id") is None:
            print(session.get("user_id"), "user")
            return redirect("/")
        return f(*args, **kwargs)

    return decorated_function

# Check if input for registration is valid
def check_valid_registration(db, username, password, password2, balance):
    # Get list of existing usernames
    usernames = list(db.table("users").select("username").execute())[0][1]
    usernames = [user["username"] for user in usernames]
    
    # Check if all section is filled out
    if (username == "") or (password == "") or (password2 == ""):
        flash("All fields must be filled out!")
        return False
    
    # Check if username is valid
    if username in usernames:
        flash("Username already exists!")
        return False
    
    # Check for invalid characters in username
    allowed = "abcdefghijklmnopqrstuvwxyz0123456789_."
    for letter in username:
        if letter not in allowed:
            flash("Username can only contain lowercase letters a-z, digits 0-9, periods or underscores!")
            return False
    
    # Check for password security level
    symbols = "`~!@#$%^&*()_-+=;:,.<>?/{}[]\\|"
    has_symbol = False
    has_digit = False
    has_upper = False
    for letter in password:
        if letter in symbols:
            has_symbol = True
        elif letter.isdigit():
            has_digit = True
        elif letter != letter.lower():
            has_upper = True
        
        if has_symbol and has_digit and has_upper:
            break
    else:
        flash("Password must meet security criteria!")
        return False
    
    if len(password) < 8:
        flash("Password must meet security criteria!")
        return False
    
    # Check if password was confirmed
    if password != password2:
        flash("Password was not confirmed!")
        return False
    
    # Check for valid starting balance
    if balance < 0:
        flash("Invalid starting balance!")
        return False
    
    # All fields pass
    return True

# Check if login inputs are valid
def check_valid_login(db, username, password):
    # Check if username is in database
    try:
        # Get data of user that matches username
        users = list(db.table("users").select("*").eq("username", username).execute())[0][1][0]
    except:
        # User was not found
        flash("Incorrect username and/or password!")
        return False
    
    # Check if password was incorrect
    if not check_password_hash(users["password_hash"], password):
        flash("Incorrect username and/or password!")
        return False
    
    # All inputs are valid
    return True

# Log in user
def set_session_user(db, username):
    user = db.table("users").select("id").eq("username", username).execute().data[0]
    session['user_id'] = user["id"]
    session['username'] = username
    session["categories_income"] = db.table("categories").select("*").eq("income", True).execute().data
    session["categories_expense"] = db.table("categories").select("*").eq("expense", True).execute().data
    
# Get user's balance from database
def get_user_balance(db, user_id):
    print(db.table("balances").select("current_balance").eq("user_id", user_id).execute().data)
    balance = db.table("balances").select("current_balance").eq("user_id", user_id).execute().data[0].get("current_balance")
    return balance