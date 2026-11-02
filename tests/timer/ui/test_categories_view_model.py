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


def category_named(categories_view_model, name):
    for category in categories_view_model.categories():
        if category.name == name:
            return category
    raise AssertionError(f"No category named {name}")


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


# --- rename ------------------------------------------------------------------


def test_a_renamed_category_is_listed_under_its_new_name_in_its_new_place(
    categories_view_model,
):
    categories_view_model.add("Apple", "#112233")
    categories_view_model.add("Banana", "#445566")
    banana = category_named(categories_view_model, "Banana")

    message = categories_view_model.rename(banana.id, "Aardvark")

    assert message is None
    assert names(categories_view_model) == ["None", "Aardvark", "Apple"]
    assert category_named(categories_view_model, "Aardvark").color == "#445566"


def test_the_new_name_is_trimmed(categories_view_model):
    categories_view_model.add("Work", "#112233")
    work = category_named(categories_view_model, "Work")

    categories_view_model.rename(work.id, "  Job \t")

    assert names(categories_view_model) == ["None", "Job"]


def test_a_category_may_change_the_case_of_its_own_name(categories_view_model):
    categories_view_model.add("Work", "#112233")
    work = category_named(categories_view_model, "Work")

    message = categories_view_model.rename(work.id, "WORK")

    assert message is None
    assert names(categories_view_model) == ["None", "WORK"]


@pytest.mark.parametrize(
    ("new_name", "key"),
    [
        ("", "category.name_empty"),
        ("   ", "category.name_empty"),
        ("apple", "category.name_taken"),
        ("none", "category.name_taken"),
    ],
)
def test_a_rejected_new_name_gives_the_message_and_changes_nothing(
    categories_view_model, new_name, key
):
    categories_view_model.add("Apple", "#112233")
    categories_view_model.add("Banana", "#445566")
    banana = category_named(categories_view_model, "Banana")

    message = categories_view_model.rename(banana.id, new_name)

    assert message == t(key)
    assert names(categories_view_model) == ["None", "Apple", "Banana"]


# --- recolor -----------------------------------------------------------------


def test_a_recolored_category_is_listed_with_its_new_color(categories_view_model):
    categories_view_model.add("Work", "#112233")
    work = category_named(categories_view_model, "Work")

    message = categories_view_model.recolor(work.id, "#aabbcc")

    assert message is None
    assert category_named(categories_view_model, "Work").color == "#aabbcc"


def test_a_rejected_color_gives_the_message_and_changes_nothing(categories_view_model):
    categories_view_model.add("Work", "#112233")
    work = category_named(categories_view_model, "Work")

    message = categories_view_model.recolor(work.id, "red")

    assert message == t("category.color_invalid")
    assert category_named(categories_view_model, "Work").color == "#112233"


# --- archive -----------------------------------------------------------------


def test_an_archived_category_is_no_longer_listed(categories_view_model):
    categories_view_model.add("Apple", "#112233")
    categories_view_model.add("Banana", "#445566")
    apple = category_named(categories_view_model, "Apple")

    message = categories_view_model.archive(apple.id)

    assert message is None
    assert names(categories_view_model) == ["None", "Banana"]


# --- the system category -----------------------------------------------------


@pytest.mark.parametrize(
    "change",
    [
        lambda view_model, category_id: view_model.rename(category_id, "Nothing"),
        lambda view_model, category_id: view_model.recolor(category_id, "#aabbcc"),
        lambda view_model, category_id: view_model.archive(category_id),
    ],
    ids=["rename", "recolor", "archive"],
)
def test_the_system_category_cannot_be_changed(categories_view_model, change):
    system = category_named(categories_view_model, "None")

    message = change(categories_view_model, system.id)

    assert message == t("category.system_readonly")
    assert categories_view_model.categories() == [system]


# --- strings -----------------------------------------------------------------


@pytest.mark.parametrize(
    "key",
    [
        "categories.rename",
        "categories.recolor",
        "categories.archive",
        "categories.rename_title",
        "categories.rename_prompt",
    ],
)
def test_the_strings_of_the_row_controls_exist_in_the_catalog(key):
    assert t(key)


def test_the_archive_question_names_the_category():
    assert "Work" in t("categories.archive_confirm", name="Work")
