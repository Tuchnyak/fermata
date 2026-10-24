import re
from importlib.resources.abc import Traversable

from timer.storage.db import Db

_FILE_NAME_EXPRESSION = re.compile(r"^(\d{3})_.+\.sql$")


def migrate(db: Db, directory: Traversable) -> None:
    migrations = _find_migrations(directory)

    current_version = db.query_one("PRAGMA user_version", mapper=lambda row: int(row[0]))
    assert current_version is not None
    latest_version = migrations[-1][0] if migrations else 0

    if current_version > latest_version:
        raise RuntimeError(
            f"Database version {current_version} is newer than "
            f"the latest migration {latest_version}"
        )
    for version, file in migrations:
        if version > current_version:
            with db.transaction():
                db.execute_script(file.read_text(encoding="utf-8"))
                db.execute(f"PRAGMA user_version = {version}")


def _find_migrations(directory: Traversable) -> list[tuple[int, Traversable]]:
    """Return (version, file) pairs for the `NNN_*.sql` files, ordered by version."""
    migrations = []
    for file in directory.iterdir():
        match = _FILE_NAME_EXPRESSION.match(file.name)
        if match:
            migrations.append(
                (int(match.group(1)), file)
            )
    return sorted(migrations, key=lambda migration: migration[0])
