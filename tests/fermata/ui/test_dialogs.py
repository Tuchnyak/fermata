import pytest
from fermata import i18n
from fermata.ui import dialogs
from fermata.ui.dialogs import ask_yes_no


class Asked:
    """Stands in for `Messagebox.yesno`: remembers the call, answers what a test says."""

    def __init__(self, answer):
        self.answer = answer
        self.calls = []

    def __call__(self, **keywords):
        self.calls.append(keywords)
        return self.answer


@pytest.fixture
def ask(monkeypatch):
    def install(answer):
        asked = Asked(answer)
        monkeypatch.setattr(dialogs.Messagebox, "yesno", asked)
        return asked

    return install


def test_the_yes_button_means_yes(ask):
    ask(i18n.t("dialog.yes"))

    assert ask_yes_no(None, "Sure?", "Title") is True


def test_the_no_button_means_no(ask):
    ask(i18n.t("dialog.no"))

    assert ask_yes_no(None, "Sure?", "Title") is False


def test_closing_the_question_means_no(ask):
    ask(None)

    assert ask_yes_no(None, "Sure?", "Title") is False


def test_the_buttons_are_named_in_the_language_in_force_and_the_answer_is_read_in_it(ask):
    i18n.set_language("ru")
    asked = ask("Да")

    assert ask_yes_no(None, "Точно?", "Заголовок") is True
    keywords = asked.calls[0]
    assert keywords["buttons"] == ["Нет", "Да"]
    assert keywords["localize"] is False
    assert (keywords["message"], keywords["title"]) == ("Точно?", "Заголовок")


def test_the_english_answer_is_not_taken_for_yes_in_another_language(ask):
    i18n.set_language("ru")
    ask("Yes")

    assert ask_yes_no(None, "Точно?", "Заголовок") is False
