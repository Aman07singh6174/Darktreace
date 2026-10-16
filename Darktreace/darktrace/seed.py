import random
from datetime import timedelta

from .extensions import db
from .models import (
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


FIRST_NAMES = ("Avery", "Jordan", "Morgan", "Riley", "Taylor", "Casey", "Quinn", "Reese", "Cameron", "Skyler", "Emerson", "Parker", "Rowan", "Drew", "Sage", "Blake", "Jamie", "Kendall", "Finley", "Dakota", "Alex", "Robin", "Arden", "Elliot")
LAST_NAMES = ("Parker", "Morgan", "Brooks", "Reed", "Hayes", "Rivera", "Bell", "Shaw", "Morris", "Lane", "Bennett", "Cole", "Ward", "James", "Ellis", "Young", "Turner", "Wells", "Price", "Gray", "Kelly", "Cruz", "Ross", "Bailey")
DEPARTMENTS = ("Research", "IT Operations", "Student Services", "Data Lab", "Network Team", "Security Lab")
COMMUNITY_DATA = (
    ("Signal Exchange", "Fictional indicator notes from a controlled training environment.", "Indicators"),
    ("Incident Watch", "Tabletop incident observations for analyst practice.", "Incidents"),
    ("Research Commons", "Safe defensive research summaries and lessons.", "Research"),
    ("Campus SOC Lab", "Simulated monitoring observations from a classroom lab.", "Monitoring"),
    ("Identity Desk", "Training scenarios for account security and access review.", "Identity"),
    ("Patch Circle", "Fictional patch status and asset-owner follow-up notes.", "Vulnerability"),
    ("Network Review", "Benign network telemetry scenarios for triage practice.", "Network"),
    ("Blue Team Notes", "Defensive response playbooks and tabletop outcomes.", "Response"),
    ("Audit Exchange", "Mock audit evidence and control observations.", "Governance"),
    ("Service Health", "Synthetic availability and service health observations.", "Availability"),
)
POST_TEXT = (
    "Training exercise: unusual sign-in frequency was reviewed in the fictional tenant.",
    "Synthetic network event correlated with the scheduled classroom test window.",
    "Analyst note: confirm the mock asset owner before closing this practice ticket.",
    "Tabletop observation: repeated test actions were grouped for review.",
    "Simulated identity alert cleared after the test account's recovery step.",
    "Fictional endpoint reported a policy mismatch; no real host was contacted.",
    "Routine lab check: verify the sample service inventory and record the result.",
    "Controlled exercise noted a suspicious session pattern for analyst review.",
    "Mock patch advisory mapped to a training asset with a documented owner.",
    "Practice incident closed after the synthetic signal was verified as expected.",
)
EVENT_TYPES = (
    "successful_login", "failed_login", "unusual_login_frequency", "rapid_repeated_action",
    "restricted_page_attempt", "suspicious_session", "temporary_block", "account_unblocked",
    "report_submitted", "community_post", "admin_force_logout", "account_suspended",
    "account_activated", "seeded_monitoring_event", "risk_threshold_crossed",
)
RISK_LEVELS = ("Low", "Medium", "High", "Critical")
THREAT_TYPES = ("Identity anomaly", "Synthetic network signal", "Mock patch advisory", "Session pattern review", "Training data exposure mention", "Service health deviation", "Repeated test activity", "Access policy mismatch")
SAFE_IPS = tuple([f"192.0.2.{value}" for value in range(10, 80)] + [f"198.51.100.{value}" for value in range(10, 80)] + [f"203.0.113.{value}" for value in range(10, 80)] + [f"10.10.{value // 250}.{value % 250 + 1}" for value in range(1, 90)])


def _past_time(rng, days=14):
    return utc_now() - timedelta(minutes=rng.randint(1, days * 24 * 60))


def seed_demo_data(seed=20261002):
    if MonitoredUser.query.count() >= 20:
        return False
    rng = random.Random(seed)
    now = utc_now()
    users = []
    for index, first in enumerate(FIRST_NAMES):
        score = [4, 17, 28, 33, 46, 53, 61, 68, 74, 82, 91, 12][index % 12]
        status = "Suspicious" if score >= 60 else "Active"
        blocked = index in {7, 16, 21}
        user = MonitoredUser(
            username=f"demo-{index + 1:03d}",
            display_name=f"{first} {LAST_NAMES[index]}",
            department=DEPARTMENTS[index % len(DEPARTMENTS)],
            status=status,
            risk_score=score,
            risk_level=RISK_LEVELS[0 if score < 30 else 1 if score < 60 else 2 if score < 80 else 3],
            is_active=index not in {22},
            is_suspended=index == 22,
            blocked_at=now - timedelta(minutes=3) if blocked else None,
            blocked_until=now + timedelta(minutes=12 + index % 7) if blocked else None,
            last_seen=_past_time(rng, 3),
            created_at=_past_time(rng, 40),
        )
        users.append(user)
    communities = [Community(name=name, description=description, topic=topic, created_at=_past_time(rng, 30)) for name, description, topic in COMMUNITY_DATA]
    db.session.add_all(users + communities)
    db.session.flush()

    for index in range(50):
        user = rng.choice(users)
        community = rng.choice(communities)
        points = rng.choice((0, 5, 12, 18, 24, 32, 45, 62, 78, 88))
        db.session.add(CommunityPost(
            community_id=community.id,
            user_id=user.id,
            content=rng.choice(POST_TEXT),
            risk_score=points,
            created_at=_past_time(rng, 14),
        ))

    for index in range(24):
        score = rng.choice((12, 26, 38, 49, 62, 71, 84, 93))
        level = RISK_LEVELS[0 if score < 30 else 1 if score < 60 else 2 if score < 80 else 3]
        db.session.add(ThreatReport(
            threat_id=f"DT-{now.year}-{index + 1:04d}",
            threat_type=THREAT_TYPES[index % len(THREAT_TYPES)],
            risk_level=level,
            status=rng.choice(("Open", "Investigating", "Contained", "Closed")),
            source_type=rng.choice(("Simulated telemetry", "Training community", "Tabletop exercise", "Synthetic identity monitor")),
            detected_at=_past_time(rng, 21),
            description=f"Fictional classroom scenario {index + 1:02d}: {rng.choice(POST_TEXT)} No real account, system, or external service is involved.",
            related_user_id=rng.choice(users).id,
            analyst_status=rng.choice(("Needs review", "In progress", "Reviewed", "Closed")),
        ))

    for index in range(85):
        event = EVENT_TYPES[index % len(EVENT_TYPES)]
        user = rng.choice(users)
        points = rng.choice((0, 3, 8, 12, 18, 25, 32, 42, 56, 67, 79, 91)) if event not in {"successful_login", "community_post"} else rng.choice((0, 0, 0, 4, 8))
        level = RISK_LEVELS[0 if points < 30 else 1 if points < 60 else 2 if points < 80 else 3]
        db.session.add(SecurityLog(
            user_id=user.id,
            event_type=event,
            details=f"Fictional {event.replace('_', ' ')} observed during a controlled demo scenario.",
            source_ip=rng.choice(SAFE_IPS),
            risk_points=points,
            risk_level=level,
            created_at=_past_time(rng, 10),
        ))

    login_names = [user.username for user in users] + ["root", "unknown-demo"]
    for index in range(60):
        db.session.add(LoginAttempt(
            username=rng.choice(login_names),
            succeeded=index % 4 != 0,
            source_ip=rng.choice(SAFE_IPS),
            attempted_at=_past_time(rng, 10),
        ))

    for index in range(20):
        user = rng.choice(users)
        severity = RISK_LEVELS[index % len(RISK_LEVELS)].lower()
        db.session.add(SecurityAlert(
            user_id=user.id,
            title=rng.choice(("Repeated demo sign-in failures", "Unusual activity frequency", "Simulated session review", "Risk threshold crossed", "Temporary demo block applied")),
            severity=severity,
            message=f"Fictional monitoring alert for {user.username}; verify the related demo event and record an analyst decision.",
            acknowledged=index % 5 == 0,
            created_at=_past_time(rng, 12),
        ))

    for index in range(14):
        user = rng.choice(users)
        db.session.add(AdminAction(
            action=rng.choice(("review_user", "view_activity", "force_logout", "temporary_block", "unblock", "suspend", "activate", "review_report")),
            target_user_id=user.id,
            details=f"Seeded administrative audit record {index + 1:02d} for a fictional account.",
            created_at=_past_time(rng, 9),
        ))

    db.session.commit()
    return True