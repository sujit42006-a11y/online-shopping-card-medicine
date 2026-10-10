import os, uuid
from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify, send_from_directory
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from config import Config
from database import get_db

app=Flask(__name__)
app.config.from_object(Config)
os.makedirs(app.config["UPLOAD_FOLDER"],exist_ok=True)

def query(sql,args=(),one=False,commit=False):
    db=get_db(); cur=db.cursor(dictionary=True)
    try:
        cur.execute(sql,args)
        if commit: db.commit(); return None
        data=cur.fetchone() if one else cur.fetchall()
        return data
    finally:
        cur.close(); db.close()

def current_user():
    uid=session.get("user_id")
    return query("SELECT id,name,email,phone,role FROM users WHERE id=%s AND is_active=1",(uid,),True) if uid else None

def login_required(f):
    @wraps(f)
    def wrapper(*a,**kw):
        if not session.get("user_id"): return redirect(url_for("login",next=request.path))
        return f(*a,**kw)
    return wrapper

def admin_required(f):
    @wraps(f)
    def wrapper(*a,**kw):
        if session.get("role")!="admin": return redirect(url_for("admin_login"))
        return f(*a,**kw)
    return wrapper

@app.context_processor
def inject():
    return {"current_user":current_user(),"cart_count": (query("SELECT COALESCE(SUM(ci.quantity),0) AS n FROM cart c JOIN cart_items ci ON ci.cart_id=c.id WHERE c.user_id=%s", (session.get("user_id"),), True) or {"n": 0})["n"] if session.get("user_id") else 0}

@app.route("/")
def home():
    meds=query("""SELECT m.*,c.name category_name FROM medicines m JOIN categories c ON c.id=m.category_id
                  WHERE m.is_active=1 ORDER BY m.id DESC LIMIT 8""")
    cats=query("SELECT * FROM categories WHERE is_active=1 ORDER BY name")
    return render_template("index.html",medicines=meds,categories=cats)

@app.route("/register",methods=["GET","POST"])
def register():
    if request.method=="POST":
        name=request.form.get("name","").strip(); email=request.form.get("email","").strip().lower()
        phone=request.form.get("phone","").strip(); password=request.form.get("password","")
        if not name or not email or len(password)<6: flash("Enter valid details. Password must be at least 6 characters.","error")
        elif query("SELECT id FROM users WHERE email=%s",(email,),True): flash("Email is already registered.","error")
        else:
            query("INSERT INTO users(name,email,phone,password_hash,role) VALUES(%s,%s,%s,%s,'customer')",
                  (name,email,phone,generate_password_hash(password)),commit=True)
            flash("Registration successful. Please log in.","success"); return redirect(url_for("login"))
    return render_template("register.html")

@app.route("/login",methods=["GET","POST"])
def login():
    if request.method=="POST":
        email=request.form.get("email","").strip().lower(); password=request.form.get("password","")
        u=query("SELECT * FROM users WHERE email=%s AND is_active=1",(email,),True)
        if u and check_password_hash(u["password_hash"],password):
            session["user_id"]=u["id"]; session["role"]=u["role"]
            return redirect(request.args.get("next") or url_for("home"))
        flash("Invalid email or password.","error")
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear(); return redirect(url_for("home"))

@app.route("/profile",methods=["GET","POST"])
@login_required
def profile():
    u=current_user()
    if request.method=="POST":
        name=request.form.get("name","").strip(); phone=request.form.get("phone","").strip()
        query("UPDATE users SET name=%s,phone=%s WHERE id=%s",(name,phone,u["id"]),commit=True)
        flash("Profile updated.","success"); return redirect(url_for("profile"))
    return render_template("profile.html",user=u)

@app.route("/medicines")
def medicines():
    q=request.args.get("q","").strip(); cat=request.args.get("category","").strip(); sort=request.args.get("sort","name")
    order={"name":"m.name ASC","price_low":"m.price ASC","price_high":"m.price DESC"}.get(sort,"m.name ASC")
    sql="""SELECT m.*,c.name category_name FROM medicines m JOIN categories c ON c.id=m.category_id
           WHERE m.is_active=1 AND (m.name LIKE %s OR m.brand LIKE %s OR m.generic_name LIKE %s)"""
    args=[f"%{q}%",f"%{q}%",f"%{q}%"]
    if cat: sql+=" AND m.category_id=%s"; args.append(cat)
    sql+=f" ORDER BY {order}"
    return render_template("medicines.html",medicines=query(sql,args),categories=query("SELECT * FROM categories WHERE is_active=1 ORDER BY name"),q=q,cat=cat,sort=sort)

