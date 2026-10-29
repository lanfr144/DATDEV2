"""
Book&Ride - Unit 04 - books service: configuration loader kept from Unit 03.
(Unit 04 runs the "prod" block; the API key moved to the gateway.)

    APP_ENV (dev by default) --> config/config.yaml [environments][APP_ENV]
                             --> + config/config.local.yaml [APP_ENV]   (optional)
                             --> + environment variables                (secrets, Docker)
                             --> Settings (Pydantic): types + required keys + prod rules

Course exercises covered:
    Ex. 2  load_config(): APP_ENV, default dev, ValueError if unknown
    Ex. 2  validation: required keys -> clear error at START-UP, not mid-request
    Ext.   Pydantic schema, local overrides, logging of the loaded env
    Ex. 3  `python -m app.settings` prints the 3 runs with masked secrets

Golden rules (Unit 03 workflow sheet):
    1. never commit real secrets  -> secrets are NOT in config.yaml
    2. never print a full DB_URL or key -> describe() masks them
    3. in production, secrets come from a vault or the CI -> environment variables
"""
import logging
import sys
import os
from functools import lru_cache
from pathlib import Path
from typing import Literal
from urllib.parse import quote_plus

import yaml
from pydantic import BaseModel, Field, ValidationError, model_validator

CONFIG_DIR = Path(os.getenv("CONFIG_DIR", Path(__file__).resolve().parents[1] / "config"))
ENVIRONMENTS = ("dev", "staging", "prod")
SECRETS = ("DB_PASSWORD", "MONGO_ROOT_PASSWORD")

logger = logging.getLogger("bookandride.settings")


class Settings(BaseModel):
    """Typed schema (course extension "Schema Validation with Pydantic")."""
    APP_ENV: Literal["dev", "staging", "prod"]
    APP_VERSION: str = "1.0.0"
    DEBUG: bool                                   # "true"/"false" strings -> bool
    LOG_LEVEL: Literal["DEBUG", "INFO", "WARNING", "ERROR"]
    # database: either a full DB_URL (tests, SQLite) or the parts
    DB_URL: str | None = None
    DB_HOST: str = Field(min_length=1)
    DB_PORT: int = Field(ge=1, le=65535)
    DB_NAME: str = Field(min_length=1)
    DB_USER: str = Field(min_length=1)
    DB_PASSWORD: str = Field(min_length=1)        # secret
    # logs (MongoDB, as in Units 01-02); empty MONGO_HOST = stdout only
    MONGO_HOST: str = ""
    MONGO_PORT: int = 27017
    MONGO_DB: str = "logs"
    MONGO_ROOT_USER: str = "admin"
    MONGO_ROOT_PASSWORD: str = ""                 # secret

    @model_validator(mode="after")
    def production_rules(self):
        """Rules that only make sense in prod: refuse to START rather than run unsafe."""
        if self.APP_ENV == "prod":
            if self.DEBUG:
                raise ValueError("DEBUG must be false in prod")
            if self.DB_URL and self.DB_URL.startswith("sqlite"):
                raise ValueError("SQLite is not allowed in prod")
        return self

    @property
    def database_url(self) -> str:
        if self.DB_URL:
            return self.DB_URL
        return (f"postgresql+psycopg://{quote_plus(self.DB_USER)}:{quote_plus(self.DB_PASSWORD)}"
                f"@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}")

    def describe(self) -> dict:
        """Configuration safe to print or to return on /config: secrets masked."""
        data = self.model_dump(exclude={"DB_URL"})
        for key in SECRETS:
            data[key] = mask(data[key])
        data["database_url"] = self.database_url.replace(quote_plus(self.DB_PASSWORD), "****") \
            if self.DB_PASSWORD else self.database_url
        return data


def mask(secret: str, visible: int = 4) -> str:
    """'s3cr3t-value' -> 's3cr... (masked)' (course: f"{cfg['API_KEY'][:4]}... (masked)")."""
    return f"{secret[:visible]}... (masked)" if secret else ""


def _read_yaml(path: Path) -> dict:
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def load_config(env: str | None = None) -> Settings:
    env = (env or os.getenv("APP_ENV", "dev")).strip().lower()          # default: dev
    data = _read_yaml(CONFIG_DIR / "config.yaml")
    configs = data.get("environments", data)
    if env not in configs:
        raise ValueError(f"Invalid APP_ENV: {env}. Choose from {list(configs)}")
    merged: dict = {"APP_ENV": env, **configs[env]}

    local = CONFIG_DIR / "config.local.yaml"                             # 2. local overrides
    if local.exists():
        merged.update(_read_yaml(local).get(env) or {})

    for key in Settings.model_fields:                                    # 1. environment wins
        if key != "APP_ENV" and os.getenv(key) is not None:
            merged[key] = os.environ[key]

    try:
        settings = Settings(**merged)
    except ValidationError as exc:
        # one line per problem, without echoing the (secret) input values
        problems = "; ".join(f"{'.'.join(map(str, e['loc'])) or 'config'}: {e['msg']}"
                             for e in exc.errors())
        raise ValueError(f"Invalid configuration for APP_ENV={env}: {problems}") from None
    logger.info("configuration loaded: environment=%s source=%s%s", env,
                (CONFIG_DIR / "config.yaml").name, " + config.local.yaml" if local.exists() else "")
    return settings


@lru_cache
def get_settings() -> Settings:
    """Loaded once per process (the configuration does not change at runtime)."""
    return load_config()


def print_run(settings: Settings) -> None:
    """Output of the course's app.py (exercise 3)."""
    print(f"=== APP_ENV={settings.APP_ENV} ===")
    print("[DEBUG MODE] Verbose logs enabled" if settings.DEBUG
          else "[PRODUCTION MODE] Logging minimal")
    print(f"Connecting to DB: {settings.describe()['database_url']}")
    print(f"Logs -> MongoDB {settings.MONGO_HOST or '(stdout only)'}/{settings.MONGO_DB}, level {settings.LOG_LEVEL}")


if __name__ == "__main__":
    # python -m app.settings            -> the environment of APP_ENV
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s", stream=sys.stdout)
    print_run(load_config())
