from backend.core.conf import settings
from backend.core.registrar import register_app


def test_frontend_origins_are_registered_for_cors() -> None:
    app = register_app()
    cors = next(
        middleware for middleware in app.user_middleware if middleware.cls.__name__ == "CORSMiddleware"
    )

    assert cors.kwargs["allow_origins"] == settings.CORS_ALLOWED_ORIGINS
    assert "http://127.0.0.1:4174" in cors.kwargs["allow_origins"]
