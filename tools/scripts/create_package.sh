#!/bin/sh

set -eu

cd "$(dirname "$0")/../.."

repo_dir="$PWD"
venv_dir="$repo_dir/venv"
wheel_dir="$repo_dir/wheels"

create_venv() {
  if [ ! -d "$venv_dir" ]; then
    ./tools/scripts/create_venv.sh
  fi
  # shellcheck disable=SC1090
  . "$venv_dir/bin/activate"
}

install_wheels() {
  if [ -d "$wheel_dir" ]; then
    echo "Clearing old wheels"
    rm -rf "$wheel_dir"
  fi
  echo "Installing wheels"
  pip wheel -r "$repo_dir/requirements.txt" --wheel-dir="$wheel_dir" --no-deps
}

create_package() {
  echo "Creating parser package"
  python -m build --sdist
}

main() {
  create_venv
  install_wheels
  create_package
}

main