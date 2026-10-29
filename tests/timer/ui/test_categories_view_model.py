import re

import pytest
from timer.i18n import t
from timer.storage.categories import CategoryRepository
from timer.storage.db import Db
from timer.storage.migrate import MIGRATIONS_DIR, migrate
from timer.ui.categories_view_model import DEFAULT_COLOR, CategoriesViewModel


@pytest.fixture
def db():
    db = Db.open(":memory:")
    migrate(db, MIGRATIONS_DIR)
    return db


@pytest.fixture
def category_repository(db):
    return CategoryRepository(db)


@pytest.fixture
def categories_view_model(category_repository):
    return CategoriesViewModel(category_repository)


def names(categories_view_model):
    return [category.name for category in categories_view_model.categories()]


def test_the_list_holds_the_system_category_at_first(categories_view_model):
    (category,) = categories_view_model.categories()

    assert (category.name, category.is_system) == ("None", True)


def test_an_added_category_is_listed_with_its_color(categories_view_model):
    message = categories_view_model.add("Work", "#112233")

    assert message is None
    assert names(categories_view_model) == ["None", "Work"]
    assert categories_view_model.categories()[1].color == "#112233"


def test_the_name_of_an_added_category_is_trimmed(categories_view_model):
    categories_view_model.add("  Work \t", "#112233")

    assert names(categories_view_model) == ["None", "Work"]


def test_archived_categories_are_not_listed(categories_view_model, category_repository):
    work = category_repository.create("Work", "#112233")
    category_repository.archive(work.id)

    assert names(categories_view_model) == ["None"]


@pytest.mark.parametrize(
    ("name", "color", "key"),
    [
        ("", "#112233", "category.name_empty"),
        ("   ", "#112233", "category.name_empty"),
        ("none", "#112233", "category.name_taken"),
        ("Work", "red", "category.color_invalid"),
    ],
)
def test_a_rejected_category_gives_the_message_and_is_not_listed(
    categories_view_model, name, color, key
):
    message = categories_view_model.add(name, color)

    assert message == t(key)
    assert names(categories_view_model) == ["None"]


def test_a_second_category_with_the_same_name_is_rejected(categories_view_model):
    categories_view_model.add("Work", "#112233")

    message = categories_view_model.add("work", "#445566")

    assert message == t("category.name_taken")
    assert names(categories_view_model) == ["None", "Work"]


def test_the_default_color_is_valid_and_can_be_used_as_it_is(categories_view_model):
    assert re.fullmatch(r"#[0-9a-fA-F]{6}", DEFAULT_COLOR)

    assert categories_view_model.add("Work", DEFAULT_COLOR) is None


@pytest.mark.parametrize(
    "key",
    [
        "categories.name",
        "categories.choose_color",
        "categories.add",
        "categories.color_dialog_title",
    ],
)
def test_the_strings_of_the_screen_exist_in_the_catalog(key):
    assert t(key)
