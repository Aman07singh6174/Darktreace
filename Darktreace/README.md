# DarkTrace

**DarkTrace – Simulated Dark-Web Threat Intelligence & Security Monitoring Platform** is a localhost-only college demonstration of defensive monitoring and analyst response. It uses fictional monitored identities, synthetic activity, and local MySQL data. It does not access the real dark web, external threat feeds, criminal services, or network enforcement controls.

## Requirements

- Windows 10/11
- Python 3.10+
- MySQL Server 8.x running locally on port `3306`
- The dashboard's Chart.js and Three.js builds are bundled locally; no CDN or internet connection is needed at runtime.

## Windows setup

Open PowerShell in `D:\Darktreace`:

```powershell
py -m venv .venv
Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
```

Open `.env` and set `MYSQL_HOST`, `MYSQL_PORT`, `MYSQL_USER`, `MYSQL_PASSWORD`, `MYSQL_DATABASE`, `ADMIN_USERNAME`, and `ADMIN_PASSWORD`. A blank `APP_SECRET_KEY` gets a cryptographically random key at startup; set a private stable key locally if you want sessions to survive server restarts. The included example uses the requested local MySQL defaults and root admin defaults. Do not commit `.env` or share its password. The login screen never displays account credentials.

Check that MySQL is running:

```powershell
Get-Service MySQL80
```

The initializer creates the configured database if it does not exist, creates ORM tables, hashes the configured Admin password, and can populate demo rows:

```powershell
python scripts/init_db.py --seed
```

The equivalent manual SQL setup is `database/schema.sql`, which creates the `darktrace` schema and all tables. The schema creation is non-destructive; it does not drop existing tables.

## Run and sign in

```powershell
python app.py
```

Open `http://127.0.0.1:5000`. Sign in with the single Admin username and password configured in the local `.env`. Keep the terminal open while demonstrating the app. Stop Flask with `Ctrl+C`.

To regenerate the fictional records after setup:

```powershell
python scripts/seed_demo_data.py
```

The generator is deterministic and idempotent. It creates 24 monitored identities, 10 communities, 50 posts, 24 reports, 85 security logs, 60 login attempts, 20 alerts, and 14 audit records. These monitored identities have no login credentials; the database has one Admin account only.

## Demo workflow

1. Sign in as Admin and review the eight dashboard counts, recent alerts, sign-in history, suspicious identities, temporary blocks, and audit actions.
2. Open **Monitored identities** to inspect risk, view activity, force a session-generation change, block/unblock, suspend, or activate a fictional identity.
3. In **Simulated communities**, add a fictional post for a monitored identity. Repeated activity and configured training phrases generate risk events and alerts.
4. Review the risk threshold response: crossing the configured threshold marks the identity suspicious, stores a block start/expiry time, invalidates its session generation, and creates an alert. Expired blocks are restored on the next request.
5. Add or update a fictional threat report; acknowledge its alerts and inspect linked user/community/post/report nodes in the relationship graph.

All activity and source IPs in generated records are synthetic. Documentation ranges (`192.0.2.0/24`, `198.51.100.0/24`, `203.0.113.0/24`) and private `10.10.0.0/16` examples are used.

## Detection rules

- Scores are bounded to 0–100: `0–29 Low`, `30–59 Medium`, `60–79 High`, `80–100 Critical`.
- Repeated failed Admin sign-ins, unusual login frequency, rapid repeated demo activity, suspicious sessions, and unauthenticated restricted-route attempts generate log events.
- A monitored identity crossing the `RISK_THRESHOLD` in `.env` is marked suspicious, automatically blocked for `TEMP_BLOCK_MINUTES`, and generates an Admin alert.
- Safe detector example: `Training credential exposure and mock access token exposure in a fictional lab.`
- `FAILED_LOGIN_LIMIT` and `FAILED_LOGIN_WINDOW_MINUTES` configure the temporary Admin login block.
- Blocks affect only local demo application records. No IP or network traffic is blocked.

## Tests

```powershell
python -m unittest discover -s tests -v
```

Tests use isolated SQLite databases as a test adapter; the running app uses the configured MySQL database.

## Troubleshooting

- **Can't connect to MySQL:** check `Get-Service MySQL80`, port `3306`, and the values in `.env`. Verify the configured MySQL account can create the `darktrace` database and tables.
- **Access denied:** set `MYSQL_USER` and `MYSQL_PASSWORD` to the local MySQL account that has schema privileges, then rerun `python scripts/init_db.py --seed`.
- **MySQL module/Flask import error:** activate `.venv` in the same PowerShell window and rerun `python -m pip install -r requirements.txt`.
- **Address already in use:** stop the other Flask process with `Ctrl+C`, or change the port in `app.py` and use that URL.
- **Blank charts:** confirm local files exist under `darktrace/static/vendor/` and reload the dashboard; the app does not fetch chart libraries from a CDN.
- **Admin lockout:** wait for `TEMP_BLOCK_MINUTES` to expire. Block expiry is stored in MySQL and checked automatically on requests.
- **Reset demo records:** back up anything needed, then remove only the demo rows from MySQL or use a fresh local demo schema. Do not drop a database containing unrelated records.
- **PowerShell activation blocked:** `Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned`, then activate `.venv` again.

## Architecture

```text
Browser: local HTML / CSS / JavaScript
  |-- local Chart.js dashboard + decorative Three.js network canvas
  |-- admin-only Flask routes, session checks, CSRF, validation
  |-- security rules, temporary blocks, and audit actions
  `-- SQLAlchemy ORM / PyMySQL --> MySQL: darktrace
```

`darktrace/config.py` reads `.env`; `models.py` defines ORM entities; `db.py` creates the schema and exactly one Admin; `seed.py` generates safe synthetic data; `security.py` applies risk and block rules; `routes.py` implements the admin control plane. The SQL schema is also provided in `database/schema.sql`.

## Eight-slide presentation outline

1. DarkTrace title and local-demo boundary
2. Problem statement, abstract, and objectives
3. System architecture and MySQL data flow
4. Database entities and synthetic seed volumes
5. Risk bands, detection rules, and temporary response
6. Admin dashboard, user controls, reports, and graph
7. Security safeguards and live demo workflow
8. Test evidence, limitations, and conclusion

The generated deck is `presentation/DarkTrace_Project_Presentation.pptx`; regenerate it with `python presentation/build_presentation.py`.

## Project structure

```text
Darktreace/
|-- app.py
|-- .env.example
|-- requirements.txt
|-- database/schema.sql
|-- darktrace/
|   |-- config.py, extensions.py, models.py
|   |-- db.py, seed.py, security.py, routes.py
|   |-- templates/
|   `-- static/css, static/js, static/vendor
|-- scripts/init_db.py, scripts/seed_demo_data.py
|-- tests/test_app.py
|-- docs/PROJECT_REPORT.md, docs/VIVA_QUESTIONS.md
`-- presentation/
```

## Safety and deployment boundary

This is a college demo, not a production SOC. It has one administrator, fictional monitored identities, rule-based scores, and local-only account controls. Use only the local development server, keep `.env` private, and never enter real incident or credential data.