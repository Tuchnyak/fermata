"""What the categories screen shows and does, without any Tk.

`add` answers with the message to show next to the form, already localized, or None.
"""

from timer.i18n import t
from timer.storage.categories import Category, CategoryRepository
from timer.validation import ValidationError

DEFAULT_COLOR = "#3b82f6"


class CategoriesViewModel:
    def __init__(self, category_repository: CategoryRepository):
        self._category_repository = category_repository

    def categories(self) -> list[Category]:
        return self._category_repository.list_active()

    def add(self, name: str, color: str) -> str | None:
        try:
            self._category_repository.create(name, color)
        except ValidationError as error:
            return t(error.key)
        return None
