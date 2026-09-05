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

@app.route("/visitors")
def visitors():

    cursor = db.cursor(dictionary=True)

    cursor.execute("SELECT * FROM visitor")

    visitors = cursor.fetchall()

    cursor.close()

    return render_template("visitors.html", visitors=visitors)

@app.route("/view-visitor/<int:visitor_id>")
def view_visitor(visitor_id):

    cursor = db.cursor(dictionary=True)

    cursor.execute(
        "SELECT * FROM visitor WHERE visitor_id = %s",
        (visitor_id,)
    )

    visitor = cursor.fetchone()

    cursor.close()

    return render_template("view_visitor.html", visitor=visitor)

@app.route("/edit-visitor/<int:visitor_id>", methods=["GET", "POST"])
def edit_visitor(visitor_id):

    cursor = db.cursor(dictionary=True)

    if request.method == "POST":

        name = request.form["name"]
        phone = request.form["phone"]
        email = request.form["email"]
        purpose = request.form["purpose"]

        cursor.execute(
            """
            UPDATE visitor
            SET name = %s,
                phone = %s,
                email = %s,
                purpose = %s
            WHERE visitor_id = %s
            """,
            (name, phone, email, purpose, visitor_id)
        )

        db.commit()
        cursor.close()

        return redirect(url_for("visitors"))

    cursor.execute(
        "SELECT * FROM visitor WHERE visitor_id = %s",
        (visitor_id,)
    )

    visitor = cursor.fetchone()

    cursor.close()

    return render_template("edit_visitor.html", visitor=visitor)


@app.route("/delete-visitor/<int:visitor_id>")
def delete_visitor(visitor_id):

    cursor = db.cursor()

    cursor.execute(
        "DELETE FROM visitor WHERE visitor_id = %s",
        (visitor_id,)
    )

    db.commit()
    cursor.close()

    return redirect(url_for("visitors"))

@app.route("/add-visitor", methods=["GET", "POST"])
def add_visitor():

    if request.method == "POST":
        name = request.form["name"]
        phone = request.form["phone"]
        email = request.form["email"]
        purpose = request.form["purpose"]

        cursor = db.cursor()

        cursor.execute(
            """
            INSERT INTO visitor (name, phone, email, purpose, admin_id)
            VALUES (%s, %s, %s, %s, %s)
            """,
            (name, phone, email, purpose, 1)
        )

        db.commit()
        cursor.close()

        return redirect(url_for("visitors"))

    return render_template("add_visitor.html")

if __name__ == "__main__":
    app.run(debug=True)