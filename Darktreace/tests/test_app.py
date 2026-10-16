import os
import tempfile
import unittest
from datetime import timedelta

from darktrace import create_app
from darktrace.extensions import db
from darktrace.models import (
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
from darktrace.seed import seed_demo_data
from darktrace.security import record_security_event, score_text


class DarkTraceAdminTests(unittest.TestCase):
    def setUp(self):
        handle, self.database_path = tempfile.mkstemp(suffix=".sqlite3")
        os.close(handle)
        self.app = create_app({
            "TESTING": True,
            "SECRET_KEY": "isolated-test-secret",
            "SQLALCHEMY_DATABASE_URI": f"sqlite:///{self.database_path}",
            "ADMIN_USERNAME": "root",
            "ADMIN_PASSWORD": "root",
            "FAILED_LOGIN_LIMIT": 5,
            "RISK_THRESHOLD": 60,
            "TEMP_BLOCK_MINUTES": 15,
            "SEED_DEMO_ON_START": True,
        })
        self.client = self.app.test_client()

    def tearDown(self):
        with self.app.app_context():
            db.session.remove()
            db.engine.dispose()
        os.unlink(self.database_path)

    def token(self):
        self.client.get("/login")
        with self.client.session_transaction() as session:
            return session["csrf_token"]

    def login(self, username="root", password="root"):
        return self.client.post("/login", data={
            "csrf_token": self.token(),
            "username": username,
            "password": password,
        }, follow_redirects=True)

    def test_login_page_shows_no_password_or_other_accounts(self):
        response = self.client.get("/login")
        self.assertEqual(response.status_code, 200)
        self.assertNotIn(b"Admin@123", response.data)
        self.assertNotIn(b"Demo@123", response.data)
        self.assertNotIn(b"analyst", response.data)
        self.assertNotIn(b"DEMO ACCESS", response.data)

    def test_seed_generator_creates_expected_fictional_volumes(self):
        with self.app.app_context():
            self.assertEqual(AdminAccount.query.count(), 1)
            self.assertEqual(MonitoredUser.query.count(), 24)
            self.assertEqual(Community.query.count(), 10)
            self.assertEqual(CommunityPost.query.count(), 50)
            self.assertEqual(ThreatReport.query.count(), 24)
            self.assertEqual(SecurityLog.query.count(), 85)
            self.assertEqual(LoginAttempt.query.count(), 60)
            self.assertEqual(SecurityAlert.query.count(), 20)
            self.assertEqual(AdminAction.query.count(), 14)
            self.assertFalse(seed_demo_data())

    def test_only_admin_can_access_dashboard_and_admin_pages(self):
        response = self.client.get("/dashboard")
        self.assertEqual(response.status_code, 302)
        self.login()
        for path in ("/dashboard", "/users", "/alerts", "/reports", "/communities", "/logs", "/suspicious", "/graph", "/api/overview", "/api/graph"):
            with self.subTest(path=path):
                self.assertEqual(self.client.get(path).status_code, 200)
        graph = self.client.get("/api/graph").json
        self.assertEqual({node["kind"] for node in graph["nodes"]}, {"user", "community", "post", "report"})
        with self.client.session_transaction() as session:
            session.clear()
            session["user_id"] = 3
            session["session_version"] = 0
        self.assertEqual(self.client.get("/dashboard").status_code, 302)

    def test_login_hash_and_session_logout(self):
        with self.app.app_context():
            admin = db.session.get(AdminAccount, 1)
            self.assertNotEqual(admin.password_hash, "root")
        self.assertEqual(self.login().status_code, 200)
        response = self.client.post("/logout", data={"csrf_token": self.token()}, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.client.get("/dashboard").status_code, 302)

    def test_repeated_failed_admin_signins_apply_temporary_block(self):
        started = utc_now()
        for _ in range(5):
            self.client.post("/login", data={"csrf_token": self.token(), "username": "root", "password": "incorrect"})
        with self.app.app_context():
            admin = db.session.get(AdminAccount, 1)
            self.assertGreater(admin.blocked_until, utc_now())
            recent_failures = LoginAttempt.query.filter_by(username="root", succeeded=False).filter(LoginAttempt.attempted_at >= started).count()
            self.assertEqual(recent_failures, 5)
            self.assertGreater(SecurityAlert.query.filter_by(severity="critical").count(), 0)

    def test_risk_threshold_applies_block_and_alert(self):
        with self.app.app_context():
            user = MonitoredUser.query.first()
            user.risk_score = 50
            user.risk_level = "Medium"
            db.session.commit()
            record_security_event("suspicious_session", "Synthetic session deviation.", "192.0.2.88", user=user, points=12)
            db.session.commit()
            self.assertEqual(user.risk_score, 62)
            self.assertEqual(user.status, "Blocked")
            self.assertGreater(user.blocked_until, utc_now())
            self.assertTrue(SecurityAlert.query.filter_by(user_id=user.id, title="Automatic temporary block applied").first())

    def test_only_fictional_training_phrases_drive_text_score(self):
        score, matches = score_text("Training credential exposure and mock access token exposure in a fictional lab.")
        self.assertEqual(score, 60)
        self.assertEqual(len(matches), 2)

    def test_manual_unblock_is_audited_without_immediate_reblock(self):
        self.login()
        with self.app.app_context():
            user = MonitoredUser.query.first()
            user.risk_score = 80
            user.risk_level = "Critical"
            user.blocked_at = utc_now() - timedelta(minutes=1)
            user.blocked_until = utc_now() + timedelta(minutes=10)
            db.session.commit()
            user_id = user.id
        response = self.client.post(f"/users/{user_id}/action", data={"csrf_token": self.token(), "action": "unblock"})
        self.assertEqual(response.status_code, 302)
        with self.app.app_context():
            user = db.session.get(MonitoredUser, user_id)
            self.assertIsNone(user.blocked_until)
            self.assertEqual(user.status, "Suspicious")
            self.assertTrue(AdminAction.query.filter_by(action="unblock", target_user_id=user_id).first())

    def test_expired_temporary_block_restores_identity_and_records_event(self):
        self.login()
        with self.app.app_context():
            user = MonitoredUser.query.first()
            user.blocked_at = utc_now() - timedelta(minutes=20)
            user.blocked_until = utc_now() - timedelta(minutes=5)
            user.status = "Blocked"
            db.session.commit()
            user_id = user.id
        self.assertEqual(self.client.get("/dashboard").status_code, 200)
        with self.app.app_context():
            user = db.session.get(MonitoredUser, user_id)
            self.assertIsNone(user.blocked_until)
            self.assertIn(user.status, {"Active", "Suspicious"})
            self.assertTrue(SecurityLog.query.filter_by(user_id=user_id, event_type="account_unblocked").first())

    def test_report_status_and_suspension_controls_are_audited(self):
        self.login()
        with self.app.app_context():
            report_id = ThreatReport.query.first().id
            user_id = MonitoredUser.query.first().id
        report_response = self.client.post(f"/reports/{report_id}/status", data={"csrf_token": self.token(), "status": "Investigating"})
        self.assertEqual(report_response.status_code, 302)
        suspend_response = self.client.post(f"/users/{user_id}/action", data={"csrf_token": self.token(), "action": "suspend"})
        self.assertEqual(suspend_response.status_code, 302)
        with self.app.app_context():
            self.assertEqual(db.session.get(ThreatReport, report_id).status, "Investigating")
            self.assertTrue(db.session.get(MonitoredUser, user_id).is_suspended)
            self.assertTrue(AdminAction.query.filter_by(action="suspend", target_user_id=user_id).first())

    def test_bad_csrf_and_unknown_route_have_friendly_errors(self):
        bad_form = self.client.post("/login", data={"csrf_token": "bad"})
        missing = self.client.get("/not-a-route")
        self.assertEqual(bad_form.status_code, 400)
        self.assertEqual(missing.status_code, 404)


if __name__ == "__main__":
    unittest.main()