import secrets
from datetime import timedelta
from functools import wraps

from flask import Blueprint, abort, current_app, flash, g, jsonify, redirect, render_template, request, session, url_for
from sqlalchemy import func
from werkzeug.security import check_password_hash

from .extensions import db
from .models import (
    AdminAccount,
    AdminAction,
    Community,
    CommunityPost,
    LoginAttempt,
    MonitoredUser,
    SecurityAlert,
    SecurityLog,
    ThreatReport,
    utc_now,
)
from .security import (
    apply_temporary_block,
    classify_risk,
    create_alert,
    log_admin_action,
    record_security_event,
    refresh_expired_blocks,
    remaining_seconds,
    score_text,
)


bp = Blueprint("main", __name__)
RESTRICTED_ENDPOINTS = {"main.dashboard", "main.users", "main.user_detail", "main.alerts", "main.communities", "main.reports", "main.graph", "main.security_logs", "main.suspicious"}


def csrf_token():
    if "csrf_token" not in session:
        session["csrf_token"] = secrets.token_hex(32)
    return session["csrf_token"]


def pretty_time(value):
    if not value:
        return "Never"
    return value.strftime("%b %d, %H:%M UTC")


def current_admin():
    return getattr(g, "admin", None)


def _client_ip():
    return request.remote_addr or "127.0.0.1"


def _check_csrf():
    submitted = request.form.get("csrf_token", "")
    expected = session.get("csrf_token", "")
    if not expected or not secrets.compare_digest(submitted, expected):
        abort(400)


def _log_restricted_attempt():
    endpoint = request.endpoint
    if endpoint not in RESTRICTED_ENDPOINTS or current_admin():
        return
    log = record_security_event(
        "restricted_page_attempt",
        f"Unauthenticated request to restricted route {request.path}.",
        _client_ip(),
        points=18,
        create_risk_alert=False,
    )
    del log
    window_start = utc_now() - timedelta(minutes=current_app.config["FAILED_LOGIN_WINDOW_MINUTES"])
    attempts = SecurityLog.query.filter(
        SecurityLog.event_type == "restricted_page_attempt",
        SecurityLog.source_ip == _client_ip(),
        SecurityLog.created_at >= window_start,
    ).count()
    if attempts == 3 or attempts % 5 == 0:
        create_alert("Repeated restricted-page access", "high", f"{attempts} unauthenticated requests to protected views from {_client_ip()}.")
    db.session.commit()


@bp.before_app_request
def load_admin():
    g.admin = None
    refresh_expired_blocks()
    if session.get("admin_id") != 1:
        _log_restricted_attempt()
        return
    admin = db.session.get(AdminAccount, 1)
    if admin is None or not admin.is_active or admin.is_suspended:
        session.clear()
        flash("Administrator access is suspended. Contact the local database administrator.", "danger")
        return
    if admin.blocked_until and admin.blocked_until > utc_now():
        session.clear()
        flash(f"Administrator sign-in is temporarily blocked until {pretty_time(admin.blocked_until)}.", "danger")
        return
    if session.get("session_version") != admin.session_version:
        session.clear()
        flash("This administrator session was ended. Please sign in again.", "warning")
        return
    g.admin = admin


def admin_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if current_admin() is None:
            flash("Administrator sign-in is required.", "warning")
            return redirect(url_for("main.login"))
        return view(*args, **kwargs)
    return wrapped


def _record_login(username, succeeded):
    attempt = LoginAttempt(username=username[:80], succeeded=succeeded, source_ip=_client_ip())
    db.session.add(attempt)
    target = MonitoredUser.query.filter_by(username=username[:80]).first()
    detail = "Successful administrator sign-in." if succeeded else "Unsuccessful sign-in attempt for the configured administrator."
    record_security_event("successful_login" if succeeded else "failed_login", detail, _client_ip(), user=target, points=0 if succeeded else 12)
    return attempt


@bp.route("/")
def index():
    return redirect(url_for("main.dashboard" if current_admin() else "main.login"))


