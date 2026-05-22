from motopay.config import get_settings


def get_migration_database_url() -> str:
    s = get_settings()
    mu = (s.database_migration_url or "").strip()
    if mu:
        return mu
    return s.database_url
