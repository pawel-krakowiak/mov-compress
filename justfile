set shell := ["bash", "-uc"]

alias_name := "mc"
project_dir := justfile_directory()

# List the available recipes.
default:
    @just --list

# Run the app straight from the source tree.
run *files:
    uv run mov-compress {{ files }}

# Install dependencies into the local virtualenv.
install:
    uv sync

# Run the test suite.
test *args:
    uv run pytest {{ args }}

# Lint the code and check its formatting.
lint:
    uv run ruff check .
    uv run ruff format --check .

# Fix what ruff can fix, then format.
fmt:
    uv run ruff check --fix .
    uv run ruff format .

# Lint and test, the same checks CI runs.
check: lint test

# Remove caches and build artefacts.
clean:
    rm -rf .pytest_cache .ruff_cache dist build
    find . -name '__pycache__' -type d -prune -exec rm -rf {} +

# Install the app as a global uv tool, so `mov-compress` works anywhere.
install-tool:
    uv tool install --force {{ project_dir }}
    @echo "Installed. Run 'mov-compress' from any directory."

# Remove the global uv tool installation.
uninstall-tool:
    uv tool uninstall mov-compress

# Print the shell alias without touching any file, so you can copy it yourself.
alias-show:
    @echo 'alias {{ alias_name }}="uv run --project {{ project_dir }} mov-compress"'

# Report whether the alias is present in your shell startup file.
alias-status:
    #!/usr/bin/env bash
    set -euo pipefail
    rc="$(just --justfile '{{ justfile() }}' _rc-file)"
    if [[ ! -f "$rc" ]]; then
        echo "no shell startup file found at $rc"
        exit 0
    fi
    if grep -q "alias {{ alias_name }}=" "$rc"; then
        echo "alias '{{ alias_name }}' is defined in $rc:"
        grep -n "alias {{ alias_name }}=" "$rc"
    else
        echo "alias '{{ alias_name }}' is not defined in $rc"
    fi

# Add the alias to your shell startup file, verifying before and after.
alias-install:
    #!/usr/bin/env bash
    set -euo pipefail
    rc="$(just --justfile '{{ justfile() }}' _rc-file)"
    line="alias {{ alias_name }}=\"uv run --project {{ project_dir }} mov-compress\""

    if [[ -f "$rc" ]] && grep -qF "$line" "$rc"; then
        echo "alias '{{ alias_name }}' is already installed in $rc - nothing to do"
        exit 0
    fi
    if [[ -f "$rc" ]] && grep -q "alias {{ alias_name }}=" "$rc"; then
        echo "error: a different alias named '{{ alias_name }}' already exists in $rc:" >&2
        grep -n "alias {{ alias_name }}=" "$rc" >&2
        echo "Remove it first, or pick another name: just alias_name=myname alias-install" >&2
        exit 1
    fi
    if ! command -v uv >/dev/null; then
        echo "error: uv is not on PATH - install it first (https://docs.astral.sh/uv/)" >&2
        exit 1
    fi

    mkdir -p "$(dirname "$rc")"
    touch "$rc"
    cp "$rc" "$rc.mov-compress.bak"
    printf '\n# mov-compress\n%s\n' "$line" >> "$rc"

    if grep -qF "$line" "$rc"; then
        echo "added to $rc (backup: $rc.mov-compress.bak)"
        echo "Run 'source $rc' or open a new terminal, then use: {{ alias_name }}"
    else
        echo "error: failed to write the alias to $rc" >&2
        exit 1
    fi

# Remove the alias from your shell startup file.
alias-uninstall:
    #!/usr/bin/env bash
    set -euo pipefail
    rc="$(just --justfile '{{ justfile() }}' _rc-file)"
    if [[ ! -f "$rc" ]] || ! grep -q "alias {{ alias_name }}=" "$rc"; then
        echo "alias '{{ alias_name }}' is not in $rc - nothing to do"
        exit 0
    fi
    cp "$rc" "$rc.mov-compress.bak"
    grep -v -e "alias {{ alias_name }}=" -e '^# mov-compress$' "$rc" > "$rc.tmp"
    mv "$rc.tmp" "$rc"
    echo "removed from $rc (backup: $rc.mov-compress.bak)"

# Print the startup file of the current shell.
[private]
_rc-file:
    #!/usr/bin/env bash
    set -euo pipefail
    case "$(basename "${SHELL:-/bin/bash}")" in
        zsh)  echo "${ZDOTDIR:-$HOME}/.zshrc" ;;
        bash) [[ "$(uname)" == "Darwin" ]] && echo "$HOME/.bash_profile" || echo "$HOME/.bashrc" ;;
        fish) echo "$HOME/.config/fish/config.fish" ;;
        *)    echo "$HOME/.profile" ;;
    esac
