#!/bin/sh
# Read-only: no installs and no access to account configuration.
set -u
probe() {
    label=$1; shift
    printf '\n%s\n' "$label"
    if command -v "$1" >/dev/null 2>&1; then
        command -v "$1"
        "$@" 2>&1 || printf 'UNAVAILABLE (command failed)\n'
    else
        printf 'MISSING\n'
    fi
}
probe 'Python (CPython)' python3 --version
probe 'JavaScript (Node)' node --version
probe Go go version
probe 'Java runtime' java -version
probe 'Java compiler' javac -version
probe 'C++' c++ --version
probe Rust rustc --version