@app.route("/medicine/<int:mid>")
def medicine_detail(mid):
    m=query("SELECT m.*,c.name category_name FROM medicines m JOIN categories c ON c.id=m.category_id WHERE m.id=%s AND m.is_active=1",(mid,),True)
    if not m: return render_template("error.html",code=404,message="Medicine not found"),404
    return render_template("medicine-details.html",medicine=m)

@app.route("/categories")
def categories():
    cats=query("SELECT c.*,COUNT(m.id) medicine_count FROM categories c LEFT JOIN medicines m ON m.category_id=c.id AND m.is_active=1 WHERE c.is_active=1 GROUP BY c.id ORDER BY c.name")
    return render_template("categories.html",categories=cats)

@app.route("/category/<int:cid>")
def category(cid): return redirect(url_for("medicines",category=cid))

def cart_data():
    if not session.get("user_id"): return [],0,0,0
    rows=query("""SELECT ci.id ci_id,ci.quantity,m.*,m.price*ci.quantity line_total
                  FROM cart c JOIN cart_items ci ON ci.cart_id=c.id JOIN medicines m ON m.id=ci.medicine_id
                  WHERE c.user_id=%s""",(session["user_id"],))
    subtotal=sum(float(x["line_total"]) for x in rows); discount=sum(float(x["discount"])*x["quantity"] for x in rows)
    delivery=40 if rows and subtotal-discount<500 else 0
    return rows,subtotal,discount,delivery

def get_or_create_cart(uid):
    c=query("SELECT id FROM cart WHERE user_id=%s",(uid,),True)
    if c:return c["id"]
    query("INSERT INTO cart(user_id) VALUES(%s)",(uid,),commit=True)
    return query("SELECT id FROM cart WHERE user_id=%s",(uid,),True)["id"]

@app.route("/cart")
@login_required
def cart():
    rows,subtotal,discount,delivery=cart_data()
    return render_template("cart.html",items=rows,subtotal=subtotal,discount=discount,delivery=delivery,total=subtotal-discount+delivery)

@app.route("/api/cart/add",methods=["POST"])
@login_required
def cart_add():
    data=request.get_json(silent=True) or request.form; mid=int(data.get("medicine_id")); qty=max(1,int(data.get("quantity",1)))
    m=query("SELECT id,stock,is_active FROM medicines WHERE id=%s",(mid,),True)
    if not m or not m["is_active"]: return jsonify(success=False,message="Medicine unavailable"),404
    if qty>m["stock"]: return jsonify(success=False,message="Not enough stock"),400
    cid=get_or_create_cart(session["user_id"])
    item=query("SELECT id,quantity FROM cart_items WHERE cart_id=%s AND medicine_id=%s",(cid,mid),True)
    if item:
        newq=item["quantity"]+qty
        if newq>m["stock"]: return jsonify(success=False,message="Stock limit exceeded"),400
        query("UPDATE cart_items SET quantity=%s WHERE id=%s",(newq,item["id"]),commit=True)
    else: query("INSERT INTO cart_items(cart_id,medicine_id,quantity) VALUES(%s,%s,%s)",(cid,mid,qty),commit=True)
    return jsonify(success=True,message="Added to cart")

@app.route("/api/cart/update",methods=["POST"])
@login_required
def cart_update():
    item_id=int(request.form.get("item_id")); qty=int(request.form.get("quantity"))
    item=query("""SELECT ci.id,m.stock FROM cart_items ci JOIN cart c ON c.id=ci.cart_id JOIN medicines m ON m.id=ci.medicine_id
                  WHERE ci.id=%s AND c.user_id=%s""",(item_id,session["user_id"]),True)
    if not item:return jsonify(success=False,message="Cart item not found"),404
    if qty<=0: query("DELETE FROM cart_items WHERE id=%s",(item_id,),commit=True)
    elif qty<=item["stock"]: query("UPDATE cart_items SET quantity=%s WHERE id=%s",(qty,item_id),commit=True)
    else:return jsonify(success=False,message="Stock limit exceeded"),400
    return jsonify(success=True)

