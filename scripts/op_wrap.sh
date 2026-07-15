#!/usr/bin/env bash
# Wrapper script to run commands with 1Password injected environment variables
# Usage: ./scripts/op_wrap.sh <command>

if ! command -v op &> /dev/null; then
    echo "Error: 1Password CLI ('op') is not installed or not in PATH."
    exit 1
fi

ENV_FILE=".env"

if [ -f "$ENV_FILE" ]; then
    exec op run --env-file="$ENV_FILE" -- "$@"
else
    echo "Warning: $ENV_FILE not found. Running without 1Password injection."
    exec "$@"
fi
