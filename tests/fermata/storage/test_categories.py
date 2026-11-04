import pytest
from fermata.i18n import t
from fermata.storage.categories import Category, CategoryRepository
from fermata.storage.db import Db
from fermata.storage.migrate import MIGRATIONS_DIR, migrate
from fermata.validation import ValidationError


@pytest.fixture
def db():
    db = Db.open(":memory:")
    migrate(db, MIGRATIONS_DIR)
    return db


@pytest.fixture
def category_repository(db):
    return CategoryRepository(db)


def names(category_repository):
    return [category.name for category in category_repository.list_active()]


# --- create ------------------------------------------------------------------


def test_create_returns_the_new_category(category_repository):
    category = category_repository.create("Work", "#112233")

    assert category == Category(
        id=category.id, name="Work", color="#112233", is_system=False, is_archived=False
    )
    assert category.id != 1  # 1 is the system category `None`


def test_created_category_can_be_read_back(category_repository):
    category = category_repository.create("Work", "#112233")

    assert category_repository.get_by_id(category.id) == category


def test_name_is_trimmed(category_repository):
    assert category_repository.create("  Work \t", "#112233").name == "Work"


@pytest.mark.parametrize("name", ["", "   ", "\t\n"])
def test_empty_name_is_rejected(category_repository, name):
    with pytest.raises(ValidationError) as error:
        category_repository.create(name, "#112233")

    assert error.value.key == "category.name_empty"


@pytest.mark.parametrize(
    "color", ["red", "", "#fff", "#12345", "#1234567", "112233", "#gg0000", "#11223 "]
)
def test_color_must_look_like_rrggbb(category_repository, color):
    with pytest.raises(ValidationError) as error:
        category_repository.create("Work", color)

    assert error.value.key == "category.color_invalid"


@pytest.mark.parametrize("color", ["#000000", "#aabbcc", "#AABBCC", "#1A2b3C"])
def test_hex_digits_of_either_case_are_accepted(category_repository, color):
    assert category_repository.create("Work", color).color == color


@pytest.mark.parametrize(
    ("first", "second"),
    [
        ("Work", "Work"),
        ("Work", "work"),
        ("Work", "  WORK  "),
        ("Работа", "РАБОТА"),  # SQLite's NOCASE would miss this one
        ("Straße", "STRASSE"),
    ],
)
def test_name_must_be_unique_ignoring_case(category_repository, first, second):
    category_repository.create(first, "#112233")

    with pytest.raises(ValidationError) as error:
        category_repository.create(second, "#445566")

    assert error.value.key == "category.name_taken"


@pytest.mark.parametrize("name", ["None", "none", "nOnE"])
def test_name_of_the_system_category_is_taken(category_repository, name):
    with pytest.raises(ValidationError) as error:
        category_repository.create(name, "#112233")

    assert error.value.key == "category.name_taken"


def test_rejected_category_is_not_stored(category_repository):
    with pytest.raises(ValidationError):
        category_repository.create("Work", "red")

    assert names(category_repository) == ["None"]


@pytest.mark.parametrize(
    "key",
    [
        "category.name_empty",
        "category.name_taken",
        "category.color_invalid",
        "category.system_readonly",
    ],
)
def test_error_messages_exist_in_the_catalog(key):
    assert t(key)


# --- get_by_id ---------------------------------------------------------------


def test_get_by_id_returns_the_system_category(category_repository):
    category = category_repository.get_by_id(1)

    assert category.name == "None"
    assert category.is_system is True
    assert category.is_archived is False


def test_get_by_id_returns_an_archived_category_too(db, category_repository):
    category = category_repository.create("Work", "#112233")
    db.execute("UPDATE category SET is_archived = 1 WHERE id = ?", (category.id,))

    assert category_repository.get_by_id(category.id).is_archived is True


def test_get_by_id_returns_none_for_an_unknown_id(category_repository):
    assert category_repository.get_by_id(999) is None


# --- list_active -------------------------------------------------------------


def test_list_contains_only_the_system_category_at_first(category_repository):
    assert names(category_repository) == ["None"]


def test_none_comes_first_then_categories_by_name_ignoring_case(category_repository):
    category_repository.create("banana", "#112233")
    category_repository.create("Apple", "#112233")
    category_repository.create("cherry", "#112233")

    assert names(category_repository) == ["None", "Apple", "banana", "cherry"]


def test_names_are_ordered_by_case_folded_text_for_any_alphabet(category_repository):
    category_repository.create("бета", "#112233")
    category_repository.create("Альфа", "#112233")

    assert names(category_repository) == ["None", "Альфа", "бета"]


def test_archived_categories_are_not_listed(db, category_repository):
    work = category_repository.create("Work", "#112233")
    category_repository.create("Reading", "#445566")
    db.execute("UPDATE category SET is_archived = 1 WHERE id = ?", (work.id,))

    assert names(category_repository) == ["None", "Reading"]


# --- update ------------------------------------------------------------------


def test_update_changes_name_and_color_and_returns_the_category(category_repository):
    work = category_repository.create("Work", "#112233")

    updated = category_repository.update(work.id, name="Job", color="#445566")

    assert updated == Category(
        id=work.id, name="Job", color="#445566", is_system=False, is_archived=False
    )
    assert category_repository.get_by_id(work.id) == updated


def test_update_of_the_name_only_keeps_the_color(category_repository):
    work = category_repository.create("Work", "#112233")

    updated = category_repository.update(work.id, name="Job")

    assert (updated.name, updated.color) == ("Job", "#112233")


def test_update_of_the_color_only_keeps_the_name(category_repository):
    work = category_repository.create("Work", "#112233")

    updated = category_repository.update(work.id, color="#445566")

    assert (updated.name, updated.color) == ("Work", "#445566")


