from flask import Flask

from .config import build_config
from .db import init_db
from .extensions import db


def create_app(test_config=None):
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_mapping(build_config(test_config))
    db.init_app(app)
    from . import routes
    from . import models

    app.register_blueprint(routes.bp)
    app.jinja_env.globals["csrf_token"] = routes.csrf_token
    app.jinja_env.filters["pretty_time"] = routes.pretty_time

    with app.app_context():
        init_db(seed_demo=app.config.get("SEED_DEMO_ON_START", False))
    return app