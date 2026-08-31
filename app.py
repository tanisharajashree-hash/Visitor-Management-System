from flask import Flask, render_template, request, redirect, url_for
import mysql.connector

app = Flask(__name__)

# MySQL Database Connection
db = mysql.connector.connect(
    host="localhost",
    user="root",
    password="tanisha@2006",
    database="visitor_management"
)

@app.route("/", methods=["GET", "POST"])
def login():

    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        cursor = db.cursor(dictionary=True)

        cursor.execute(
            "SELECT * FROM admin WHERE username = %s AND password = %s",
            (username, password)
        )

        admin = cursor.fetchone()
        cursor.close()

        print("LOGIN RESULT:", admin)  # Debugging statement

        if admin:
            return redirect(url_for("dashboard"))

        return render_template(
            "login.html",
            error="Invalid username or password"
        )

    return render_template("login.html")


@app.route("/dashboard")
def dashboard():
    return render_template("dashboard.html")


if __name__ == "__main__":
    app.run(debug=True)