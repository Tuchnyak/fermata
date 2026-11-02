#!/usr/bin/env bash
# Build the application as a single executable and install it for the current user:
#   ~/.local/bin/timer                          the program
#   ~/.local/share/applications/timer.desktop   its entry in the application menu
#
# The executable is a release: its data lives in ~/.local/share/timer (apart from the data of
# a run from source) and its clock is the real one. It is built for this machine only.
# To remove it, delete the two files above (the data stays until you delete it too).
set -euo pipefail

cd "$(dirname "$0")/.."
root="$(pwd)"  # PyInstaller reads --add-data paths relative to the spec directory
bin_dir="${HOME}/.local/bin"
menu_dir="${HOME}/.local/share/applications"

uv sync --frozen
uv run pyinstaller \
    --noconfirm --clean --onefile --name timer \
    --distpath dist --workpath build --specpath build \
    --paths src \
    --add-data "${root}/src/timer/locales:timer/locales" \
    --add-data "${root}/src/timer/storage/migrations:timer/storage/migrations" \
    --add-data "${root}/src/timer/sounds:timer/sounds" \
    --collect-all ttkbootstrap \
    --hidden-import PIL._tkinter_finder \
    src/timer/__main__.py

install -Dm755 dist/timer "${bin_dir}/timer"
install -d "${menu_dir}"
cat > "${menu_dir}/timer.desktop" <<DESKTOP
[Desktop Entry]
Type=Application
Name=Timer
Comment=Pomodoro timer
Exec=${bin_dir}/timer
Terminal=false
Categories=Utility;
DESKTOP

echo "Installed ${bin_dir}/timer and ${menu_dir}/timer.desktop"