@bp.route("/login", methods=["GET", "POST"])
def login():
    if current_admin():
        return redirect(url_for("main.dashboard"))
    admin = db.session.get(AdminAccount, 1)
    if request.method == "POST":
        _check_csrf()
        username = request.form.get("username", "").strip().lower()
        password = request.form.get("password", "")
        if admin and (not admin.is_active or admin.is_suspended):
            flash("Administrator account is suspended or inactive. Access is not available.", "danger")
            return render_template("login.html"), 403
        if admin and admin.blocked_until and admin.blocked_until > utc_now():
            flash(f"Administrator sign-in is temporarily blocked until {pretty_time(admin.blocked_until)}.", "danger")
            return render_template("login.html"), 423
        valid = bool(admin and username == admin.username and admin.is_active and not admin.is_suspended and check_password_hash(admin.password_hash, password))
        _record_login(username or "blank", valid)
        if not valid:
            start = utc_now() - timedelta(minutes=current_app.config["FAILED_LOGIN_WINDOW_MINUTES"])
            failures = LoginAttempt.query.filter_by(username=username or "blank", succeeded=False).filter(LoginAttempt.attempted_at >= start).count()
            if failures >= current_app.config["FAILED_LOGIN_LIMIT"] and admin and not admin.is_suspended:
                until = apply_temporary_block(admin, reason="Repeated failed administrator sign-ins")
                create_alert("Administrator sign-in temporarily blocked", "critical", f"Repeated failed sign-ins from {_client_ip()}; access restores at {pretty_time(until)}.")
                db.session.add(SecurityLog(event_type="admin_temporary_block", details="Admin account temporarily blocked after repeated failed sign-ins.", source_ip=_client_ip(), risk_points=0, risk_level="Critical"))
                db.session.commit()
                flash(f"Too many failed sign-ins. Access is paused until {pretty_time(until)}.", "danger")
                return render_template("login.html"), 423
            db.session.commit()
            flash("Administrator username or password was not accepted.", "danger")
            return render_template("login.html"), 401
        session.clear()
        session.permanent = True
        session["admin_id"] = 1
        session["session_version"] = admin.session_version
        session["csrf_token"] = secrets.token_hex(32)
        admin.last_login = utc_now()
        db.session.add(admin)
        start = utc_now() - timedelta(minutes=10)
        recent_successes = LoginAttempt.query.filter_by(source_ip=_client_ip(), succeeded=True).filter(LoginAttempt.attempted_at >= start).count()
        if recent_successes >= 7:
            record_security_event("unusual_login_frequency", "Unusually frequent successful local demo sign-ins.", _client_ip(), points=24, create_risk_alert=False)
            create_alert("Unusual administrator login frequency", "high", f"{recent_successes} successful demo sign-ins from {_client_ip()} in ten minutes.")
        db.session.commit()
        return redirect(url_for("main.dashboard"))
    return render_template("login.html")


@bp.post("/logout")
@admin_required
def logout():
    _check_csrf()
    log_admin_action("logout", "Administrator signed out.")
    db.session.commit()
    session.clear()
    flash("You have signed out.", "success")
    return redirect(url_for("main.login"))


@bp.route("/dashboard")
@admin_required
def dashboard():
    now = utc_now()
    threshold = current_app.config["RISK_THRESHOLD"]
    recent_alerts = SecurityAlert.query.order_by(SecurityAlert.created_at.desc()).limit(8).all()
    recent_logins = LoginAttempt.query.order_by(LoginAttempt.attempted_at.desc()).limit(10).all()
    suspicious_users = MonitoredUser.query.filter(MonitoredUser.risk_score >= threshold).order_by(MonitoredUser.risk_score.desc()).limit(10).all()
    blocked_users = MonitoredUser.query.filter(MonitoredUser.blocked_until.isnot(None), MonitoredUser.blocked_until > now).order_by(MonitoredUser.blocked_until).all()
    recent_actions = AdminAction.query.order_by(AdminAction.created_at.desc()).limit(8).all()
    metrics = {
        "total_users": MonitoredUser.query.count(),
        "active_users": MonitoredUser.query.filter_by(is_active=True, is_suspended=False).filter((MonitoredUser.blocked_until.is_(None)) | (MonitoredUser.blocked_until <= now)).count(),
        "suspicious_users": MonitoredUser.query.filter(MonitoredUser.risk_score >= threshold).count(),
        "blocked_users": MonitoredUser.query.filter(MonitoredUser.blocked_until.isnot(None), MonitoredUser.blocked_until > now).count(),
        "total_alerts": SecurityAlert.query.count(),
        "high_critical": SecurityLog.query.filter(SecurityLog.risk_level.in_(("High", "Critical"))).count(),
        "communities": Community.query.count(),
        "reports": ThreatReport.query.count(),
    }
    return render_template("dashboard.html", metrics=metrics, alerts=recent_alerts, logins=recent_logins, suspicious_users=suspicious_users, blocked_users=blocked_users, admin_actions=recent_actions)


