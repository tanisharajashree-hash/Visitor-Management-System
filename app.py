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
        if "admin_id" not in session and "user_id" not in session:
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

@app.route("/login", methods=["GET", "POST"])
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

            if admin["role"] == "Security":
                return redirect(url_for("security_dashboard"))
              
            return redirect(url_for("dashboard"))

        return render_template(
            "login.html",
            error="Invalid username or password"
        )

    return render_template("login.html")

@app.route("/security-login", methods=["GET", "POST"])
def security_login():

    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        cursor = db.cursor(dictionary=True)

        cursor.execute(
            "SELECT * FROM admin WHERE username = %s AND password = %s AND role = 'Security'",
            (username, password)
        )

        security = cursor.fetchone()
        cursor.close()

        if security:
            session["admin_id"] = security["admin_id"]
            session["username"] = security["username"]
            session["role"] = "Security"

            return redirect(url_for("security_dashboard"))

        return render_template(
            "security_login.html",
            error="Invalid username or password"
        )

    return render_template("security_login.html")

@app.route("/user-register", methods=["GET", "POST"])
def user_register():

    if request.method == "POST":

        username = request.form["username"]
        password = request.form["password"]
        name = request.form["name"]
        email = request.form["email"]
        phone = request.form["phone"]

        cursor = db.cursor(dictionary=True)

        cursor.execute(
            "SELECT * FROM user WHERE username = %s",
            (username,)
        )

        existing_user = cursor.fetchone()

        if existing_user:
            cursor.close()
            return render_template(
                "user_register.html",
                error="Username already exists"
            )

        cursor.execute(
            """
            INSERT INTO user
            (username, password, name, email, phone)
            VALUES (%s, %s, %s, %s, %s)
            """,
            (username, password, name, email, phone)
        )

        db.commit()
        cursor.close()

        return redirect(url_for("user_login"))

    return render_template("user_register.html")

@app.route("/user-login", methods=["GET", "POST"])
def user_login():

    if request.method == "POST":

        username = request.form["username"]
        password = request.form["password"]

        cursor = db.cursor(dictionary=True)

        cursor.execute(
            """
            SELECT * FROM user
            WHERE username = %s AND password = %s
            """,
            (username, password)
        )

        user = cursor.fetchone()
        cursor.close()

        if user:
            session["user_id"] = user["user_id"]
            session["username"] = user["username"]
            session["user_email"] = user["email"]
            session["role"] = "User"

            return redirect(url_for("user_dashboard"))

        return render_template(
            "user_login.html",
            error="Invalid username or password"
        )

    return render_template("user_login.html")

@app.route("/user-dashboard")
def user_dashboard():

    if session.get("role") != "User":
        return "Access Denied: User only", 403

    return render_template("user_dashboard.html")

@app.route("/user-profile")
def user_profile():

    if session.get("role") != "User":
         return "Access Denied: User only", 403

    cursor = db.cursor(dictionary=True)

    cursor.execute(
        "SELECT * FROM user WHERE user_id = %s",
        (session["user_id"],)
    )

    user = cursor.fetchone()
    cursor.close()

    return render_template("user_profile.html", user=user)


@app.route("/user-new-request", methods=["GET", "POST"])
def user_new_request():

    if session.get("role") != "User":
        return "Access Denied: User only", 403

    if request.method == "POST":

        visitor_name = request.form["visitor_name"]
        visit_date = request.form["visit_date"]
        purpose = request.form["purpose"]

        cursor = db.cursor(dictionary=True)

        # Get logged-in user's details
        cursor.execute(
            "SELECT name, email, phone FROM user WHERE user_id = %s",
            (session["user_id"],)
        )

        user = cursor.fetchone()

        # Create visitor record
        cursor.execute(
            """
            INSERT INTO visitor
            (name, phone, email, purpose)
            VALUES (%s, %s, %s, %s)
            """,
            (
                visitor_name,
                user["phone"],
                user["email"],
                purpose
            )
        )

        visitor_id = cursor.lastrowid

        # Create visit request
        cursor.execute(
            """
            INSERT INTO visit_request
            (visitor_id, visit_date, purpose, status, request_time)
            VALUES (%s, %s, %s, %s, NOW())
            """,
            (
                visitor_id,
                visit_date,
                purpose,
                "Pending"
            )
        )

        db.commit()
        cursor.close()

        return redirect(url_for("user_dashboard"))

    return render_template("user_new_request.html")

@app.route("/user-visit-requests")
def user_visit_requests():

    if session.get("role") != "User":
        return "Access Denied: User only", 403

    cursor = db.cursor(dictionary=True)

    cursor.execute(
        """
        SELECT
            vr.request_id,
            v.name AS visitor_name,
            vr.visit_date,
            vr.purpose,
            vr.status,
            vr.request_time
        FROM visit_request vr
        JOIN visitor v
            ON vr.visitor_id = v.visitor_id
        WHERE v.email = %s
        ORDER BY vr.request_time DESC
        """,
        (session.get("user_email"),)
    )

    requests = cursor.fetchall()
    cursor.close()

    return render_template(
        "user_visit_requests.html",
        requests=requests
    )

@app.route("/user-logout")
def user_logout():
    session.clear()
    return redirect(url_for("user_login"))

