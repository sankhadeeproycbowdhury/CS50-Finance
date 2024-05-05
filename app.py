import os

from cs50 import SQL
from flask import Flask, flash, redirect, render_template, request, session
from flask_session import Session
from werkzeug.security import check_password_hash, generate_password_hash

from helpers import apology, login_required, lookup, usd

# Configure application
app = Flask(__name__)

# Custom filter
app.jinja_env.filters["usd"] = usd

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///finance.db")


@app.after_request
def after_request(response):
    """Ensure responses aren't cached"""
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response


@app.route("/")
@login_required
def index():
    """Show portfolio of stocks"""
    rows = db.execute(
        "SELECT symbol,shares,price FROM buy WHERE user_id = ?", session["user_id"]
    )

    cash = db.execute("SELECT cash FROM users WHERE id = ?", session["user_id"])

    total = 0
    for row in rows:
        row["total"] = "{:.2f}".format(
            round(int(row["shares"]) * float(row["price"]), 2)
        )
        total = total + float(row["total"])

    total = "{:.2f}".format(round(total + float(cash[0]["cash"]), 2))

    cash = "{:.2f}".format(round(cash[0]["cash"], 2))

    return render_template("index.html", rows=rows, cash=cash, total=total)


@app.route("/buy", methods=["GET", "POST"])
@login_required
def buy():
    """Buy shares of stock"""
    if request.method == "POST":
        if not request.form.get("symbol"):
            return apology("please enter symbol", 400)

        lookup_res = lookup(request.form.get("symbol"))
        if lookup_res == None:
            return apology("please enter a valid symbol", 400)

        if not request.form.get("shares"):
            return apology("please enter a valid share Number", 400)

        try:
            share = int(request.form.get("shares"))
        except ValueError:
            return apology("please enter a valid share number", 400)

        if int(request.form.get("shares")) <= 0:
            return apology("please enter a valid share Number", 400)

        cash = db.execute("SELECT cash FROM users WHERE id = ?", session["user_id"])

        if float(lookup_res["price"]) * int(request.form.get("shares")) > float(
            cash[0]["cash"]
        ):
            return apology("Sorry, stock purchase is unsuccessful due low cash", 403)

        search = db.execute(
            "SELECT * FROM buy WHERE user_id = ? AND symbol = ?",
            session["user_id"],
            lookup_res["symbol"],
        )

        if search:
            db.execute(
                "UPDATE buy SET shares = ? WHERe user_id = ? AND symbol = ?",
                int(request.form.get("shares")) + int(search[0]["shares"]),
                session["user_id"],
                request.form.get("symbol"),
            )

        else:
            db.execute(
                "INSERT INTO buy (symbol, price, user_id, shares) VALUES (?, ?, ?, ?)",
                lookup_res["symbol"],
                float(lookup_res["price"]),
                session["user_id"],
                request.form.get("shares"),
            )

        cost = float(lookup_res["price"]) * float(request.form.get("shares"))
        db.execute(
            "UPDATE users SET cash = ? WHERe id = ?",
            float(cash[0]["cash"]) - cost,
            session["user_id"],
        )

        db.execute(
            "INSERT INTO logs (symbol, price, status, user_id, shares) VALUES (?, ?, ?, ?, ?)",
            lookup_res["symbol"],
            float(lookup_res["price"]),
            "BUY",
            session["user_id"],
            request.form.get("shares"),
        )
        return redirect("/")

    else:
        return render_template("buy.html")


@app.route("/history")
@login_required
def history():
    """Show history of transactions"""
    rows = db.execute(
        "SELECT symbol,price,status,created_at,shares FROM logs WHERE user_id = ? ORDER BY session_id",
        session["user_id"],
    )

    for row in rows:
        row["price"] = "{:.2f}".format(round(float(row["price"]), 2))

    return render_template("logs.html", rows=rows)


@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""

    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":
        # Ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username", 403)

        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password", 403)

        # Query database for username
        rows = db.execute(
            "SELECT * FROM users WHERE username = ?", request.form.get("username")
        )

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(
            rows[0]["hash"], request.form.get("password")
        ):
            return apology("invalid username and/or password", 403)

        # Remember which user has logged in
        session["user_id"] = rows[0]["id"]

        # Redirect user to home page
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")


