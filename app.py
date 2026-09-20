from flask import Flask, render_template, request, redirect, url_for, session
from functools import wraps
import mysql.connector

app = Flask(__name__)
app.secret_key = "visitor_management_secret"

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get("role") != "Admin":
            return "Access Denied: Admin only", 403
        return f(*args, **kwargs)
    return decorated_function

def staff_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get("role") not in ["Admin", "Security"]:
            return "Access Denied: Staff only", 403
        return f(*args, **kwargs)
    return decorated_function

def login_required(f):
    @wraps(f)
    def decorated_function(*args,**kwargs):
        if "admin_id" not in session:
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated_function

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

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
            session["admin_id"] = admin["admin_id"]
            session["username"] = admin["username"]
            session["role"] = admin["role"]
              
            return redirect(url_for("dashboard"))

        return render_template(
            "login.html",
            error="Invalid username or password"
        )

    return render_template("login.html")


@app.route("/dashboard")
@login_required
def dashboard():
    role = session.get("role")

    cursor = db.cursor(dictionary=True)

    cursor.execute("SELECT COUNT(*) AS total FROM visitor")
    total_visitors = cursor.fetchone()["total"]

    cursor.execute("""
        SELECT COUNT(*) AS total
        FROM visit_request
        WHERE status = 'Pending'
    """)
    pending_requests = cursor.fetchone()["total"]

    cursor.execute("""
        SELECT COUNT(*) AS total
        FROM visit_request
    """)
    
    total_requests = cursor.fetchone()["total"]

    cursor.execute("""
        SELECT COUNT(*) AS total
        FROM visit_log
        WHERE DATE(in_time) = CURDATE()
    """)
    todays_visits = cursor.fetchone()["total"]

    cursor.execute("""
        SELECT COUNT(*) AS total
        FROM gate_pass
        WHERE status = 'Active'
    """)
    active_passes = cursor.fetchone()["total"]

    cursor.execute("""
    SELECT
        visit_log.log_id,
        visitor.name,
        visit_log.in_time,
        visit_log.out_time
    FROM visit_log
    JOIN gate_pass
    ON visit_log.pass_id = gate_pass.pass_id
    JOIN visitor
    ON gate_pass.visitor_id = visitor.visitor_id
    ORDER BY visit_log.in_time DESC
    LIMIT 5
""")

    recent_activity = cursor.fetchall()

    cursor.close()

    return render_template(
        "dashboard.html",
        role=role,
        total_visitors=total_visitors,
        total_requests=total_requests,
        active_passes=active_passes,
        pending_requests=pending_requests,
        todays_visits=todays_visits,
        recent_activity=recent_activity
    )
     

@app.route("/visitors")
@login_required
def visitors():

    search = request.args.get("search", "")

    cursor = db.cursor(dictionary=True)

    if search:
        cursor.execute(
            """
            SELECT * FROM visitor
            WHERE name LIKE %s
               OR phone LIKE %s
               OR email LIKE %s
            """,
            (f"%{search}%", f"%{search}%", f"%{search}%")
        )
    else:
        cursor.execute("SELECT * FROM visitor")

    visitors = cursor.fetchall()

    cursor.close()

    return render_template(
        "visitors.html",
        visitors=visitors,
        search=search
    )

@app.route("/visit-requests")
@login_required
def visit_requests():

    cursor = db.cursor(dictionary=True)

    cursor.execute("SELECT * FROM visit_request")

    requests = cursor.fetchall()

    cursor.close()

    return render_template(
        "visit_requests.html",
        requests=requests
    )


@app.route("/view-visitor/<int:visitor_id>")
@login_required
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
@admin_required
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
@admin_required
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
@admin_required
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