@app.route("/security-dashboard")
@staff_required
def security_dashboard():
    cursor = db.cursor(dictionary=True)

    cursor.execute("""
        SELECT COUNT(*) AS total
        FROM visit_request
        WHERE status = 'Approved'
    """)
    approved_requests = cursor.fetchone()["total"]

    cursor.execute("""
        SELECT COUNT(*) AS total
        FROM gate_pass
        WHERE status = 'Active'
    """)
    active_passes = cursor.fetchone()["total"]

    cursor.execute("""
        SELECT COUNT(*) AS total
        FROM visit_log
        WHERE DATE(in_time) = CURDATE()
    """)
    todays_visits = cursor.fetchone()["total"]

    cursor.close()

    return render_template(
        "security_dashboard.html",
        approved_requests=approved_requests,
        active_passes=active_passes,
        todays_visits=todays_visits
    )

@app.route("/")
def landing():
    return render_template("landing.html")

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

    search = request.args.get("search", "").strip()

    cursor = db.cursor(dictionary=True)

    if search:
        cursor.execute(
            """
            SELECT * FROM visitor
            WHERE CONCAT('V', LPAD(visitor_id, 3, '0')) LIKE %s
               OR CAST(visitor_id AS CHAR) LIKE %s
               OR name LIKE %s
               OR phone LIKE %s
               OR email LIKE %s
            ORDER BY visitor_id DESC
            """,
            (
                f"%{search}%",
                f"%{search}%",
                f"%{search}%",
                f"%{search}%",
                f"%{search}%"
            )
        )
    else:
        cursor.execute(
            """
            SELECT * FROM visitor
            ORDER BY visitor_id DESC
            """
        )

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

    if session.get("role") == "Security":
        cursor.execute("""
            SELECT *
            FROM visit_request
            WHERE status = 'Approved'
            ORDER BY request_time DESC
        """)
    else:
        cursor.execute("""
            SELECT *
            FROM visit_request
            ORDER BY request_time DESC
        """)

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

@app.route("/user-gate-passes")
def user_gate_passes():

    if session.get("role") != "User":
        return "Access Denied: User only", 403

    cursor = db.cursor(dictionary=True)

    cursor.execute(
        """
        SELECT
            gp.pass_id,
            gp.request_id,
            gp.visitor_id,
            gp.issue_date,
            gp.valid_time,
            gp.status,
            v.name AS visitor_name
        FROM gate_pass gp
        JOIN visitor v
            ON gp.visitor_id = v.visitor_id
        WHERE v.email = %s
        ORDER BY gp.issue_date DESC
        """,
        (session.get("user_email"),)
    )

    passes = cursor.fetchall()
    cursor.close()

    return render_template(
        "user_gate_passes.html",
        passes=passes
    )

@app.route("/visit-logs")
@login_required
def visit_logs():

    search = request.args.get("search", "").strip()
    date = request.args.get("date", "").strip()
    status = request.args.get("status", "").strip()

    cursor = db.cursor(dictionary=True)

    query = """
        SELECT visit_log.*, gate_pass.visitor_id
        FROM visit_log
        JOIN gate_pass
        ON visit_log.pass_id = gate_pass.pass_id
        WHERE 1=1
    """

    params = []

    # Search Visitor ID or Pass ID
    if search:
        query += """
            AND (
                CONCAT('V', LPAD(gate_pass.visitor_id, 3, '0')) LIKE %s
                OR CAST(gate_pass.visitor_id AS CHAR) LIKE %s
                OR CONCAT('GP', LPAD(visit_log.pass_id, 3, '0')) LIKE %s
                OR CAST(visit_log.pass_id AS CHAR) LIKE %s
            )
        """

        params.extend([
            f"%{search}%",
            f"%{search}%",
            f"%{search}%",
            f"%{search}%"
        ])

    # Date filter
    if date:
        query += " AND DATE(visit_log.in_time) = %s"
        params.append(date)

    # Entry / Exit filter
    if status == "entered":
        query += " AND visit_log.out_time IS NULL"

    elif status == "exited":
        query += " AND visit_log.out_time IS NOT NULL"

    query += " ORDER BY visit_log.log_id DESC"

    cursor.execute(query, params)

    logs = cursor.fetchall()

    cursor.close()

    return render_template(
        "visit_logs.html",
        logs=logs,
        search=search,
        date=date,
        status=status
    )


@app.route("/settings")
@login_required
def settings():
    cursor = db.cursor(dictionary=True)

    cursor.execute("""
        SELECT admin_id, username, name, email, phone, role
        FROM admin
        WHERE admin_id = %s
    """, (session["admin_id"],))

    admin = cursor.fetchone()
    cursor.close()

    return render_template("settings.html", admin=admin)

@app.route("/change-password", methods=["GET", "POST"])
@login_required
def change_password():

    cursor = db.cursor(dictionary=True)

    if request.method == "POST":

        current_password = request.form["current_password"]
        new_password = request.form["new_password"]
        confirm_password = request.form["confirm_password"]

        cursor.execute("""
            SELECT password
            FROM admin
            WHERE admin_id = %s
        """, (session["admin_id"],))

        admin = cursor.fetchone()

        if admin["password"] != current_password:
            cursor.close()
            return "Current password is incorrect"

        if new_password != confirm_password:
            cursor.close()
            return "New passwords do not match"

        cursor.execute("""
            UPDATE admin
            SET password = %s
            WHERE admin_id = %s
        """, (new_password, session["admin_id"]))

        db.commit()
        cursor.close()

        return "Password changed successfully"

    cursor.close()

    return render_template("change_password.html")

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