@app.route("/api/cart/remove",methods=["POST"])
@login_required
def cart_remove():
    query("""DELETE ci FROM cart_items ci JOIN cart c ON c.id=ci.cart_id WHERE ci.id=%s AND c.user_id=%s""",(int(request.form["item_id"]),session["user_id"]),commit=True)
    return jsonify(success=True)

@app.route("/checkout", methods=["GET", "POST"])
@login_required
def checkout():
    user_id = session["user_id"]

    items = query("""
        SELECT ci.id AS ci_id, ci.quantity,
               m.id, m.name, m.price, m.discount,
               m.stock, m.prescription_required,
               (m.price * ci.quantity) AS line_total
        FROM cart c
        JOIN cart_items ci ON ci.cart_id = c.id
        JOIN medicines m ON m.id = ci.medicine_id
        WHERE c.user_id = %s AND m.is_active = 1
        ORDER BY ci.id DESC
    """, (user_id,))

    if not items:
        flash("Your cart is empty.", "error")
        return redirect(url_for("cart"))

    # Validate stock before showing/placing the order.
    for item in items:
        if item["quantity"] > item["stock"]:
            flash(f"Not enough stock for {item['name']}.", "error")
            return redirect(url_for("cart"))

    addresses = query("""
        SELECT *
        FROM addresses
        WHERE user_id = %s
        ORDER BY is_default DESC, id DESC
    """, (user_id,))

    subtotal = sum(float(item["line_total"]) for item in items)
    discount = sum(float(item["discount"]) * item["quantity"] for item in items)
    delivery = 40 if subtotal - discount < 500 else 0
    total = subtotal - discount + delivery

    if request.method == "POST":
        address_id = request.form.get("address_id", "").strip()
        payment = request.form.get("payment_method", "COD").strip()

        if payment not in ("COD", "Demo Payment"):
            payment = "COD"

        if not address_id:
            flash("Please select a delivery address.", "error")
            return redirect(url_for("checkout"))

        selected = query("""
            SELECT *
            FROM addresses
            WHERE id = %s AND user_id = %s
        """, (address_id, user_id), True)

        if not selected:
            flash("Selected address was not found.", "error")
            return redirect(url_for("checkout"))

        # Prescription-required items need an approved prescription.
        needs_prescription = any(item["prescription_required"] for item in items)
        if needs_prescription:
            approved = query("""
                SELECT id
                FROM prescriptions
                WHERE user_id = %s AND status = 'Approved'
                ORDER BY id DESC
                LIMIT 1
            """, (user_id,), True)
            if not approved:
                flash("Prescription approval is required before placing this order.", "error")
                return redirect(url_for("prescription_upload"))

        full_address = (
            f"{selected['line1']}, {selected['city']}, "
            f"{selected['state']} - {selected['pincode']}"
        )
        phone = selected["phone"]
        order_number = "MK-" + uuid.uuid4().hex[:10].upper()
        status = "Confirmed" if not needs_prescription else "Prescription Verification"

        db = get_db()
        cur = db.cursor()
        try:
            cur.execute("""
                INSERT INTO orders
                (order_number, user_id, address, phone, payment_method,
                 subtotal, discount, delivery_charge, total, status)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            """, (
                order_number, user_id, full_address, phone, payment,
                subtotal, discount, delivery, total, status
            ))
            order_id = cur.lastrowid

            for item in items:
                cur.execute("""
                    INSERT INTO order_items
                    (order_id, medicine_id, medicine_name, quantity, unit_price)
                    VALUES (%s,%s,%s,%s,%s)
                """, (
                    order_id, item["id"], item["name"],
                    item["quantity"], item["price"]
                ))

                cur.execute("""
                    UPDATE medicines
                    SET stock = stock - %s
                    WHERE id = %s AND stock >= %s
                """, (item["quantity"], item["id"], item["quantity"]))

                if cur.rowcount != 1:
                    raise ValueError(f"Stock changed for {item['name']}. Please try again.")

            cur.execute("""
                DELETE ci
                FROM cart_items ci
                JOIN cart c ON c.id = ci.cart_id
                WHERE c.user_id = %s
            """, (user_id,))

            cur.execute("""
                INSERT INTO payments(order_id, method, status, amount)
                VALUES (%s,%s,'Pending',%s)
            """, (order_id, payment, total))

            db.commit()

        except Exception:
            db.rollback()
            raise
        finally:
            cur.close()
            db.close()

        flash("Order placed successfully.", "success")
        return redirect(url_for("order_detail", oid=order_id))

    return render_template(
        "checkout.html",
        items=items,
        addresses=addresses,
        subtotal=subtotal,
        discount=discount,
        delivery=delivery,
        total=total
    )

