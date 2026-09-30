import os
from dotenv import load_dotenv
from datetime import datetime, timezone
from functools import wraps

from flask import Flask, render_template, request, redirect, url_for, session, jsonify, flash
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import func
from werkzeug.security import generate_password_hash, check_password_hash

from services.recommendation import recommend_crop, fertilizer_advisory
from services.weather import get_weather
from services.market import get_market_data

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(BASE_DIR, '.env'))
app = Flask(__name__)
app.secret_key = os.environ.get("AGROZ_SECRET_KEY", "agroz-dev-secret-change-me")

DATABASE_URL = os.environ.get("DATABASE_URL", "").strip()
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql+psycopg://", 1)
elif DATABASE_URL.startswith("postgresql://"):
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+psycopg://", 1)

app.config["SQLALCHEMY_DATABASE_URI"] = DATABASE_URL or "sqlite:///agro_z.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {"pool_pre_ping": True}
db = SQLAlchemy(app)


def now():
    return datetime.now(timezone.utc)


class User(db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    location = db.Column(db.String(255), default="")
    role = db.Column(db.String(30), default="farmer", nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), default=now, nullable=False)


class SoilInput(db.Model):
    __tablename__ = "soil_inputs"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    n = db.Column(db.Float, nullable=False)
    p = db.Column(db.Float, nullable=False)
    k = db.Column(db.Float, nullable=False)
    ph = db.Column(db.Float, nullable=False)
    temperature = db.Column(db.Float, nullable=False)
    humidity = db.Column(db.Float, nullable=False)
    rainfall = db.Column(db.Float, nullable=False)
    location = db.Column(db.String(255), default="")
    created_at = db.Column(db.DateTime(timezone=True), default=now, nullable=False)


class Recommendation(db.Model):
    __tablename__ = "recommendations"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    soil_id = db.Column(db.Integer, db.ForeignKey("soil_inputs.id"))
    crop = db.Column(db.String(100), nullable=False)
    confidence = db.Column(db.Float, nullable=False)
    fertilizer_summary = db.Column(db.Text)
    created_at = db.Column(db.DateTime(timezone=True), default=now, nullable=False)


class Advisory(db.Model):
    __tablename__ = "advisories"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    recommendation_id = db.Column(db.Integer, db.ForeignKey("recommendations.id"))
    risk_type = db.Column(db.String(80), nullable=False)
    message = db.Column(db.Text, nullable=False)
    severity = db.Column(db.String(30), default="info")
    created_at = db.Column(db.DateTime(timezone=True), default=now, nullable=False)


class WeatherLog(db.Model):
    __tablename__ = "weather_history"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    location = db.Column(db.String(255), nullable=False)
    temperature = db.Column(db.Float)
    humidity = db.Column(db.Float)
    wind = db.Column(db.Float)
    description = db.Column(db.String(255))
    live = db.Column(db.Boolean, default=False)
    raw_summary = db.Column(db.Text)
    created_at = db.Column(db.DateTime(timezone=True), default=now, nullable=False)


class MarketLog(db.Model):
    __tablename__ = "market_history"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    commodity = db.Column(db.String(120), nullable=False)
    source = db.Column(db.String(255))
    best_market = db.Column(db.String(255))
    best_price = db.Column(db.Float)
    live = db.Column(db.Boolean, default=False)
    raw_summary = db.Column(db.Text)
    created_at = db.Column(db.DateTime(timezone=True), default=now, nullable=False)


def init_db():
    with app.app_context():
        db.create_all()

        # Admin credentials are controlled by environment variables so the
        # deployed admin email/password can be changed from Render without
        # editing the source code.
        admin_email = os.environ.get("AGROZ_ADMIN_EMAIL", "admin@agroz.local").strip().lower()
        admin_password = os.environ.get("AGROZ_ADMIN_PASSWORD", "admin123")

        admin = User.query.filter_by(role="admin").first()
        email_owner = User.query.filter_by(email=admin_email).first()

        if email_owner and (admin is None or email_owner.id != admin.id):
            raise RuntimeError(f"AGROZ_ADMIN_EMAIL is already used by another account: {admin_email}")

        if not admin:
            admin = User(
                name="Agro Z Admin",
                email=admin_email,
                password_hash=generate_password_hash(admin_password),
                location="India",
                role="admin"
            )
            db.session.add(admin)
        else:
            # Keep the existing admin account, but synchronize its credentials
            # with the current Render environment variables.
            admin.email = admin_email
            admin.password_hash = generate_password_hash(admin_password)

        db.session.commit()


