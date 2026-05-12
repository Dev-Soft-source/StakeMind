import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

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
