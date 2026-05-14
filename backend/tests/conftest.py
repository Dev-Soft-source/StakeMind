import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

import pytest  # noqa: E402

from app.core.config import Settings  # noqa: E402
from app.main import create_app  # noqa: E402


@pytest.fixture
def test_settings() -> Settings:
    return Settings(
        environment="test",
        database_url="postgresql://stakemind:stakemind@localhost:5432/stakemind",
        redis_url="redis://localhost:6379/0",
    )


@pytest.fixture
def app(test_settings: Settings):
    return create_app(test_settings)
