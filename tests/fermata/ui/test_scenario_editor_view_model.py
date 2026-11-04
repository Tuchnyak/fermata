import pytest
from fermata.i18n import t
from fermata.scenarios import Scenario, ScenarioRow
from fermata.storage.categories import CategoryRepository
from fermata.storage.db import Db
from fermata.storage.migrate import MIGRATIONS_DIR, migrate
from fermata.storage.scenarios import ScenarioRepository
from fermata.storage.settings import Settings, SettingsRepository
from fermata.ui.progress import Circle, CircleState, LongBreakGap
from fermata.ui.scenario_editor_view_model import RowDraft, ScenarioEditorViewModel

NONE_CATEGORY_ID = 1


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
def settings_repository(db):
    return SettingsRepository(db)


@pytest.fixture
def work(category_repository):
    return category_repository.create("Work", "#112233")


@pytest.fixture
def personal(category_repository):
    return category_repository.create("Personal", "#445566")


@pytest.fixture
def editor(scenario_repository, category_repository, settings_repository):
    return ScenarioEditorViewModel(
        scenario_repository, category_repository, settings_repository
    )


@pytest.fixture
def example(scenario_repository, work, personal):
    """The example of the spec: (Work × 2, Personal × 1) × 2."""
    return scenario_repository.create(
        Scenario(
            "Work day",
            (ScenarioRow(work.id, 2), ScenarioRow(personal.id, 1)),
            repeat_count=2,
        )
    )


@pytest.fixture
def example_editor(
    scenario_repository, category_repository, settings_repository, example
):
    return ScenarioEditorViewModel(
        scenario_repository, category_repository, settings_repository, example
    )


def fill_example(editor, work, personal):
    """Make a new editor hold the example of the spec."""
    editor.set_name("Work day")
    editor.set_row_category(0, work.id)
    editor.set_row_count(0, "2")
    editor.add_row()
    editor.set_row_category(1, personal.id)
    editor.set_repeat_count("2")


def shape(items):
    return "".join("C" if isinstance(item, Circle) else "G" for item in items)


# --- a new scenario --------------------------------------------------------------


def test_a_new_editor_starts_with_an_empty_name_and_one_row_of_one_interval(editor):
    assert editor.name() == ""
    assert editor.rows() == [RowDraft(NONE_CATEGORY_ID, 1)]
    assert editor.repeat_count() == 1


def test_the_categories_to_choose_from_are_the_active_ones(editor, work, category_repository):
    category_repository.archive(work.id)

    assert [category.name for category in editor.categories()] == ["None"]


def test_a_new_editor_has_no_overrides(editor):
    assert editor.overrides() == {
        "work_minutes": None,
        "short_break_minutes": None,
        "long_break_minutes": None,
        "long_break_every": None,
    }


def test_the_global_settings_are_offered_for_the_overrides(editor, settings_repository):
    settings_repository.set("work_minutes", 40)

    assert editor.global_settings() == Settings(work_minutes=40)


# --- the rows --------------------------------------------------------------------


def test_a_new_row_has_one_interval_and_the_category_of_the_row_before(editor, work):
    editor.set_row_category(0, work.id)

    editor.add_row()

    assert editor.rows() == [RowDraft(work.id, 1), RowDraft(work.id, 1)]


def test_a_row_is_removed(editor, work, personal):
    fill_example(editor, work, personal)

    editor.remove_row(0)

    assert editor.rows() == [RowDraft(personal.id, 1)]


def test_the_last_row_can_be_removed(editor):
    editor.remove_row(0)

    assert editor.rows() == []


def test_a_row_moves_up_and_down(editor, work, personal):
    fill_example(editor, work, personal)

    editor.move_row_down(0)

    assert editor.rows() == [RowDraft(personal.id, 1), RowDraft(work.id, 2)]

    editor.move_row_up(1)

    assert editor.rows() == [RowDraft(work.id, 2), RowDraft(personal.id, 1)]


