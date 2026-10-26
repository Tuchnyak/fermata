import re
import sqlite3
from dataclasses import dataclass

from timer.storage.db import Db
from timer.validation import ValidationError

_COLOR = re.compile(r"#[0-9a-fA-F]{6}")


@dataclass(frozen=True)
class Category:
    id: int
    name: str
    color: str
    is_system: bool
    is_archived: bool


def _to_category(row: sqlite3.Row) -> Category:
    return Category(
        id=row["id"],
        name=row["name"],
        color=row["color"],
        is_system=bool(row["is_system"]),
        is_archived=bool(row["is_archived"]),
    )


class CategoryRepository:
    def __init__(self, db: Db):
        self._db = db

    def create(self, name: str, color: str) -> Category:
        name = name.strip()
        if not name:
            raise ValidationError("category.name_empty")
        if not _COLOR.fullmatch(color):
            raise ValidationError("category.color_invalid")
        if self._name_is_taken(name):
            raise ValidationError("category.name_taken")
        category_id = self._db.insert(
            "INSERT INTO category (name, color) VALUES (:name, :color)",
            {"name": name, "color": color},
        )
        assert category_id is not None
        return Category(category_id, name, color, is_system=False, is_archived=False)

    def get_by_id(self, category_id: int) -> Category | None:
        return self._db.query_one(
            "SELECT * FROM category WHERE id = ?", (category_id,), mapper=_to_category
        )

    def list_active(self) -> list[Category]:
        active = self._db.query(
            "SELECT * FROM category WHERE is_archived = 0", mapper=_to_category
        )
        system = [category for category in active if category.is_system]
        others = [category for category in active if not category.is_system]
        others.sort(key=lambda category: category.name.casefold())
        return system + others

    def _name_is_taken(self, name: str) -> bool:
        # SQLite's NOCASE folds only ASCII, so names are compared here instead.
        taken = self._db.query("SELECT name FROM category", mapper=lambda row: row["name"])
        return name.casefold() in {existing.casefold() for existing in taken}