@bp.get("/api/overview")
@admin_required
def overview_data():
    start = utc_now() - timedelta(days=6)
    activity_rows = db.session.query(func.date(SecurityLog.created_at), func.count(SecurityLog.id)).filter(SecurityLog.created_at >= start).group_by(func.date(SecurityLog.created_at)).all()
    activity = [{"day": str(day), "count": count} for day, count in activity_rows]
    severity = [{"severity": level, "count": SecurityAlert.query.filter_by(severity=level.lower()).count()} for level in ("Low", "Medium", "High", "Critical")]
    risk_distribution = [{"level": level, "count": MonitoredUser.query.filter_by(risk_level=level).count()} for level in ("Low", "Medium", "High", "Critical")]
    top_users = MonitoredUser.query.order_by(MonitoredUser.risk_score.desc()).limit(8).all()
    threat_types = [row[0] for row in db.session.query(ThreatReport.threat_type).distinct().all()]
    threat_distribution = [{"type": kind, "count": ThreatReport.query.filter_by(threat_type=kind).count()} for kind in threat_types]
    return jsonify({"activity": activity, "severity": severity, "risk": risk_distribution, "users": [{"name": user.display_name, "score": user.risk_score} for user in top_users], "threats": threat_distribution})


@bp.route("/users")
@admin_required
def users():
    people = MonitoredUser.query.order_by(MonitoredUser.risk_score.desc(), MonitoredUser.display_name).all()
    now = utc_now()
    return render_template("users.html", users=people, now=now, threshold=current_app.config["RISK_THRESHOLD"])


@bp.route("/users/<int:user_id>")
@admin_required
def user_detail(user_id):
    user = db.get_or_404(MonitoredUser, user_id)
    logs = SecurityLog.query.filter_by(user_id=user.id).order_by(SecurityLog.created_at.desc()).limit(25).all()
    reports = ThreatReport.query.filter_by(related_user_id=user.id).order_by(ThreatReport.detected_at.desc()).limit(12).all()
    log_admin_action("view_user", f"Viewed monitored identity {user.username}.", user)
    db.session.commit()
    return render_template("user_detail.html", user=user, logs=logs, reports=reports, remaining=remaining_seconds(user.blocked_until))


@bp.post("/users/<int:user_id>/action")
@admin_required
def user_action(user_id):
    _check_csrf()
    user = db.get_or_404(MonitoredUser, user_id)
    action = request.form.get("action", "")
    if action == "force_logout":
        user.session_version += 1
        log_admin_action(action, f"Forced logout for {user.display_name}; session generation incremented.", user)
    elif action == "temporary_block":
        until = apply_temporary_block(user, reason="Administrator action")
        create_alert("Administrator applied temporary block", "high", f"{user.display_name} is blocked until {pretty_time(until)}.", user)
        log_admin_action(action, f"Temporary account block through {pretty_time(until)}.", user)
    elif action == "unblock":
        user.blocked_at = None
        user.blocked_until = None
        user.session_version += 1
        user.status = "Suspicious" if user.risk_score >= current_app.config["RISK_THRESHOLD"] else "Active"
        record_security_event("account_unblocked", "Administrator manually unblocked this fictional monitored account.", _client_ip(), user=user, points=0, create_risk_alert=False)
        log_admin_action(action, "Manually removed temporary block.", user)
    elif action == "suspend":
        user.is_suspended = True
        user.is_active = False
        user.status = "Suspended"
        user.session_version += 1
        user.blocked_at = None
        user.blocked_until = None
        log_admin_action(action, "Suspended fictional monitored identity.", user)
    elif action == "activate":
        user.is_suspended = False
        user.is_active = True
        user.status = "Suspicious" if user.risk_score >= current_app.config["RISK_THRESHOLD"] else "Active"
        user.session_version += 1
        log_admin_action(action, "Activated fictional monitored identity.", user)
    else:
        abort(400)
    db.session.commit()
    flash(f"{action.replace('_', ' ').title()} recorded for {user.display_name}.", "success")
    return redirect(url_for("main.user_detail", user_id=user.id))


