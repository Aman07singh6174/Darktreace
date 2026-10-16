import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from darktrace import create_app
from darktrace.seed import seed_demo_data


if __name__ == "__main__":
    app = create_app()
    with app.app_context():
        print("Fictional demo data generated." if seed_demo_data() else "Demo data already exists; no rows were changed.")