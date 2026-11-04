import pytest
from fermata.i18n import t
from fermata.scenarios import Scenario, ScenarioEntity, ScenarioRow
from fermata.storage.categories import CategoryRepository
from fermata.storage.db import Db
from fermata.storage.migrate import MIGRATIONS_DIR, migrate
from fermata.storage.scenarios import ScenarioRepository
from fermata.validation import ValidationError


@pytest.fixture
def db():
    db = Db.open(":memory:")
    migrate(db, MIGRATIONS_DIR)
    return db


@pytest.fixture
def category_repository(db):
    return CategoryRepository(db)


@pytest.fixture
def scenario_repository(db):
    return ScenarioRepository(db)


@pytest.fixture
def work(category_repository):
    return category_repository.create("Work", "#112233")


@pytest.fixture
def personal(category_repository):
    return category_repository.create("Personal", "#445566")


@pytest.fixture
def example(work, personal):
    """The example of the spec: (Work × 2, Personal × 1) × 2."""
    return Scenario(
        name="Work day",
        rows=(ScenarioRow(work.id, 2), ScenarioRow(personal.id, 1)),
        repeat_count=2,
    )


def rejected_key(action) -> str:
    with pytest.raises(ValidationError) as error:
        action()
    return error.value.key


def stored_counts(db):
    return (
        db.query_one("SELECT COUNT(*) AS n FROM scenario", mapper=lambda r: r["n"]),
        db.query_one("SELECT COUNT(*) AS n FROM scenario_row", mapper=lambda r: r["n"]),
    )


# --- create and read -----------------------------------------------------------


def test_create_returns_the_stored_scenario(scenario_repository, example):
    scenario = scenario_repository.create(example)

    assert isinstance(scenario, ScenarioEntity)
    assert (scenario.name, scenario.rows, scenario.repeat_count) == (
        example.name,
        example.rows,
        example.repeat_count,
    )


def test_a_created_scenario_can_be_read_back(scenario_repository, example):
    scenario = scenario_repository.create(example)

    assert scenario_repository.get_by_id(scenario.id) == scenario


def test_the_rows_keep_their_order(scenario_repository, work, personal):
    rows = (
        ScenarioRow(personal.id, 1),
        ScenarioRow(work.id, 3),
        ScenarioRow(personal.id, 2),
    )

    scenario = scenario_repository.create(Scenario("Mixed", rows))

    assert scenario_repository.get_by_id(scenario.id).rows == rows


def test_the_overrides_are_stored(scenario_repository, work):
    scenario = scenario_repository.create(
        Scenario(
            "Short",
            (ScenarioRow(work.id, 1),),
            work_minutes=10,
            short_break_minutes=2,
            long_break_minutes=7,
            long_break_every=3,
        )
    )

    stored = scenario_repository.get_by_id(scenario.id)

    assert (
        stored.work_minutes,
        stored.short_break_minutes,
        stored.long_break_minutes,
        stored.long_break_every,
    ) == (10, 2, 7, 3)


def test_missing_overrides_stay_empty(scenario_repository, example):
    scenario = scenario_repository.create(example)

    stored = scenario_repository.get_by_id(scenario.id)

    assert (
        stored.work_minutes,
        stored.short_break_minutes,
        stored.long_break_minutes,
        stored.long_break_every,
    ) == (None, None, None, None)


def test_an_unknown_id_is_not_found(scenario_repository):
    assert scenario_repository.get_by_id(999) is None


def test_the_list_is_empty_without_scenarios(scenario_repository):
    assert scenario_repository.list_all() == []


def test_the_list_is_ordered_by_name_ignoring_case(scenario_repository, work):
    for name in ["banana", "Cherry", "Apple"]:
        scenario_repository.create(Scenario(name, (ScenarioRow(work.id, 1),)))

    names = [scenario.name for scenario in scenario_repository.list_all()]

    assert names == ["Apple", "banana", "Cherry"]


# --- validation: the name ------------------------------------------------------


def test_the_name_is_trimmed(scenario_repository, work):
    scenario = scenario_repository.create(
        Scenario("  Work day \t", (ScenarioRow(work.id, 1),))
    )

    assert scenario.name == "Work day"


@pytest.mark.parametrize("name", ["", "   ", "\t\n"])
def test_an_empty_name_is_rejected(scenario_repository, work, name):
    scenario = Scenario(name, (ScenarioRow(work.id, 1),))

    assert rejected_key(lambda: scenario_repository.create(scenario)) == "scenario.name_empty"


