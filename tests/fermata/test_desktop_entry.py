from fermata.desktop_entry import desktop_entry

EXECUTABLE = "/home/someone/.local/bin/fermata"


def lines():
    return desktop_entry(EXECUTABLE).splitlines()


def test_the_entry_is_an_application_entry():
    assert lines()[0] == "[Desktop Entry]"
    assert "Type=Application" in lines()
    assert "Terminal=false" in lines()
    assert "Categories=Utility;" in lines()


def test_the_entry_has_the_icon_of_the_program():
    assert "Icon=fermata" in lines()


def test_the_entry_starts_the_installed_program():
    assert f"Exec={EXECUTABLE}" in lines()


def test_the_entry_carries_the_name_and_the_line_under_it():
    assert "Name=Fermata" in lines()
    assert "GenericName=Focus timer" in lines()
    assert "Comment=Focus timer with scenarios" in lines()


def test_the_line_under_the_name_comes_in_every_language_of_the_program():
    assert "Comment[ru]=Фокус-таймер со сценариями" in lines()
    assert "GenericName[ru]=Фокус-таймер" in lines()
    for locale in ("es", "pt_BR", "de", "zh_CN", "ja"):
        assert any(line.startswith(f"Comment[{locale}]=") for line in lines()), locale
        assert any(line.startswith(f"GenericName[{locale}]=") for line in lines()), locale


def test_the_name_is_not_translated():
    assert not any(line.startswith("Name[") for line in lines())


def test_the_entry_ends_with_a_new_line():
    assert desktop_entry(EXECUTABLE).endswith("\n")
