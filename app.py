from flask import Flask, render_template, request

app = Flask(__name__)

transactions = []
balance = 0

@app.route("/", methods=["GET", "POST"])
def index():
    global balance

    if request.method == "POST":
        description = request.form["description"]
        amount = float(request.form["amount"])
        trans_type = request.form["type"]

        if trans_type == "income":
            balance += amount
        elif trans_type == "expense":
            balance -= amount

        transactions.append({
            "description": description,
            "amount": amount,
            "type": trans_type
        })

    return render_template("index.html", transactions=transactions, balance=balance)

if __name__ == "__main__":
    app.run(debug=True)
