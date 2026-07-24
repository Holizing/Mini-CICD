import os


DEFAULT_CORS_ORIGINS = (
    "http://localhost:3000",
    "http://127.0.0.1:3000",
)


def get_cors_origins() -> list[str]:
    configured_origins = os.getenv("MINI_CICD_CORS_ORIGINS")
    if not configured_origins:
        return list(DEFAULT_CORS_ORIGINS)

    origins = [origin.strip() for origin in configured_origins.split(",") if origin.strip()]
    if not origins:
        raise RuntimeError("MINI_CICD_CORS_ORIGINS must contain at least one origin")
    return origins
