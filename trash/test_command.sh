#!/bin/bash
# Quick command tester for FQS backend
# Usage: ./test_command.sh "balance"
#        ./test_command.sh "orders list"

cd "$(dirname "$0")"

if [ -z "$1" ]; then
    echo "Usage: $0 \"<command>\""
    echo ""
    echo "Examples:"
    echo "  $0 \"balance\""
    echo "  $0 \"orders list\""
    echo "  $0 \"positions show\""
    echo "  $0 \"help\""
    echo ""
    echo "Options:"
    echo "  $0 --status        Show command system status"
    echo "  $0 --help-commands List available commands"
    exit 1
fi

python3 cmd/execute_command.py "$@"
