import os
from datetime import timedelta

from flask import Flask
from werkzeug.middleware.proxy_fix import ProxyFix


def create_app():
    app = Flask(__name__)
    secret = os.environ.get("SECRET_KEY")
    if not secret:
        raise RuntimeError("Falta la variable SECRET_KEY")
    app.config.update(
        SECRET_KEY=secret,
        PERMANENT_SESSION_LIFETIME=timedelta(hours=10),
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
        SESSION_COOKIE_SECURE=os.environ.get("COOKIE_SECURE", "1") == "1",
        APPSMITH_URL=os.environ.get("APPSMITH_URL", ""),
        APP_NAME=os.environ.get("APP_NAME", "SF-EMPRESARIAL"),
        SOPORTE_NOMBRE=os.environ.get("SOPORTE_NOMBRE", ""),
        SOPORTE_TEL=os.environ.get("SOPORTE_TEL", ""),
    )
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)

    from .routes import bp
    app.register_blueprint(bp)
    return app