def login_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if "user_id" not in session:
            return redirect(url_for("login"))
        return fn(*args, **kwargs)
    return wrapper


def admin_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if session.get("role") != "admin":
            flash("Admin access required.", "error")
            return redirect(url_for("dashboard"))
        return fn(*args, **kwargs)
    return wrapper


@app.context_processor
def inject_globals():
    return {"app_year": now().year}


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        location = request.form.get("location", "").strip()
        if not name or not email or len(password) < 6:
            flash("Enter all fields. Password must be at least 6 characters.", "error")
            return render_template("register.html")
        if User.query.filter_by(email=email).first():
            flash("An account with that email already exists.", "error")
            return render_template("register.html")
        db.session.add(User(name=name, email=email, password_hash=generate_password_hash(password), location=location))
        db.session.commit()
        flash("Account created. Your farm workspace is ready.", "success")
        return redirect(url_for("login"))
    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        user = User.query.filter_by(email=email).first()
        if user and check_password_hash(user.password_hash, password):
            session.clear()
            session["user_id"] = user.id
            session["name"] = user.name
            session["role"] = user.role
            return redirect(url_for("admin" if user.role == "admin" else "dashboard"))
        flash("Invalid email or password.", "error")
    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("index"))


@app.route("/dashboard")
@login_required
def dashboard():
    uid = session["user_id"]
    recent = Recommendation.query.filter_by(user_id=uid).order_by(Recommendation.id.desc()).limit(6).all()
    soil = SoilInput.query.filter_by(user_id=uid).order_by(SoilInput.id.desc()).first()
    user = db.session.get(User, uid)
    stats = {
        "soil": SoilInput.query.filter_by(user_id=uid).count(),
        "recommendations": Recommendation.query.filter_by(user_id=uid).count(),
        "weather": WeatherLog.query.filter_by(user_id=uid).count(),
        "market": MarketLog.query.filter_by(user_id=uid).count(),
    }
    return render_template("dashboard.html", recent=recent, soil=soil, user=user, stats=stats)


@app.route("/recommendation", methods=["GET", "POST"])
@login_required
def recommendation():
    result = fert = None
    if request.method == "POST":
        try:
            data = {
                "n": float(request.form["n"]), "p": float(request.form["p"]), "k": float(request.form["k"]),
                "ph": float(request.form["ph"]), "temperature": float(request.form["temperature"]),
                "humidity": float(request.form["humidity"]), "rainfall": float(request.form["rainfall"]),
                "location": request.form.get("location", "").strip()
            }
            if not (0 <= data["ph"] <= 14 and 0 <= data["humidity"] <= 100):
                raise ValueError
        except (KeyError, ValueError):
            flash("Please enter valid soil and climate values.", "error")
            return render_template("recommendation.html")

        result = recommend_crop(data)
        fert = fertilizer_advisory(result["crop"], data)
        soil = SoilInput(user_id=session["user_id"], **{k: data[k] for k in ["n","p","k","ph","temperature","humidity","rainfall","location"]})
        db.session.add(soil)
        db.session.flush()
        summary = ", ".join(x["name"] for x in fert["recommendations"])
        rec = Recommendation(user_id=session["user_id"], soil_id=soil.id, crop=result["crop"], confidence=result["confidence"], fertilizer_summary=summary)
        db.session.add(rec)
        db.session.commit()
        result["recommendation_id"] = rec.id
        flash(f"Analysis saved. Recommended crop: {result['crop']}.", "success")
    return render_template("recommendation.html", result=result, fert=fert)


@app.route("/fertilizer")
@login_required
def fertilizer():
    return render_template("fertilizer.html")


@app.route("/weather")
@login_required
def weather():
    user = db.session.get(User, session["user_id"])
    return render_template("weather.html", user=user)