@bp.route("/communities", methods=["GET", "POST"])
@admin_required
def communities():
    if request.method == "POST":
        _check_csrf()
        content = request.form.get("content", "").strip()
        user_id = request.form.get("user_id", type=int)
        community_id = request.form.get("community_id", type=int)
        user = db.session.get(MonitoredUser, user_id) if user_id else None
        community = db.session.get(Community, community_id) if community_id else None
        if not user or not community or not content or len(content) > 1000:
            flash("Choose a demo user and community, and enter a note under 1,000 characters.", "danger")
            return redirect(url_for("main.communities"))
        score, matches = score_text(content)
        post = CommunityPost(community_id=community.id, user_id=user.id, content=content, risk_score=score)
        db.session.add(post)
        record_security_event("suspicious_post" if score else "community_post", f"Simulated community note in {community.name}; matched: {', '.join(matches) if matches else 'no configured indicators'}.", _client_ip(), user=user, points=score if score else 2)
        if matches:
            create_alert("Simulated community indicator match", classify_risk(score), f"Fictional post by {user.display_name} matched configured training indicators: {', '.join(matches)}.", user)
        log_admin_action("create_demo_post", f"Added a fictional post for {user.username} in {community.name}.", user)
        db.session.commit()
        flash("Fictional community activity was added and evaluated.", "success")
        return redirect(url_for("main.communities"))
    rooms = Community.query.order_by(Community.name).all()
    people = MonitoredUser.query.filter_by(is_active=True).order_by(MonitoredUser.display_name).all()
    posts = CommunityPost.query.order_by(CommunityPost.created_at.desc()).limit(40).all()
    return render_template("communities.html", communities=rooms, users=people, posts=posts)


@bp.route("/reports", methods=["GET", "POST"])
@admin_required
def reports():
    if request.method == "POST":
        _check_csrf()
        title = request.form.get("title", "").strip()
        description = request.form.get("description", "").strip()
        threat_type = request.form.get("threat_type", "").strip()
        risk_level = request.form.get("risk_level", "Medium")
        source_type = request.form.get("source_type", "Training simulation")
        user_id = request.form.get("related_user_id", type=int)
        if not title or len(title) > 100 or not description or len(description) > 1200 or risk_level not in {"Low", "Medium", "High", "Critical"}:
            flash("Complete the report fields using the allowed lengths and risk levels.", "danger")
            return redirect(url_for("main.reports"))
        latest = ThreatReport.query.order_by(ThreatReport.id.desc()).first()
        serial = latest.id + 1 if latest else 1
        report = ThreatReport(threat_id=f"DT-{utc_now().year}-{serial:04d}", threat_type=threat_type[:100] or title[:100], risk_level=risk_level, source_type=source_type[:80], description=description, related_user_id=user_id, status="Open", analyst_status="Needs review")
        db.session.add(report)
        db.session.flush()
        if risk_level in {"High", "Critical"}:
            create_alert("High-severity fictional report", risk_level, f"{report.threat_id}: {title}")
        log_admin_action("create_threat_report", f"Created fictional threat report {report.threat_id}.", db.session.get(MonitoredUser, user_id) if user_id else None)
        db.session.commit()
        flash("Fictional report added to the analyst register.", "success")
        return redirect(url_for("main.reports"))
    items = ThreatReport.query.order_by(ThreatReport.detected_at.desc()).all()
    people = MonitoredUser.query.order_by(MonitoredUser.username).all()
    return render_template("reports.html", reports=items, users=people)