def test_updated_name_is_trimmed(category_repository):
    work = category_repository.create("Work", "#112233")

    assert category_repository.update(work.id, name="  Job \t").name == "Job"


def test_update_does_not_touch_other_categories(category_repository):
    work = category_repository.create("Work", "#112233")
    reading = category_repository.create("Reading", "#445566")

    category_repository.update(work.id, name="Job", color="#778899")

    assert category_repository.get_by_id(reading.id) == reading


@pytest.mark.parametrize("name", ["Work", "WORK", "work"])
def test_category_may_keep_its_own_name_or_change_only_its_case(
    category_repository, name
):
    work = category_repository.create("Work", "#112233")

    assert category_repository.update(work.id, name=name).name == name


@pytest.mark.parametrize("name", ["", "   "])
def test_update_rejects_an_empty_name(category_repository, name):
    work = category_repository.create("Work", "#112233")

    with pytest.raises(ValidationError) as error:
        category_repository.update(work.id, name=name)

    assert error.value.key == "category.name_empty"


@pytest.mark.parametrize("color", ["red", "#fff", "112233"])
def test_update_rejects_an_invalid_color(category_repository, color):
    work = category_repository.create("Work", "#112233")

    with pytest.raises(ValidationError) as error:
        category_repository.update(work.id, color=color)

    assert error.value.key == "category.color_invalid"


@pytest.mark.parametrize("name", ["Reading", "reading", "  READING ", "None"])
def test_update_rejects_a_name_taken_by_another_category(category_repository, name):
    category_repository.create("Reading", "#445566")
    work = category_repository.create("Work", "#112233")

    with pytest.raises(ValidationError) as error:
        category_repository.update(work.id, name=name)

    assert error.value.key == "category.name_taken"


def test_update_rejects_a_name_taken_by_an_archived_category(db, category_repository):
    reading = category_repository.create("Reading", "#445566")
    db.execute("UPDATE category SET is_archived = 1 WHERE id = ?", (reading.id,))
    work = category_repository.create("Work", "#112233")

    with pytest.raises(ValidationError) as error:
        category_repository.update(work.id, name="Reading")

    assert error.value.key == "category.name_taken"


@pytest.mark.parametrize(
    "changes", [{"name": " ", "color": "#445566"}, {"name": "Job", "color": "red"}]
)
def test_rejected_update_changes_nothing(category_repository, changes):
    work = category_repository.create("Work", "#112233")

    with pytest.raises(ValidationError):
        category_repository.update(work.id, **changes)

    assert category_repository.get_by_id(work.id) == work


@pytest.mark.parametrize("changes", [{"name": "Job"}, {"color": "#445566"}])
def test_system_category_cannot_be_updated(category_repository, changes):
    with pytest.raises(ValidationError) as error:
        category_repository.update(1, **changes)

    assert error.value.key == "category.system_readonly"
    assert category_repository.get_by_id(1).name == "None"
    assert category_repository.get_by_id(1).color != "#445566"


def test_update_of_an_unknown_id_raises_lookup_error(category_repository):
    with pytest.raises(LookupError):
        category_repository.update(999, name="Job")


# --- archive and unarchive ---------------------------------------------------


def test_archived_category_is_not_listed(category_repository):
    work = category_repository.create("Work", "#112233")
    category_repository.create("Reading", "#445566")

    category_repository.archive(work.id)

    assert names(category_repository) == ["None", "Reading"]


def test_archived_category_can_still_be_read_with_its_name_and_color(category_repository):
    work = category_repository.create("Work", "#112233")

    category_repository.archive(work.id)

    archived = category_repository.get_by_id(work.id)
    assert archived == Category(
        id=work.id, name="Work", color="#112233", is_system=False, is_archived=True
    )


def test_archived_name_stays_reserved(category_repository):
    work = category_repository.create("Work", "#112233")
    category_repository.archive(work.id)

    with pytest.raises(ValidationError) as error:
        category_repository.create("work", "#445566")

    assert error.value.key == "category.name_taken"


def test_unarchived_category_is_listed_again_in_its_place(category_repository):
    category_repository.create("Apple", "#112233")
    banana = category_repository.create("Banana", "#112233")
    category_repository.create("Cherry", "#112233")
    category_repository.archive(banana.id)

    category_repository.unarchive(banana.id)

    assert names(category_repository) == ["None", "Apple", "Banana", "Cherry"]
    assert category_repository.get_by_id(banana.id) == banana


def test_archive_does_not_touch_other_categories(category_repository):
    work = category_repository.create("Work", "#112233")
    reading = category_repository.create("Reading", "#445566")

    category_repository.archive(work.id)

    assert category_repository.get_by_id(reading.id) == reading


def test_archiving_twice_is_harmless(category_repository):
    work = category_repository.create("Work", "#112233")

    category_repository.archive(work.id)
    category_repository.archive(work.id)

    assert category_repository.get_by_id(work.id).is_archived is True


def test_unarchiving_an_active_category_is_harmless(category_repository):
    work = category_repository.create("Work", "#112233")

    category_repository.unarchive(work.id)

    assert category_repository.get_by_id(work.id) == work


@pytest.mark.parametrize("operation", ["archive", "unarchive"])
def test_system_category_cannot_be_archived_or_unarchived(category_repository, operation):
    with pytest.raises(ValidationError) as error:
        getattr(category_repository, operation)(1)

    assert error.value.key == "category.system_readonly"
    assert names(category_repository) == ["None"]


@pytest.mark.parametrize("operation", ["archive", "unarchive"])
def test_unknown_id_raises_lookup_error(category_repository, operation):
    with pytest.raises(LookupError):
        getattr(category_repository, operation)(999)
