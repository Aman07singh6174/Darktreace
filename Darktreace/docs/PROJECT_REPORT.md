# DarkTrace Project Report

## Project abstract

DarkTrace is a localhost-only demonstration platform for defensive security monitoring. It models how synthetic activity can be stored, assigned a bounded risk score, surfaced as an Admin alert, and handled with a reversible account-level response. Flask provides the admin-only web application, SQLAlchemy and PyMySQL connect to MySQL, and local Chart.js and Three.js assets visualize activity. All identities, events, communities, posts, IPs, and reports are fictional. The project does not access the real dark web or external threat services.

## Problem statement

Monitoring teams need to correlate activity, prioritize risk, review alerts, and record response decisions. A student project should make that workflow visible without using real users, incidents, criminal content, or external systems. DarkTrace provides a safe local model using generated data and application-only controls.

## Objectives

- Implement one configurable Admin account with a password hash and protected Flask session.
- Store monitored identities, events, alerts, login attempts, reports, communities, posts, and audit actions in MySQL.
- Generate reproducible fictional records to populate the dashboard.
- Demonstrate explainable rule-based detection and risk bands from Low through Critical.
- Apply configurable timed blocks, manual unblock, suspension, and activation with audit records.
- Visualize activity, risk distribution, threat distribution, and entity relationships.

## Scope and safety boundary

This is a local college demo. There are no dark-web connections, crawlers, external feeds, real threat actors, real criminal services, weapons, drugs, illegal transaction examples, or network enforcement. Monitored identities are telemetry rows and cannot sign in. Temporary blocks only affect those simulated records; they do not block IP addresses, Windows accounts, firewalls, or network traffic. The only authenticated account is the Admin configured through `.env`.

## Key features

- Admin authentication with Werkzeug password hashing, secure session attributes, logout, CSRF validation, and login attempt tracking.
- Admin-only dashboard with eight counts, four local Chart.js visualizations, recent alerts/sign-ins, suspicious identities, active blocks, and audit trail.
- 24 monitored identities, 10 communities, 50 posts, 24 threat reports, 85 security logs, 60 login attempts, 20 alerts, and 14 audit records from a deterministic seed.
- Risk score bands: 0–29 Low, 30–59 Medium, 60–79 High, and 80–100 Critical.
- Configurable automatic temporary blocks, expiry restoration, manual unblock, force logout, suspend, and activate actions.
- Relationship graph with users, communities, posts, and threat reports.
- Fully local Chart.js/Three.js browser assets and reduced-motion/mobile behavior for the background scene.

## System architecture

```text
Admin browser
   | HTML / responsive CSS / JavaScript
   | local Chart.js + decorative Three.js background
   v
Flask routes and Jinja templates
   | session + CSRF + Admin authorization
   | validation + rule-based security service + audit log
   v
SQLAlchemy ORM / PyMySQL
   |
   v
MySQL 8.x · localhost:3306 · darktrace
```

`darktrace/config.py` loads environment settings; `extensions.py` initializes the ORM; `models.py` defines tables; `db.py` creates the configured database and the single Admin bootstrap; `seed.py` provides generated demo data; `security.py` classifies risk and applies temporary blocks; and `routes.py` implements the Admin-only workflows. `database/schema.sql` is the manual MySQL schema alternative.

## Data model

- `admin_accounts`: one configured Admin identity, password hash, active/suspended state, block timestamps, session version, and last login.
- `monitored_users`: fictional identities, risk score, risk level, active/suspended state, block timestamps, and last activity.
- `communities` and `community_posts`: simulated discussion sources and fictional post observations.
- `threat_reports`: ID, type, risk, workflow state, source type, detection time, description, related identity, and analyst status.
- `security_logs`, `security_alerts`, and `login_attempts`: detector output, triage state, timestamps, event detail, and documentation/private demo IPs.
- `admin_actions`: auditable administrative events and optional target identity.

Foreign keys and indexes are declared in the ORM and SQL schema. Queries use SQLAlchemy's bound parameters. The database initializer creates missing schema objects and does not drop existing tables.

## Authentication and access control

The Admin username/password are read from the ignored local `.env` file. The password is stored only as a Werkzeug password hash. Flask session cookies use `HttpOnly`, `SameSite=Lax`, configurable `Secure`, and an eight-hour lifetime. Only `admin_id=1` with a matching session version reaches protected routes. Failed Admin sign-ins are logged; the configured number of failures within the configured time window temporarily blocks Admin sign-in. No monitored identity has a login account, and no route can create another administrator.

## Detection and temporary-block workflow

Signals such as failed sign-ins, unusual frequency, rapid repeated actions, suspicious session patterns, and restricted-route attempts create timestamped security logs. Every event has a 0–100 score and risk band. A monitored identity crossing `RISK_THRESHOLD` is marked suspicious, receives a `blocked_at` and `blocked_until` value, has its session generation incremented, and triggers an Admin alert. On subsequent requests, expired blocks are cleared automatically and an unblock event is recorded. Admin manual block/unblock, suspend, activate, force logout, report updates, alert acknowledgements, and review actions are added to the audit log.

## Validation

`python -m unittest discover -s tests -v` uses isolated SQLite test databases to exercise the ORM independently from the configured MySQL demo. Tests cover single-admin login, protected routes, seed counts, password hashing, failed-login block, risk-threshold auto-block, manual unblock auditing, report actions, and friendly errors. A separate local setup check initializes and seeds the MySQL 8 database.

## Installation and demo

Use the PowerShell sequence in the root README: create/activate `.venv`, install `requirements.txt`, create `.env` from `.env.example` only when missing, run `python scripts/init_db.py --seed`, then start `python app.py`. The login view displays no Admin password or alternate account.

## Limitations and future work

The rule engine is intentionally transparent and may produce false positives. This development server is not intended for public deployment. A production system would need stronger secrets management, mature authentication controls, audit retention policy, threat-model review, and independent rule validation. Further coursework extensions could add export, filters, and testable detection-rule configuration.