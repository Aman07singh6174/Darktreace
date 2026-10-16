from werkzeug.security import check_password_hash, generate_password_hash
from flask import current_app
import pymysql

from .extensions import db
from .models import AdminAccount


def init_db(seed_demo=False):
    _ensure_mysql_database()
    db.create_all()
    admin = db.session.get(AdminAccount, 1)
    if admin is None:
        admin = AdminAccount(
            id=1,
            username=current_app.config["ADMIN_USERNAME"],
            password_hash=generate_password_hash(current_app.config["ADMIN_PASSWORD"]),
        )
        db.session.add(admin)
    else:
        admin.username = current_app.config["ADMIN_USERNAME"]
        if not check_password_hash(admin.password_hash, current_app.config["ADMIN_PASSWORD"]):
            admin.password_hash = generate_password_hash(current_app.config["ADMIN_PASSWORD"])
    db.session.commit()
    if seed_demo:
        from .seed import seed_demo_data

        seed_demo_data()


def _ensure_mysql_database():
    uri = str(current_app.config["SQLALCHEMY_DATABASE_URI"])
    if not uri.startswith("mysql+"):
        return
    name = current_app.config["MYSQL_DATABASE"]
    connection = pymysql.connect(
        host=current_app.config["MYSQL_HOST"],
        port=current_app.config["MYSQL_PORT"],
        user=current_app.config["MYSQL_USER"],
        password=current_app.config["MYSQL_PASSWORD"],
        charset="utf8mb4",
        connect_timeout=5,
        autocommit=True,
    )
    try:
        with connection.cursor() as cursor:
            cursor.execute(f"CREATE DATABASE IF NOT EXISTS `{name}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
    finally:
        connection.close()