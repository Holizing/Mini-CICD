import os
import secrets
from functools import lru_cache
from pathlib import Path


JWT_ALGORITHM = "HS256"
JWT_ISSUER = "mini-cicd"
JWT_AUDIENCE = "mini-cicd-web"
DEFAULT_ACCESS_TOKEN_EXPIRE_MINUTES = 60
MIN_JWT_SECRET_LENGTH = 32
REPOSITORY_ROOT = Path(__file__).resolve().parents[2]


def get_access_token_expire_minutes() -> int:
    raw_value = os.getenv(
        "MINI_CICD_ACCESS_TOKEN_EXPIRE_MINUTES",
        str(DEFAULT_ACCESS_TOKEN_EXPIRE_MINUTES),
    )

    try:
        value = int(raw_value)
    except ValueError as exc:
        raise RuntimeError("MINI_CICD_ACCESS_TOKEN_EXPIRE_MINUTES must be an integer") from exc

    if value < 5 or value > 1440:
        raise RuntimeError("Access token expiration must be between 5 and 1440 minutes")

    return value


def _jwt_secret_path() -> Path:
    configured_path = os.getenv("MINI_CICD_JWT_SECRET_FILE")
    if configured_path:
        return Path(configured_path).expanduser().resolve()
    return REPOSITORY_ROOT / ".mini-cicd-jwt-secret"


@lru_cache(maxsize=1)
def get_jwt_secret() -> str:
    environment_secret = os.getenv("MINI_CICD_JWT_SECRET")
    if environment_secret:
        if len(environment_secret) < MIN_JWT_SECRET_LENGTH:
            raise RuntimeError("MINI_CICD_JWT_SECRET must contain at least 32 characters")
        return environment_secret

    secret_path = _jwt_secret_path()
    if secret_path.exists():
        secret = secret_path.read_text(encoding="utf-8").strip()
        if len(secret) < MIN_JWT_SECRET_LENGTH:
            raise RuntimeError(f"JWT secret file is invalid: {secret_path}")
        return secret

    secret_path.parent.mkdir(parents=True, exist_ok=True)
    generated_secret = secrets.token_urlsafe(64)

    try:
        with secret_path.open("x", encoding="utf-8") as secret_file:
            secret_file.write(generated_secret)
        try:
            secret_path.chmod(0o600)
        except OSError:
            pass
        return generated_secret
    except FileExistsError:
        secret = secret_path.read_text(encoding="utf-8").strip()
        if len(secret) < MIN_JWT_SECRET_LENGTH:
            raise RuntimeError(f"JWT secret file is invalid: {secret_path}")
        return secret