def test_the_first_row_cannot_move_up_nor_the_last_down(editor, work, personal):
    fill_example(editor, work, personal)

    editor.move_row_up(0)
    editor.move_row_down(1)

    assert editor.rows() == [RowDraft(work.id, 2), RowDraft(personal.id, 1)]


def test_a_count_is_read_from_text(editor):
    editor.set_row_count(0, " 7 ")

    assert editor.rows()[0].count == 7


@pytest.mark.parametrize("text", ["", "abc", "2.5", "-"])
def test_a_count_that_is_not_a_whole_number_is_remembered_as_such(editor, text):
    editor.set_row_count(0, text)

    assert editor.rows()[0].count is None


def test_the_repeat_count_is_read_from_text(editor):
    editor.set_repeat_count("3")

    assert editor.repeat_count() == 3


def test_a_repeat_count_that_is_not_a_whole_number_is_remembered_as_such(editor):
    editor.set_repeat_count("x")

    assert editor.repeat_count() is None


# --- the preview -----------------------------------------------------------------


def test_the_preview_shows_a_future_circle_per_work_interval_with_the_category_color(
    editor, work, personal
):
    fill_example(editor, work, personal)

    preview = editor.preview()

    assert preview.work_count == 6
    assert preview.items == [
        Circle(CircleState.FUTURE, "#112233"),
        Circle(CircleState.FUTURE, "#112233"),
        Circle(CircleState.FUTURE, "#445566"),
        Circle(CircleState.FUTURE, "#112233"),
        LongBreakGap(),
        Circle(CircleState.FUTURE, "#112233"),
        Circle(CircleState.FUTURE, "#445566"),
    ]


def test_the_preview_tells_the_count_and_the_total_duration(editor, work, personal):
    fill_example(editor, work, personal)

    assert editor.preview().text == "Work intervals: 6 · ~3h 05m"


def test_the_preview_follows_the_overrides(editor, work, personal):
    fill_example(editor, work, personal)

    editor.set_override("long_break_every", 2)
    editor.set_override("work_minutes", 10)
    preview = editor.preview()

    assert shape(preview.items) == "CCGCCGCC"
    # Six work intervals of 10 minutes; breaks after 1..5: 5 + 15 + 5 + 15 + 5 = 45.
    assert preview.text == "Work intervals: 6 · ~1h 45m"


def test_removing_an_override_returns_to_the_global_value(editor, work, personal):
    fill_example(editor, work, personal)
    before = editor.preview()

    editor.set_override("work_minutes", 10)
    editor.set_override("work_minutes", None)

    assert editor.preview() == before


def test_the_preview_follows_the_global_settings(editor, settings_repository, work, personal):
    fill_example(editor, work, personal)
    settings_repository.set("long_break_every", 3)

    assert shape(editor.preview().items) == "CCCGCCC"
    assert editor.preview().work_count == 6


def test_the_preview_is_empty_without_rows(editor):
    editor.remove_row(0)

    preview = editor.preview()

    assert (preview.items, preview.work_count, preview.text) == ([], 0, "")


@pytest.mark.parametrize(
    ("setter", "text"),
    [
        ("count", "x"),
        ("repeat", "x"),
        ("count", "21"),  # beyond the limit: no preview of an absurd number of circles
        ("repeat", "0"),
        ("count", "99999999"),
    ],
)
def test_the_preview_is_empty_while_a_number_is_not_valid(editor, setter, text):
    if setter == "count":
        editor.set_row_count(0, text)
    else:
        editor.set_repeat_count(text)

    preview = editor.preview()

    assert (preview.items, preview.work_count, preview.text) == ([], 0, "")


# --- saving ----------------------------------------------------------------------


