"""L'Étudiant × Alberthon — webapp principale (site vitrine + portail entreprises)."""
import math
import sqlite3
from datetime import datetime
from io import BytesIO
from pathlib import Path

import markdown as md_lib
from flask import (
    Flask, abort, flash, jsonify, redirect, render_template, request,
    send_file, send_from_directory, session, url_for,
)
from flask_login import (
    LoginManager, current_user, login_required, login_user, logout_user,
)

import auth as auth_mod
import barometer_service
import leads_service

ROOT = Path(__file__).parent
PARENT = ROOT.parent

app = Flask(__name__, static_folder="static", template_folder="templates")
app.config["SECRET_KEY"] = "alberthon-letudiant-demo-2026"  # demo only
app.config["MAX_CONTENT_LENGTH"] = 4 * 1024 * 1024  # 4 MB

login_manager = LoginManager(app)
login_manager.login_view = "login"
login_manager.login_message = "Connectez-vous pour accéder au portail."
login_manager.login_message_category = "info"


# Plan capabilities — single source of truth used in templates and route guards
PLAN_FEATURES = {
    "starter":       {"barometre": True,  "leads": False, "leads_class": [],          "label": "Baromètre Starter",   "price": "6 000 €/an"},
    "growth":        {"barometre": True,  "leads": False, "leads_class": [],          "label": "Baromètre Growth",    "price": "14 000 €/an"},
    "premium":       {"barometre": True,  "leads": True,  "leads_class": ["A","B","C"], "label": "Baromètre Premium",   "price": "28 000 €/an"},
    "leads_only":    {"barometre": False, "leads": True,  "leads_class": ["A","B","C"], "label": "Leads CPL",           "price": "à l'usage"},
    "premium_leads": {"barometre": True,  "leads": True,  "leads_class": ["A","B","C"], "label": "Premium + Leads",     "price": "sur devis"},
    "admin":         {"barometre": True,  "leads": True,  "leads_class": ["A","B","C"], "label": "Administrateur",      "price": "—"},
}


@login_manager.user_loader
def load_user(user_id):
    return auth_mod.User.get(user_id)


@app.context_processor
def inject_globals():
    return {
        "current_year": datetime.now().year,
        "plan_features": PLAN_FEATURES,
    }


# ─── Helpers ───────────────────────────────────────────────────────────────────

def _client_meta():
    return request.remote_addr, (request.user_agent.string or "")[:200]


def _require_plan_access(feature: str):
    plan = current_user.plan
    if not PLAN_FEATURES.get(plan, {}).get(feature):
        flash(
            f"Cette fonctionnalité n'est pas incluse dans votre plan ({PLAN_FEATURES[plan]['label']}). "
            "Contactez-nous pour upgrader.",
            "warning",
        )
        return False
    return True


# ─── Site vitrine ──────────────────────────────────────────────────────────────

@app.route("/")
def home():
    bdata = barometer_service.load_barometer()
    return render_template("public/home.html", kpis=bdata["kpis"])


@app.route("/produits/barometre")
def product_barometre():
    return render_template("public/product_barometre.html")


@app.route("/produits/leads")
def product_leads():
    return render_template("public/product_leads.html")


@app.route("/tarifs")
def pricing():
    return render_template("public/pricing.html")


@app.route("/articles")
def articles():
    conn = auth_mod.get_db()
    rows = conn.execute(
        "SELECT * FROM articles ORDER BY published_at DESC"
    ).fetchall()
    conn.close()
    return render_template("public/articles.html", articles=[dict(r) for r in rows])


@app.route("/articles/<slug>")
def article_detail(slug):
    conn = auth_mod.get_db()
    row = conn.execute("SELECT * FROM articles WHERE slug = ?", (slug,)).fetchone()
    conn.close()
    if not row:
        abort(404)
    article = dict(row)
    article["body_html"] = md_lib.markdown(article["body"] or "", extensions=["extra"])
    return render_template("public/article_detail.html", article=article)


@app.route("/a-propos")
def about():
    return render_template("public/about.html")


