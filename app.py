from flask import Flask, request, redirect, session
import sqlite3
import qrcode
import io
import base64

app = Flask(__name__)
app.secret_key = "secret"
DB = "certificates.db"

def db():
    c = sqlite3.connect(DB)
    c.row_factory = sqlite3.Row
    return c

def page(body):
    return "<html><head><title>Online Certificate Verification</title></head><body style='font-family:Arial;padding:25px'>" + body + "</body></html>"

@app.route("/")
def home():
    return page(
        "<h1>Online Certificate Verification</h1>"
        "<form method='post' action='/verify'>"
        "<input name='certificate_id' placeholder='Enter Certificate ID' required>"
        "<button>Verify</button></form>"
        "<br><a href='/login'>Admin Login</a>"
    )

@app.route("/verify", methods=["POST"])
def verify():
    return redirect("/verify/" + request.form["certificate_id"].strip())

@app.route("/verify/<cid>")
def verify_id(cid):
    c = db()
    x = c.execute(
        "SELECT * FROM certificates WHERE certificate_id=?",
        (cid,)
    ).fetchone()
    c.close()

    if not x:
        return page(
            "<h2 style='color:red'>Certificate Not Found</h2>"
            "<a href='/'>Home</a>"
        )

    qr = qrcode.make(
        request.host_url.rstrip("/") + "/verify/" + x["certificate_id"]
    )

    b = io.BytesIO()
    qr.save(b, format="PNG")
    img = base64.b64encode(b.getvalue()).decode()

    return page(
        "<h1>Certificate Verified</h1>"
        "<p><b>Certificate ID:</b> " + x["certificate_id"] + "</p>"
        "<p><b>Name:</b> " + x["name"] + "</p>"
        "<p><b>Course:</b> " + x["course"] + "</p>"
        "<p><b>College:</b> " + x["college"] + "</p>"
        "<p><b>Year:</b> " + x["year"] + "</p>"
        "<p><b>Status:</b> " + x["status"] + "</p>"
        "<h2>QR Code</h2>"
        "<img width='220' src='data:image/png;base64," + img + "'>"
        "<br><br>"
        "<button onclick='window.print()'>Print</button>"
        "<br><br><a href='/'>Home</a>"
    )

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        if (
            request.form.get("username") == "admin"
            and request.form.get("password") == "admin123"
        ):
            session["admin"] = True
            return redirect("/admin")

        return page(
            "<h2 style='color:red'>Invalid Login</h2>"
            "<a href='/login'>Try Again</a>"
        )

    return page(
        "<h1>Admin Login</h1>"
        "<form method='post'>"
        "<input name='username' placeholder='Username' required><br><br>"
        "<input name='password' type='password' placeholder='Password' required><br><br>"
        "<button>Login</button>"
        "</form>"
    )

@app.route("/admin")
def admin():
    if not session.get("admin"):
        return redirect("/login")

    q = request.args.get("search", "").strip()

    c = db()

    total = c.execute(
        "SELECT COUNT(*) FROM certificates"
    ).fetchone()[0]

    valid = c.execute(
        "SELECT COUNT(*) FROM certificates WHERE status='Valid'"
    ).fetchone()[0]

    invalid = c.execute(
        "SELECT COUNT(*) FROM certificates WHERE status='Invalid'"
    ).fetchone()[0]

    if q:
        rows = c.execute(
            "SELECT * FROM certificates "
            "WHERE certificate_id LIKE ? "
            "OR name LIKE ? "
            "OR course LIKE ? "
            "OR college LIKE ? "
            "ORDER BY id DESC",
            (
                "%" + q + "%",
                "%" + q + "%",
                "%" + q + "%",
                "%" + q + "%"
            )
        ).fetchall()
    else:
        rows = c.execute(
            "SELECT * FROM certificates ORDER BY id DESC"
        ).fetchall()

    c.close()

    h = "<h1>Admin Dashboard</h1>"
    h += "<h3>Total Certificate: " + str(total) + "</h3>"
    h += "<h3>Valid Certificate: " + str(valid) + "</h3>"
    h += "<h3>Invalid Certificate: " + str(invalid) + "</h3>"

    h += "<a href='/add'>Add Certificate</a> | "
    h += "<a href='/logout'>Logout</a><br><br>"

    h += "<form>"
    h += "<input name='search' value='" + q + "' placeholder='Search'>"
    h += "<button>Search</button>"
    h += "</form><br>"

    h += "<table border='1' cellpadding='8'>"
    h += "<tr>"
    h += "<th>ID</th><th>Name</th><th>Course</th>"
    h += "<th>College</th><th>Year</th><th>Status</th><th>Action</th>"
    h += "</tr>"

    for x in rows:
        h += "<tr>"
        h += "<td>" + x["certificate_id"] + "</td>"
        h += "<td>" + x["name"] + "</td>"
        h += "<td>" + x["course"] + "</td>"
        h += "<td>" + x["college"] + "</td>"
        h += "<td>" + x["year"] + "</td>"
        h += "<td>" + x["status"] + "</td>"
        h += "<td>"
        h += "<a href='/edit/" + str(x["id"]) + "'>Edit</a> | "
        h += "<a href='/delete/" + str(x["id"]) + "'>Delete</a>"
        h += "</td>"
        h += "</tr>"

    h += "</table>"

    return page(h)