@pytest.mark.parametrize(("first", "second"), [("Work day", "WORK DAY"), ("Работа", "работа")])
def test_a_name_is_unique_ignoring_case_also_beyond_ascii(
    scenario_repository, work, first, second
):
    scenario_repository.create(Scenario(first, (ScenarioRow(work.id, 1),)))

    duplicate = Scenario(second, (ScenarioRow(work.id, 1),))

    assert rejected_key(lambda: scenario_repository.create(duplicate)) == "scenario.name_taken"


def test_a_scenario_may_keep_its_own_name_on_update(scenario_repository, example):
    scenario = scenario_repository.create(example)

    updated = scenario_repository.update(scenario.id, example)

    assert updated.name == example.name


def test_an_update_cannot_take_the_name_of_another_scenario(
    scenario_repository, example, work
):
    scenario_repository.create(Scenario("Taken", (ScenarioRow(work.id, 1),)))
    scenario = scenario_repository.create(example)
    renamed = Scenario("TAKEN", example.rows)

    assert rejected_key(lambda: scenario_repository.update(scenario.id, renamed)) == (
        "scenario.name_taken"
    )


# --- validation: rows and repeat -----------------------------------------------


def test_a_scenario_needs_at_least_one_row(scenario_repository):
    assert rejected_key(lambda: scenario_repository.create(Scenario("Empty", ()))) == (
        "scenario.rows_empty"
    )


@pytest.mark.parametrize("count", [0, -1, 21])
def test_the_count_of_a_row_is_limited(scenario_repository, work, count):
    scenario = Scenario("Rows", (ScenarioRow(work.id, count),))

    assert rejected_key(lambda: scenario_repository.create(scenario)) == (
        "scenario.row_count_invalid"
    )


@pytest.mark.parametrize("count", [1, 20])
def test_the_limits_of_a_row_count_are_allowed(scenario_repository, work, count):
    scenario = Scenario(f"Rows {count}", (ScenarioRow(work.id, count),))

    assert scenario_repository.create(scenario).rows[0].count == count


@pytest.mark.parametrize("repeat_count", [0, -1, 21])
def test_the_repeat_count_is_limited(scenario_repository, work, repeat_count):
    scenario = Scenario("Repeat", (ScenarioRow(work.id, 1),), repeat_count)

    assert rejected_key(lambda: scenario_repository.create(scenario)) == (
        "scenario.repeat_invalid"
    )


@pytest.mark.parametrize("repeat_count", [1, 20])
def test_the_limits_of_the_repeat_count_are_allowed(
    scenario_repository, work, repeat_count
):
    scenario = Scenario(f"Repeat {repeat_count}", (ScenarioRow(work.id, 1),), repeat_count)

    assert scenario_repository.create(scenario).repeat_count == repeat_count


# --- validation: categories ----------------------------------------------------


def test_the_system_category_can_be_used(scenario_repository):
    scenario = Scenario("Anything", (ScenarioRow(1, 1),))

    assert scenario_repository.create(scenario).rows == (ScenarioRow(1, 1),)


def test_an_unknown_category_is_rejected(scenario_repository):
    scenario = Scenario("Ghost", (ScenarioRow(999, 1),))

    assert rejected_key(lambda: scenario_repository.create(scenario)) == (
        "scenario.category_unavailable"
    )


def test_an_archived_category_is_rejected(scenario_repository, category_repository, work):
    category_repository.archive(work.id)
    scenario = Scenario("Archived", (ScenarioRow(work.id, 1),))

    assert rejected_key(lambda: scenario_repository.create(scenario)) == (
        "scenario.category_unavailable"
    )


# --- validation: the overrides -------------------------------------------------


@pytest.mark.parametrize(
    ("field", "value", "key"),
    [
        ("work_minutes", 0, "setting.work_minutes_invalid"),
        ("work_minutes", 121, "setting.work_minutes_invalid"),
        ("short_break_minutes", 31, "setting.short_break_minutes_invalid"),
        ("long_break_minutes", 61, "setting.long_break_minutes_invalid"),
        ("long_break_every", 11, "setting.long_break_every_invalid"),
    ],
)
def test_an_override_has_the_range_of_its_global_setting(
    scenario_repository, work, field, value, key
):
    scenario = Scenario("Override", (ScenarioRow(work.id, 1),), **{field: value})

    assert rejected_key(lambda: scenario_repository.create(scenario)) == key


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("work_minutes", 120),
        ("short_break_minutes", 1),
        ("long_break_minutes", 60),
        ("long_break_every", 10),
    ],
)
def test_the_limits_of_an_override_are_allowed(scenario_repository, work, field, value):
    scenario = Scenario("Override", (ScenarioRow(work.id, 1),), **{field: value})

    assert getattr(scenario_repository.create(scenario), field) == value