@app.route("/orders")
@login_required
def orders():
    return render_template(
        "orders.html",
        orders=query(
            "SELECT * FROM orders WHERE user_id=%s ORDER BY created_at DESC",
            (session["user_id"],)
        )
    )


@app.route("/orders/<int:oid>")
@login_required
def order_detail(oid):

    # Get order
    order_result = query("""
        SELECT *
        FROM orders
        WHERE id = %s
          AND user_id = %s
    """, (oid, session["user_id"]))

    if not order_result:
        flash("Order not found.", "error")
        return redirect(url_for("orders"))

    order = order_result[0]

    # Get order items + medicine details
    items = query("""
        SELECT
            oi.*,
            m.name,
            m.price AS price
        FROM order_items oi
        JOIN medicines m
            ON oi.medicine_id = m.id
        WHERE oi.order_id = %s
    """, (oid,))

    return render_template(
        "order-details.html",
        order=order,
        items=items
    )

@app.route("/prescription/upload",methods=["GET","POST"])
@login_required
def prescription_upload():
    if request.method=="POST":
        f=request.files.get("prescription")
        if not f or not f.filename: flash("Choose a file.","error")
        else:
            ext=f.filename.rsplit(".",1)[-1].lower() if "." in f.filename else ""
            if ext not in app.config["ALLOWED_EXTENSIONS"]: flash("Allowed: JPG, JPEG, PNG, PDF.","error")
            else:
                name=secure_filename(f"{uuid.uuid4().hex}_{f.filename}")
                f.save(os.path.join(app.config["UPLOAD_FOLDER"],name))
                query("INSERT INTO prescriptions(user_id,filename,original_name,status) VALUES(%s,%s,%s,'Pending')",(session["user_id"],name,f.filename),commit=True)
                flash("Prescription uploaded for review.","success"); return redirect(url_for("orders"))
    return render_template("prescription-upload.html")

@app.route("/addresses", methods=["GET", "POST"])
@login_required
def addresses():
    user_id = session["user_id"]

    if request.method == "POST":
        label = request.form.get("label", "").strip()
        line1 = request.form.get("line1", "").strip()
        city = request.form.get("city", "").strip()
        state = request.form.get("state", "").strip()
        pincode = request.form.get("pincode", "").strip()
        phone = request.form.get("phone", "").strip()

        if not all([label, line1, city, state, pincode, phone]):
            flash("Please fill all address fields.", "error")
            return redirect(url_for("addresses"))

        # First saved address becomes the default automatically.
        count = query(
            "SELECT COUNT(*) AS n FROM addresses WHERE user_id=%s",
            (user_id,), True
        )["n"]
        is_default = 1 if count == 0 else 0

        query("""
            INSERT INTO addresses
            (user_id, label, line1, city, state, pincode, phone, is_default)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
        """, (
            user_id, label, line1, city, state, pincode, phone, is_default
        ), commit=True)

        flash("Address saved successfully.", "success")
        return redirect(url_for("addresses"))

    saved = query("""
        SELECT *
        FROM addresses
        WHERE user_id = %s
        ORDER BY is_default DESC, id DESC
    """, (user_id,))

    return render_template("addresses.html", addresses=saved)


