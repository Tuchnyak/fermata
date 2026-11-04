"""The questions the application asks in a dialog."""

import tkinter

from fermata.i18n import t
from ttkbootstrap.dialogs import Messagebox


def ask_yes_no(parent: tkinter.Misc, message: str, title: str) -> bool:
    """Ask a question with Yes and No buttons named in the language in force.

    The dialog answers with the text of the button pressed, so the answer is read in that
    language; closing the question without an answer counts as No.
    """
    answer = Messagebox.yesno(
        message=message,
        title=title,
        parent=parent,
        buttons=[t("dialog.no"), t("dialog.yes")],
        localize=False,
    )
    return answer == t("dialog.yes")
