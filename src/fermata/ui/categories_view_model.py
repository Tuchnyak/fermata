"""What the categories screen shows and does, without any Tk.

Every change answers with the message to show next to the form, already localized, or None.
"""

from collections.abc import Callable
from functools import partial

from fermata.i18n import t
from fermata.storage.categories import Category, CategoryRepository
from fermata.validation import ValidationError

DEFAULT_COLOR = "#3b82f6"


class CategoriesViewModel:
    def __init__(self, category_repository: CategoryRepository):
        self._category_repository = category_repository

    def categories(self) -> list[Category]:
        return self._category_repository.list_active()

    def add(self, name: str, color: str) -> str | None:
        return self._apply(partial(self._category_repository.create, name, color))

    def rename(self, category_id: int, name: str) -> str | None:
        return self._apply(
            partial(self._category_repository.update, category_id, name=name)
        )

    def recolor(self, category_id: int, color: str) -> str | None:
        return self._apply(
            partial(self._category_repository.update, category_id, color=color)
        )

    def archive(self, category_id: int) -> str | None:
        return self._apply(partial(self._category_repository.archive, category_id))

    def _apply(self, change: Callable[[], object]) -> str | None:
        """Make the change; return the message to show if it is rejected, else None."""
        try:
            change()
        except ValidationError as error:
            return t(error.key)
        return None
