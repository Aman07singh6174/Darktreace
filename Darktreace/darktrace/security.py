from datetime import timedelta

from flask import current_app
from .extensions import db
from .models import AdminAction, AdminAccount, MonitoredUser, SecurityAlert, SecurityLog, utc_now


EVENT_POINTS = {
    "failed_login": 12,
    "unusual_login_frequency": 24,
    "rapid_repeated_action": 22,
    "restricted_page_attempt": 18,
    "suspicious_session": 28,
    "suspicious_post": 20,
    "temporary_block": 0,
    "account_unblocked": 0,
    "successful_login": 0,
    "admin_action": 0,
}
SUSPICIOUS_TERMS = (
    "training credential exposure", "synthetic sign-in anomaly", "mock access token exposure",
    "fictional session misuse", "training data exposure", "simulated malware marker",
    "mock account takeover",
)


def classify_risk(score):
    score = max(0, min(100, int(score or 0)))
    if score < 30:
        return "Low"
    if score < 60:
        return "Medium"
    if score < 80:
        return "High"
    return "Critical"


def score_text(text):
    normalized = text.casefold()
    matches = [term for term in SUSPICIOUS_TERMS if term in normalized]
    return min(95, len(matches) * 30), matches


def create_alert(title, severity, message, user=None):
    alert = SecurityAlert(
        user_id=user.id if user else None,
        title=title[:160],
        severity=severity.lower(),
        message=message[:800],
    )
    db.session.add(alert)
    return alert


def apply_temporary_block(account, minutes=None, reason="Risk threshold crossed"):
    duration = minutes or current_app.config["TEMP_BLOCK_MINUTES"]
    now = utc_now()
    account.blocked_at = now
    account.blocked_until = now + timedelta(minutes=duration)
    account.session_version += 1
    if isinstance(account, MonitoredUser):
        account.status = "Blocked"
    db.session.add(account)
    if isinstance(account, MonitoredUser):
        db.session.add(SecurityLog(
            user_id=account.id,
            event_type="temporary_block",
            details=f"Temporary application block applied: {reason} ({duration} minutes).",
            source_ip="127.0.0.1",
            risk_points=0,
            risk_level=account.risk_level,
        ))
    return account.blocked_until


def record_security_event(event_type, details, source_ip, user=None, points=None, create_risk_alert=True):
    points = EVENT_POINTS.get(event_type, 8) if points is None else max(0, min(100, int(points)))
    current_score = 0
    if user is not None:
        previous_score = user.risk_score
        user.risk_score = min(100, user.risk_score + points)
        user.risk_level = classify_risk(user.risk_score)
        current_score = user.risk_score
        if user.risk_score >= current_app.config["RISK_THRESHOLD"] and points > 0 and not user.blocked_until:
            user.status = "Suspicious"
        db.session.add(user)
    event = SecurityLog(
        user_id=user.id if user else None,
        event_type=event_type[:80],
        details=details[:800],
        source_ip=source_ip[:45],
        risk_points=points,
        risk_level=classify_risk(current_score if user else points),
    )
    db.session.add(event)
    if user is not None and event_type in {"community_post", "suspicious_post", "successful_login", "failed_login"}:
        cutoff = utc_now() - timedelta(seconds=60)
        repeated = SecurityLog.query.filter(
            SecurityLog.user_id == user.id,
            SecurityLog.event_type == event_type,
            SecurityLog.created_at >= cutoff,
        ).count()
        if repeated >= 4:
            record_security_event(
                "rapid_repeated_action",
                f"Four or more {event_type.replace('_', ' ')} events occurred within one minute.",
                source_ip,
                user=user,
                points=EVENT_POINTS["rapid_repeated_action"],
                create_risk_alert=create_risk_alert,
            )
    crossed_threshold = user is not None and points > 0 and previous_score < current_app.config["RISK_THRESHOLD"] <= user.risk_score
    if crossed_threshold and not user.blocked_until and not user.is_suspended:
        expiry = apply_temporary_block(user, reason="Configurable risk threshold crossed")
        if create_risk_alert:
            create_alert(
                "Automatic temporary block applied",
                user.risk_level,
                f"{user.display_name} crossed the configured risk threshold; the demo account is blocked until {expiry:%H:%M UTC}.",
                user,
            )
    elif user is not None and points > 0 and user.risk_score >= 30 and create_risk_alert:
        create_alert(
            "Suspicious activity detected",
            user.risk_level,
            f"{user.display_name}: {details[:500]}",
            user,
        )
    return event


def log_admin_action(action, details, target_user=None):
    audit = AdminAction(
        action=action[:80],
        target_user_id=target_user.id if target_user else None,
        details=details[:800],
    )
    db.session.add(audit)
    if target_user:
        record_security_event("admin_action", f"Admin action: {details}", "127.0.0.1", target_user, points=0, create_risk_alert=False)
    return audit


def refresh_expired_blocks():
    now = utc_now()
    monitored = MonitoredUser.query.filter(MonitoredUser.blocked_until.isnot(None), MonitoredUser.blocked_until <= now).all()
    for user in monitored:
        user.blocked_at = None
        user.blocked_until = None
        user.status = "Suspicious" if user.risk_score >= current_app.config["RISK_THRESHOLD"] else "Active"
        user.session_version += 1
        db.session.add(user)
        db.session.add(SecurityLog(
            user_id=user.id,
            event_type="account_unblocked",
            details="Temporary demo block expired automatically.",
            source_ip="127.0.0.1",
            risk_points=0,
            risk_level=user.risk_level,
        ))
    admin = db.session.get(AdminAccount, 1)
    admin_expired = bool(admin and admin.blocked_until and admin.blocked_until <= now)
    if admin_expired:
        admin.blocked_at = None
        admin.blocked_until = None
        admin.session_version += 1
        db.session.add(admin)
        db.session.add(SecurityLog(
            event_type="admin_block_expired",
            details="Temporary administrator sign-in block expired automatically.",
            source_ip="127.0.0.1",
            risk_points=0,
            risk_level="Low",
        ))
    if monitored or admin_expired:
        db.session.commit()


def remaining_seconds(until):
    if not until:
        return 0
    return max(0, int((until - utc_now()).total_seconds()))