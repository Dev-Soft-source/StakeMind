import pytest

from app.core.config import Settings
from app.main import create_app


@pytest.fixture
def test_settings() -> Settings:
    return Settings(
        environment="test",
        database_url="postgresql://postgres:Radu5443043gis.@localhost:5432/stakemind",
        redis_url="redis://localhost:6379/0",
    )


@pytest.fixture
def app(test_settings: Settings):
    return create_app(test_settings)
