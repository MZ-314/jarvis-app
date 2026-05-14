# backend/app/extensions.py

import os
import redis
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_jwt_extended import JWTManager
from flask_socketio import SocketIO
from flask_cors import CORS
from celery import Celery
from flask import Flask

db       = SQLAlchemy()
migrate  = Migrate()
jwt      = JWTManager()
socketio = SocketIO()
cors     = CORS()

# Standard redis-py client for rate limiter and general caching.
# Initialised lazily via init_redis() called from create_app().
redis_client: redis.Redis | None = None


def init_redis(app: Flask) -> None:
    global redis_client
    url = os.getenv("REDIS_URL")
    if url:
        redis_client = redis.Redis.from_url(url, decode_responses=True)
    else:
        app.logger.warning("REDIS_URL not set — rate limiter and caching disabled")


def celery_init_app(app: Flask) -> Celery:
    celery_app = Celery(app.name)
    celery_app.config_from_object(app.config["CELERY"])

    celery_app.conf.update(
        task_always_eager=False,
    )

    class FlaskTask(celery_app.Task):
        def __call__(self, *args, **kwargs):
            with app.app_context():
                return self.run(*args, **kwargs)

    celery_app.Task = FlaskTask
    celery_app.set_default()
    app.extensions["celery"] = celery_app
    return celery_app