@app.route("/addresses/default/<int:address_id>", methods=["POST"])
@login_required
def set_default_address(address_id):
    user_id = session["user_id"]

    selected = query("""
        SELECT id
        FROM addresses
        WHERE id=%s AND user_id=%s
    """, (address_id, user_id), True)

    if not selected:
        flash("Address not found.", "error")
        return redirect(url_for("addresses"))

    query("""
        UPDATE addresses
        SET is_default=0
        WHERE user_id=%s
    """, (user_id,), commit=True)

    query("""
        UPDATE addresses
        SET is_default=1
        WHERE id=%s AND user_id=%s
    """, (address_id, user_id), commit=True)

    flash("Default address updated successfully.", "success")
    return redirect(url_for("addresses"))


@app.route("/addresses/edit/<int:address_id>", methods=["GET", "POST"])
@login_required
def edit_address(address_id):
    user_id = session["user_id"]
    result = query("""
        SELECT *
        FROM addresses
        WHERE id=%s AND user_id=%s
    """, (address_id, user_id))

    if not result:
        flash("Address not found.", "error")
        return redirect(url_for("addresses"))

    address = result[0]

    if request.method == "POST":
        label = request.form.get("label", "").strip()
        line1 = request.form.get("line1", "").strip()
        city = request.form.get("city", "").strip()
        state = request.form.get("state", "").strip()
        pincode = request.form.get("pincode", "").strip()
        phone = request.form.get("phone", "").strip()

        if not all([label, line1, city, state, pincode, phone]):
            flash("Please fill all fields.", "error")
            return redirect(url_for("edit_address", address_id=address_id))

        query("""
            UPDATE addresses
            SET label=%s, line1=%s, city=%s, state=%s,
                pincode=%s, phone=%s
            WHERE id=%s AND user_id=%s
        """, (
            label, line1, city, state, pincode, phone,
            address_id, user_id
        ), commit=True)

        flash("Address updated successfully.", "success")
        return redirect(url_for("addresses"))

    return render_template("edit-address.html", address=address)


@app.route("/addresses/delete/<int:address_id>", methods=["POST"])
@login_required
def delete_address(address_id):
    user_id = session["user_id"]

    existing = query("""
        SELECT is_default
        FROM addresses
        WHERE id=%s AND user_id=%s
    """, (address_id, user_id), True)

    if not existing:
        flash("Address not found.", "error")
        return redirect(url_for("addresses"))

    query("""
        DELETE FROM addresses
        WHERE id=%s AND user_id=%s
    """, (address_id, user_id), commit=True)

    # If the deleted address was default, make the newest remaining one default.
    if existing["is_default"]:
        remaining = query("""
            SELECT id
            FROM addresses
            WHERE user_id=%s
            ORDER BY id DESC
            LIMIT 1
        """, (user_id,), True)
        if remaining:
            query("""
                UPDATE addresses
                SET is_default=1
                WHERE id=%s AND user_id=%s
            """, (remaining["id"], user_id), commit=True)

    flash("Address deleted successfully.", "success")
    return redirect(url_for("addresses"))


@app.route("/about")
def about(): return render_template("about.html")
@app.route("/contact")
def contact(): return render_template("contact.html")
@app.route("/privacy")
def privacy(): return render_template("privacy.html")
@app.route("/terms")
def terms(): return render_template("terms.html")

@app.route("/admin/login",methods=["GET","POST"])
def admin_login():
    if request.method=="POST":
        u=query("SELECT * FROM users WHERE email=%s AND role='admin' AND is_active=1",(request.form["email"].strip().lower(),),True)
        if u and check_password_hash(u["password_hash"],request.form["password"]):
            session["user_id"]=u["id"];session["role"]="admin";return redirect(url_for("admin_dashboard"))
        flash("Invalid admin credentials.","error")
    return render_template("admin/login.html")