def test_a_rejected_scenario_stores_nothing(scenario_repository, db, work):
    scenario = Scenario("Half", (ScenarioRow(work.id, 1), ScenarioRow(999, 1)))

    rejected_key(lambda: scenario_repository.create(scenario))

    assert stored_counts(db) == (0, 0)


# --- update --------------------------------------------------------------------


def test_update_replaces_the_fields_and_the_rows(
    scenario_repository, example, work, personal
):
    scenario = scenario_repository.create(example)
    changed = Scenario(
        "Evening",
        (ScenarioRow(personal.id, 3),),
        repeat_count=1,
        work_minutes=15,
    )

    updated = scenario_repository.update(scenario.id, changed)

    assert updated == ScenarioEntity(
        id=scenario.id,
        name="Evening",
        rows=(ScenarioRow(personal.id, 3),),
        repeat_count=1,
        work_minutes=15,
    )
    assert scenario_repository.get_by_id(scenario.id) == updated


def test_update_can_remove_an_override(scenario_repository, work):
    scenario = scenario_repository.create(
        Scenario("Short", (ScenarioRow(work.id, 1),), work_minutes=10)
    )

    scenario_repository.update(scenario.id, Scenario("Short", (ScenarioRow(work.id, 1),)))

    assert scenario_repository.get_by_id(scenario.id).work_minutes is None


def test_a_rejected_update_changes_nothing(scenario_repository, example):
    scenario = scenario_repository.create(example)
    broken = Scenario("Broken", (ScenarioRow(999, 1),))

    rejected_key(lambda: scenario_repository.update(scenario.id, broken))

    assert scenario_repository.get_by_id(scenario.id) == scenario


def test_updating_an_unknown_scenario_fails(scenario_repository, example):
    with pytest.raises(LookupError):
        scenario_repository.update(999, example)


# --- delete --------------------------------------------------------------------


def test_delete_removes_the_scenario_and_its_rows(scenario_repository, db, example):
    scenario = scenario_repository.create(example)

    scenario_repository.delete(scenario.id)

    assert scenario_repository.get_by_id(scenario.id) is None
    assert stored_counts(db) == (0, 0)


def test_delete_leaves_other_scenarios_alone(scenario_repository, example, work):
    scenario = scenario_repository.create(example)
    other = scenario_repository.create(Scenario("Other", (ScenarioRow(work.id, 1),)))

    scenario_repository.delete(scenario.id)

    assert scenario_repository.list_all() == [other]


def test_deleting_an_unknown_scenario_fails(scenario_repository):
    with pytest.raises(LookupError):
        scenario_repository.delete(999)


# --- archiving a category ------------------------------------------------------


def test_a_category_used_by_a_scenario_cannot_be_archived(
    scenario_repository, category_repository, example, work
):
    scenario_repository.create(example)

    assert rejected_key(lambda: category_repository.archive(work.id)) == (
        "category.used_by_scenario"
    )
    assert work in category_repository.list_active()


def test_a_category_can_be_archived_once_no_scenario_uses_it(
    scenario_repository, category_repository, example, work, personal
):
    scenario = scenario_repository.create(example)
    scenario_repository.update(scenario.id, Scenario("Work day", (ScenarioRow(personal.id, 1),)))

    category_repository.archive(work.id)

    assert work not in category_repository.list_active()


def test_a_category_can_be_archived_after_its_scenario_is_deleted(
    scenario_repository, category_repository, example, work
):
    scenario_repository.delete(scenario_repository.create(example).id)

    category_repository.archive(work.id)

    assert work not in category_repository.list_active()


# --- the messages --------------------------------------------------------------


@pytest.mark.parametrize(
    "key",
    [
        "scenario.name_empty",
        "scenario.name_taken",
        "scenario.rows_empty",
        "scenario.row_count_invalid",
        "scenario.repeat_invalid",
        "scenario.category_unavailable",
        "category.used_by_scenario",
    ],
)
def test_the_messages_exist_in_the_catalog(key):
    assert t(key)