@app.route("/add", methods=["GET", "POST"])
def add():
    if not session.get("admin"):
        return redirect("/login")

    if request.method == "POST":
        try:
            c = db()

            c.execute(
                "INSERT INTO certificates "
                "(certificate_id,name,course,college,year,status) "
                "VALUES (?,?,?,?,?,?)",
                (
                    request.form["certificate_id"],
                    request.form["name"],
                    request.form["course"],
                    request.form["college"],
                    request.form["year"],
                    request.form["status"]
                )
            )

            c.commit()
            c.close()

            return redirect("/admin")

        except sqlite3.IntegrityError:
            return page(
                "<h2>Certificate ID already exists</h2>"
                "<a href='/add'>Back</a>"
            )

    return page(
        "<h1>Add Certificate</h1>"
        "<form method='post'>"
        "<input name='certificate_id' placeholder='Certificate ID' required><br><br>"
        "<input name='name' placeholder='Name' required><br><br>"
        "<input name='course' placeholder='Course' required><br><br>"
        "<input name='college' placeholder='College' required><br><br>"
        "<input name='year' placeholder='Year' required><br><br>"
        "<select name='status'>"
        "<option>Valid</option>"
        "<option>Invalid</option>"
        "</select><br><br>"
        "<button>Add Certificate</button>"
        "</form>"
        "<br><a href='/admin'>Back</a>"
    )

@app.route("/edit/<int:cid>", methods=["GET", "POST"])
def edit(cid):
    if not session.get("admin"):
        return redirect("/login")

    c = db()

    x = c.execute(
        "SELECT * FROM certificates WHERE id=?",
        (cid,)
    ).fetchone()

    if not x:
        c.close()
        return page("Certificate not found")

    if request.method == "POST":
        c.execute(
            "UPDATE certificates SET "
            "name=?,course=?,college=?,year=?,status=? "
            "WHERE id=?",
            (
                request.form["name"],
                request.form["course"],
                request.form["college"],
                request.form["year"],
                request.form["status"],
                cid
            )
        )

        c.commit()
        c.close()

        return redirect("/admin")

    h = "<h1>Edit Certificate</h1>"
    h += "<p>Certificate ID: <b>" + x["certificate_id"] + "</b></p>"
    h += "<form method='post'>"
    h += "<input name='name' value='" + x["name"] + "' required><br><br>"
    h += "<input name='course' value='" + x["course"] + "' required><br><br>"
    h += "<input name='college' value='" + x["college"] + "' required><br><br>"
    h += "<input name='year' value='" + x["year"] + "' required><br><br>"
    h += "<select name='status'>"
    h += "<option>Valid</option>"
    h += "<option>Invalid</option>"
    h += "</select><br><br>"
    h += "<button>Update</button>"
    h += "</form><br>"
    h += "<a href='/admin'>Back</a>"

    c.close()

    return page(h)

@app.route("/delete/<int:cid>")
def delete(cid):
    if not session.get("admin"):
        return redirect("/login")

    c = db()
    c.execute("DELETE FROM certificates WHERE id=?", (cid,))
    c.commit()
    c.close()

    return redirect("/admin")

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)