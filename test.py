from cs50 import SQL
db = SQL("sqlite:///finance.db")
from helpers import apology, login_required, lookup, usd
# rows = db.execute(
#             "SELECT symbol,shares,price FROM buy WHERE user_id = ?",1
#         )



# for row in rows:
#     row["total"] = int(row['shares']) * float(row['price'])


# cash = db.execute(
#             "SELECT cash FROM users WHERE id = ?", 1
#         )

test = {"price":10.000 , "symbol":"effc"}

symbol = test['symbol']
price = round(float(test['price']),3)

print(symbol)
print(price)