@app.route("/logout")
def logout():
    """Log user out"""

    # Forget any user_id
    session.clear()

    # Redirect user to login form
    return redirect("/")


@app.route("/quote", methods=["GET", "POST"])
@login_required
def quote():
    """Get stock quote."""
    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":
        if not request.form.get("symbol"):
            return apology("please enter a valid symbol", 400)

        lookup_res = lookup(request.form.get("symbol"))
        if lookup_res == None:
            return apology("please enter a valid symbol", 400)

        symbol = lookup_res["symbol"]
        price = "{:.2f}".format(round(float(lookup_res["price"]), 2))

        return render_template("quoted.html", symbol=symbol, price=price)

    else:
        return render_template("quote.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":
        if not request.form.get("username"):
            return apology("must provide username", 400)
        elif not request.form.get("password"):
            return apology("must provide password", 400)
        elif not request.form.get("confirmation"):
            return apology("must provide confirmation", 400)
        elif request.form.get("password") != request.form.get("confirmation"):
            return apology("must provide same confirmation and Password", 400)

        rows = db.execute(
            "SELECT * FROM users WHERE username = ?", request.form.get("username")
        )

        if len(rows) >= 1:
            return apology("username alreadt exits,try another one", 400)

        db.execute(
            "INSERT INTO users (username, hash) VALUES (?, ?)",
            request.form.get("username"),
            generate_password_hash(request.form.get("password")),
        )

        return redirect("/login")
    else:
        return render_template("register.html")


@app.route("/sell", methods=["GET", "POST"])
@login_required
def sell():
    """Sell shares of stock"""
    if request.method == "POST":
        if not request.form.get("symbol"):
            return apology("please enter a valid symbol", 403)

        if not request.form.get("shares"):
            return apology("please enter the  Number of shares ", 403)

        try:
            share = int(request.form.get("shares"))
        except ValueError:
            return apology("please enter a valid share number", 403)

        value = db.execute(
            "SELECT shares,price FROM buy WHERE symbol = ? AND user_id = ?",
            request.form.get("symbol"),
            session["user_id"],
        )

        if (
            int(request.form.get("shares")) <= 0
            or int(request.form.get("shares")) > value[0]["shares"]
        ):
            return apology("please enter a valid number of shares ", 400)

        db.execute(
            "UPDATE buy SET shares = ? WHERE user_id = ? AND  symbol = ?",
            value[0]["shares"] - int(request.form.get("shares")),
            session["user_id"],
            request.form.get("symbol"),
        )

        cash = db.execute("SELECT cash FROM users WHERE id = ?", session["user_id"])
        cost = int(request.form.get("shares")) * value[0]["price"]

        db.execute(
            "UPDATE users SET cash = ? WHERe id = ?",
            cash[0]["cash"] + cost,
            session["user_id"],
        )

        shares = db.execute(
            "SELECT shares FROM buy WHERE symbol = ? AND user_id = ?",
            request.form.get("symbol"),
            session["user_id"],
        )

        if int(shares[0]["shares"]) <= 0:
            db.execute(
                "DELETE FROM buy WHERE symbol = ? AND user_id = ?",
                request.form.get("symbol"),
                session["user_id"],
            )

        db.execute(
            "INSERT INTO logs (symbol, price, status, user_id, shares) VALUES (?, ?, ?, ?, ?)",
            request.form.get("symbol"),
            value[0]["price"],
            "SELL",
            session["user_id"],
            request.form.get("shares"),
        )

        return redirect("/")

    else:
        rows = db.execute(
            "SELECT symbol FROM buy WHERE user_id = ?", session["user_id"]
        )

        return render_template("sell.html", rows=rows)


@app.route("/add", methods=["GET", "POST"])
@login_required
def add():
    if request.method == "POST":
        if not request.form.get("money"):
            return apology("please enter the amount", 403)

        try:
            money = float(request.form.get("money"))
        except ValueError:
            return apology("please enter valid amount", 403)

        if money <= 0:
            return apology("please enter valid amount", 403)

        cash = db.execute("SELECT cash FROM users WHERE id = ?", session["user_id"])

        db.execute(
            "UPDATE users SET cash = ? WHERe id = ?",
            round(float(cash[0]["cash"]) + float(request.form.get("money")), 2),
            session["user_id"],
        )

        return redirect("/")
