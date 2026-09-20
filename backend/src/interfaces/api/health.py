from src.infrastructure.db import check_database_connection


def health_check() -> dict[str, str]:
    db_ok = check_database_connection()

    return {
        "status": "ok" if db_ok else "degraded",
        "db": "ok" if db_ok else "fail",
    }