def test_saving_a_new_scenario_stores_it(
    editor, scenario_repository, work, personal
):
    fill_example(editor, work, personal)

    message = editor.save()

    assert message is None
    (stored,) = scenario_repository.list_all()
    assert stored.id == editor.saved_scenario_id
    assert (stored.name, stored.rows, stored.repeat_count) == (
        "Work day",
        (ScenarioRow(work.id, 2), ScenarioRow(personal.id, 1)),
        2,
    )


def test_saving_stores_the_overrides(editor, scenario_repository, work):
    editor.set_name("Short")
    editor.set_row_category(0, work.id)
    editor.set_override("work_minutes", 10)
    editor.set_override("long_break_every", 3)

    editor.save()

    (stored,) = scenario_repository.list_all()
    assert (stored.work_minutes, stored.short_break_minutes, stored.long_break_every) == (
        10,
        None,
        3,
    )


def test_saving_twice_updates_the_same_scenario(editor, scenario_repository, work):
    editor.set_name("Day")
    editor.set_row_category(0, work.id)
    editor.save()

    editor.set_name("Day off")
    message = editor.save()

    assert message is None
    (stored,) = scenario_repository.list_all()
    assert (stored.id, stored.name) == (editor.saved_scenario_id, "Day off")


def test_nothing_is_saved_before_save(editor, scenario_repository, work):
    editor.set_name("Day")
    editor.set_row_category(0, work.id)

    assert scenario_repository.list_all() == []
    assert editor.saved_scenario_id is None


@pytest.mark.parametrize(
    ("prepare", "key"),
    [
        (lambda editor: editor.set_name("  "), "scenario.name_empty"),
        (lambda editor: editor.remove_row(0), "scenario.rows_empty"),
        (lambda editor: editor.set_row_count(0, "21"), "scenario.row_count_invalid"),
        (lambda editor: editor.set_repeat_count("0"), "scenario.repeat_invalid"),
        (lambda editor: editor.set_row_count(0, "x"), "scenario.number_invalid"),
        (lambda editor: editor.set_repeat_count("x"), "scenario.number_invalid"),
        (lambda editor: editor.set_override("work_minutes", 0), "setting.work_minutes_invalid"),
    ],
)
def test_a_rejected_scenario_answers_with_the_message(editor, prepare, key):
    editor.set_name("Day")
    prepare(editor)

    assert editor.save() == t(key)
    assert editor.saved_scenario_id is None


def test_a_name_that_is_taken_is_rejected(
    editor, scenario_repository, work
):
    scenario_repository.create(Scenario("Day", (ScenarioRow(work.id, 1),)))
    editor.set_name("day")

    assert editor.save() == t("scenario.name_taken")


# --- editing an existing scenario ---------------------------------------------------


def test_the_editor_of_an_existing_scenario_starts_with_its_values(
    example_editor, work, personal
):
    assert example_editor.name() == "Work day"
    assert example_editor.rows() == [RowDraft(work.id, 2), RowDraft(personal.id, 1)]
    assert example_editor.repeat_count() == 2
    assert example_editor.saved_scenario_id is None  # nothing is saved yet


def test_the_editor_of_an_existing_scenario_shows_its_overrides(
    scenario_repository, category_repository, settings_repository, work
):
    scenario = scenario_repository.create(
        Scenario("Short", (ScenarioRow(work.id, 1),), work_minutes=10)
    )

    editor = ScenarioEditorViewModel(
        scenario_repository, category_repository, settings_repository, scenario
    )

    assert editor.overrides()["work_minutes"] == 10
    assert editor.overrides()["short_break_minutes"] is None


def test_saving_an_existing_scenario_updates_it(example_editor, scenario_repository, example):
    example_editor.set_name("Work day (new)")

    message = example_editor.save()

    assert message is None
    (stored,) = scenario_repository.list_all()
    assert (stored.id, stored.name) == (example.id, "Work day (new)")
    assert example_editor.saved_scenario_id == example.id


def test_the_scenario_keeps_its_name_when_saved_unchanged(example_editor):
    assert example_editor.save() is None
