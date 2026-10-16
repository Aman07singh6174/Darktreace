from datetime import datetime, timezone

from .extensions import db


def utc_now():
    return datetime.now(timezone.utc).replace(tzinfo=None, microsecond=0)


class AdminAccount(db.Model):
    __tablename__ = "admin_accounts"

    id = db.Column(db.Integer, primary_key=True, autoincrement=False, default=1)
    username = db.Column(db.String(80), nullable=False, unique=True)
    password_hash = db.Column(db.String(255), nullable=False)
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    is_suspended = db.Column(db.Boolean, nullable=False, default=False)
    blocked_at = db.Column(db.DateTime, nullable=True)
    blocked_until = db.Column(db.DateTime, nullable=True)
    session_version = db.Column(db.Integer, nullable=False, default=0)
    last_login = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=utc_now)


class MonitoredUser(db.Model):
    __tablename__ = "monitored_users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), nullable=False, unique=True)
    display_name = db.Column(db.String(120), nullable=False)
    department = db.Column(db.String(80), nullable=False, default="Research")
    status = db.Column(db.String(24), nullable=False, default="Active")
    risk_score = db.Column(db.Integer, nullable=False, default=0)
    risk_level = db.Column(db.String(16), nullable=False, default="Low")
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    is_suspended = db.Column(db.Boolean, nullable=False, default=False)
    blocked_at = db.Column(db.DateTime, nullable=True)
    blocked_until = db.Column(db.DateTime, nullable=True)
    session_version = db.Column(db.Integer, nullable=False, default=0)
    last_seen = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=utc_now)


class Community(db.Model):
    __tablename__ = "communities"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False, unique=True)
    description = db.Column(db.String(500), nullable=False)
    topic = db.Column(db.String(80), nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=utc_now)


class CommunityPost(db.Model):
    __tablename__ = "community_posts"

    id = db.Column(db.Integer, primary_key=True)
    community_id = db.Column(db.Integer, db.ForeignKey("communities.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey("monitored_users.id", ondelete="CASCADE"), nullable=False, index=True)
    content = db.Column(db.String(1000), nullable=False)
    risk_score = db.Column(db.Integer, nullable=False, default=0)
    created_at = db.Column(db.DateTime, nullable=False, default=utc_now, index=True)
    community = db.relationship("Community")
    user = db.relationship("MonitoredUser")


class ThreatReport(db.Model):
    __tablename__ = "threat_reports"

    id = db.Column(db.Integer, primary_key=True)
    threat_id = db.Column(db.String(32), nullable=False, unique=True)
    threat_type = db.Column(db.String(100), nullable=False)
    risk_level = db.Column(db.String(16), nullable=False)
    status = db.Column(db.String(24), nullable=False, default="Open")
    source_type = db.Column(db.String(80), nullable=False)
    detected_at = db.Column(db.DateTime, nullable=False, default=utc_now, index=True)
    description = db.Column(db.String(1200), nullable=False)
    related_user_id = db.Column(db.Integer, db.ForeignKey("monitored_users.id", ondelete="SET NULL"), nullable=True, index=True)
    analyst_status = db.Column(db.String(24), nullable=False, default="Needs review")
    related_user = db.relationship("MonitoredUser")


class SecurityLog(db.Model):
    __tablename__ = "security_logs"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("monitored_users.id", ondelete="SET NULL"), nullable=True, index=True)
    event_type = db.Column(db.String(80), nullable=False, index=True)
    details = db.Column(db.String(800), nullable=False)
    source_ip = db.Column(db.String(45), nullable=False)
    risk_points = db.Column(db.Integer, nullable=False, default=0)
    risk_level = db.Column(db.String(16), nullable=False, default="Low")
    created_at = db.Column(db.DateTime, nullable=False, default=utc_now, index=True)
    user = db.relationship("MonitoredUser")


class SecurityAlert(db.Model):
    __tablename__ = "security_alerts"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("monitored_users.id", ondelete="SET NULL"), nullable=True, index=True)
    title = db.Column(db.String(160), nullable=False)
    severity = db.Column(db.String(16), nullable=False, index=True)
    message = db.Column(db.String(800), nullable=False)
    acknowledged = db.Column(db.Boolean, nullable=False, default=False)
    created_at = db.Column(db.DateTime, nullable=False, default=utc_now, index=True)
    user = db.relationship("MonitoredUser")


class LoginAttempt(db.Model):
    __tablename__ = "login_attempts"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), nullable=False, index=True)
    succeeded = db.Column(db.Boolean, nullable=False, default=False)
    source_ip = db.Column(db.String(45), nullable=False, index=True)
    attempted_at = db.Column(db.DateTime, nullable=False, default=utc_now, index=True)


class AdminAction(db.Model):
    __tablename__ = "admin_actions"

    id = db.Column(db.Integer, primary_key=True)
    action = db.Column(db.String(80), nullable=False)
    target_user_id = db.Column(db.Integer, db.ForeignKey("monitored_users.id", ondelete="SET NULL"), nullable=True, index=True)
    details = db.Column(db.String(800), nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=utc_now, index=True)
    target_user = db.relationship("MonitoredUser")