@app.route("/new-request", methods=["GET", "POST"])
@admin_required
def new_request():

    cursor = db.cursor(dictionary=True)

    if request.method == "POST":

        visitor_id = request.form["visitor_id"]
        visit_date = request.form["visit_date"]
        purpose = request.form["purpose"]

        cursor.execute(
            """
            INSERT INTO visit_request
            (visitor_id, visit_date, purpose, status, request_time)
            VALUES (%s, %s, %s, %s, NOW())
            """,
            (visitor_id, visit_date, purpose, "Pending")
        )

        db.commit()
        cursor.close()

        return redirect(url_for("visit_requests"))

    cursor.execute("SELECT visitor_id, name FROM visitor")
    visitors = cursor.fetchall()

    cursor.close()

    return render_template(
        "new_request.html",
        visitors=visitors
    )

@app.route("/approve-request/<int:request_id>")
@admin_required
def approve_request(request_id):
    cursor = db.cursor()
    cursor.execute(
        "UPDATE visit_request SET status = %s WHERE request_id = %s",
        ("Approved", request_id)
    )
    db.commit()
    cursor.close()
    return redirect(url_for("visit_requests"))

@app.route("/reject-request/<int:request_id>")
@admin_required
def reject_request(request_id):
    cursor = db.cursor()
    cursor.execute(
        "UPDATE visit_request SET status = %s WHERE request_id = %s",
        ("Rejected", request_id)
    )
    db.commit()
    cursor.close()
    return redirect(url_for("visit_requests"))

@app.route("/view-request/<int:request_id>")
@login_required
def view_request(request_id):
    cursor = db.cursor(dictionary=True)

    cursor.execute(
        """
        SELECT visit_request.*, visitor.name, visitor.phone, visitor.email
        FROM visit_request
        JOIN visitor ON visit_request.visitor_id = visitor.visitor_id
        WHERE visit_request.request_id = %s
        """,
        (request_id,)
    )

    req = cursor.fetchone()
    cursor.close()

    return render_template("view_request.html", req=req)

@app.route("/gate-passes")
@login_required
def gate_passes():
    cursor = db.cursor(dictionary=True)

    cursor.execute("SELECT * FROM gate_pass")

    passes = cursor.fetchall()
    cursor.close()

    return render_template("gate_passes.html", passes=passes)

@app.route("/generate-gate-pass", methods=["GET", "POST"])
@admin_required
def generate_gate_pass():
    cursor = db.cursor(dictionary=True)

    if request.method == "POST":
        request_id = request.form["request_id"]
        visitor_id = request.form["visitor_id"]
        valid_time = request.form["valid_time"]

        cursor.execute(
            """
            INSERT INTO gate_pass
            (request_id, visitor_id, issue_date, valid_time, status)
            VALUES (%s, %s, CURDATE(), %s, %s)
            """,
            (request_id, visitor_id, valid_time, "Active")
        )

        db.commit()
        cursor.close()

        return redirect(url_for("gate_passes"))

    cursor.execute(
        """
        SELECT visit_request.request_id,
               visit_request.visitor_id,
               visitor.name,
               visit_request.visit_date,
               visit_request.purpose
        FROM visit_request
        JOIN visitor
        ON visit_request.visitor_id = visitor.visitor_id
        WHERE visit_request.status = 'Approved'
        """
    )

    requests = cursor.fetchall()
    cursor.close()

    return render_template(
        "generate_gate_pass.html",
        requests=requests
    )

@app.route("/view-gate-pass/<int:pass_id>")
@login_required
def view_gate_pass(pass_id):
    cursor = db.cursor(dictionary=True)

    cursor.execute(
        """
        SELECT gate_pass.*, visitor.name
        FROM gate_pass
        JOIN visitor ON gate_pass.visitor_id = visitor.visitor_id
        WHERE gate_pass.pass_id = %s
        """,
        (pass_id,)
    )

    gate_pass = cursor.fetchone()
    cursor.close()

    return render_template("view_gate_pass.html", gate_pass=gate_pass)

