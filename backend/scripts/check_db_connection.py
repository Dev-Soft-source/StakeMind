import asyncio
import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.core.config import get_settings


async def main() -> int:
    settings = get_settings()
    print(f"DATABASE_URL={settings.database_url}")

    try:
        import asyncpg
    except ImportError:
        print("asyncpg is not installed in this environment.")
        return 1

    url = settings.async_database_url().replace("postgresql+asyncpg://", "postgresql://", 1)
    try:
        connection = await asyncpg.connect(url)
    except Exception as exc:
        print(f"Connection failed: {exc}")
        print("If you use local PostgreSQL, run scripts/bootstrap-local-postgres.ps1 first.")
        return 1

    try:
        value = await connection.fetchval("SELECT current_user")
        print(f"Connected as {value}")
    finally:
        await connection.close()

    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