@bp.post("/reports/<int:report_id>/status")
@admin_required
def report_status(report_id):
    _check_csrf()
    report = db.get_or_404(ThreatReport, report_id)
    status = request.form.get("status", "")
    if status not in {"Open", "Investigating", "Contained", "Closed"}:
        abort(400)
    report.status = status
    report.analyst_status = status
    log_admin_action("update_report", f"Updated {report.threat_id} to {status}.", report.related_user)
    db.session.commit()
    flash(f"{report.threat_id} updated to {status}.", "success")
    return redirect(url_for("main.reports"))


@bp.route("/alerts")
@admin_required
def alerts():
    items = SecurityAlert.query.order_by(SecurityAlert.created_at.desc()).limit(200).all()
    return render_template("alerts.html", alerts=items)


@bp.post("/alerts/<int:alert_id>/acknowledge")
@admin_required
def acknowledge_alert(alert_id):
    _check_csrf()
    alert = db.get_or_404(SecurityAlert, alert_id)
    alert.acknowledged = True
    log_admin_action("acknowledge_alert", f"Acknowledged alert {alert.id}.", alert.user)
    db.session.commit()
    flash("Alert acknowledged.", "success")
    return redirect(url_for("main.alerts"))


@bp.route("/logs")
@admin_required
def security_logs():
    logs = SecurityLog.query.order_by(SecurityLog.created_at.desc()).limit(250).all()
    log_admin_action("view_security_logs", "Opened security event log review.")
    db.session.commit()
    return render_template("logs.html", logs=logs)


@bp.route("/suspicious")
@admin_required
def suspicious():
    users = MonitoredUser.query.filter(MonitoredUser.risk_score >= current_app.config["RISK_THRESHOLD"]).order_by(MonitoredUser.risk_score.desc()).all()
    return render_template("suspicious.html", users=users)


@bp.route("/graph")
@admin_required
def graph():
    return render_template("graph.html")


@bp.get("/api/graph")
@admin_required
def graph_data():
    nodes, edges = _build_graph_data()
    return jsonify({"nodes": nodes, "edges": edges})


def _build_graph_data():
    users = MonitoredUser.query.order_by(MonitoredUser.risk_score.desc()).limit(24).all()
    communities = Community.query.order_by(Community.name).all()
    posts = CommunityPost.query.order_by(CommunityPost.created_at.desc()).limit(16).all()
    reports = ThreatReport.query.order_by(ThreatReport.detected_at.desc()).limit(12).all()
    nodes = []
    edges = []
    included_users = {user.id for user in users}
    for user in users:
        nodes.append({"id": f"u{user.id}", "label": user.display_name, "kind": "user", "risk": user.risk_level})
    for community in communities:
        nodes.append({"id": f"c{community.id}", "label": community.name, "kind": "community", "risk": "Low"})
    for post in posts:
        nodes.append({"id": f"p{post.id}", "label": f"Post {post.id}", "kind": "post", "risk": classify_risk(post.risk_score)})
        edges.extend(({"from": f"p{post.id}", "to": f"u{post.user_id}"}, {"from": f"p{post.id}", "to": f"c{post.community_id}"}))
    for report in reports:
        nodes.append({"id": f"r{report.id}", "label": report.threat_id, "kind": "report", "risk": report.risk_level})
        if report.related_user_id in included_users:
            edges.append({"from": f"r{report.id}", "to": f"u{report.related_user_id}"})
    return nodes, edges


@bp.app_errorhandler(404)
def not_found(_error):
    return render_template("error.html", code=404, message="That record or page is not available."), 404


@bp.errorhandler(400)
def bad_request(_error):
    return render_template("error.html", code=400, message="The request could not be processed. Refresh the page and check the submitted form."), 400


@bp.errorhandler(403)
def forbidden(_error):
    return render_template("error.html", code=403, message="Administrator access is required for this view."), 403


@bp.errorhandler(500)
def internal_error(_error):
    db.session.rollback()
    return render_template("error.html", code=500, message="An unexpected server error occurred. Your data was not confirmed as saved; return to the app and try again."), 500