@app.route("/market")
@login_required
def market():
    return render_template("market.html")


@app.route("/api/weather")
@login_required
def api_weather():
    location = request.args.get("location", "").strip()
    crop = request.args.get("crop", "").strip()
    user = db.session.get(User, session["user_id"])
    location = location or (user.location if user else "")
    data = get_weather(location, crop)
    if location and data:
        db.session.add(WeatherLog(user_id=session["user_id"], location=location, temperature=data.get("temperature"), humidity=data.get("humidity"), wind=data.get("wind"), description=data.get("description"), live=bool(data.get("live")), raw_summary=str(data.get("alerts", []))))
        db.session.commit()
    return jsonify(data)


@app.route("/api/market")
@login_required
def api_market():
    commodity = request.args.get("commodity", "Rice").strip()
    data = get_market_data(commodity)
    db.session.add(MarketLog(user_id=session["user_id"], commodity=commodity, source=data.get("source", ""), best_market=data.get("best_market"), best_price=data.get("best_price"), live=bool(data.get("live")), raw_summary=str(data.get("markets", []))))
    db.session.commit()
    return jsonify(data)


@app.route("/api/profile", methods=["GET", "POST"])
@login_required
def api_profile():
    user = db.session.get(User, session["user_id"])
    if request.method == "POST":
        user.name = request.form.get("name", "").strip() or user.name
        user.location = request.form.get("location", "").strip()
        db.session.commit()
        session["name"] = user.name
    return jsonify({"id": user.id, "name": user.name, "email": user.email, "location": user.location, "role": user.role, "created_at": user.created_at.isoformat()})


@app.route("/api/history")
@login_required
def api_history():
    uid = session["user_id"]
    rows = Recommendation.query.filter_by(user_id=uid).order_by(Recommendation.id.desc()).limit(12).all()
    return jsonify([{"crop": r.crop, "confidence": r.confidence, "created_at": r.created_at.isoformat()} for r in rows])


@app.route("/profile")
@login_required
def profile():
    return render_template("profile.html")


@app.route("/admin")
@login_required
@admin_required
def admin():
    users = User.query.order_by(User.id.desc()).all()
    stats = {
        "users": User.query.count(),
        "farmers": User.query.filter_by(role="farmer").count(),
        "soil": SoilInput.query.count(),
        "recommendations": Recommendation.query.count(),
        "weather": WeatherLog.query.count(),
        "market": MarketLog.query.count(),
    }
    top = db.session.query(Recommendation.crop, func.count(Recommendation.id).label("count")).group_by(Recommendation.crop).order_by(func.count(Recommendation.id).desc()).limit(5).all()
    return render_template("admin.html", users=users, stats=stats, top_crops=top)


@app.route("/health")
def health():
    try:
        db.session.execute(db.text("SELECT 1"))
        db_status = "ok"
        db_backend = db.engine.url.get_backend_name()
        table_count = db.session.execute(db.text(
            "SELECT count(*) FROM information_schema.tables WHERE table_schema='public'"
        )).scalar() if db_backend == "postgresql" else None
    except Exception as exc:
        db_status = "error"
        db_backend = "unknown"
        table_count = None
    return jsonify({
        "status": "ok",
        "app": "Agro Z",
        "database": db_status,
        "database_backend": db_backend,
        "public_table_count": table_count,
        "weather_configured": bool(os.environ.get("OPENWEATHER_API_KEY"))
    })

@app.route("/api/db-check")
@login_required
def api_db_check():
    uid = session["user_id"]
    return jsonify({
        "database_backend": db.engine.url.get_backend_name(),
        "current_user_id": uid,
        "users": User.query.count(),
        "your_soil_inputs": SoilInput.query.filter_by(user_id=uid).count(),
        "your_recommendations": Recommendation.query.filter_by(user_id=uid).count(),
        "your_weather_logs": WeatherLog.query.filter_by(user_id=uid).count(),
        "your_market_logs": MarketLog.query.filter_by(user_id=uid).count(),
        "tables": [name for name in db.metadata.tables.keys()]
    })


init_db()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=True)
