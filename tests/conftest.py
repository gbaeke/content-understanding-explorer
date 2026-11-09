import pytest
from fastapi.testclient import TestClient

from content_understanding.api.app import create_app
from content_understanding.config import Settings, settings_without_env_file


@pytest.fixture(autouse=True)
def isolate_from_env(monkeypatch):
    """No setting leaks in from the shell: tests build their Settings explicitly."""
    for name in Settings.model_fields:
        monkeypatch.delenv(name.upper(), raising=False)


@pytest.fixture
def settings() -> Settings:
    return settings_without_env_file()


@pytest.fixture
def client(settings):
    """The app on test settings; `with` runs its startup and shutdown."""
    with TestClient(create_app(settings)) as c:
        yield c
