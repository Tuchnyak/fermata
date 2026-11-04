import re
import sqlite3
from dataclasses import dataclass, replace

from fermata.storage.db import Db
from fermata.validation import ValidationError

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
        name = self._validate(name, color)
        category_id = self._db.insert(
            "INSERT INTO category (name, color) VALUES (:name, :color)",
            {"name": name, "color": color},
        )
        assert category_id is not None
        return Category(category_id, name, color, is_system=False, is_archived=False)

    def update(
        self, category_id: int, *, name: str | None = None, color: str | None = None
    ) -> Category:
        category = self._get_changeable(category_id)
        new_color = category.color if color is None else color
        new_name = self._validate(
            category.name if name is None else name, new_color, own_id=category_id
        )
        self._db.execute(
            "UPDATE category SET name = :name, color = :color WHERE id = :id",
            {"name": new_name, "color": new_color, "id": category_id},
        )
        return replace(category, name=new_name, color=new_color)

    def archive(self, category_id: int) -> None:
        if self._is_used_by_scenario(category_id):
            raise ValidationError("category.used_by_scenario")
        self._set_archived(category_id, True)

    def unarchive(self, category_id: int) -> None:
        self._set_archived(category_id, False)

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

    def _is_used_by_scenario(self, category_id: int) -> bool:
        return (
            self._db.query_one(
                "SELECT 1 AS used FROM scenario_row WHERE category_id = ? LIMIT 1",
                (category_id,),
                mapper=lambda row: row["used"],
            )
            is not None
        )

    def _get_changeable(self, category_id: int) -> Category:
        category = self.get_by_id(category_id)
        if category is None:
            raise LookupError(f"No category with id {category_id}")
        if category.is_system:
            raise ValidationError("category.system_readonly")
        return category

    def _set_archived(self, category_id: int, archived: bool) -> None:
        self._get_changeable(category_id)
        self._db.execute(
            "UPDATE category SET is_archived = ? WHERE id = ?", (int(archived), category_id)
        )

    def _validate(self, name: str, color: str, own_id: int | None = None) -> str:
        """Validate a name and a color together; return the trimmed name."""
        name = name.strip()
        if not name:
            raise ValidationError("category.name_empty")
        if not _COLOR.fullmatch(color):
            raise ValidationError("category.color_invalid")
        if self._name_is_taken(name, own_id):
            raise ValidationError("category.name_taken")
        return name

    def _name_is_taken(self, name: str, own_id: int | None) -> bool:
        # SQLite's NOCASE folds only ASCII, so names are compared here instead.
        others = self._db.query(
            "SELECT id, name FROM category",
            mapper=lambda row: (row["id"], row["name"]),
        )
        return any(
            existing_id != own_id and existing.casefold() == name.casefold()
            for existing_id, existing in others
        )
