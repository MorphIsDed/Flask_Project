import os
import io
import json
import logging
from functools import wraps
from datetime import datetime
from decimal import Decimal

from dotenv import load_dotenv
from flask import Flask, flash, redirect, render_template, request, url_for, send_file, jsonify
from flask_login import LoginManager, UserMixin, login_required, login_user, logout_user, current_user
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import create_engine
from werkzeug.security import check_password_hash, generate_password_hash

load_dotenv()

db = SQLAlchemy()
login_manager = LoginManager()
login_manager.login_view = "login"
logger = logging.getLogger(__name__)


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(160), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(40), default="Sales staff")
    active = db.Column(db.Boolean, default=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


class Customer(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(140), nullable=False)
    phone = db.Column(db.String(30), nullable=False)
    email = db.Column(db.String(160))
    city = db.Column(db.String(80))
    segment = db.Column(db.String(40), default="Retail")
    notes = db.Column(db.Text)
    loyalty_points = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class Lead(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(140), nullable=False)
    phone = db.Column(db.String(30), nullable=False)
    source = db.Column(db.String(60), default="Walk-in")
    stage = db.Column(db.String(40), default="New")
    value = db.Column(db.Numeric(12, 2), default=0)
    next_follow_up = db.Column(db.Date)
    notes = db.Column(db.Text)


class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    sku = db.Column(db.String(40), unique=True, nullable=False)
    name = db.Column(db.String(140), nullable=False)
    category = db.Column(db.String(60), nullable=False)
    metal = db.Column(db.String(30), default="Gold")
    purity = db.Column(db.String(20), default="22K")
    gross_weight = db.Column(db.Numeric(10, 3), default=0)
    stone_weight = db.Column(db.Numeric(10, 3), default=0)
    stock_qty = db.Column(db.Integer, default=0)
    price = db.Column(db.Numeric(12, 2), default=0)
    reorder_level = db.Column(db.Integer, default=1)
    active = db.Column(db.Boolean, default=True)
    barcode = db.Column(db.String(80), unique=True)


class Sale(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    invoice_no = db.Column(db.String(30), unique=True, nullable=False)
    customer_id = db.Column(db.Integer, db.ForeignKey("customer.id"))
    subtotal = db.Column(db.Numeric(12, 2), default=0)
    gst = db.Column(db.Numeric(12, 2), default=0)
    discount = db.Column(db.Numeric(12, 2), default=0)
    total = db.Column(db.Numeric(12, 2), default=0)
    payment_method = db.Column(db.String(30), default="UPI")
    status = db.Column(db.String(30), default="Paid")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    customer = db.relationship("Customer")
    lines = db.relationship("SaleLine", backref="sale", cascade="all, delete-orphan")


class SaleLine(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    sale_id = db.Column(db.Integer, db.ForeignKey("sale.id"), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey("product.id"), nullable=False)
    quantity = db.Column(db.Integer, default=1)
    unit_price = db.Column(db.Numeric(12, 2), default=0)
    product = db.relationship("Product")


class Supplier(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(140), nullable=False)
    phone = db.Column(db.String(30))
    email = db.Column(db.String(160))
    gstin = db.Column(db.String(20))
    address = db.Column(db.String(240))
    active = db.Column(db.Boolean, default=True)


class PurchaseOrder(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    po_number = db.Column(db.String(30), unique=True, nullable=False)
    supplier_id = db.Column(db.Integer, db.ForeignKey("supplier.id"), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey("product.id"), nullable=False)
    quantity = db.Column(db.Integer, default=1)
    unit_cost = db.Column(db.Numeric(12, 2), default=0)
    status = db.Column(db.String(30), default="Draft")
    ordered_at = db.Column(db.DateTime, default=datetime.utcnow)
    supplier = db.relationship("Supplier")
    product = db.relationship("Product")


class GoldRate(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    rate_date = db.Column(db.Date, default=datetime.utcnow().date, nullable=False)
    purity = db.Column(db.String(10), nullable=False)
    rate_per_gram = db.Column(db.Numeric(12, 2), nullable=False)
    source = db.Column(db.String(100), default="Store manager")


class ReturnTransaction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    sale_id = db.Column(db.Integer, db.ForeignKey("sale.id"), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey("product.id"), nullable=False)
    quantity = db.Column(db.Integer, default=1)
    reason = db.Column(db.String(240))
    mode = db.Column(db.String(30), default="Refund")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    sale = db.relationship("Sale")
    product = db.relationship("Product")


class Employee(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(140), nullable=False)
    phone = db.Column(db.String(30))
    designation = db.Column(db.String(80), default="Sales Executive")
    salary = db.Column(db.Numeric(12, 2), default=0)
    incentive_rate = db.Column(db.Numeric(5, 2), default=0)
    joining_date = db.Column(db.Date)
    status = db.Column(db.String(30), default="Active")


class Repair(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    ticket_no = db.Column(db.String(30), unique=True, nullable=False)
    customer_id = db.Column(db.Integer, db.ForeignKey("customer.id"))
    item_description = db.Column(db.String(240), nullable=False)
    status = db.Column(db.String(40), default="Received")
    estimated_cost = db.Column(db.Numeric(12, 2), default=0)
    due_date = db.Column(db.Date)
    customer = db.relationship("Customer")


def create_app():
    app = Flask(__name__)
    app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "dev-key-change-me")
    database_uri = os.getenv("DATABASE_URL", "sqlite:///jewellery_crm.db")
    if database_uri.startswith("postgres://"):
        database_uri = "postgresql://" + database_uri[len("postgres://"):]
    try:
        probe_engine = create_engine(database_uri, pool_pre_ping=True)
        with probe_engine.connect():
            pass
        probe_engine.dispose()
    except Exception as error:
        logger.warning("Database unavailable (%s); using temporary fallback data.", error)
        database_uri = "sqlite:///:memory:"
        app.config["DB_FALLBACK_ACTIVE"] = True
    app.config["SQLALCHEMY_DATABASE_URI"] = database_uri
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    db.init_app(app)
    login_manager.init_app(app)

    with app.app_context():
        db.create_all()
        migrate_legacy_schema()
        seed_data()

    register_routes(app)
    return app


@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))


def migrate_legacy_schema():
    """Add fields introduced after the starter database was created."""
    inspector = db.inspect(db.engine)
    columns = {c["name"] for c in inspector.get_columns("customer")}
    if "loyalty_points" not in columns:
        db.session.execute(db.text("ALTER TABLE customer ADD COLUMN loyalty_points INTEGER DEFAULT 0"))
    columns = {c["name"] for c in inspector.get_columns("product")}
    if "barcode" not in columns:
        db.session.execute(db.text("ALTER TABLE product ADD COLUMN barcode VARCHAR(80)"))
    db.session.commit()


def roles_required(*roles):
    def decorator(view):
        @wraps(view)
        @login_required
        def wrapped(*args, **kwargs):
            if current_user.role not in roles:
                flash("You do not have permission to access that area.", "error")
                return redirect(url_for("dashboard"))
            return view(*args, **kwargs)
        return wrapped
    return decorator


def seed_data():
    if User.query.first():
        return
    admin = User(name="Admin", email=os.getenv("ADMIN_EMAIL", "admin@aurum.local"), role="Owner/Admin")
    admin.set_password(os.getenv("ADMIN_PASSWORD", "admin123"))
    db.session.add(admin)
    db.session.add_all([
        Customer(name="Priya Sharma", phone="9876543210", email="priya@example.com", city="Mumbai", segment="VIP"),
        Customer(name="Rohan Kapoor", phone="9811122233", city="Delhi", segment="Retail"),
        Customer(name="Neha Iyer", phone="9988776655", city="Bengaluru", segment="Wholesale"),
    ])
    db.session.add_all([
        Product(sku="RNG-22-001", name="Classic Gold Ring", category="Rings", metal="Gold", purity="22K", gross_weight=4.250, stone_weight=0, stock_qty=3, price=38500, reorder_level=2),
        Product(sku="NKC-18-002", name="Diamond Necklace", category="Necklaces", metal="Gold", purity="18K", gross_weight=18.400, stone_weight=1.2, stock_qty=1, price=168000, reorder_level=1),
        Product(sku="BGL-22-003", name="Temple Gold Bangles", category="Bangles", metal="Gold", purity="22K", gross_weight=32.000, stone_weight=0, stock_qty=0, price=246000, reorder_level=2),
    ])
    db.session.add_all([
        Lead(name="Ananya Rao", phone="9900112233", source="Instagram", stage="Qualified", value=95000),
        Lead(name="Vikram Singh", phone="9765432100", source="Referral", stage="Proposal", value=220000),
    ])
    db.session.add(Employee(name="Kavya Nair", phone="9898989898", designation="Store Manager", salary=65000, incentive_rate=2.5, status="Active"))
    db.session.commit()


def register_routes(app):
    @app.route("/login", methods=["GET", "POST"])
    def login():
        if request.method == "POST":
            user = User.query.filter_by(email=request.form["email"].strip().lower()).first()
            if user and user.active and user.check_password(request.form["password"]):
                login_user(user)
                return redirect(url_for("dashboard"))
            flash("Invalid email or password.", "error")
        return render_template("login.html")

    @app.get("/logout")
    @login_required
    def logout():
        logout_user()
        return redirect(url_for("login"))

    @app.get("/")
    @login_required
    def dashboard():
        revenue = db.session.query(db.func.coalesce(db.func.sum(Sale.total), 0)).scalar()
        return render_template("dashboard.html", customers=Customer.query.count(), products=Product.query.count(), leads=Lead.query.count(), employees=Employee.query.count(), sales=Sale.query.count(), revenue=revenue, low_stock=Product.query.filter(Product.stock_qty <= Product.reorder_level).all())

    @app.route("/customers", methods=["GET", "POST"])
    @login_required
    def customers():
        if request.method == "POST":
            db.session.add(Customer(name=request.form["name"], phone=request.form["phone"], email=request.form.get("email"), city=request.form.get("city"), segment=request.form.get("segment", "Retail"), notes=request.form.get("notes")))
            db.session.commit()
            flash("Customer profile created.", "success")
            return redirect(url_for("customers"))
        search = request.args.get("q", "").strip()
        query = Customer.query.order_by(Customer.created_at.desc())
        if search:
            query = query.filter(db.or_(Customer.name.ilike(f"%{search}%"), Customer.phone.ilike(f"%{search}%")))
        return render_template("customers.html", customers=query.all(), search=search)

    @app.route("/leads", methods=["GET", "POST"])
    @login_required
    def leads():
        if request.method == "POST":
            db.session.add(Lead(name=request.form["name"], phone=request.form["phone"], source=request.form.get("source"), stage=request.form.get("stage", "New"), value=Decimal(request.form.get("value") or 0), notes=request.form.get("notes")))
            db.session.commit()
            flash("Lead added to pipeline.", "success")
            return redirect(url_for("leads"))
        return render_template("leads.html", leads=Lead.query.order_by(Lead.id.desc()).all())

    @app.route("/inventory", methods=["GET", "POST"])
    @login_required
    def inventory():
        if request.method == "POST":
            try:
                sku = request.form["sku"].strip()
                if not sku or not request.form["name"].strip() or not request.form["category"].strip():
                    raise ValueError("SKU, name and category are required.")
                if Product.query.filter_by(sku=sku).first():
                    raise ValueError("That SKU already exists.")
                stock_qty = int(request.form.get("stock_qty") or 0)
                if stock_qty < 0:
                    raise ValueError("Stock quantity cannot be negative.")
                db.session.add(Product(sku=sku, barcode=request.form.get("barcode") or sku, name=request.form["name"].strip(), category=request.form["category"].strip(), metal=request.form.get("metal"), purity=request.form.get("purity"), gross_weight=Decimal(request.form.get("gross_weight") or 0), stock_qty=stock_qty, price=Decimal(request.form.get("price") or 0), reorder_level=int(request.form.get("reorder_level") or 1)))
                db.session.commit(); flash("Product added to inventory.", "success")
            except (ValueError, ArithmeticError) as error:
                db.session.rollback(); flash(str(error), "error")
            return redirect(url_for("inventory"))
        return render_template("inventory.html", products=Product.query.order_by(Product.id.desc()).all())

    @app.route("/pos", methods=["GET", "POST"])
    @login_required
    def pos():
        products = Product.query.filter(Product.stock_qty > 0, Product.active.is_(True)).order_by(Product.name).all()
        customers = Customer.query.order_by(Customer.name).all()
        if request.method == "POST":
            try:
                product = db.session.get(Product, int(request.form["product_id"]))
                quantity = int(request.form.get("quantity") or 1)
            except (TypeError, ValueError):
                flash("Choose a valid product and quantity.", "error"); return redirect(url_for("pos"))
            if quantity < 1:
                flash("Quantity must be at least 1.", "error"); return redirect(url_for("pos"))
            if not product or product.stock_qty < quantity:
                flash("That quantity is not available in stock.", "error")
                return redirect(url_for("pos"))
            subtotal = Decimal(product.price or 0) * quantity
            gst = subtotal * Decimal("0.03")
            invoice = Sale(invoice_no=f"INV-{datetime.utcnow().strftime('%y%m%d%H%M%S%f')}", customer_id=request.form.get("customer_id") or None, subtotal=subtotal, gst=gst, total=subtotal + gst, payment_method=request.form.get("payment_method", "UPI"))
            product.stock_qty -= quantity
            db.session.add(invoice)
            db.session.flush()
            db.session.add(SaleLine(sale_id=invoice.id, product_id=product.id, quantity=quantity, unit_price=product.price))
            if invoice.customer:
                invoice.customer.loyalty_points = (invoice.customer.loyalty_points or 0) + int(invoice.total // 100)
            db.session.commit()
            flash(f"Invoice {invoice.invoice_no} created for INR {invoice.total:,.0f}.", "success")
            return redirect(url_for("pos"))
        return render_template("pos.html", products=products, customers=customers, sales=Sale.query.order_by(Sale.created_at.desc()).limit(8).all())

    @app.get("/scan-product")
    @login_required
    def scan_product():
        code = request.args.get("code", "").strip()
        product = Product.query.filter(db.or_(Product.barcode == code, Product.sku == code)).first()
        if not product:
            return jsonify({"found": False}), 404
        return jsonify({"found": True, "id": product.id, "sku": product.sku, "name": product.name, "price": float(product.price or 0), "stock": product.stock_qty})

    @app.get("/invoice/<int:sale_id>.pdf")
    @login_required
    def invoice_pdf(sale_id):
        from reportlab.lib.pagesizes import A4
        from reportlab.pdfgen import canvas
        import qrcode
        sale = db.session.get(Sale, sale_id)
        if not sale:
            return render_template("404.html"), 404
        output = io.BytesIO(); pdf = canvas.Canvas(output, pagesize=A4)
        _, height = A4
        pdf.setFont("Helvetica-Bold", 18); pdf.drawString(48, height - 55, "AURUM JEWELLERY")
        pdf.setFont("Helvetica", 10); pdf.drawString(48, height - 75, "GST Invoice · Mumbai, India")
        pdf.drawRightString(545, height - 55, sale.invoice_no); pdf.drawRightString(545, height - 72, sale.created_at.strftime("%d %b %Y"))
        y = height - 125; pdf.setFont("Helvetica-Bold", 10); pdf.drawString(48, y, "DESCRIPTION"); pdf.drawString(390, y, "QTY"); pdf.drawRightString(545, y, "AMOUNT")
        y -= 22; pdf.setFont("Helvetica", 10)
        for line in sale.lines:
            pdf.drawString(48, y, f"{line.product.name} ({line.product.sku})"); pdf.drawString(395, y, str(line.quantity)); pdf.drawRightString(545, y, f"INR {line.unit_price * line.quantity:,.2f}"); y -= 20
        y -= 15; pdf.line(350, y, 545, y); y -= 20
        for label, value in [("Subtotal", sale.subtotal), ("GST", sale.gst), ("TOTAL", sale.total)]:
            pdf.setFont("Helvetica-Bold" if label == "TOTAL" else "Helvetica", 10); pdf.drawString(390, y, label); pdf.drawRightString(545, y, f"INR {value:,.2f}"); y -= 18
        qr = qrcode.make(json.dumps({"invoice": sale.invoice_no, "total": float(sale.total), "gst": float(sale.gst)})); qr_buf = io.BytesIO(); qr.save(qr_buf, format="PNG"); qr_buf.seek(0)
        from reportlab.lib.utils import ImageReader
        pdf.drawImage(ImageReader(qr_buf), 48, 55, width=92, height=92); pdf.setFont("Helvetica", 8); pdf.drawString(150, 72, "Scan to verify invoice")
        pdf.save(); output.seek(0)
        return send_file(output, mimetype="application/pdf", as_attachment=True, download_name=f"{sale.invoice_no}.pdf")

    @app.route("/suppliers", methods=["GET", "POST"])
    @roles_required("Owner/Admin", "Manager")
    def suppliers():
        if request.method == "POST":
            db.session.add(Supplier(name=request.form["name"], phone=request.form.get("phone"), email=request.form.get("email"), gstin=request.form.get("gstin"), address=request.form.get("address")))
            db.session.commit(); flash("Supplier added.", "success"); return redirect(url_for("suppliers"))
        return render_template("suppliers.html", suppliers=Supplier.query.order_by(Supplier.id.desc()).all(), products=Product.query.all(), orders=PurchaseOrder.query.order_by(PurchaseOrder.id.desc()).all())

    @app.post("/purchase-orders")
    @roles_required("Owner/Admin", "Manager")
    def purchase_orders():
        try:
            quantity = int(request.form["quantity"]); supplier_id = int(request.form["supplier_id"]); product_id = int(request.form["product_id"])
            if quantity < 1: raise ValueError("Quantity must be at least 1.")
            if not db.session.get(Supplier, supplier_id) or not db.session.get(Product, product_id): raise ValueError("Choose a valid supplier and product.")
            order = PurchaseOrder(po_number=f"PO-{datetime.utcnow().strftime('%y%m%d%H%M%S%f')}", supplier_id=supplier_id, product_id=product_id, quantity=quantity, unit_cost=Decimal(request.form.get("unit_cost") or 0), status="Ordered")
        except (TypeError, ValueError, ArithmeticError) as error:
            flash(str(error), "error"); return redirect(url_for("suppliers"))
        db.session.add(order); db.session.commit(); flash("Purchase order created.", "success"); return redirect(url_for("suppliers"))

    @app.route("/gold-rates", methods=["GET", "POST"])
    @roles_required("Owner/Admin", "Manager")
    def gold_rates():
        if request.method == "POST":
            try:
                rate = Decimal(request.form["rate_per_gram"])
                if rate <= 0: raise ValueError("Gold rate must be greater than zero.")
                db.session.add(GoldRate(rate_date=datetime.strptime(request.form["rate_date"], "%Y-%m-%d").date(), purity=request.form["purity"], rate_per_gram=rate))
            except (KeyError, ValueError, ArithmeticError) as error:
                flash(str(error), "error"); return redirect(url_for("gold_rates"))
            db.session.commit(); flash("Gold rate recorded.", "success"); return redirect(url_for("gold_rates"))
        return render_template("gold_rates.html", rates=GoldRate.query.order_by(GoldRate.rate_date.desc()).all(), today=datetime.utcnow().date())

    @app.route("/returns", methods=["GET", "POST"])
    @roles_required("Owner/Admin", "Manager", "Cashier")
    def returns():
        if request.method == "POST":
            sale = Sale.query.filter_by(invoice_no=request.form.get("invoice_no", "").strip()).first()
            try: product = db.session.get(Product, int(request.form["product_id"])); qty = int(request.form.get("quantity") or 1)
            except (TypeError, ValueError): product = None; qty = 0
            sold_qty = sum(line.quantity for line in sale.lines if line.product_id == product.id) if sale and product else 0
            returned_qty = sum(item.quantity for item in ReturnTransaction.query.filter_by(sale_id=sale.id, product_id=product.id).all()) if sale and product else 0
            if not sale or not product: flash("Invoice or product not found.", "error")
            elif qty < 1 or qty > sold_qty - returned_qty: flash("Return quantity exceeds the quantity sold.", "error")
            else:
                product.stock_qty += qty; db.session.add(ReturnTransaction(sale_id=sale.id, product_id=product.id, quantity=qty, reason=request.form.get("reason"), mode=request.form.get("mode", "Refund"))); db.session.commit(); flash("Return recorded and stock restored.", "success")
            return redirect(url_for("returns"))
        return render_template("returns.html", products=Product.query.all(), returns=ReturnTransaction.query.order_by(ReturnTransaction.created_at.desc()).limit(30).all())

    @app.route("/employees", methods=["GET", "POST"])
    @login_required
    def employees():
        if request.method == "POST":
            db.session.add(Employee(name=request.form["name"], phone=request.form.get("phone"), designation=request.form.get("designation"), salary=Decimal(request.form.get("salary") or 0), incentive_rate=Decimal(request.form.get("incentive_rate") or 0)))
            db.session.commit()
            flash("Employee record added.", "success")
            return redirect(url_for("employees"))
        return render_template("employees.html", employees=Employee.query.order_by(Employee.id.desc()).all())

    @app.route("/users", methods=["GET", "POST"])
    @roles_required("Owner/Admin")
    def users():
        if request.method == "POST":
            email = request.form["email"].strip().lower()
            if User.query.filter_by(email=email).first():
                flash("That email is already in use.", "error")
            else:
                user = User(name=request.form["name"], email=email, role=request.form["role"])
                user.set_password(request.form["password"]); db.session.add(user); db.session.commit(); flash("Team login created.", "success")
            return redirect(url_for("users"))
        return render_template("users.html", users=User.query.order_by(User.id).all())

    @app.get("/reports")
    @login_required
    def reports():
        sales_total = db.session.query(db.func.coalesce(db.func.sum(Sale.total), 0)).scalar()
        pipeline = db.session.query(db.func.coalesce(db.func.sum(Lead.value), 0)).scalar()
        inventory_value = db.session.query(db.func.coalesce(db.func.sum(Product.price * Product.stock_qty), 0)).scalar()
        sales_series = [{"label": s.created_at.strftime("%d %b"), "value": float(s.total or 0)} for s in Sale.query.order_by(Sale.created_at.desc()).limit(14).all()][::-1]
        return render_template("reports.html", sales_total=sales_total, pipeline=pipeline, inventory_value=inventory_value, sales_series=sales_series)

    @app.errorhandler(404)
    def not_found(_error):
        return render_template("404.html"), 404


app = create_app()

if __name__ == "__main__":
    app.run(debug=True)
