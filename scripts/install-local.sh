#!/usr/bin/env bash
# Build the application as a single executable and install it for the current user:
#   ~/.local/bin/fermata                          the program
#   ~/.local/share/applications/fermata.desktop   its entry in the application menu
#
# The executable is a release: its data lives in ~/.local/share/fermata (apart from the data of
# a run from source) and its clock is the real one. It is built for this machine only.
# To remove it, delete the two files above (the data stays until you delete it too).
set -euo pipefail

cd "$(dirname "$0")/.."
root="$(pwd)"  # PyInstaller reads --add-data paths relative to the spec directory
bin_dir="${HOME}/.local/bin"
menu_dir="${HOME}/.local/share/applications"

uv sync --frozen
uv run pyinstaller \
    --noconfirm --clean --onefile --name fermata \
    --distpath dist --workpath build --specpath build \
    --paths src \
    --add-data "${root}/src/fermata/locales:fermata/locales" \
    --add-data "${root}/src/fermata/storage/migrations:fermata/storage/migrations" \
    --add-data "${root}/src/fermata/sounds:fermata/sounds" \
    --collect-all ttkbootstrap \
    --hidden-import PIL._tkinter_finder \
    src/fermata/__main__.py

install -Dm755 dist/fermata "${bin_dir}/fermata"
install -d "${menu_dir}"
uv run --frozen python -m fermata.desktop_entry "${bin_dir}/fermata" > "${menu_dir}/fermata.desktop"

echo "Installed ${bin_dir}/fermata and ${menu_dir}/fermata.desktop"