@app.route("/admin")
@admin_required
def admin_dashboard():
    stats={
      "users":query("SELECT COUNT(*) n FROM users WHERE role='customer'",one=True)["n"],
      "medicines":query("SELECT COUNT(*) n FROM medicines",one=True)["n"],
      "orders":query("SELECT COUNT(*) n FROM orders",one=True)["n"],
      "pending":query("SELECT COUNT(*) n FROM orders WHERE status IN ('Pending','Prescription Verification')",one=True)["n"],
      "prescriptions":query("SELECT COUNT(*) n FROM prescriptions WHERE status='Pending'",one=True)["n"],
      "lowstock":query("SELECT COUNT(*) n FROM medicines WHERE stock<=10 AND is_active=1",one=True)["n"],
      "sales":query("SELECT COALESCE(SUM(total),0) n FROM orders WHERE status<>'Cancelled'",one=True)["n"]
    }
    return render_template("admin/dashboard.html",stats=stats)

@app.route("/admin/medicines",methods=["GET","POST"])
@admin_required
def admin_medicines():
    if request.method=="POST":
        data=request.form
        query("""INSERT INTO medicines(name,brand,generic_name,category_id,price,discount,stock,pack_size,description,manufacturer,prescription_required)
                 VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",(data["name"],data["brand"],data["generic_name"],data["category_id"],data["price"],data["discount"],data["stock"],data["pack_size"],data["description"],data["manufacturer"],1 if data.get("prescription_required") else 0),commit=True)
        flash("Medicine added.","success");return redirect(url_for("admin_medicines"))
    return render_template("admin/medicines.html",medicines=query("SELECT m.*,c.name category_name FROM medicines m JOIN categories c ON c.id=m.category_id ORDER BY m.id DESC"),categories=query("SELECT * FROM categories ORDER BY name"))

@app.route("/admin/medicines/<int:mid>/toggle",methods=["POST"])
@admin_required
def toggle_medicine(mid):
    query("UPDATE medicines SET is_active=1-is_active WHERE id=%s",(mid,),commit=True);return redirect(url_for("admin_medicines"))

@app.route("/admin/categories",methods=["GET","POST"])
@admin_required
def admin_categories():
    if request.method=="POST":
        query("INSERT INTO categories(name,description) VALUES(%s,%s)",(request.form["name"],request.form.get("description","")),commit=True)
        return redirect(url_for("admin_categories"))
    return render_template("admin/categories.html",categories=query("SELECT * FROM categories ORDER BY name"))

@app.route("/admin/users")
@admin_required
def admin_users(): return render_template("admin/users.html",users=query("SELECT id,name,email,phone,role,is_active,created_at FROM users ORDER BY id DESC"))

@app.route("/admin/orders",methods=["GET","POST"])
@admin_required
def admin_orders():
    if request.method=="POST":
        query("UPDATE orders SET status=%s WHERE id=%s",(request.form["status"],request.form["order_id"]),commit=True)
    return render_template("admin/orders.html",orders=query("SELECT o.*,u.name customer FROM orders o JOIN users u ON u.id=o.user_id ORDER BY o.created_at DESC"))

@app.route("/admin/prescriptions")
@admin_required
def admin_prescriptions(): return render_template("admin/prescriptions.html",prescriptions=query("SELECT p.*,u.name user_name,u.email FROM prescriptions p JOIN users u ON u.id=p.user_id ORDER BY p.created_at DESC"))

@app.route("/admin/prescriptions/<int:pid>/<action>",methods=["POST"])
@admin_required
def review_prescription(pid,action):
    status={"approve":"Approved","reject":"Rejected"}.get(action)
    if status: query("UPDATE prescriptions SET status=%s,reviewed_by=%s,reviewed_at=NOW() WHERE id=%s",(status,session["user_id"],pid),commit=True)
    return redirect(url_for("admin_prescriptions"))

@app.route("/uploads/prescriptions/<path:name>")
@admin_required
def prescription_file(name): return send_from_directory(app.config["UPLOAD_FOLDER"],name,as_attachment=False)

@app.errorhandler(413)
def e413(e): return render_template("error.html",code=413,message="Uploaded file is too large. Maximum size is 5 MB."),413

@app.errorhandler(404)
def e404(e): return render_template("error.html",code=404,message="Page Not Found"),404
@app.errorhandler(403)
def e403(e): return render_template("error.html",code=403,message="Access Denied"),403
@app.errorhandler(500)
def e500(e): return render_template("error.html",code=500,message="Server Error"),500

if __name__=="__main__":
    app.run(debug=True,host="127.0.0.1",port=5000)
