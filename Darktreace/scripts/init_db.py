import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from darktrace import create_app
from darktrace.extensions import db
from darktrace.seed import seed_demo_data


def main():
    seed = "--seed" in sys.argv
    app = create_app()
    with app.app_context():
        db.create_all()
        if seed:
            inserted = seed_demo_data()
            print("Demo data generated." if inserted else "Demo data already exists; no rows were changed.")
        print(f"MySQL schema ready: {app.config['MYSQL_DATABASE']}@{app.config['MYSQL_HOST']}:{app.config['MYSQL_PORT']}")


if __name__ == "__main__":
    main()