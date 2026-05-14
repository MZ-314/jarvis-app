# backend/app/__init__.py

import os
import sentry_sdk
from sentry_sdk.integrations.flask import FlaskIntegration
from flask import Flask
from .extensions import db, migrate, jwt, socketio, cors, celery_init_app, init_redis


def create_app(config_name: str = None) -> Flask:
    app = Flask(__name__)

    # ── Config ────────────────────────────────────────────────────────────────
    env = config_name or os.getenv("FLASK_ENV", "development")
    app.config["ENV"] = env
    app.config["SECRET_KEY"] = os.getenv("SECRET_KEY")
    app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv("DATABASE_URL")
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
        "pool_pre_ping": True,
        "pool_recycle": 300,
    }
    app.config["JWT_SECRET_KEY"] = os.getenv("SECRET_KEY")
    app.config["JWT_ACCESS_TOKEN_EXPIRES"] = 60 * 60 * 24        # 1 day
    app.config["JWT_REFRESH_TOKEN_EXPIRES"] = 60 * 60 * 24 * 30  # 30 days

    # Celery / Redis (requires standard redis:// URL, not Upstash REST)
    redis_url = os.getenv("REDIS_URL")
    app.config["CELERY"] = {
        "broker_url": redis_url,
        "result_backend": redis_url,
        "broker_use_ssl": redis_url.startswith("rediss://") if redis_url else False,
        "redis_backend_use_ssl": redis_url.startswith("rediss://") if redis_url else False,
        "task_serializer": "json",
        "result_serializer": "json",
        "accept_content": ["json"],
        "timezone": "UTC",
        "enable_utc": True,
    }

    # ── Sentry (before anything else so it catches init errors) ───────────────
    dsn = os.getenv("SENTRY_DSN_BACKEND")
    if dsn:
        sentry_sdk.init(
            dsn=dsn,
            integrations=[FlaskIntegration()],
            traces_sample_rate=0.2,
            environment=env,
        )

    # ── Extensions ────────────────────────────────────────────────────────────
    db.init_app(app)
    migrate.init_app(app, db)
    jwt.init_app(app)
    cors.init_app(app, resources={r"/api/*": {"origins": "*"}})
    init_redis(app)

    is_production = env == "production"
    socketio.init_app(
        app,
        cors_allowed_origins="*",
        async_mode="threading",
        message_queue=redis_url if is_production else None,
    )

    celery_init_app(app)

    # ── Blueprints ────────────────────────────────────────────────────────────
    from .blueprints.auth   import auth_bp
    from .blueprints.voice  import voice_bp
    from .blueprints.ai     import ai_bp
    from .blueprints.memory import memory_bp
    from .blueprints.tools  import tools_bp

    app.register_blueprint(auth_bp,   url_prefix="/api/auth")
    app.register_blueprint(voice_bp,  url_prefix="/api/voice")
    app.register_blueprint(ai_bp,     url_prefix="/api/ai")
    app.register_blueprint(memory_bp, url_prefix="/api/memory")
    app.register_blueprint(tools_bp,  url_prefix="/api/tools")

    # ── Health check ──────────────────────────────────────────────────────────
    @app.get("/health")
    def health():
        return {"status": "ok", "env": env}, 200
    
    from . import sockets  # noqa — registers socket event handlers

    # ── Global rate limiter ──────────────────────────────────────────────────
    from .middleware.rate_limiter import init_rate_limiter
    init_rate_limiter(app)

    return app