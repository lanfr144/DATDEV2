"""
DEVOP2 Unit 03 verification checklist, as automated tests:
    - no APP_ENV loads dev; staging / prod load their own block
    - each environment has a different DB URL; prod has DEBUG = False
    - an unknown environment raises ValueError
    - missing required keys are detected at start-up
    - secrets are masked; environment variables override the YAML;
      config.local.yaml overrides config.yaml (course extension)
"""
import pytest

from app import settings as s

SECRETS = {"DB_PASSWORD": "pw-123", "API_KEY": "prod-9f3a1c77", "MONGO_ROOT_PASSWORD": "m"}


@pytest.fixture
def clean_env(monkeypatch):
    """Start from the YAML only: remove what conftest.py put in the environment."""
    for key in ("APP_ENV", "DB_URL", "MONGO_HOST", "DEBUG", "DB_HOST"):
        monkeypatch.delenv(key, raising=False)
    for key, value in SECRETS.items():
        monkeypatch.setenv(key, value)
    return monkeypatch


def test_default_environment_is_dev(clean_env):
    cfg = s.load_config()
    assert cfg.APP_ENV == "dev" and cfg.DEBUG is True and cfg.LOG_LEVEL == "DEBUG"


def test_three_environments_three_databases(clean_env):
    urls = {env: s.load_config(env).database_url for env in s.ENVIRONMENTS}
    assert len(set(urls.values())) == 3
    assert "@staging-db:5432/staging_db" in urls["staging"]
    assert s.load_config("prod").DEBUG is False
    assert s.load_config("staging").DEBUG is True


def test_unknown_environment_raises_value_error(clean_env):
    with pytest.raises(ValueError, match="Invalid APP_ENV: qa"):
        s.load_config("qa")


def test_missing_secret_is_detected_at_start_up(clean_env):
    clean_env.delenv("DB_PASSWORD")
    with pytest.raises(ValueError, match="DB_PASSWORD"):
        s.load_config("staging")


def test_debug_string_is_normalised_to_bool(clean_env):
    clean_env.setenv("DEBUG", "false")              # env var = string
    assert s.load_config("dev").DEBUG is False


def test_prod_refuses_debug_and_dev_keys(clean_env):
    clean_env.setenv("DEBUG", "true")
    with pytest.raises(ValueError, match="DEBUG must be false in prod"):
        s.load_config("prod")
    clean_env.delenv("DEBUG")
    clean_env.setenv("API_KEY", "dev-12345678")
    with pytest.raises(ValueError, match="real API_KEY"):
        s.load_config("prod")


def test_environment_variable_overrides_yaml(clean_env):
    clean_env.setenv("DB_HOST", "db.internal")
    assert "@db.internal:" in s.load_config("prod").database_url


def test_local_override_file(clean_env, tmp_path):
    (tmp_path / "config.yaml").write_text((s.CONFIG_DIR / "config.yaml").read_text())
    (tmp_path / "config.local.yaml").write_text('dev:\n  DB_URL: "sqlite:///./mine.db"\n')
    clean_env.setattr(s, "CONFIG_DIR", tmp_path)
    assert s.load_config("dev").database_url == "sqlite:///./mine.db"
    assert s.load_config("staging").database_url.startswith("postgresql")   # other envs untouched


def test_secrets_are_masked(clean_env):
    described = s.load_config("prod").describe()
    assert described["API_KEY"] == "prod... (masked)"
    assert "pw-123" not in str(described) and "9f3a1c77" not in str(described)
    assert "prod_user:****@prod-db" in described["database_url"]