@app.route("/contact", methods=["GET", "POST"])
def contact():
    if request.method == "POST":
        name = (request.form.get("name") or "").strip()
        email = (request.form.get("email") or "").strip().lower()
        school = (request.form.get("school") or "").strip()
        message = (request.form.get("message") or "").strip()
        if not (name and email and message):
            flash("Merci de remplir nom, email et message.", "warning")
        else:
            auth_mod.save_contact(name, email, school, message)
            flash("Merci ! Notre équipe vous recontacte sous 48 h.", "success")
            return redirect(url_for("contact"))
    return render_template("public/contact.html")


# ─── Auth ──────────────────────────────────────────────────────────────────────

@app.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("portal_home"))

    if request.method == "POST":
        email = (request.form.get("email") or "").strip().lower()
        password = request.form.get("password") or ""
        user = auth_mod.User.by_email(email)
        if not user or not auth_mod.verify_password(password, user.password_hash):
            flash("Email ou mot de passe invalide.", "error")
        elif user.status != "active":
            flash("Votre compte est en attente de validation. Contactez-nous.", "warning")
        else:
            login_user(user)
            ip, ua = _client_meta()
            auth_mod.log_access(user.id, "login", ip, ua)
            next_url = request.args.get("next") or url_for("portal_home")
            return redirect(next_url)
    return render_template("auth/login.html")


@app.route("/signup", methods=["GET", "POST"])
def signup():
    if current_user.is_authenticated:
        return redirect(url_for("portal_home"))

    if request.method == "POST":
        email = (request.form.get("email") or "").strip().lower()
        password = request.form.get("password") or ""
        school = (request.form.get("school_name") or "").strip()
        plan = (request.form.get("plan") or "starter").strip()

        if plan not in PLAN_FEATURES or plan == "admin":
            plan = "starter"

        if not email or len(password) < 8 or not school:
            flash("Email, école et mot de passe (≥ 8 caractères) requis.", "warning")
        elif auth_mod.User.by_email(email):
            flash("Un compte existe déjà avec cet email.", "warning")
        else:
            user = auth_mod.User.create(
                email=email,
                password=password,
                school_name=school,
                role="client",
                plan=plan,
                quota_leads=500,
                status="pending",
            )
            if user:
                flash(
                    "Compte créé ! Un administrateur le validera sous 24 h. "
                    "Vous recevrez un email de confirmation.",
                    "success",
                )
                return redirect(url_for("login"))
            flash("Erreur lors de la création du compte.", "error")
    return render_template("auth/signup.html")


@app.route("/logout", methods=["POST", "GET"])
@login_required
def logout():
    auth_mod.log_access(current_user.id, "logout", *_client_meta())
    logout_user()
    flash("Déconnecté.", "info")
    return redirect(url_for("home"))


# ─── Portail entreprise ────────────────────────────────────────────────────────

@app.route("/portal")
@login_required
def portal_home():
    consumed = sum(auth_mod.consumption_summary(current_user.id).values())
    kpis = leads_service.kpis_for_user(current_user.quota_leads, consumed)
    bdata = barometer_service.load_barometer()
    plan = PLAN_FEATURES[current_user.plan]
    last_logs = auth_mod.recent_access_logs(current_user.id, 5)
    return render_template(
        "portal/dashboard.html",
        kpis=kpis,
        bdata=bdata,
        plan=plan,
        last_logs=last_logs,
    )


@app.route("/portal/barometre")
@login_required
def portal_barometre():
    if not _require_plan_access("barometre"):
        return redirect(url_for("portal_home"))
    bdata = barometer_service.load_barometer()
    auth_mod.log_access(current_user.id, "view_barometre", *_client_meta())
    return render_template("portal/barometre.html", bdata=bdata)


@app.route("/portal/leads")
@login_required
def portal_leads():
    if not _require_plan_access("leads"):
        return redirect(url_for("portal_home"))

    refs = leads_service.reference_values()
    region = request.args.get("region", "all")
    level = request.args.get("level", "all")
    domain = request.args.get("domain", "all")
    lead_class = request.args.get("lead_class", "all")
    score_min = request.args.get("score_min", 0)
    page = int(request.args.get("page", 1))

    df = leads_service.filter_leads(
        region=region, level=level, domain=domain,
        lead_class=lead_class, score_min=score_min, optin_only=True,
    )
    page_df, total, pages = leads_service.paginate(df, page=page, per_page=50)
    counts = leads_service.class_counts(df)

    consumed = sum(auth_mod.consumption_summary(current_user.id).values())
    quota_pct = round(consumed / current_user.quota_leads * 100, 1) if current_user.quota_leads else 0

    return render_template(
        "portal/leads.html",
        rows=page_df.to_dict(orient="records"),
        total=total,
        pages=pages,
        page=page,
        counts=counts,
        refs=refs,
        filters={"region": region, "level": level, "domain": domain,
                 "lead_class": lead_class, "score_min": score_min},
        consumed=consumed,
        quota=current_user.quota_leads,
        quota_pct=min(100, quota_pct),
    )