@app.route("/visit-logs")
@login_required
def visit_logs():
    cursor = db.cursor(dictionary=True)

    cursor.execute("""
        SELECT visit_log.*, gate_pass.visitor_id
        FROM visit_log
        JOIN gate_pass
        ON visit_log.pass_id = gate_pass.pass_id
    """)

    logs = cursor.fetchall()
    cursor.close()

    return render_template("visit_logs.html", logs=logs)


@app.route("/view-log/<int:log_id>")
@login_required
def view_log(log_id):
    cursor = db.cursor(dictionary=True)

    cursor.execute("""
        SELECT visit_log.log_id,
               visit_log.pass_id,
               gate_pass.visitor_id,
               visitor.name,
               visitor.phone,
               visitor.email,
               visit_log.in_time,
               visit_log.out_time,
               visit_log.remarks
        FROM visit_log
        JOIN gate_pass
        ON visit_log.pass_id = gate_pass.pass_id
        JOIN visitor
        ON gate_pass.visitor_id = visitor.visitor_id
        WHERE visit_log.log_id = %s
    """, (log_id,))

    log = cursor.fetchone()
    cursor.close()

    if not log:
        return "Visitor log not found", 404

    return render_template("view_log.html", log=log)


@app.route("/record-entry", methods=["GET", "POST"])
@staff_required
def record_entry():
    cursor = db.cursor(dictionary=True)

    if request.method == "POST":
        pass_id = request.form["pass_id"]
        remarks = request.form["remarks"]

        cursor.execute(
            """
            INSERT INTO visit_log
            (pass_id, in_time, out_time, remarks)
            VALUES (%s, NOW(), NULL, %s)
            """,
            (pass_id, remarks)
        )

        db.commit()
        cursor.close()

        return redirect(url_for("visit_logs"))

    cursor.execute(
        """
        SELECT gate_pass.pass_id,
               gate_pass.visitor_id,
               visitor.name
        FROM gate_pass
        JOIN visitor
        ON gate_pass.visitor_id = visitor.visitor_id
        WHERE gate_pass.status = 'Active'
        """
    )

    passes = cursor.fetchall()
    cursor.close()

    return render_template(
        "record_entry.html",
        passes=passes
    )

@app.route("/record-exit/<int:log_id>")
@staff_required
def record_exit(log_id):
    cursor = db.cursor()

    cursor.execute(
        """
        UPDATE visit_log
        SET out_time = NOW()
        WHERE log_id = %s
          AND out_time IS NULL
        """,
        (log_id,)
    )

    db.commit()
    cursor.close()

    return redirect(url_for("visit_logs"))

@app.route("/reports")
@login_required
def reports():
    search = request.args.get("search", "")
    date = request.args.get("date", "")

    cursor = db.cursor(dictionary=True)

    query = """
        SELECT visit_log.log_id,
               gate_pass.pass_id,
               visitor.visitor_id,
               visitor.name,
               visit_request.purpose,
               visit_log.in_time,
               visit_log.out_time,
               visit_log.remarks
        FROM visit_log
        JOIN gate_pass
        ON visit_log.pass_id = gate_pass.pass_id
        JOIN visitor
        ON gate_pass.visitor_id = visitor.visitor_id
        JOIN visit_request
        ON gate_pass.request_id = visit_request.request_id
        WHERE 1=1
    """

    values = []

    if search:
        query += """
            AND (
                visitor.name LIKE %s
                OR visitor.phone LIKE %s
                OR visitor.email LIKE %s
            )
        """
        values.extend([
            f"%{search}%",
            f"%{search}%",
            f"%{search}%"
        ])

    if date:
        query += " AND DATE(visit_log.in_time) = %s"
        values.append(date)

    query += " ORDER BY visit_log.in_time DESC"

    cursor.execute(query, values)

    reports = cursor.fetchall()
    cursor.close()

    return render_template(
        "reports.html",
        reports=reports,
        search=search,
        date=date
    )


if __name__ == "__main__":
    app.run(debug=True)