@app.route("/portal/leads/export.csv")
@login_required
def portal_leads_export():
    if not _require_plan_access("leads"):
        return redirect(url_for("portal_home"))

    df = leads_service.filter_leads(
        region=request.args.get("region", "all"),
        level=request.args.get("level", "all"),
        domain=request.args.get("domain", "all"),
        lead_class=request.args.get("lead_class", "all"),
        score_min=request.args.get("score_min", 0),
        optin_only=True,
    )

    consumed = sum(auth_mod.consumption_summary(current_user.id).values())
    available = max(0, current_user.quota_leads - consumed)
    if len(df) > available:
        df = df.head(available)

    counts = leads_service.class_counts(df)
    if df.empty:
        flash("Aucun lead à exporter (vérifiez vos filtres ou votre quota).", "warning")
        return redirect(url_for("portal_leads"))

    auth_mod.record_export(current_user.id, {k: int(v) for k, v in counts.items()})
    auth_mod.log_access(
        current_user.id,
        f"export_csv ({len(df)} leads)",
        *_client_meta(),
    )

    payload = leads_service.to_export_csv(df)
    filename = f"letudiant_leads_{datetime.now():%Y%m%d_%H%M}.csv"
    return send_file(
        BytesIO(payload),
        mimetype="text/csv; charset=utf-8",
        as_attachment=True,
        download_name=filename,
    )


@app.route("/portal/billing")
@login_required
def portal_billing():
    summary = auth_mod.consumption_summary(current_user.id)
    consumed = sum(summary.values())
    history = auth_mod.consumption_history(current_user.id, 30)
    plan = PLAN_FEATURES[current_user.plan]
    return render_template(
        "portal/billing.html",
        plan=plan,
        summary=summary,
        consumed=consumed,
        quota=current_user.quota_leads,
        quota_pct=min(100, round(consumed / current_user.quota_leads * 100, 1)) if current_user.quota_leads else 0,
        history=history,
    )


@app.route("/portal/compliance")
@login_required
def portal_compliance():
    logs = auth_mod.recent_access_logs(current_user.id, 30)
    return render_template("portal/compliance.html", logs=logs)


@app.route("/portal/profile", methods=["GET", "POST"])
@login_required
def portal_profile():
    if request.method == "POST":
        action = request.form.get("action")
        if action == "profile":
            school = (request.form.get("school_name") or "").strip()
            if school:
                current_user.update_profile(school)
                flash("Profil mis à jour.", "success")
        elif action == "password":
            old = request.form.get("old_password") or ""
            new = request.form.get("new_password") or ""
            if not auth_mod.verify_password(old, current_user.password_hash):
                flash("Ancien mot de passe incorrect.", "error")
            elif len(new) < 8:
                flash("Nouveau mot de passe trop court (min. 8 caractères).", "warning")
            else:
                current_user.update_password(new)
                auth_mod.log_access(current_user.id, "password_changed", *_client_meta())
                flash("Mot de passe modifié.", "success")
        return redirect(url_for("portal_profile"))
    return render_template("portal/profile.html")


# ─── Endpoints utilitaires ─────────────────────────────────────────────────────

@app.route("/data/barometer.json")
def data_barometer():
    """Sert les données baromètre au front (pour Chart.js dans les portails authentifiés)."""
    return jsonify(barometer_service.load_barometer())


@app.errorhandler(404)
def err_404(e):
    return render_template("public/404.html"), 404


if __name__ == "__main__":
    if not Path(auth_mod.DB_PATH).exists():
        print("⚠️  app.db absent — lancez d'abord  python seed.py")
    app.run(host="0.0.0.0", port=5050, debug=True)
